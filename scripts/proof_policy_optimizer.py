#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.7 — 证明策略元优化器（Dream-RSI 完整机制落地：P0 + P2 + P3）

对齐 arXiv 2609.14858 (Dream-RSI) 的核心机制——**优化探索策略本身**，而非单个候选解。
这是 v2.7.0（replay_strategies.py 只优化「变异策略选择」）缺失的核心层：

  P0  探索策略元优化   : 把「证明策略」（变异策略权重 / 并行度 / 放弃阈值 / 探索率）
                         编码为可执行对象，用 archive 历史重放反馈迭代改进策略参数本身。
  P2  replay objective  : V = 发现质量 − β1·执行成本 + β2·并行奖励（三项量化）。
  P3  单调性保证        : 候选策略集始终包含当前策略 π_t，选 max 保证不退化。

与 Stage 3.6（stage36_evolution.py）的关系：
  Stage 3.6 优化「证明代码」（Lean 的修复），用 5 个固定变异策略 ε-greedy 选择；
  Stage 3.7 优化「证明策略」（如何选择变异策略 + 并行几路 + 何时放弃）——是 Stage 3.6 的元层。
  两者正交：Stage 3.6 跑进化时，用 Stage 3.7 学到的策略参数来指导「选哪个变异动作」。

循环（Dream-RSI 三阶段）：
  select(当前策略 π_t) → 生成 M 个候选策略（参数扰动 + 可选 LLM 开发）
  → 重放评估（在 archive 历史决策点上重放每个候选策略）
  → replay objective 评分 → 选 max（含 π_t，单调）→ π_{t+1} 部署

用法：
  python proof_policy_optimizer.py \
      --archive /path/to/archive.jsonl \
      [--rounds 3] [--candidates 8] \
      [--beta1 0.1] [--beta2 0.5] \
      [--output /tmp/policy_opt/] \
      [--dry-run]        # 只用参数扰动，不调 LLM（离线自测）
      [--self-test]      # 构造假 archive 全流程自测
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_strategies import MUTATION_STRATEGIES, DEFECT_PRIORITY, defect_signature

STRATEGY_NAMES = list(MUTATION_STRATEGIES.keys())


# ── P0：可执行证明策略 ────────────────────────────────────────────
class ProofPolicy:
    """把「如何探索证明空间」编码为可执行、可评估、可改进的策略对象。

    对应 Dream-RSI 的「exploration policy 是可执行代码」——这里用结构化参数表示
    证明策略，使其可被重放评估与迭代改进（策略开发 agent 改这些参数）。

    参数字段：
      strategy_weights : dict[str, float]  各变异策略的偏好权重（softmax 后为选择概率）
      parallelism      : int              并行度 W（一次并行几路变异）
      abandon_threshold: float            放弃阈值（预期收益低于此值则跳过该决策点）
      epsilon          : float            探索率（ε-greedy，随机探索 vs 贪心利用）
    """

    def __init__(self, strategy_weights=None, parallelism=2, abandon_threshold=0.0, epsilon=0.15):
        self.strategy_weights = dict(strategy_weights or {n: 1.0 for n in STRATEGY_NAMES})
        self.parallelism = max(1, int(parallelism))
        self.abandon_threshold = max(0.0, float(abandon_threshold))
        self.epsilon = max(0.0, min(1.0, float(epsilon)))

    def to_dict(self) -> dict:
        return {
            "strategy_weights": self.strategy_weights,
            "parallelism": self.parallelism,
            "abandon_threshold": self.abandon_threshold,
            "epsilon": self.epsilon,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProofPolicy":
        return cls(
            strategy_weights=d.get("strategy_weights"),
            parallelism=d.get("parallelism", 2),
            abandon_threshold=d.get("abandon_threshold", 0.0),
            epsilon=d.get("epsilon", 0.15),
        )

    def mutate_params(self, rng: random.Random) -> "ProofPolicy":
        """参数扰动：生成一个邻近策略（无 LLM 的确定性探索）。"""
        d = self.to_dict()
        w = {k: max(0.1, v * rng.uniform(0.8, 1.2)) for k, v in d["strategy_weights"].items()}
        return ProofPolicy(
            strategy_weights=w,
            parallelism=max(1, d["parallelism"] + rng.choice([-1, 0, 1])),
            abandon_threshold=max(0.0, d["abandon_threshold"] + rng.uniform(-0.05, 0.05)),
            epsilon=max(0.0, min(1.0, d["epsilon"] + rng.uniform(-0.05, 0.05))),
        )


# ── P2：replay objective（质量 − β1·成本 + β2·并行）────────────────
class PolicyReplayEvaluator:
    """用 archive 历史在「决策点」上重放评估策略。

    每个历史 record（defects_before → mutation_strategy → outcome）是一个「决策点」。
    对策略 π，在每个决策点：
      1. 计算每个变异策略的选择得分 = 权重 × 历史成功率(同缺陷签名) × 针对性；
      2. 取 top-W（W = 并行度）作为「并行 W 路」的模拟；
      3. 若最高分 < 放弃阈值 → 跳过该决策点（不调用，省成本）；
      4. 每路的预期收益 = 该路历史成功率 × 历史平均 gain。

    replay objective（Dream-RSI 式三项）：
      V = Σ(预期收益) − β1·Σ(调用次数) + β2·(平均并行度)
    """

    def __init__(self, records: list[dict], beta1=0.1, beta2=0.5):
        self.records = records
        self.beta1 = beta1
        self.beta2 = beta2
        # 预统计：相同缺陷签名(condition)下，各策略的成功率与平均 gain
        self._cond_stats = self._build_cond_stats(records)

    def _build_cond_stats(self, records):
        stats = defaultdict(lambda: defaultdict(lambda: {"attempts": 0, "accepted": 0, "gains": []}))
        for r in records:
            strat = r.get("mutation_strategy", "unknown")
            if strat in ("seed", "unknown", None, ""):
                continue
            cond = defect_signature(r.get("defects_before") or {})
            s = stats[cond][strat]
            s["attempts"] += 1
            if r.get("accepted"):
                s["accepted"] += 1
            gain = r.get("gain", 0.0)
            if isinstance(gain, (int, float)):
                s["gains"].append(gain)
        return stats

    def _success_rate(self, cond, strat):
        s = self._cond_stats.get(cond, {}).get(strat)
        if not s or s["attempts"] == 0:
            return None
        return s["accepted"] / s["attempts"]

    def _avg_gain(self, cond, strat):
        s = self._cond_stats.get(cond, {}).get(strat)
        if not s or not s["gains"]:
            return 0.0
        return sum(s["gains"]) / len(s["gains"])

    def _decision_points(self) -> list[dict]:
        """历史决策点 = 去重后的唯一缺陷签名（condition）。

        多条相同 defects_before 的 record 聚合为同一个决策点（它们是对同一状态的多次历史尝试）。
        """
        conds: dict[str, dict] = {}
        for r in self.records:
            defects = r.get("defects_before") or {}
            active = [k for k in DEFECT_PRIORITY if defects.get(k, 0) and defects.get(k, 0) > 0]
            if active:
                cond = defect_signature(defects)
                conds.setdefault(cond, {"defects": defects, "condition": cond})
        return list(conds.values())

    def evaluate(self, policy: ProofPolicy) -> dict:
        """重放评估策略，返回 {score, quality, cost, parallel, n_decisions, skipped}。

        关键分离（对齐 Dream-RSI）：
          - 「选择」由策略权重决定（× 针对性软约束：不针对当前缺陷的策略权重 ×0.05），
            这是策略 π 的偏好，反映在「选哪些动作」。
          - 「结果」由历史真实结果决定（该动作在该 condition 下的历史成功率 × 平均 gain），
            这是 replay 的「确定性返回记录」，与策略偏好无关。

        replay objective（P2）：V = 质量 − β1·成本 + β2·平均并行度。
        """
        pts = self._decision_points()
        quality = 0.0
        cost = 0
        parallel = 0
        n_decisions = 0
        skipped = 0

        for pt in pts:
            cond = pt["condition"]
            active = [k for k in DEFECT_PRIORITY if pt["defects"].get(k, 0) > 0]

            # 选择得分 = 策略权重 × 针对性软约束
            choices = []
            for name in STRATEGY_NAMES:
                w = policy.strategy_weights.get(name, 1.0)
                targeted = sum(1 for t in MUTATION_STRATEGIES[name]["targets"] if t in active)
                sel = w * (0.05 if targeted == 0 else 1.0)
                choices.append((sel, name))

            # ε-greedy 探索
            if policy.epsilon > 0 and random.random() < policy.epsilon:
                random.shuffle(choices)
            choices.sort(key=lambda x: -x[0])

            # 取 top-W（并行 W 路）
            top = choices[:policy.parallelism]

            # 放弃阈值：最高选择得分低于阈值则跳过（不调用，省成本）
            if top[0][0] < policy.abandon_threshold:
                skipped += 1
                continue

            n_decisions += 1
            for _, name in top:
                cost += 1  # 每路 = 1 次 LLM 调用
                succ = self._success_rate(cond, name)
                eff = succ if succ is not None else 0.5
                quality += eff * self._avg_gain(cond, name)
            parallel += len(top)

        avg_parallel = parallel / max(1, n_decisions)
        V = quality - self.beta1 * cost + self.beta2 * avg_parallel

        return {
            "score": round(V, 4),
            "quality": round(quality, 2),
            "cost": cost,
            "parallel": parallel,
            "avg_parallel": round(avg_parallel, 3),
            "n_decisions": n_decisions,
            "skipped": skipped,
        }


# ── P0：策略开发（生成候选策略）───────────────────────────────────
def develop_candidates(current: ProofPolicy, n_candidates: int, rng: random.Random,
                       client=None, eval_report=None) -> list[ProofPolicy]:
    """生成 M 个候选策略 = 参数扰动（确定性）+ 可选 LLM 开发（读重放轨迹改进）。

    P3 单调性：候选集始终包含 current 本身（由主循环保证），确保选中策略不退化。
    """
    candidates = [current]  # 含当前策略（P3）
    for _ in range(n_candidates):
        candidates.append(current.mutate_params(rng))

    if client is not None and eval_report is not None:
        llm_policy = _llm_develop_policy(client, current, eval_report)
        if llm_policy is not None:
            candidates.append(llm_policy)
    return candidates


def _llm_develop_policy(client, current: ProofPolicy, eval_report: dict):
    """（可选）让 v4-flash 读当前策略 + 重放评估报告，产出改进的策略参数 JSON。

    对应 Dream-RSI 的「policy-development agent 检查重放轨迹，改写策略代码」。
    """
    try:
        prompt = f"""你是形式化证明探索策略的优化专家（Dream-RSI 风格策略元优化）。

当前证明策略（可调参数）：
{json.dumps(current.to_dict(), ensure_ascii=False, indent=2)}

该策略在历史 archive 上的重放评估报告（replay objective = 质量 − β1·成本 + β2·并行）：
{json.dumps(eval_report, ensure_ascii=False, indent=2)}

5 个可用的变异策略：{json.dumps({n: c["desc"] for n, c in MUTATION_STRATEGIES.items()}, ensure_ascii=False)}

请分析当前策略的弱点（哪些策略权重过高/过低、并行度是否合适、放弃阈值是否合理），
并输出一个**改进后的策略参数 JSON**，格式严格为：
{{"strategy_weights": {{"repair_dangling": 1.0, "axiomatize": 1.0, "tactic_complete": 1.0,
"lemma_decompose": 1.0, "deduplicate": 1.0}}, "parallelism": 2,
"abandon_threshold": 0.0, "epsilon": 0.15}}

只输出 JSON，不要任何解释文字或 markdown 围栏。"""
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=2048, timeout=120,
            extra_body={"thinking": {"type": "disabled"}},
        )
        content = (resp.choices[0].message.content or "").strip()
        content = content.strip("`").strip()
        content = content.removeprefix("json").strip()
        d = json.loads(content)
        return ProofPolicy.from_dict(d)
    except Exception:
        return None


# ── 主循环：P0 元优化 + P3 单调性 ─────────────────────────────────
def optimize(archive_path: Path, output_dir: Path, rounds: int, n_candidates: int,
             beta1: float, beta2: float, dry_run: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    records = []
    if archive_path.exists():
        for line in archive_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    evaluator = PolicyReplayEvaluator(records, beta1=beta1, beta2=beta2)
    rng = random.Random(42)  # 固定种子可复现

    current = ProofPolicy()
    policy_log = []

    client = None
    if not dry_run:
        key = _load_api_key()
        if key:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        else:
            print("[Stage3.7] ⚠️ 无 API key，降级为 dry-run（仅参数扰动）")

    for t in range(1, rounds + 1):
        base_eval = evaluator.evaluate(current)
        policy_log.append({"round": t - 1, "policy": current.to_dict(), **base_eval})
        print(f"\n[Round {t-1}] 当前策略 V={base_eval['score']} "
              f"(质量={base_eval['quality']} 成本={base_eval['cost']} "
              f"并行={base_eval['parallel']}/{base_eval['n_decisions']}决策 "
              f"跳过={base_eval['skipped']})")

        # 生成候选（含 current，P3）
        candidates = develop_candidates(current, n_candidates, rng, client, base_eval)

        # 重放评估所有候选
        evals = [(c, evaluator.evaluate(c)) for c in candidates]

        # 选最优（P3：候选集含 current，保证 V* ≥ V(current)）
        best_policy, best_eval = max(evals, key=lambda x: x[1]["score"])

        if best_eval["score"] <= base_eval["score"]:
            print(f"[Round {t}] 无改进（V={best_eval['score']} ≤ {base_eval['score']}），策略保持不变")
        else:
            print(f"[Round {t}] ✅ 策略改进：V {base_eval['score']} → {best_eval['score']}")
            current = best_policy

    # 最终评估 + 落盘
    final_eval = evaluator.evaluate(current)
    policy_log.append({"round": rounds, "policy": current.to_dict(), **final_eval})
    result = {
        "best_policy": current.to_dict(),
        "final_eval": final_eval,
        "rounds": rounds,
        "archive_records": len(records),
        "policy_log": policy_log,
        "monotone_guarantee": "V(best) >= V(initial) guaranteed (candidate set includes current policy)",
    }
    (output_dir / "policy_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _load_api_key() -> str:
    for env_path in [
        "/mnt/d/123321/CityHDGanalysis/Spatial_Reasoning_Agent/.env",
        str(Path.home() / ".hermes/.env"),
        "/mnt/c/123321/ML-Master/.env",
    ]:
        p = Path(env_path)
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    import os
    return os.environ.get("DEEPSEEK_API_KEY", "")


# ── 离线自测 ─────────────────────────────────────────────────────
def _self_test() -> int:
    """构造假 archive（同一 condition 多策略、成功率分化），验证 P0/P2/P3 机制。"""
    tmp = Path("/tmp/policy_opt_selftest.jsonl")
    records = [
        # condition "sorry>0"：axiomatize 成功率高(1.0)，lemma_decompose 半成功(0.5)
        {"mutation_strategy": "axiomatize", "accepted": True, "gain": 20, "defects_before": {"sorry": 2}},
        {"mutation_strategy": "axiomatize", "accepted": True, "gain": 15, "defects_before": {"sorry": 1}},
        {"mutation_strategy": "lemma_decompose", "accepted": True, "gain": 8, "defects_before": {"sorry": 1}},
        {"mutation_strategy": "lemma_decompose", "accepted": False, "gain": 0, "defects_before": {"sorry": 2}},
        # condition "trivial_or_true_stub>0"：tactic_complete 成功(1.0)，lemma_decompose 失败(0.0)
        {"mutation_strategy": "tactic_complete", "accepted": True, "gain": 12, "defects_before": {"trivial_or_true_stub": 2}},
        {"mutation_strategy": "lemma_decompose", "accepted": False, "gain": 0, "defects_before": {"trivial_or_true_stub": 1}},
    ]
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")

    recs = [json.loads(l) for l in tmp.read_text(encoding="utf-8").splitlines()]
    ev = PolicyReplayEvaluator(recs, beta1=0.1, beta2=0.5)

    # 验证点 1：W=1 vs W=2 的 quality/cost 差异（并行探索更广）
    p1 = ProofPolicy(parallelism=1, epsilon=0.0)
    p2 = ProofPolicy(parallelism=2, epsilon=0.0)
    r1 = ev.evaluate(p1)
    r2 = ev.evaluate(p2)
    print("=== W=1 vs W=2（均匀权重）===")
    print(f"W=1: {json.dumps(r1, ensure_ascii=False)}")
    print(f"W=2: {json.dumps(r2, ensure_ascii=False)}")
    assert r2["quality"] > r1["quality"], "W=2 并行探索更广，quality 应更高"
    assert r2["cost"] > r1["cost"], "W=2 成本应更高"

    # 验证点 2：β1 惩罚成本（增大 β1 → score 下降）
    ev_hi_beta1 = PolicyReplayEvaluator(recs, beta1=5.0, beta2=0.5)
    r_hi_b1 = ev_hi_beta1.evaluate(p2)
    print(f"\n=== β1=0.1 vs β1=5.0（同一策略 W=2）===")
    print(f"β1=0.1: score={r2['score']}   β1=5.0: score={r_hi_b1['score']}")
    assert r_hi_b1["score"] < r2["score"], "增大 β1（成本惩罚）应降低 score"

    # 验证点 3：β2 奖励并行（增大 β2 → 高并行策略 score 相对上升）
    ev_hi_beta2 = PolicyReplayEvaluator(recs, beta1=0.1, beta2=5.0)
    r2_hi_b2 = ev_hi_beta2.evaluate(p2)
    r1_hi_b2 = ev_hi_beta2.evaluate(p1)
    gap_default = r2["score"] - r1["score"]
    gap_hi_b2 = r2_hi_b2["score"] - r1_hi_b2["score"]
    print(f"\n=== β2 奖励并行 ===")
    print(f"β2=0.5: W=2-W=1 差距={gap_default:.3f}   β2=5.0: W=2-W=1 差距={gap_hi_b2:.3f}")
    assert gap_hi_b2 > gap_default, "增大 β2（并行奖励）应放大高并行策略的相对优势"

    # 验证点 4：策略权重影响选择（偏好 axiom/tactic 的策略应比偏好 repair_dangling 的高）
    good = ProofPolicy(strategy_weights={"repair_dangling": 0.1, "axiomatize": 5.0,
                                         "tactic_complete": 4.0, "lemma_decompose": 1.0,
                                         "deduplicate": 1.0}, parallelism=1, epsilon=0.0)
    bad = ProofPolicy(strategy_weights={"repair_dangling": 5.0, "axiomatize": 0.1,
                                        "tactic_complete": 0.1, "lemma_decompose": 1.0,
                                        "deduplicate": 1.0}, parallelism=1, epsilon=0.0)
    r_good = ev.evaluate(good)
    r_bad = ev.evaluate(bad)
    print(f"\n=== 权重影响选择（W=1）===")
    print(f"偏好 axiom/tactic: {json.dumps(r_good, ensure_ascii=False)}")
    print(f"偏好 repair_dangling: {json.dumps(r_bad, ensure_ascii=False)}")
    assert r_good["quality"] > r_bad["quality"], "偏好历史成功策略应获得更高 quality"

    # 验证点 5：全流程 optimize + 单调性（P3）
    print("\n=== 全流程 optimize（dry-run，3 轮，8 候选）===")
    res = optimize(tmp, Path("/tmp/policy_opt_selftest_out"), rounds=3, n_candidates=8,
                   beta1=0.1, beta2=0.5, dry_run=True)
    init_score = res["policy_log"][0]["score"]
    final_score = res["final_eval"]["score"]
    print(f"最优策略: {json.dumps(res['best_policy'], ensure_ascii=False)}")
    print(f"初始 V={init_score} → 最终 V={final_score}")
    assert final_score >= init_score, "P3 单调性保证失败"

    print("\n自测通过 ✓（P0 策略元优化 + P2 replay objective + P3 单调性全验证）")
    tmp.unlink()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 3.7 证明策略元优化器（Dream-RSI P0/P2/P3）")
    ap.add_argument("--archive", help="archive.jsonl 历史证据路径")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--candidates", type=int, default=8)
    ap.add_argument("--beta1", type=float, default=0.1)
    ap.add_argument("--beta2", type=float, default=0.5)
    ap.add_argument("--output", default="/tmp/policy_opt_output")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.archive:
        print("错误：需要 --archive（或 --self-test）", file=sys.stderr)
        return 2

    print("=" * 62)
    print("STAGE 3.7: Proof Policy Meta-Optimizer (Dream-RSI P0/P2/P3)")
    print("=" * 62)
    res = optimize(Path(args.archive), Path(args.output), args.rounds,
                   args.candidates, args.beta1, args.beta2, args.dry_run)
    print("\n" + "=" * 62)
    print(f"最优策略: {json.dumps(res['best_policy'], ensure_ascii=False)}")
    print(f"最终 replay score V = {res['final_eval']['score']}")
    print(f"策略日志: {args.output}/policy_result.json")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
