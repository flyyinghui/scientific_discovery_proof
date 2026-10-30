#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mvp0_smoke — MVP-0 最小闭环：Propose → Probe(4 路并行) → Arbiter → Diff → Rank → Compose

这是把 harness2 的 RSI 接到 scientific-discovery-proof 的**最小可运行单元**。
不动主线五阶段，只新增一个「策略层进化环」：

    ┌──────────────────────────────────────────────────────────┐
    │ ① Propose   proof_harness.propose_edits()  提 4 个 harness│
    │ ② Probe     agent_fleet.run_fleet()        4 路并行跑同一猜想│
    │ ③ Arbiter   agent_fleet.arbitrate()        唯一判定入口   │
    │ ④ Diff      trajectory_diff.diff_runs()    抽首个分歧步   │
    │ ⑤ Rank      jev_arbiter_bridge.rank_runs() 只在都过关的里排│
    │ ⑥ Compose   本脚本 _compose()              差异互补组下一代│
    └──────────────────────────────────────────────────────────┘

关键设计（这三条是整套方案成立的前提，代码里都做了强制）：
  ① **判定与排序分离**：只有 Arbiter 写 lean_ok/verdict；Jev 只排先后，进不了 gate。
  ② **单维编辑**：4 个变体每个只改一个维度 → 分歧步能归因到具体维度，不是玄学。
  ③ **降级可用**：Jev 端点没起、Lean 没装都不阻塞 —— 用轨迹推断 + 文档化降级。

用法：
    python mvp0_smoke.py                          # 默认猜想 + 4 路
    python mvp0_smoke.py --n 6 --rounds 2         # 6 路 × 2 代
    python mvp0_smoke.py --output /tmp/mvp0/      # 落盘报告

自测（不需要任何外部依赖）：
    python mvp0_smoke.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from proof_harness import ProofHarness, propose_edits
from agent_fleet import run_fleet, arbitrate, PIPELINE
from trajectory_diff import diff_runs, render_report
from jev_arbiter_bridge import probe_health, rank_runs

DEFAULT_CONJECTURE = """\
g_TC^2 = 24*pi^2/35, i.e. the triple-gauge coupling squared equals 24π²/35 ≈ 6.77.
Derive it from the SL(6,C) framework's λ_⊥ = 35/3 and prove the resulting bound is
not a definition tautology.
"""


# ── Compose：从轨迹差异组合下一代 harness ─────────────────────────
def _compose(base: ProofHarness, runs: list, diff: dict, rank: dict) -> dict:
    """Harness² 的第三段：不是「取平均」，而是「取差异互补」。

    规则（可解释、可审计）：
      · 找出基准 run 里**失败**而其它 run 里**成功**的步骤 → 采纳那个 run 在对应维度的设置
      · 若全部分歧都是结构性的（structural_gap），则保留两个变体作为下一代双亲（不做合并）
      · 若轨迹完全收敛 → 无需组合，返回 base（单调性保证：不退化）

    返回 {next_harness, decisions: [...], rationale}
    """
    decisions = []
    by_name = {r.harness_name: r for r in runs}
    base_run = by_name.get(base.name) or runs[0]

    # 收集每个 harness 的维度设置（从 harness 对象拿，需要外部传入 name→harness 映射）
    return {"note": "see _compose_with_harnesses", "diff_converged": diff["converged"],
            "decisions": decisions, "base_run_name": base_run.harness_name}


def _compose_with_harnesses(base: ProofHarness, harnesses: list, runs: list,
                            diff: dict, rank: dict) -> dict:
    """带 harness 对象的 Compose（能真正改维度）。

    单调性保证（最重要的规则，优先于一切）：
      若**基线自己已经全部通过**（lean_ok=True），则不做任何编辑、直接保持基线。
      否则「改进」会变成「在已通过的基础上瞎改」，这正是 AIDE² 报告的退化来源。
    """
    h_by_name = {h.name: h for h in harnesses}
    r_by_name = {r.harness_name: r for r in runs}
    baseline_run = r_by_name.get(base.name) or runs[0]
    decisions = []

    # ⓪ 单调性：基线全过 → 保持（不改、不选别人）
    if baseline_run.lean_ok is True:
        return {"next": base.to_dict(), "decisions": [
            {"action": "keep",
             "reason": "基线已在 %d 步全部通过（lean_ok=True），按单调性保持不动" % len(baseline_run.steps)}],
            "rationale": "baseline already passes → no edit (monotonicity)", "n_edits": 0}

    if diff["converged"]:
        return {"next": base.to_dict(), "decisions": [
            {"action": "keep", "reason": "轨迹完全收敛且基线未通过，无可归因分歧"}],
            "rationale": "no divergence → no edit", "n_edits": 0}

    # 逐个分歧步：找「基准失败但别人成功」的维度
    edit_dims = {}
    for dv in diff["divergences"]:
        sid = dv["step_id"]
        if "outcome_diverge" not in dv["kinds"]:
            continue
        b_step = next((s for s in baseline_run.steps if s.step_id == sid), None)
        if b_step is None or b_step.ok:
            continue                     # 基准没失败 → 不需要改
        # 谁的这一步成功了？
        winners = []
        for r in runs:
            if r.harness_name == baseline_run.harness_name:
                continue
            s = next((x for x in r.steps if x.step_id == sid), None)
            if s is not None and s.ok:
                winners.append(r.harness_name)
        if not winners:
            continue
        # 取第一个 winner，比对它与基准的维度差异
        w = h_by_name.get(winners[0])
        if not w:
            continue
        for dim in ("prompt_style", "memory_policy", "scaffold_phase", "parallelism"):
            if getattr(w, dim) != getattr(base, dim):
                edit_dims[dim] = (getattr(w, dim), sid, winners[0])

    # 应用编辑
    nd = base.to_dict()
    for dim, (val, sid, wn) in edit_dims.items():
        old = nd.get(dim)
        nd[dim] = val
        decisions.append({"action": "adopt", "dim": dim, "from": old, "to": val,
                          "because": "step %s failed under baseline but passed under %s" % (sid, wn)})
    nd["name"] = "composed_r1"
    nd["lineage"] = base.fingerprint()
    next_h = ProofHarness.from_dict(nd)

    # 若没有可归因的维度编辑（例如分歧都是 structural_gap），退化为「保留最优变体」
    if not decisions:
        # 用 Jev 排序的第一名（若可用）或第一个非基准 harness
        pick = None
        if rank.get("available"):
            top_label = rank["order"][0][0] if rank.get("order") else None
            for h in harnesses:
                if top_label and top_label.startswith(h.name):
                    pick = h
                    break
        if pick is None:
            pick = harnesses[1] if len(harnesses) > 1 else base
        return {"next": pick.to_dict(), "decisions": [
            {"action": "select", "reason": "无单维可归因编辑，保留候选 %s" % pick.name}],
            "rationale": "no attributable single-dim edit", "n_edits": 0}

    return {"next": next_h.to_dict(), "decisions": decisions,
            "rationale": "%d 个单维编辑，每个都对应一处「基准失败/他者成功」的分歧步" % len(decisions),
            "n_edits": len(decisions)}


# ── 主流程 ────────────────────────────────────────────────────────
def run_mvp0(conjecture: str = DEFAULT_CONJECTURE, n: int = 4, rounds: int = 1,
             outdir: str = None, verbose: bool = True) -> dict:
    t_start = time.time()
    report = {
        "conjecture": conjecture.strip()[:200],
        "n_harnesses": n, "rounds": rounds,
        "pipeline_steps": PIPELINE,
        "jev_available": probe_health(),
        "rounds_detail": [],
    }

    base = ProofHarness.baseline()
    cur = base
    for rd in range(rounds):
        t0 = time.time()
        # ① Propose
        harnesses = propose_edits(cur, n=n)
        if verbose:
            print("\n" + "=" * 72)
            print("ROUND %d  Propose: %d 个 harness" % (rd + 1, len(harnesses)))
            print("=" * 72)
            for h in harnesses:
                print("  %-20s style=%-8s mem=%-13s scaffold=%-5s p=%d  fp=%s" % (
                    h.name, h.prompt_style, h.memory_policy, h.scaffold_phase,
                    h.parallelism, h.fingerprint()))

        # ② Probe：N 路并行
        memory = {"archive_priors": [{"strategy": "axiomatize", "gain": 0.31},
                                     {"strategy": "tactic_complete", "gain": 0.22}]}
        runs = run_fleet(harnesses, conjecture, memory=memory, max_workers=min(n, 8))
        probe_s = time.time() - t0

        # ③ Arbiter：唯一判定
        arb = [arbitrate(r) for r in runs]

        if verbose:
            print("\n  Probe: %.2fs（%d 路并行）  Arbiter 已写回判定" % (probe_s, n))
            print("  %-20s %6s %6s %7s  %s" % ("harness", "steps", "ok", "lean", "verdict"))
            for r, a in zip(runs, arb):
                print("  %-20s %6d %6d %7s  %s" % (
                    r.harness_name, len(r.steps), sum(s.ok for s in r.steps),
                    a["lean_ok"], a["verdict"]))

        # ④ Diff
        diff = diff_runs(runs, step_order=PIPELINE)
        if verbose:
            print()
            print(render_report(diff))

        # ⑤ Rank（只在都过关的候选里排；不可用则降级）
        passed = [r for r, a in zip(runs, arb) if a["verdict"] == "PASS"]
        rank = rank_runs(passed) if passed else {"available": False, "order": [], "mode": "no_pass"}
        if verbose:
            print("Rank mode=%s available=%s" % (rank["mode"], rank.get("available")))
            for lab, p in (rank.get("order") or [])[:4]:
                print("   %-40s %.3f" % (lab[:40], p))
            if rank.get("reason"):
                print("   reason:", rank["reason"])

        # ⑥ Compose
        comp = _compose_with_harnesses(cur, harnesses, runs, diff, rank)
        if verbose:
            print("\nCompose: n_edits=%d  %s" % (comp["n_edits"], comp["rationale"]))
            for d in comp["decisions"]:
                print("   %s" % json.dumps(d, ensure_ascii=False))

        report["rounds_detail"].append({
            "round": rd + 1,
            "harnesses": [h.to_dict() for h in harnesses],
            "fleet_wall_s": round(probe_s, 3),
            "arbiter": arb,
            "diff": {k: v for k, v in diff.items() if k != "per_step"},
            "rank": rank,
            "compose": comp,
        })
        cur = ProofHarness.from_dict(comp["next"])   # 保留 compose 给的 name（composed_r1）

    report["wall_s"] = round(time.time() - t_start, 3)
    report["final_harness"] = cur.to_dict()

    if outdir:
        p = Path(outdir); p.mkdir(parents=True, exist_ok=True)
        (p / "mvp0_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        if verbose:
            print("\n-> %s" % (p / "mvp0_report.json"))

    return report


# ── 自测 ──────────────────────────────────────────────────────────
def _self_test() -> int:
    print("=== MVP-0 自测（离线，无需 Lean / API key / Jev 端点）===")
    rep = run_mvp0(n=4, rounds=1, outdir=None, verbose=True)

    prints = []
    prints.append(("4 路并行", len(rep["rounds_detail"][0]["harnesses"]) == 4))
    d0 = rep["rounds_detail"][0]
    prints.append(("Arbiter 写回 4 份", len(d0["arbiter"]) == 4
                   and all(a["verdict"] in ("PASS", "BLOCK") for a in d0["arbiter"])))
    prints.append(("轨迹有分歧", d0["diff"]["converged"] is False))
    prints.append(("抽到首个分歧步", d0["diff"]["first_divergence"] is not None))
    prints.append(("Compose 产出下一代", rep["final_harness"]["name"] == "composed_r1"))
    prints.append(("回写报告可序列化", bool(json.dumps(rep, ensure_ascii=False))))

    print("\n" + "=" * 72)
    for name, ok in prints:
        print("  %-24s %s" % (name, "✅" if ok else "❌"))
    allok = all(ok for _, ok in prints)
    print("=" * 72)
    print("[OK] mvp0 self-test 通过" if allok else "[FAIL] mvp0 self-test 未通过")
    return 0 if allok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MVP-0 四路并行最小闭环")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--conjecture", default=DEFAULT_CONJECTURE)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--output", default=None, help="报告目录")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    rep = run_mvp0(a.conjecture, n=a.n, rounds=a.rounds, outdir=a.output)
    print("\n总耗时 %.2fs" % rep["wall_s"])
