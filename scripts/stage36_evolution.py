#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.6 — 冻结评估器进化循环（RSIHub 风格 hill_climb + Dream-RSI 重放模拟器）

把「生成 Lean → 验证 → 分析失败 → 改证明 → 再验证」这条人工迭代自动化。

核心设计（对齐 RSIHub 的可信性保证）：
  1. **评估器被冻结**：`evaluate_lean()` 是确定性的（正则 grep + proof_dag_audit.py），
     不掺任何 LLM —— 候选者不能改评分规则。
  2. **变异有界**：mutate 只改 Lean 证明文件（或 prompt），不改评估器。
  3. **评估规范化**：每代从干净快照评分。
  4. **证据持久**：append-only `archive.jsonl` 记录每代分数 + 缺陷 + 是否被接受。

Dream-RSI（arXiv 2609.14858）增量增强（P0-P2，见 replay_strategies.py）：
  P0  replay simulator : archive.jsonl 升级为可重放的模拟器，统计各变异策略历史成功率。
  P1  off-policy 反馈  : 变异前做盲区检测（哪些缺陷历史从未修复成功），注入诊断 prompt。
  P2  变异策略显式化   : 单一「诊断→修复」拆成 5 个可评估策略，ε-greedy 动态选择。

循环：select(父代) → replay 选策略 → analyze(DeepSeek 诊断 + 盲区提示) →
      mutate(DeepSeek 按策略修复) → gate(严格改进才接受) → record(archive.jsonl 带策略)

用法：
  python stage36_evolution.py \
      --lean /path/to/proof.lean \
      [--generations 3] \
      [--epsilon 0.15] \
      [--output /tmp/stage36/] \
      [--dry-run]        # 只跑冻结评估器 + DAG 审计，不调 LLM（离线自测）

不改动现有 Stage 1-4；与 Stage A（lean_recursive_repair）的差异：
  Stage A 是「单点 sorry 修复」，Stage 3.6 是「多维冻结评分驱动的多代进化 + 严格门控 + 证据链 + 策略重放」。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from replay_strategies import ReplaySimulator, MUTATION_STRATEGIES, DEFECT_PRIORITY, defect_signature

SCRIPTS_DIR = Path(__file__).resolve().parent
VENV_PYTHON = "/usr/local/lib/hermes-agent-v14/venv/bin/python"

# ── 冻结评估器（确定性，无 LLM）───────────────────────────────────

def _run_dag_audit(lean_path: Path, output_dir: Path) -> dict | None:
    """调用 proof_dag_audit.py（若存在），返回其 JSON 报告。"""
    dag_script = SCRIPTS_DIR / "proof_dag_audit.py"
    if not dag_script.exists():
        return None
    out = output_dir / "dag_audit_tmp.json"
    try:
        subprocess.run(
            [VENV_PYTHON, str(dag_script), "--lean", str(lean_path), "--output", str(out)],
            capture_output=True, text=True, timeout=120,
        )
        if out.exists():
            return json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def evaluate_lean(lean_text: str, dag_report: dict | None) -> dict:
    """冻结评分：满分 100，按缺陷扣分。完全确定性，候选者无法改写。"""
    sorry = len(re.findall(r"\bsorry\b", lean_text))
    admit = len(re.findall(r"\badmit\b", lean_text))
    trivial = len(re.findall(r":=\s*by\s+trivial", lean_text))
    true_stub = len(re.findall(r":=\s*True\b", lean_text))
    redundant = len(dag_report.get("redundant_lemmas", [])) if dag_report else 0
    unused = len(dag_report.get("unused_axioms", [])) if dag_report else 0
    dangling = len(dag_report.get("dangling_refs", [])) if dag_report else 0

    defects = {
        "sorry": sorry,
        "admit": admit,
        "trivial_or_true_stub": trivial + true_stub,
        "redundant_lemmas": redundant,
        "unused_axioms": unused,
        "dangling_refs": dangling,
    }
    score = 100.0
    score -= 20 * sorry
    score -= 15 * admit
    score -= 10 * (trivial + true_stub)
    score -= 5 * redundant
    score -= 3 * unused
    score -= 50 * dangling
    score = max(0.0, score)
    return {"score": round(score, 1), "defects": defects}


# ── LLM 诊断 / 修复（DeepSeek）───────────────────────────────────

def _load_api_key() -> str:
    for env_path in [
        "~/.hermes/.env",
        str(Path.home() / ".hermes/.env"),
    ]:
        p = Path(env_path)
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    import os
    return os.environ.get("DEEPSEEK_API_KEY", "")


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


def _analyze(client, lean_text: str, defects: dict, strat_name: str, blinds: list[str],
             precedents: list[dict] = None) -> str:
    """v4-pro 诊断：读缺陷报告 + 当前策略 + 盲区提示 + 成功先例，给出根因 + 精确修复计划。"""
    strat_cfg = MUTATION_STRATEGIES.get(strat_name, {})
    blind_note = ""
    if blinds:
        names = ", ".join(blinds)
        blind_note = (
            f"\n\n【历史盲区警告】以下缺陷类型在 archive 历史中从未被成功修复过，"
            f"常规方法可能无效，请尝试全新思路：{names}。\n"
        )
    precedent_note = ""
    if precedents:
        top = precedents[:3]
        items = "; ".join(
            f"动作 {p['action']} 在相同缺陷签名下成功率 {p['success_rate']} (avg_gain {p['avg_gain']})"
            for p in top)
        precedent_note = (
            f"\n\n【历史成功先例】(P3 因果记忆：相同缺陷签名 {defect_signature(defects)} 下"
            f"被证明有效的动作)：{items}。请优先借鉴这些动作。\n"
        )
    prompt = f"""你是 Lean 4 形式化证明专家。下面是当前证明的冻结评估器缺陷报告（确定性检测，非 LLM 判断）：

{json.dumps(defects, ensure_ascii=False, indent=2)}

【本轮变异策略】{strat_cfg.get('desc', strat_name)}
策略侧重：{strat_cfg.get('focus', '综合修复')}
{blind_note}{precedent_note}
请诊断每类缺陷的根因，并给出**聚焦于本策略侧重**的精确修复计划（哪些 sorry/admit 要补证明体、
哪些 := by trivial / := True 是空壳要替换成真实策略、哪些冗余引理要删除或接入、
哪些未用 axiom 要接入证明链或删掉）。输出简洁的中文修复计划，不要输出代码。"""
    return _deepseek(client, "deepseek-v4-pro", prompt, 2048)


def _mutate(client, lean_text: str, repair_plan: str, strat_name: str) -> str:
    """v4-flash 修复：按修复计划 + 策略侧重产出修复后的完整 Lean 文件。"""
    strat_cfg = MUTATION_STRATEGIES.get(strat_name, {})
    prompt = f"""你是 Lean 4 形式化证明专家。按下面的修复计划修复 Lean 证明文件。

【修复计划】
{repair_plan}

【本轮策略侧重】{strat_cfg.get('focus', '综合修复')}

【当前证明文件】
```lean
{lean_text}
```

请输出修复后的**完整 Lean 文件**（保留所有 import、公理声明、定理结构），
只输出 Lean 代码，不要任何解释、markdown 围栏外的文字。要求：
- 聚焦【本轮策略侧重】优先处理对应缺陷，不要全盘重写无关部分。
- 每个 sorry / admit 要么补上真实策略体（nlinarith/field_simp/ring/exact ..._axiom），
  要么显式改写为诚实公理 axiom 声明（附文献引用注释）。
- 删除或接入所有冗余引理 / 未用 axiom。
- 不引入新的 sorry；不使用 := by trivial 空壳。"""
    out = _deepseek(client, "deepseek-v4-flash", prompt, 32768)
    # 剥离可能的 markdown 围栏
    out = re.sub(r"^```(?:lean)?\s*\n?", "", out)
    out = re.sub(r"\n?```\s*$", "", out)
    return out.strip() + "\n"


# ── 进化循环 ─────────────────────────────────────────────────────

def run_evolution(lean_path: Path, output_dir: Path, generations: int,
                  dry_run: bool, epsilon: float = 0.15) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "archive.jsonl"
    best_lean_path = output_dir / "best_proof.lean"

    seed_text = lean_path.read_text(encoding="utf-8", errors="replace")
    current_text = seed_text
    dag_report = _run_dag_audit(lean_path, output_dir)
    current = evaluate_lean(current_text, dag_report)

    # P0: 初始化 ReplaySimulator（读历史 archive，跨运行累计策略统计）
    replay = ReplaySimulator(archive_path)
    n_hist = replay.load(archive_path)
    if n_hist:
        print(f"[Stage3.6] 载入历史证据 {n_hist} 条 → replay simulator 就绪")

    archive = []
    client = None
    if not dry_run:
        api_key = _load_api_key()
        if not api_key:
            print("[Stage3.6] ⚠️ 无 API key，自动降级为 dry-run（只评估不进化）")
            dry_run = True
        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def append(record: dict) -> None:
        archive.append(record)
        with archive_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    # Gen 0 = 种子
    append({
        "generation": 0, "score": current["score"], "defects": current["defects"],
        "accepted": True, "mutation_strategy": "seed",
        "timestamp": datetime.now().isoformat(),
    })

    print(f"[Gen 0] score={current['score']}  {_defect_summary(current['defects'])}")

    if current["score"] >= 100.0:
        print("[Stage3.6] 种子已满分，无需进化")
    elif dry_run:
        print("[Stage3.6] dry-run 模式：仅评估，不调用 LLM")
        _report_replay(replay, current["defects"])
    else:
        for gen in range(1, generations + 1):
            # P2: ε-greedy 选择变异策略
            strategy = replay.choose(current["defects"], epsilon)
            if strategy is None:
                print("[Stage3.6] 无活跃缺陷，提前结束")
                break
            strat_name = strategy["name"]

            # P1: 盲区检测（历史从未修复成功的缺陷）
            blinds = replay.blind_spots(current["defects"])
            # P3: 因果记忆成功先例（相同缺陷签名下被证明有效的动作）
            precedents = replay.condition_match(current["defects"])

            print(f"\n[Gen {gen}] 策略={strat_name}（{MUTATION_STRATEGIES[strat_name]['desc']}）")
            if blinds:
                print(f"          ⚠️ 历史盲区: {', '.join(blinds)}")
            if precedents:
                print(f"          💡 成功先例: {len(precedents)} 条（condition={defect_signature(current['defects'])}）")

            repair_plan = _analyze(client, current_text, current["defects"], strat_name, blinds, precedents)
            print(f"[Gen {gen}] 修复中...")
            mutated = _mutate(client, current_text, repair_plan, strat_name)

            # 规范化评估：把变异结果写临时文件，跑 DAG 审计
            tmp_lean = output_dir / f"gen{gen}_candidate.lean"
            tmp_lean.write_text(mutated, encoding="utf-8")
            dag_report = _run_dag_audit(tmp_lean, output_dir)
            candidate = evaluate_lean(mutated, dag_report)

            accepted = candidate["score"] > current["score"]
            record = {
                "generation": gen,
                "score": candidate["score"],
                "defects": candidate["defects"],
                "accepted": accepted,
                "parent_score": current["score"],
                "gain": round(candidate["score"] - current["score"], 1),
                "mutation_strategy": strat_name,
                "defects_before": current["defects"],
                "condition": defect_signature(current["defects"]),  # P3: 因果三元组 condition 维度
                "timestamp": datetime.now().isoformat(),
            }
            append(record)
            replay.records.append(record)  # 即时更新重放池

            if accepted:
                print(f"[Gen {gen}] ✅ 接受：{current['score']} → {candidate['score']}  {_defect_summary(candidate['defects'])}")
                current_text = mutated
                current = candidate
                if current["score"] >= 100.0:
                    print("[Stage3.6] 收敛：满分达成")
                    break
            else:
                print(f"[Gen {gen}] ❌ 拒绝：{candidate['score']} ≤ {current['score']}（保留父代）")

    best_lean_path.write_text(current_text, encoding="utf-8")
    best = {"best_score": current["score"], "best_defects": current["defects"],
            "best_lean": str(best_lean_path), "generations_run": len(archive) - 1,
            "strategy_stats": replay.strategy_stats()}
    (output_dir / "result.json").write_text(json.dumps(best, ensure_ascii=False, indent=2), encoding="utf-8")
    return best


def _report_replay(replay: ReplaySimulator, defects: dict) -> None:
    """dry-run 时打印 replay 推荐，验证 P0-P2 逻辑。"""
    ranked = replay.rank_strategies(defects, epsilon=0.0)
    if not ranked:
        print("[Replay] 无活跃缺陷，无需推荐")
        return
    print("\n[Replay] 策略推荐（按评分降序）：")
    for r in ranked:
        succ = f"{r['success_rate']}" if r['success_rate'] is not None else "—"
        print(f"  {r['name']:16s} score={r['score']:.3f} 针对性={r['targeted']} "
              f"历史成功率={succ} 尝试={r['attempts']}")
    blinds = replay.blind_spots(defects)
    if blinds:
        print(f"[Replay] 历史盲区: {', '.join(blinds)}")


def _defect_summary(d: dict) -> str:
    parts = []
    if d.get("sorry"): parts.append(f"sorry={d['sorry']}")
    if d.get("admit"): parts.append(f"admit={d['admit']}")
    if d.get("trivial_or_true_stub"): parts.append(f"空壳={d['trivial_or_true_stub']}")
    if d.get("redundant_lemmas"): parts.append(f"冗余引理={d['redundant_lemmas']}")
    if d.get("unused_axioms"): parts.append(f"未用axiom={d['unused_axioms']}")
    if d.get("dangling_refs"): parts.append(f"悬空={d['dangling_refs']}")
    return " ".join(parts) if parts else "干净"


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 3.6 冻结评估器进化循环（+ Dream-RSI replay）")
    ap.add_argument("--lean", required=True, help="种子 Lean 证明文件路径")
    ap.add_argument("--generations", type=int, default=3, help="进化代数（默认 3）")
    ap.add_argument("--epsilon", type=float, default=0.15, help="ε-greedy 探索率（默认 0.15）")
    ap.add_argument("--output", default="/tmp/stage36_output", help="输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只评估不调 LLM（离线自测）")
    args = ap.parse_args()

    lean_path = Path(args.lean)
    if not lean_path.exists():
        print(f"错误：{lean_path} 不存在", file=sys.stderr)
        return 2

    output_dir = Path(args.output)
    print("=" * 60)
    print("STAGE 3.6: Frozen Evaluator Evolution Loop (RSIHub + Dream-RSI)")
    print("=" * 60)
    print(f"种子: {lean_path.name}")
    print(f"代数: {args.generations} | ε: {args.epsilon} | 模式: {'dry-run' if args.dry_run else 'LLM 进化'}")
    print("=" * 60)

    t0 = time.time()
    best = run_evolution(lean_path, output_dir, args.generations, args.dry_run, args.epsilon)

    print("\n" + "=" * 60)
    print(f"进化完成（{time.time()-t0:.1f}s）")
    print(f"最佳分数: {best['best_score']}  缺陷: {_defect_summary(best['best_defects'])}")
    print(f"最佳证明: {best['best_lean']}")
    print(f"证据链: {output_dir / 'archive.jsonl'}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
