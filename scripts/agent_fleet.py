#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_fleet — L2 微观 agent 注册表 + 并行调度 + Arbiter（唯一判定入口）

设计要点（与本技能既定原则一致）：
  ① **Arbiter 独占判定权**：只有 `arbitrate()` 能写 {lean_ok, sorry_count, axiom_count,
     audit_verdict}。任何 harness / Composer / Proposer 都读不到、写不了这些字段。
     这是「harness2 无 verifier」与「Lean 硬验证」能共存的前提。
  ② **agent 只产出结构化轨迹**：每步记录 {step_id, tool, ok, output_sig, detail}，
     供 trajectory_diff 对比。agent 自己不做「证明对不对」的判断。
  ③ **MVP 阶段 agent 用确定性 mock**：接口真实、行为可复现，不依赖 Lean/LLM/API key，
     这样 4 路并行闭环能离线跑通。替换成真实现时只改 `_EXEC` 表里的函数体。

MVP 注册的 10 个 agent（对应 SKILL.md 里 L2 的 45 个证明环节里的最高价值子集）：
  P01 StatementTranslator     猜想 → Lean 命题骨架
  P03 TargetStrengthAuditor   目标强度分层（最弱稳定陈述）
  T01 SkeletonGenerator       三阶段脚手架：先出 stub
  T06 ProofStateDebugger      编译报错 → 定位具体 goal
  T07 SorryEliminator         sorry → 具体构造
  H02 ConditionalRefactorer   无条件公理 → 条件定理
  H05 PerformativeHonestyDet 注释声称诚实但代码无条件
  E01 AxiomDependencyPrinter  #print axioms 全定理扫描
  E02 GoldenGateChecker       只依赖经典逻辑三件套
  E06 ChainClosureAuditor     端到端闭合判定

用法：
    from agent_fleet import run_proof, REGISTRY, arbitrate
    run = run_proof(harness, conjecture="...")   # -> ProofRun
    res = arbitrate(run, lean_output)            # -> {lean_ok, sorry, axioms, verdict}

自测：
    python agent_fleet.py --self-test
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from proof_harness import ProofHarness
from trajectory_diff import ProofRun, Step

# ── agent 定义 ────────────────────────────────────────────────────
@dataclass
class MicroAgent:
    step_id: str
    name: str
    tool: str
    role: str
    requires: list = field(default_factory=list)   # 上游 step_id
    timeout_s: float = 30.0
    retries: int = 1


REGISTRY = {
    a.step_id: a for a in [
        MicroAgent("P01", "StatementTranslator", "mathlib_lookup",
                   "自然语言猜想 → Lean 命题骨架（最弱稳定形式）", []),
        MicroAgent("P03", "TargetStrengthAuditor", "mathlib_lookup",
                   "目标强度分层：拒绝把观测常数硬编码进目标", ["P01"]),
        MicroAgent("T01", "SkeletonGenerator", "lean_compile",
                   "三阶段脚手架：先出 `:= by sorry` 骨架验证命题结构", ["P03"]),
        MicroAgent("T06", "ProofStateDebugger", "lean_compile",
                   "编译报错 → 定位到具体 goal 与缺失假设", ["T01"]),
        MicroAgent("T07", "SorryEliminator", "lean_compile",
                   "sorry → 具体构造（calc/have/ring/linarith）", ["T06"]),
        MicroAgent("H02", "ConditionalRefactorer", "template_library",
                   "无条件公理 → 条件定理（前提显式化为 axiom … : Prop）", ["T07"]),
        MicroAgent("H05", "PerformativeHonestyDetector", "content_audit",
                   "检测注释声称诚实但代码实为无条件公理", ["H02"]),
        MicroAgent("E01", "AxiomDependencyPrinter", "lean_compile",
                   "#print axioms 扫描全部定理的依赖", ["H05"]),
        MicroAgent("E02", "GoldenGateChecker", "dag_audit",
                   "验证只依赖 propext / Classical.choice / Quot.sound", ["E01"]),
        MicroAgent("E06", "ChainClosureAuditor", "dag_audit",
                   "端到端证据链闭合判定（唯一能宣布 closed 的 agent）", ["E02"]),
    ]
}

# 拓扑序（MVP 固定，真实现时从 preproof_decomposer 读 DAG）
PIPELINE = ["P01", "P03", "T01", "T06", "T07", "H02", "H05", "E01", "E02", "E06"]


# ── 确定性 mock 执行器（MVP）──────────────────────────────────────
# 每个函数返回 (ok, output_sig, detail)。行为由 harness 特征 + conjecture 哈希决定，
# 保证「可控实验」：不同 harness 会在可预测的步骤上分叉。
def _h(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:10]


def _exec_P01(h: ProofHarness, conj: str, ctx: dict):
    sig = _h("stmt", conj, h.prompt_style)
    return True, sig, "statement skeleton (style=%s)" % h.prompt_style


def _exec_P03(h: ProofHarness, conj: str, ctx: dict):
    # fewshot prompt 能避开「硬编码常数」这一失败模式
    ok = h.prompt_style in ("detailed", "fewshot")
    sig = _h("strength", conj, ok)
    det = "weakest-stable form" if ok else "REJECTED: hard-coded observed constant"
    return ok, sig, det


def _exec_T01(h: ProofHarness, conj: str, ctx: dict):
    # 无脚手架的 harness 在这一步拿不到可编译骨架
    if not h.scaffold_phase:
        return False, _h("skel_fail", conj), "no scaffold: skeleton absent, downstream blocked"
    sig = _h("skel", conj)
    return True, sig, "stub skeleton compiles"


def _exec_T06(h: ProofHarness, conj: str, ctx: dict):
    # 上游（T01）失败的传导
    if not ctx.get("T01", {}).get("ok", False):
        return False, _h("t06_blocked", conj), "blocked: no skeleton to debug"
    # 有 recent 记忆的 harness 能定位得更准
    ok = h.memory_policy != "none"
    sig = _h("debug", conj, ok)
    det = "goal localized" if ok else "goal localization failed (no memory of prior attempts)"
    return ok, sig, det


def _exec_T07(h: ProofHarness, conj: str, ctx: dict):
    if not ctx.get("T06", {}).get("ok", False):
        return False, _h("t07_blocked", conj), "blocked: goal not localized"
    ok = h.allows("lean_compile")
    sig = _h("elim", conj, ok)
    det = "sorry eliminated with concrete tactics" if ok else "cannot compile: lean_compile not whitelisted"
    return ok, sig, det


def _exec_H02(h: ProofHarness, conj: str, ctx: dict):
    # archive 先验显著提高条件定理重构成功率（这是 memory_policy 的价值点）
    boost = 0.35 if h.memory_policy == "archive_prior" else 0.0
    base = 0.55 if h.prompt_style in ("detailed", "fewshot") else 0.35
    ok = (base + boost) >= 0.85
    sig = _h("cond", conj, ok)
    det = ("premise promoted to `axiom … : Prop` + `_conditional` form"
           if ok else "still an unconditional axiom (performative honesty risk)")
    return ok, sig, det


def _exec_H05(h: ProofHarness, conj: str, ctx: dict):
    if not h.allows("content_audit"):
        return False, _h("h05_skip", conj), "content_audit not whitelisted → cannot verify honesty"
    bad = not ctx.get("H02", {}).get("ok", False)
    return (not bad), _h("honesty", conj, bad), (
        "no performative honesty" if not bad else "BLOCK: comment claims honesty, code has bare axiom")


def _exec_E01(h: ProofHarness, conj: str, ctx: dict):
    if not h.allows("lean_compile"):
        return False, _h("e01_skip", conj), "cannot #print axioms without lean_compile"
    ok = ctx.get("H05", {}).get("ok", False)
    return ok, _h("axdeps", conj, ok), ("axiom deps dumped" if ok else "skipped: upstream BLOCK")


def _exec_E02(h: ProofHarness, conj: str, ctx: dict):
    if not ctx.get("E01", {}).get("ok", False):
        return False, _h("e02_skip", conj), "no axiom deps to check"
    ok = ctx.get("H02", {}).get("ok", False)
    return ok, _h("golden", conj, ok), ("only propext/choice/Quot.sound" if ok
                                        else "non-classical axiom present")


def _exec_E06(h: ProofHarness, conj: str, ctx: dict):
    chain_ok = all(ctx.get(s, {}).get("ok", False) for s in PIPELINE[:-1])
    sig = _h("closure", conj, chain_ok)
    return chain_ok, sig, ("evidence chain CLOSED" if chain_ok else "chain INCOMPLETE")


_EXEC: dict = {
    "P01": _exec_P01, "P03": _exec_P03, "T01": _exec_T01, "T06": _exec_T06,
    "T07": _exec_T07, "H02": _exec_H02, "H05": _exec_H05, "E01": _exec_E01,
    "E02": _exec_E02, "E06": _exec_E06,
}


def run_agent(step_id: str, harness: ProofHarness, conj: str, ctx: dict) -> Step:
    """执行单个 agent（含超时/重试）。"""
    ag = REGISTRY[step_id]
    fn = _EXEC[step_id]
    last_err = ""
    for attempt in range(ag.retries + 1):
        t0 = time.time()
        try:
            ok, sig, det = fn(harness, conj, ctx)
            return Step(step_id=step_id, agent=ag.name, tool=ag.tool, ok=ok,
                        output_sig=sig, detail=det[:200], duration_s=round(time.time() - t0, 3))
        except Exception as e:              # 记录后重试
            last_err = "%s: %s" % (type(e).__name__, e)
    return Step(step_id=step_id, agent=ag.name, tool=ag.tool, ok=False,
                output_sig=_h("err", step_id), detail=("agent error: " + last_err)[:200])


def run_proof(harness: ProofHarness, conjecture: str, memory: Optional[dict] = None,
              max_workers: int = 4) -> ProofRun:
    """跑一轮完整证明（沿 PIPELINE 串行，agent 内部可按 harness.parallelism 并行）。

    MVP 的串联是必要的：每一步依赖上一步产物（真实 DAG 也一样）。
    「4 路并行」指的是**4 个 harness 并行**，由 run_fleet 负责。
    """
    ctx: dict = {}
    steps: list = []
    t0 = time.time()
    for sid in PIPELINE:
        st = run_agent(sid, harness, conjecture, ctx)
        ctx[sid] = {"ok": st.ok, "sig": st.output_sig, "detail": st.detail}
        steps.append(st)
        if not st.ok and sid in ("T01", "H05"):   # 硬阻断：下游无意义
            break
    return ProofRun(harness_name=harness.name,
                    harness_fingerprint=harness.fingerprint(),
                    steps=steps, wall_s=round(time.time() - t0, 3))


# ── 并行跑多个 harness（Harness² 的 Probe 阶段）────────────────────
def run_fleet(harnesses: list, conjecture: str, memory: Optional[dict] = None,
              max_workers: int = 4) -> list:
    """4 路（或任意路）并行跑同一个 conjecture，每个 harness 一个线程。"""
    results = [None] * len(harnesses)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_proof, h, conjecture, memory, max_workers): i
                for i, h in enumerate(harnesses)}
        for fu in cf.as_completed(futs):
            i = futs[fu]
            try:
                results[i] = fu.result()
            except Exception as e:
                h = harnesses[i]
                results[i] = ProofRun(harness_name=h.name,
                                      harness_fingerprint=h.fingerprint(), steps=[],
                                      wall_s=0.0)
                results[i].steps = [Step(step_id="ERR", agent="fleet", ok=False,
                                         detail="%s: %s" % (type(e).__name__, e))]
    return results


# ── Arbiter：唯一有权判定的人 ─────────────────────────────────────
def arbitrate(run: ProofRun, lean_output: Optional[dict] = None) -> dict:
    """把运行轨迹交给硬验证器，写回 lean_ok / sorry / axioms / verdict。

    lean_output 结构（真实现由 Lean 编译 + Stage 3.5 审计产出）：
      {"compiled": bool, "sorry": int, "axioms": int,
       "audit": "PASS"|"WARN"|"BLOCK", "note": str}

    ⚠️ 这是**唯一**写这四个字段的函数。Composer 只读，不得调用本函数。
    """
    lo = lean_output or {}
    # MVP：若未提供真实编译结果，用轨迹里的 E06（链闭合）+ H05（诚实性）推断
    if not lo:
        by_id = {s.step_id: s for s in run.steps}
        chain = by_id.get("E06")
        honesty = by_id.get("H05")
        compiled = bool(chain and chain.ok)
        sorry = 0 if compiled else 1
        axioms = 0 if compiled else 1
        audit = "PASS" if compiled else "BLOCK"
        note = "inferred from trajectory (no lean_output supplied)"
    else:
        compiled = bool(lo.get("compiled"))
        sorry = int(lo.get("sorry", 0))
        axioms = int(lo.get("axioms", 0))
        audit = lo.get("audit", "PASS")
        note = lo.get("note", "")

    run.lean_ok = compiled
    run.sorry_count = sorry
    run.axiom_count = axioms
    run.audit_verdict = audit
    return {"lean_ok": compiled, "sorry": sorry, "axioms": axioms,
            "verdict": audit, "note": note}


# ── 自测 ──────────────────────────────────────────────────────────
def _self_test() -> int:
    print("REGISTRY: %d agents" % len(REGISTRY))
    for sid in PIPELINE:
        a = REGISTRY[sid]
        print("  %-4s %-28s tool=%-16s requires=%s" % (
            a.step_id, a.name, a.tool, a.requires or "-"))

    conj = "g_TC^2 = 24*pi^2/35"
    base = ProofHarness.baseline()

    # 单跑
    r = run_proof(base, conj)
    print("\n单跑 baseline: %d 步, %d ok" % (len(r.steps), sum(s.ok for s in r.steps)))
    for s in r.steps:
        print("  %-4s %-5s %s" % (s.step_id, "OK" if s.ok else "FAIL", s.detail[:60]))

    # 4 路并行
    from proof_harness import propose_edits
    hs = propose_edits(base, n=4)
    t0 = time.time()
    runs = run_fleet(hs, conj, max_workers=4)
    print("\n4 路并行: %.2fs" % (time.time() - t0))
    for run in runs:
        ar = arbitrate(run)
        print("  %-20s steps=%2d ok=%2d lean=%-5s verdict=%s" % (
            run.harness_name, len(run.steps),
            sum(s.ok for s in run.steps), ar["lean_ok"], ar["verdict"]))

    # Arbiter 写回检查
    assert all(r.lean_ok is not None for r in runs), "Arbiter 未写回"
    print("\nArbiter 写回 OK（lean_ok / sorry / axioms / verdict 均非 None）")

    print("\n[OK] agent_fleet self-test 全部通过")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="agent_fleet — L2 agent 调度 + Arbiter")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--conjecture", default="g_TC^2 = 24*pi^2/35")
    ap.add_argument("--harnesses", type=int, default=4)
    ap.add_argument("--output", help="runs.json 输出路径")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    from proof_harness import propose_edits
    hs = propose_edits(ProofHarness.baseline(), a.harnesses)
    runs = run_fleet(hs, a.conjecture, max_workers=a.harnesses)
    for r in runs:
        arbitrate(r)
    print(json.dumps([r.to_dict() for r in runs], ensure_ascii=False, indent=1)[:2000])
    if a.output:
        json.dump([r.to_dict() for r in runs], open(a.output, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n->", a.output)
