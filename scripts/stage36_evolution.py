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

RSIAgent 复审增量（2026-10-05，代码深读新增）：
  P0-① 三大改进极限元诊断 : 连续停滞时判断根因（练习错位/验证过松/记忆污染），注入下轮诊断。
  P0-② 密封评估器 + 防 reward hack : 检测缺陷等价替换（sorry→admit 等），等价替换即拒绝。
  P0-③ learn_on_pass : 分数不退化（≥）也记录为「成功经验」，供 replay 学习「不退化」先例。
  P5  证明模式模板库 : 从 proof_templates.json 检索已冻结证明模式，注入 mutate prompt 作 few-shot。

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
from proof_template_library import load_templates, select_templates, render_few_shot

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


# ── P0-② 密封评估器 + 防 reward hack ────────────────────────────

def _detect_reward_hack(before: dict, after: dict) -> str | None:
    """检测缺陷等价替换（分数虚高但证明实质没完成）。

    RSIAgent「Incomplete Verification」极限：验证会接受不完整工作。
    LLM 修复者可能学会把 sorry 改成 admit、把 := by trivial 改成 sorry，
    让冻结评估器分数虚高但证明实质没完成。这类等价替换必须拒绝（即使分数提高）。
    返回 hack 描述字符串；无 hack 返回 None。
    """
    b, a = before, after

    def incomplete(d: dict) -> int:
        return (d.get("sorry", 0) + d.get("admit", 0) + d.get("trivial_or_true_stub", 0))

    # 1) sorry → admit 等价替换（都是「未完成证明」，只是换名字）
    if a.get("sorry", 0) < b.get("sorry", 0) and a.get("admit", 0) > b.get("admit", 0):
        return "sorry→admit 等价替换：把 sorry 改写成 admit，未完成证明只是换了个名字"
    # 2) 空壳 → sorry 等价替换（:= by trivial 改成 sorry）
    if (a.get("trivial_or_true_stub", 0) < b.get("trivial_or_true_stub", 0)
            and a.get("sorry", 0) > b.get("sorry", 0)):
        return "空壳→sorry 等价替换：把 := by trivial 改成 sorry，未完成证明总量未降"
    # 3) 未完成证明总量不降反升（sorry + admit + 空壳）
    if incomplete(a) > incomplete(b):
        return (f"未完成证明总量增加（{incomplete(b)} → {incomplete(a)}）："
                f"实质退化，分数虚高是 reward hack")
    return None


# ── P0-① 三大改进极限元诊断 ─────────────────────────────────────

def _diagnose_stall(stall_counter: int, current: dict, replay: ReplaySimulator,
                    blinds: list[str], strat_name: str) -> str | None:
    """连续停滞时判断根因（RSIAgent 三大改进极限），注入下轮诊断。

      1. Insufficiently Targeted Exploration（练习没对准弱点）
      2. Incomplete Verification（验证接受不完整工作）
      3. Unreliable Memory Consolidation（记忆固化错误规则）
    返回诊断文本（供 _analyze 注入）或 None（未达停滞阈值）。
    """
    if stall_counter < 2:
        return None
    causes = []
    # 3) 记忆污染：replay 推荐了历史上 success_rate == 0 的策略
    stats = replay.strategy_stats()
    s = stats.get(strat_name, {})
    if s.get("attempts", 0) > 0 and (s.get("success_rate") or 0.0) == 0.0:
        causes.append(
            f"Unreliable Memory Consolidation：策略「{strat_name}」历史成功率 0% 却被 replay "
            f"推荐，先验可能被污染，建议加大 ε 探索率换策略")
    # 1) 练习错位：当前活跃缺陷全是历史盲区（从未被任何策略修复过）
    if blinds:
        causes.append(
            f"Insufficiently Targeted Exploration：以下缺陷是历史盲区（从未修复成功），"
            f"练习没对准弱点：{', '.join(blinds)}")
    # 2) 验证过松：分数高但仍有核心缺陷（sorry/admit 残留）被轻判
    if (current.get("score", 0) >= 85
            and (current.get("defects", {}).get("sorry", 0) > 0
                 or current.get("defects", {}).get("admit", 0) > 0)):
        causes.append(
            "Incomplete Verification：分数高（≥85）但仍有 sorry/admit 残留，"
            "评估器对严重缺陷扣分过松，门控未拦截不完整工作")
    if not causes:
        causes.append("未明确：可能只是局部最优，建议换一种变异策略或加大 ε 探索率")
    return "；".join(causes)


# ── LLM 诊断 / 修复（DeepSeek）───────────────────────────────────

def _load_api_key() -> str:
    for env_path in [
        ".env",
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
             precedents: list[dict] = None, stall_diagnosis: str = None) -> str:
    """v4-pro 诊断：读缺陷报告 + 当前策略 + 盲区提示 + 成功先例 + 停滞诊断，给出根因 + 精确修复计划。"""
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
    stall_note = ""
    if stall_diagnosis:
        stall_note = (
            f"\n\n【进化停滞诊断】(P0-① 三大改进极限)：连续多代无增益，根因判断如下——\n"
            f"{stall_diagnosis}。\n请针对上述根因调整修复策略，不要重复已证明无效的做法。\n"
        )
    prompt = f"""你是 Lean 4 形式化证明专家。下面是当前证明的冻结评估器缺陷报告（确定性检测，非 LLM 判断）：

{json.dumps(defects, ensure_ascii=False, indent=2)}

【本轮变异策略】{strat_cfg.get('desc', strat_name)}
策略侧重：{strat_cfg.get('focus', '综合修复')}
{blind_note}{precedent_note}{stall_note}
请诊断每类缺陷的根因，并给出**聚焦于本策略侧重**的精确修复计划（哪些 sorry/admit 要补证明体、
哪些 := by trivial / := True 是空壳要替换成真实策略、哪些冗余引理要删除或接入、
哪些未用 axiom 要接入证明链或删掉）。输出简洁的中文修复计划，不要输出代码。"""
    return _deepseek(client, "deepseek-v4-pro", prompt, 2048)


def _mutate(client, lean_text: str, repair_plan: str, strat_name: str, few_shot: str = "") -> str:
    """v4-flash 修复：按修复计划 + 策略侧重 + 已冻结证明模式(few-shot)产出修复后的完整 Lean 文件。"""
    strat_cfg = MUTATION_STRATEGIES.get(strat_name, {})
    few_shot_note = ""
    if few_shot:
        few_shot_note = (
            f"\n\n【已冻结证明模式 few-shot】(P5 记忆冻结复用：以下是历史上已通过验证的修复模式，"
            f"请优先套用对应模式，不要另起炉灶)：\n{few_shot}\n"
        )
    prompt = f"""你是 Lean 4 形式化证明专家。按下面的修复计划修复 Lean 证明文件。

【修复计划】
{repair_plan}

【本轮策略侧重】{strat_cfg.get('focus', '综合修复')}
{few_shot_note}
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
        templates = load_templates()   # P5: 已冻结证明模式库
        stall_counter = 0               # P0-①: 连续无增益代数
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
            # P0-①: 三大改进极限元诊断（连续停滞时判断根因）
            stall_diagnosis = _diagnose_stall(stall_counter, current, replay, blinds, strat_name)

            print(f"\n[Gen {gen}] 策略={strat_name}（{MUTATION_STRATEGIES[strat_name]['desc']}）")
            if blinds:
                print(f"          ⚠️ 历史盲区: {', '.join(blinds)}")
            if precedents:
                print(f"          💡 成功先例: {len(precedents)} 条（condition={defect_signature(current['defects'])}）")
            if stall_diagnosis:
                print(f"          🧭 停滞诊断: {stall_diagnosis}")

            repair_plan = _analyze(client, current_text, current["defects"], strat_name,
                                   blinds, precedents, stall_diagnosis)
            print(f"[Gen {gen}] 修复中...")
            # P5: 检索已冻结证明模式作 few-shot（记忆冻结复用）
            few_shot = render_few_shot(select_templates(templates, current["defects"]))
            mutated = _mutate(client, current_text, repair_plan, strat_name, few_shot)

            # 规范化评估：把变异结果写临时文件，跑 DAG 审计
            tmp_lean = output_dir / f"gen{gen}_candidate.lean"
            tmp_lean.write_text(mutated, encoding="utf-8")
            dag_report = _run_dag_audit(tmp_lean, output_dir)
            candidate = evaluate_lean(mutated, dag_report)

            # P0-② 密封评估器 + 防 reward hack：等价替换即拒绝（即使分数提高）
            hack = _detect_reward_hack(current["defects"], candidate["defects"])
            accepted = (candidate["score"] > current["score"]) and (hack is None)
            # P0-③ learn_on_pass：分数不退化（≥）且无 hack 也记录为「成功经验」（不替换当前）
            learn_on_pass = (candidate["score"] >= current["score"]) and (hack is None) and not accepted

            record = {
                "generation": gen,
                "score": candidate["score"],
                "defects": candidate["defects"],
                "accepted": accepted,
                "learn_on_pass": learn_on_pass,
                "parent_score": current["score"],
                "gain": round(candidate["score"] - current["score"], 1),
                "mutation_strategy": strat_name,
                "defects_before": current["defects"],
                "condition": defect_signature(current["defects"]),
                "timestamp": datetime.now().isoformat(),
            }
            if hack:
                record["reward_hack"] = hack
            # P1-2 (Colosseum)：失败路径记录——精确失败点 + 变体可行条件。
            # 让 archive 从「被动记录」升级为「可复用失败知识目录」，变异前可注入避免重复踩坑。
            if not accepted and not learn_on_pass:
                record["failed_approach"] = {
                    "route": strat_name,
                    "failure_point": _defect_summary(candidate["defects"]),
                    "variant_condition": (
                        "retry with a different lemma decomposition, strengthened "
                        "hypothesis, or alternative axiom instantiation"
                    ),
                    # [v2.19.0] Scout 失败路径侦察（prove2me mission_solver §2）：
                    # 权威拒绝方 + 理由，比「自己失败」更硬的信号。archive 注入时
                    # 优先检索「权威拒绝」路径，避免重试已被拒绝的方法。
                    "rejected_by": "frozen_evaluator",
                    "reject_reason": _defect_summary(candidate["defects"]),
                }
            append(record)
            replay.records.append(record)  # 即时更新重放池

            if accepted:
                print(f"[Gen {gen}] ✅ 接受：{current['score']} → {candidate['score']}  {_defect_summary(candidate['defects'])}")
                current_text = mutated
                current = candidate
                stall_counter = 0
                if current["score"] >= 100.0:
                    print("[Stage3.6] 收敛：满分达成")
                    break
            elif hack:
                print(f"[Gen {gen}] 🛡️ 拒绝（reward hack）: {hack}")
                stall_counter += 1
            elif learn_on_pass:
                print(f"[Gen {gen}] 📌 记录成功经验（不退化 {current['score']} → {candidate['score']}，不替换）")
                stall_counter += 1
            else:
                print(f"[Gen {gen}] ❌ 拒绝：{candidate['score']} ≤ {current['score']}（保留父代）")
                stall_counter += 1

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
