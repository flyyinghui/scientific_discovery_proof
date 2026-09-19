#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Refinement — Stage 3.6b DRS (v2.8.0, from RSIAgent)
=========================================================
RSIAgent (arXiv:2609.15364) broad-then-deep 的「deep」阶段：
Deep Recursive Self-exploration (DRS) —— 聚焦历史盲区缺陷，顺序深挖，逐步加难。

与 Stage 3.6（综合进化）的关系：
  Stage 3.6 = broad（ε-greedy 多策略并行，综合修复所有缺陷）
  Stage 3.6b = deep（聚焦单一盲区缺陷，逐轮递增难度，直到修复或判定不可解）

RSIAgent 消融证据：broad-only 65.52% < deep-only 56.50% < full RSI 74.54%。
deep 单独最弱，但叠加在 broad 之上带来最大增益 —— 本阶段是 broad 的补充，非替代。

难度递增阶梯（每轮针对「目标缺陷」提高修复要求）：
  difficulty 0: 基础修复（补证明体 / 诚实公理化，附文献引用）
  difficulty 1: + 边界条件显式化（声明该缺陷成立的边界 / 隐藏约束）
  difficulty 2: + 反例搜索（主动找反例验证修复的鲁棒性）
  difficulty 3: + 最小充分集（删除冗余公理后定理仍成立）

用法：
  python deep_refinement.py \
      --lean /path/to/proof.lean \
      [--archive /path/to/archive.jsonl] \
      [--rounds 3] \
      [--output /tmp/deep_refine/] \
      [--dry-run]        # 只评估 + 选目标缺陷，不调 LLM（离线自测）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from replay_strategies import ReplaySimulator, DEFECT_PRIORITY, defect_signature, MUTATION_STRATEGIES
from stage36_evolution import evaluate_lean, _run_dag_audit, _load_api_key

SCRIPTS_DIR = Path(__file__).resolve().parent
VENV_PYTHON = "/usr/local/lib/hermes-agent-v14/venv/bin/python"

# 难度阶梯：每级给诊断/修复 prompt 追加的「更严格要求」
DIFFICULTY_LADDER = [
    "基础修复：补上真实证明体（nlinarith/field_simp/ring/exact ..._axiom），"
    "或改写为显式 axiom 声明并附文献引用注释。",
    "边界条件显式化：声明该缺陷成立的边界条件 / 隐藏约束（哪些前提是必要的、"
    "哪些参数区间内成立），并显式写入证明。",
    "反例搜索：主动构造反例，验证修复后的定理在边界处不会坍塌；"
    "若发现反例，把定理重新收窄为条件定理。",
    "最小充分集：删除冗余公理后定理仍成立（找出真正必要的公理子集，"
    "删除表演性诚实装饰）。",
]


def _select_target_defect(current: dict, replay: ReplaySimulator) -> str | None:
    """选「目标缺陷」：历史盲区优先，否则按 DEFECT_PRIORITY 最严重。"""
    defects = current["defects"]
    blinds = replay.blind_spots(defects)
    if blinds:
        # 盲区里按 DEFECT_PRIORITY 顺序取最严重
        for k in DEFECT_PRIORITY:
            if k in blinds:
                return k
    for k in DEFECT_PRIORITY:
        if defects.get(k, 0) > 0:
            return k
    return None


def _deepseek(client, model: str, prompt: str, max_tokens: int) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens,
        timeout=180,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return (resp.choices[0].message.content or "").strip()


def _diagnose(client, lean_text: str, defects: dict, target: str, difficulty: int,
              blinds: list[str], precedents: list[dict]) -> str:
    """v4-pro 深度诊断：聚焦单一目标缺陷，按当前难度阶梯给出根因 + 更严格修复计划。"""
    ladder_req = DIFFICULTY_LADDER[difficulty]
    blind_note = f"\n【历史盲区】{', '.join(blinds)} 从未被成功修复，请尝试全新思路。" if blinds else ""
    precedent_note = ""
    if precedents:
        top = precedents[:2]
        items = "; ".join(f"动作 {p['action']}(成功率 {p['success_rate']})" for p in top)
        precedent_note = f"\n【成功先例】相同缺陷签名下有效动作：{items}。"

    prompt = f"""你是 Lean 4 形式化证明专家。这是一轮**深度单缺陷修复**（DRS 阶段）。

【完整缺陷报告】
{json.dumps(defects, ensure_ascii=False, indent=2)}

【本轮目标缺陷】{target}（聚焦这一个缺陷深挖，不要分心处理其他缺陷）
【难度阶梯】第 {difficulty} 级：{ladder_req}
{blind_note}{precedent_note}

请针对目标缺陷 {target}，按第 {difficulty} 级要求给出精确修复计划。
输出简洁中文计划，不要输出代码。"""
    return _deepseek(client, "deepseek-v4-pro", prompt, 2048)


def _repair(client, lean_text: str, plan: str, target: str, difficulty: int) -> str:
    """v4-flash 深度修复：聚焦目标缺陷，按难度阶梯要求输出修复后完整 Lean。"""
    ladder_req = DIFFICULTY_LADDER[difficulty]
    prompt = f"""你是 Lean 4 形式化证明专家。按下面的修复计划，**聚焦目标缺陷 {target}** 修复 Lean 文件。

【修复计划】
{plan}

【难度要求】第 {difficulty} 级：{ladder_req}

【当前证明文件】
```lean
{lean_text}
```

请输出修复后的**完整 Lean 文件**（保留 import、公理声明、定理结构），只输出 Lean 代码。
要求：
- 只聚焦目标缺陷 {target}，不要全盘重写其他部分。
- 严格满足第 {difficulty} 级难度要求。
- 不引入新 sorry/admit；不用 := by trivial 空壳。"""
    out = _deepseek(client, "deepseek-v4-flash", prompt, 32768)
    out = re.sub(r"^```(?:lean)?\s*\n?", "", out)
    out = re.sub(r"\n?```\s*$", "", out)
    return out.strip() + "\n"


def _defect_summary(d: dict) -> str:
    parts = []
    for k in DEFECT_PRIORITY:
        if d.get(k):
            parts.append(f"{k}={d[k]}")
    return " ".join(parts) if parts else "干净"


def deep_refine(lean_path: Path, archive_path: Path | None, output_dir: Path,
                max_rounds: int, dry_run: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    arch = archive_path if archive_path else output_dir / "archive.jsonl"

    seed_text = lean_path.read_text(encoding="utf-8", errors="replace")
    current_text = seed_text
    dag_report = _run_dag_audit(lean_path, output_dir)
    current = evaluate_lean(current_text, dag_report)

    replay = ReplaySimulator(arch)
    replay.load(arch)

    rounds_log = []
    client = None
    if not dry_run:
        api_key = _load_api_key()
        if not api_key:
            print("[DRS] ⚠️ 无 API key，自动降级 dry-run")
            dry_run = True
        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    print(f"[DRS] 种子 score={current['score']}  {_defect_summary(current['defects'])}")

    # 追踪每个目标缺陷的「连续失败次数」，用于难度递增
    difficulty = 0
    prev_target = None
    streak = 0

    for rnd in range(1, max_rounds + 1):
        target = _select_target_defect(current, replay)
        if target is None:
            print("[DRS] 无活跃缺陷，深挖结束")
            break

        # 难度递增：同一缺陷连续失败 → 难度 +1（封顶 3）
        if target == prev_target:
            streak += 1
            difficulty = min(difficulty + 1, len(DIFFICULTY_LADDER) - 1)
        else:
            streak = 0
            difficulty = 0
        prev_target = target

        blinds = replay.blind_spots(current["defects"])
        precedents = replay.condition_match(current["defects"])

        print(f"\n[DRS {rnd}] 目标缺陷={target} 难度={difficulty}（{DIFFICULTY_LADDER[difficulty][:20]}...）")
        if blinds:
            print(f"          ⚠️ 盲区: {', '.join(blinds)}")
        if precedents:
            print(f"          💡 先例: {len(precedents)} 条")

        if dry_run:
            # 只评估 + 选目标，不调 LLM
            rounds_log.append({
                "round": rnd, "target": target, "difficulty": difficulty,
                "score": current["score"], "mode": "dry-run",
            })
            # dry-run 下模拟：无修复，难度仍递增但无实质变化，最多跑一轮就停
            print("[DRS] dry-run：仅评估，不调 LLM")
            break

        plan = _diagnose(client, current_text, current["defects"], target, difficulty, blinds, precedents)
        mutated = _repair(client, current_text, plan, target, difficulty)

        tmp_lean = output_dir / f"drs_r{rnd}_candidate.lean"
        tmp_lean.write_text(mutated, encoding="utf-8")
        dag_report = _run_dag_audit(tmp_lean, output_dir)
        candidate = evaluate_lean(mutated, dag_report)

        accepted = candidate["score"] > current["score"]
        record = {
            "generation": -rnd,  # 负代数标记 DRS 阶段，与 Stage 3.6 正代数区分
            "stage": "deep_refinement",
            "round": rnd,
            "target_defect": target,
            "difficulty": difficulty,
            "score": candidate["score"],
            "defects": candidate["defects"],
            "accepted": accepted,
            "parent_score": current["score"],
            "gain": round(candidate["score"] - current["score"], 1),
            "mutation_strategy": "deep_focus",
            "defects_before": current["defects"],
            "condition": defect_signature(current["defects"]),
            "timestamp": datetime.now().isoformat(),
        }
        rounds_log.append(record)
        with arch.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        replay.records.append(record)

        if accepted:
            print(f"[DRS {rnd}] ✅ 接受：{current['score']} → {candidate['score']}  {_defect_summary(candidate['defects'])}")
            current_text = mutated
            current = candidate
            if current["score"] >= 100.0:
                print("[DRS] 收敛：满分达成")
                break
        else:
            print(f"[DRS {rnd}] ❌ 拒绝：{candidate['score']} ≤ {current['score']}（难度 {difficulty} 未突破，下一轮升难度或换目标）")

    best_lean = output_dir / "best_proof.lean"
    best_lean.write_text(current_text, encoding="utf-8")
    result = {
        "best_score": current["score"],
        "best_defects": current["defects"],
        "best_lean": str(best_lean),
        "rounds_run": len(rounds_log),
        "rounds": rounds_log,
        "causal_rules": replay.causal_rules(),
    }
    (output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 3.6b Deep Refinement (DRS, RSIAgent)")
    ap.add_argument("--lean", required=True, help="种子 Lean 证明文件")
    ap.add_argument("--archive", default=None, help="archive.jsonl（历史盲区/先例来源）")
    ap.add_argument("--rounds", type=int, default=3, help="深挖轮数（默认 3）")
    ap.add_argument("--output", default="/tmp/deep_refine_output", help="输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只评估 + 选目标缺陷，不调 LLM")
    args = ap.parse_args()

    lean_path = Path(args.lean)
    if not lean_path.exists():
        print(f"错误：{lean_path} 不存在", file=sys.stderr)
        return 2

    print("=" * 60)
    print("STAGE 3.6b: Deep Refinement (DRS, RSIAgent broad-then-deep)")
    print("=" * 60)
    print(f"种子: {lean_path.name} | 轮数: {args.rounds} | 模式: {'dry-run' if args.dry_run else 'LLM 深挖'}")
    print("=" * 60)

    result = deep_refine(lean_path, Path(args.archive) if args.archive else None,
                         Path(args.output), args.rounds, args.dry_run)

    print("\n" + "=" * 60)
    print(f"深挖完成，最佳分数: {result['best_score']}  缺陷: {_defect_summary(result['best_defects'])}")
    print(f"因果规则数: {len(result['causal_rules'])}")
    print(f"最佳证明: {result['best_lean']}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
