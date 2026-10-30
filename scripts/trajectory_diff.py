#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trajectory_diff — 多路证明轨迹对比，抽「首个分歧步 + 分歧原因」

对齐 Google Research Harness² 的核心洞察：
  它**刻意不要 ground-truth 打分器**（RunView 只带 delivered / ok / trajectory），
  而是从**多个候选 harness 跑同一任务的行为轨迹差异**里组合出更好的 harness。
  理由：一个标量 gain 告诉不了你「哪一步开始分叉」，而分歧步才是可归因的改进依据。

解决的问题（本技能的真实痛点）：
  当前 `stage36_evolution.py` 的 archive.jsonl 只存
  `{gain, defects_before, defects_after, mutation_strategy}` 这类**标量摘要**。
  Stage A strict-superset 实验里最关键的那条信息——
  「第 N 步 `deriv I_cycle = 0` 把 CGICE 动力学杀掉」——
  是靠人工比对才发现的，因为标量摘要把它丢了。本模块把这一步自动化。

设计分离（严格遵守）：
  · 本模块**只读**轨迹，不产生任何正确性判定。
  · `lean_ok` 字段由 Arbiter 写入，本模块只做**对齐与对比**，不重新评判。
  · 输出仅用于「解释 harness 之间的差异」，不得作为 gate 的输入。

对齐算法：
  不同 harness 步骤数可能不同（如 scaffold_off 少一步「T01 skeleton」）。
  用 LCS（最长公共子序列）在 step_id 序列上对齐，未对齐的步标为 `gap`。
  这样可以识别三种分歧：
    ① outcome_diverge  同一步骤，ok 不同（最硬的信号）
    ② output_diverge   同一步骤都 ok，但产物摘要不同（语义分歧，需 L2 深看）
    ③ structural_gap   某 harness 少了/多了一步（harness 结构导致）

用法：
    from trajectory_diff import diff_runs, render_report
    d = diff_runs(runs)                    # runs: list[ProofRun]
    print(render_report(d))

自测：
    python trajectory_diff.py --self-test
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ── 数据结构 ───────────────────────────────────────────────────────
@dataclass
class Step:
    """轨迹中的一步（对应一个 L2 micro-agent 的执行）。"""
    step_id: str                 # 稳定 id，如 "P01" / "T06" / "E01"（跨 harness 可比）
    agent: str = ""              # 语义名，仅展示用
    tool: str = ""               # 调用的工具
    ok: bool = True
    output_sig: str = ""         # 产物摘要指纹（同一步骤在不同 harness 下的产物差异）
    detail: str = ""             # 人类可读摘要（前 200 字）
    duration_s: float = 0.0

    def key(self) -> str:
        return self.step_id


@dataclass
class ProofRun:
    """一个 harness 在某个 conjecture 上的一次完整运行。

    ⚠️ lean_ok / sorry_count / axiom_count **只能由 Arbiter 写**（agent_fleet.arbitrate）。
       本模块与 Composer 只读不写，防止 verifier 泄漏进 harness 精炼路径。
    """
    harness_name: str
    harness_fingerprint: str = ""
    steps: list = field(default_factory=list)      # list[Step]
    lean_ok: Optional[bool] = None                 # Arbiter 写
    sorry_count: Optional[int] = None              # Arbiter 写
    axiom_count: Optional[int] = None              # Arbiter 写
    audit_verdict: Optional[str] = None            # Arbiter 写（BLOCK/WARN/PASS）
    wall_s: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ProofRun":
        steps = [Step(**s) if isinstance(s, dict) else s for s in d.get("steps", [])]
        known = {f for f in cls.__dataclass_fields__}
        kw = {k: v for k, v in d.items() if k in known and k != "steps"}
        return cls(steps=steps, **kw)


# ── LCS 对齐 ──────────────────────────────────────────────────────
def _lcs_pairs(seq_a: list, seq_b: list) -> list:
    """返回最长公共子序列的 (i, j) 下标对。"""
    n, m = len(seq_a), len(seq_b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if seq_a[i] == seq_b[j] else max(dp[i + 1][j], dp[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if seq_a[i] == seq_b[j]:
            pairs.append((i, j)); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def align_runs(runs: list, step_order: Optional[list] = None) -> dict:
    """把 N 条轨迹对齐到「并集步骤序列」。

    step_order：已知的逻辑步骤顺序（如 agent_fleet.PIPELINE）。传了它，分歧就按
        **证明流程顺序**报告（首个分歧 = 流程上最早出问题的那个），而不是按
        「谁先被跑出来」——后者在 scaffold_off 这类少步骤 harness 下会把顺序搞乱。
    返回 {step_id: {run_index: Step|None}}。
    """
    if not runs:
        return {}
    all_ids, seen = [], set()
    for sid in (step_order or []):
        if sid not in seen:
            seen.add(sid); all_ids.append(sid)
    for r in runs:
        for s in r.steps:
            if s.key() not in seen:
                seen.add(s.key()); all_ids.append(s.key())

    table = {sid: {} for sid in all_ids}
    for ri, r in enumerate(runs):
        by_id = {s.key(): s for s in r.steps}
        for sid in all_ids:
            table[sid][ri] = by_id.get(sid)
    return table


# ── 分歧检测 ──────────────────────────────────────────────────────
def diff_runs(runs: list, baseline_index: int = 0,
              step_order: Optional[list] = None) -> dict:
    """对比 N 条轨迹，输出分歧清单。

    baseline_index：以哪条为基准（默认第 0 条 = harness 列表里的第一个）。
    step_order    ：逻辑步骤顺序（传 agent_fleet.PIPELINE 即按证明流程排序分歧）。
    返回结构：
      {
        "runs": [{name, fingerprint, lean_ok, sorry, axioms, verdict, n_steps}],
        "first_divergence": {step_id, kind, detail} | None,
        "divergences": [...],          # 全部
        "converged": bool,             # 是否有任一步出现分歧
        "per_step": {step_id: {...}},
      }
    """
    if not runs:
        return {"runs": [], "first_divergence": None, "divergences": [], "converged": True,
                "per_step": {}}

    table = align_runs(runs, step_order=step_order)
    base = runs[baseline_index]
    divergences = []
    per_step = {}

    for sid, per_run in table.items():
        present = {ri: s for ri, s in per_run.items() if s is not None}
        missing = [runs[ri].harness_name for ri, s in per_run.items() if s is None]

        rec = {"step_id": sid, "present_in": len(present), "missing_in": missing,
               "kinds": [], "details": []}

        # 全场都缺这一步 → 不是分歧（step_order 里给了但没有任何 run 执行它）
        if not present:
            per_step[sid] = rec
            continue

        # ③ structural_gap：部分 harness 有、部分没有
        if missing:
            rec["kinds"].append("structural_gap")
            rec["details"].append("步骤缺失于: %s" % ", ".join(missing))

        if len(present) >= 2:
            oks = {ri: s.ok for ri, s in present.items()}
            if len(set(oks.values())) > 1:
                rec["kinds"].append("outcome_diverge")
                fail = [runs[ri].harness_name for ri, v in oks.items() if not v]
                rec["details"].append("ok 不一致，失败方: %s" % ", ".join(fail))

            sigs = {ri: (s.output_sig or s.detail[:80]) for ri, s in present.items()}
            if len(set(sigs.values())) > 1 and "outcome_diverge" not in rec["kinds"]:
                rec["kinds"].append("output_diverge")
                # 找与基准不同的第一个
                bsig = sigs.get(baseline_index)
                for ri, sg in sigs.items():
                    if ri != baseline_index and sg != bsig:
                        rec["details"].append("%s 的产物与基准不同: %r vs %r" % (
                            runs[ri].harness_name, (sg or "")[:50], (bsig or "")[:50]))
                        break

        per_step[sid] = rec
        if rec["kinds"]:
            divergences.append(rec)

    first = divergences[0] if divergences else None
    out = {
        "runs": [{
            "name": r.harness_name,
            "fingerprint": r.harness_fingerprint,
            "lean_ok": r.lean_ok,
            "sorry": r.sorry_count,
            "axioms": r.axiom_count,
            "verdict": r.audit_verdict,
            "n_steps": len(r.steps),
            "wall_s": round(r.wall_s, 2),
        } for r in runs],
        "first_divergence": first,
        "divergences": divergences,
        "converged": len(divergences) == 0,
        "per_step": per_step,
    }
    return out


def render_report(d: dict) -> str:
    """把 diff_runs 的结果渲染成人读报告。"""
    L = []
    L.append("=" * 72)
    L.append("轨迹对比报告（%d 条 harness）" % len(d["runs"]))
    L.append("=" * 72)
    L.append("%-20s %-14s %6s %6s %8s %7s %s" % (
        "harness", "fingerprint", "lean", "sorry", "axioms", "steps", "verdict"))
    for r in d["runs"]:
        L.append("%-20s %-14s %6s %6s %8s %7d %s" % (
            r["name"][:20], (r["fingerprint"] or "-")[:14],
            {True: "OK", False: "FAIL", None: "-"}[r["lean_ok"]],
            r["sorry"] if r["sorry"] is not None else "-",
            r["axioms"] if r["axioms"] is not None else "-",
            r["n_steps"], r["verdict"] or "-"))
    L.append("")
    if d["converged"]:
        L.append("轨迹完全收敛 —— 所有 harness 逐步一致，无可归因分歧。")
    else:
        fd = d["first_divergence"]
        L.append("首个分歧步：%s  [%s]" % (fd["step_id"], " + ".join(fd["kinds"])))
        for det in fd["details"]:
            L.append("    · %s" % det)
        L.append("")
        L.append("全部分歧步（%d 个）：" % len(d["divergences"]))
        for x in d["divergences"]:
            L.append("  %-8s %-32s %s" % (
                x["step_id"], "+".join(x["kinds"]),
                (x["details"][0] if x["details"] else "")[:80]))
    L.append("")
    L.append("注：lean/sorry/axioms/verdict 由 Arbiter 写入；本报告只做对齐与归因，不重新判定。")
    return "\n".join(L)


# ── 自测 ──────────────────────────────────────────────────────────
def _mk_run(name, spec, **kw):
    """spec: [(step_id, ok, sig)]"""
    steps = [Step(step_id=s, agent="a_" + s, tool="t", ok=o, output_sig=g) for s, o, g in spec]
    return ProofRun(harness_name=name, steps=steps, **kw)


def _self_test() -> int:
    ORDER = ["P01", "P03", "T01", "T06", "T07", "H02", "H05", "E01", "E02", "E06"]

    # 场景 1：完全收敛
    a = _mk_run("h_a", [("P01", True, "s1"), ("T01", True, "s2"), ("E01", True, "s3")])
    b = _mk_run("h_b", [("P01", True, "s1"), ("T01", True, "s2"), ("E01", True, "s3")])
    d = diff_runs([a, b])
    assert d["converged"], "应判定收敛"
    print("[1] 收敛场景 OK")

    # 场景 2：outcome_diverge —— 两条轨迹都有 T06，一个成功一个失败
    a2 = _mk_run("h_a2", [("P01", True, "s1"), ("T01", True, "s2"),
                          ("T06", True, "ok"), ("E01", True, "s3")])
    c2 = _mk_run("h_c2", [("P01", True, "s1"), ("T01", True, "s2"),
                          ("T06", False, "boom"), ("E01", True, "s3")])
    d2 = diff_runs([a2, c2], step_order=ORDER)
    assert not d2["converged"]
    fd = d2["first_divergence"]
    assert fd["step_id"] == "T06", "首个分歧应为 T06，实际 %s" % fd["step_id"]
    assert "outcome_diverge" in fd["kinds"], "kinds=%s" % fd["kinds"]
    print("[2] outcome_diverge OK -> %s [%s]" % (fd["step_id"], "+".join(fd["kinds"])))

    # 场景 3：structural_gap —— 某条 harness 根本没有这一步
    e = _mk_run("h_e", [("P01", True, "s1"), ("T01", True, "s2")])
    d3 = diff_runs([a, e], step_order=ORDER)
    assert any("structural_gap" in x["kinds"] for x in d3["divergences"]), \
        "应检出 structural_gap，实际 %s" % [x["kinds"] for x in d3["divergences"]]
    print("[3] structural_gap OK")

    # 场景 4：output_diverge —— 都 ok 但产物不同
    f_ = _mk_run("h_f", [("P01", True, "s1_diff"), ("T01", True, "s2"), ("E01", True, "s3")])
    d4 = diff_runs([a, f_])
    assert any("output_diverge" in x["kinds"] for x in d4["divergences"])
    print("[4] output_diverge OK")

    # 场景 5：序列化往返
    rt = ProofRun.from_dict(a.to_dict())
    assert rt.harness_name == a.harness_name and len(rt.steps) == len(a.steps)
    print("[5] 序列化往返 OK")

    # 场景 6：step_order 让分歧按逻辑顺序报告（而非首次出现顺序）
    g1 = _mk_run("g1", [("P01", True, "x"), ("E01", True, "y"), ("T01", False, "z")])
    g2 = _mk_run("g2", [("P01", True, "x"), ("E01", True, "y"), ("T01", True, "z")])
    no_order = diff_runs([g1, g2])
    with_order = diff_runs([g1, g2], step_order=ORDER)
    assert no_order["first_divergence"]["step_id"] == "T01"   # 两种情况都应是 T01
    assert with_order["first_divergence"]["step_id"] == "T01"
    # 但 with_order 下 per_step 的键顺序应服从 ORDER
    keys = list(with_order["per_step"].keys())
    assert keys.index("P01") < keys.index("T01") < keys.index("E01"), \
        "step_order 未生效: %s" % keys
    print("[6] step_order 排序 OK -> %s" % keys)

    print()
    print(render_report(d2))
    print("\n[OK] trajectory_diff self-test 全部通过")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="trajectory_diff — 多路轨迹对比")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--runs", help="runs.json（list[ProofRun]）")
    ap.add_argument("--output", help="报告输出路径(.json)")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    if a.runs:
        runs = [ProofRun.from_dict(x) for x in json.load(open(a.runs, encoding="utf-8"))]
        d = diff_runs(runs)
        print(render_report(d))
        if a.output:
            json.dump(d, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("\n->", a.output)
    else:
        ap.print_help()
