#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_fleet_real — 10 个 L2 agent 的真实现（MVP-1）

与 `agent_fleet.py` 的关系：
  · `agent_fleet.py`    = 调度骨架 + 10 个确定性 mock（离线单测用，零依赖）
  · `agent_fleet_real.py` = 同一批 10 个 agent 的**真实现**，读真实 Lean 文件 + 调真实审计脚本
  两者共享 `ProofRun` / `Step` / `PIPELINE` / `arbitrate`，接口完全一致。

诚实边界（本机实测：**Lean 编译器未安装**，`~/.elan` 不存在）：
  10 个 agent 里有 4 个天然需要编译（T01/T06/T07/E01）。这 4 个在本机上走
  **静态投影**：从源码结构推断「如果编译会得到什么」，并在 detail 里显式打
  `[degraded: no lean]`。**不假装编译成功**——这是本技能一贯的诚实原则。
  其余 6 个（P01/P03/H02/H05/E02/E06）本来就是静态可判的，走完整真实现。

真实可调的审计脚本（直接 import，非 subprocess）：
  · physical_content_audit.audit(lean_text) → 定义重言式 / 浅层证明 / 退化输入
  · proof_dag_audit.audit(lean_text)        → 冗余引理 / 未用 axiom / 悬空引用

用法：
    from agent_fleet_real import run_proof_real, run_fleet_real
    run = run_proof_real(harness, "path/to/proof.lean")
    res = arbitrate(run)          # 与 mock 版同一个 Arbiter

回归：
    python agent_fleet_real.py --self-test
        → 在 V64(A30_Formal_Verification.lean) 与 CGICE(cgice_proof.lean) 上跑 4 路并行
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional

from proof_harness import ProofHarness
from trajectory_diff import ProofRun, Step
from agent_fleet import MicroAgent, REGISTRY, PIPELINE, arbitrate, run_fleet

import physical_content_audit as pca
import proof_dag_audit as pda

# 经典逻辑三件套（v2.6.0 黄金门控标准）
CLASSICAL_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

# 硬编码常数的可疑形态：长小数 / 明显反推的观测值
_HARDCODED = re.compile(r"\b(?:0\.\d{6,}|\d{3,}\.\d{4,}|\d{2,}\.\d{2,}\s*\*\s*10)")
_AXIOM_DECL = re.compile(r"^\s*axiom\s+([A-Za-z_][A-Za-z0-9_'.]*)", re.M)
_THEOREM_DECL = re.compile(r"^\s*(?:theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_'.]*)", re.M)
_SORRY = re.compile(r"\bsorry\b")


def _sig(*parts) -> str:
    import hashlib
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:10]


def _strip_comments(text: str) -> str:
    text = re.sub(r"/-.*?-/", "", text, flags=re.S)
    text = re.sub(r"--[^\n]*", "", text)
    return text


class LeanFile:
    """一次读取 + 缓存解析结果，供 10 个 agent 共享。"""

    def __init__(self, path: str):
        self.path = path
        self.raw = Path(path).read_text(encoding="utf-8", errors="replace")
        self.code = _strip_comments(self.raw)
        self.axioms = _AXIOM_DECL.findall(self.code)                 # 含重复
        self.axiom_uniq = sorted(set(self.axioms))
        self.theorems = _THEOREM_DECL.findall(self.code)
        self.sorry_count = len(_SORRY.findall(self.code))
        self.sorry_lines = [i + 1 for i, l in enumerate(self.raw.splitlines())
                            if _SORRY.search(l) and not l.strip().startswith("--")]
        self.n_lines = len(self.raw.splitlines())
        # 真审计（各跑一次，缓存）
        self._pca = None
        self._dag = None
        self.ok_lean = False        # 本机无 Lean 编译器（探测见 --self-test）

    @property
    def pca(self) -> dict:
        if self._pca is None:
            try:
                self._pca = pca.audit(self.raw)
            except Exception as e:
                self._pca = {"error": "%s: %s" % (type(e).__name__, e)}
        return self._pca

    @property
    def dag(self) -> dict:
        if self._dag is None:
            try:
                self._dag = pda.audit(self.raw)
            except Exception as e:
                self._dag = {"error": "%s: %s" % (type(e).__name__, e)}
        return self._dag

    def theorem_bodies(self) -> list:
        """[(name, has_real_body, body_head)]"""
        out = []
        lines = self.code.splitlines()
        for i, l in enumerate(lines):
            m = re.match(r"^\s*(?:theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_'.]*)", l)
            if not m:
                continue
            # 往后找 := by 之后的第一段非空内容
            body, has_by = [], False
            for j in range(i, min(i + 40, len(lines))):
                if ":=" in lines[j]:
                    has_by = True
                    body.append(lines[j].split(":=", 1)[1])
                elif has_by:
                    body.append(lines[j])
            btxt = " ".join(body).strip()
            real = bool(btxt) and "by" in btxt and not re.fullmatch(r"by\s*sorry", btxt)
            out.append((m.group(1), real, btxt[:60]))
        return out


# ── 10 个 agent 的真实现 ───────────────────────────────────────────
def _P01(h: ProofHarness, L: LeanFile, ctx: dict):
    """StatementTranslator：确认猜想已被形式化为 Lean 命题。"""
    if not L.theorems:
        return False, _sig("p01", 0), "no theorem/lemma found — conjecture not formalized"
    sig = _sig("p01", tuple(L.theorems), h.prompt_style)
    return True, sig, "%d propositions found: %s" % (
        len(L.theorems), ", ".join(L.theorems[:3]))


def _P03(h: ProofHarness, L: LeanFile, ctx: dict):
    """TargetStrengthAuditor：目标里是否存在硬编码观测常数（参数化伪装）。"""
    hits = []
    for name, _, body in L.theorem_bodies():
        for m in _HARDCODED.finditer(body):
            hits.append((name, m.group(0)))
    # detailed / fewshot prompt 在这条上不改变文件事实，只改变判定严格度：
    #   concise  → 只报「出现即失败」；detailed → 要求 ≥2 处才算系统性
    strict = h.prompt_style != "concise"
    ok = len(hits) == 0 if strict else len(hits) < 2
    sig = _sig("p03", tuple(hits), h.prompt_style)
    det = ("no hard-coded observed constant in any conclusion"
           if ok else "hard-coded constants in conclusions: %s" % hits[:3])
    return ok, sig, det


def _P03_note(h: ProofHarness) -> str:
    return "[real]" if h.prompt_style != "concise" else "[real, lenient]"


def _T01(h: ProofHarness, L: LeanFile, ctx: dict):
    """SkeletonGenerator：每个 theorem 都要有真实证明体（非空、非纯 sorry）。"""
    if not h.scaffold_phase:
        return False, _sig("t01_noscaffold"), "scaffold disabled: no skeleton produced"
    bodies = L.theorem_bodies()
    empty = [n for n, real, _ in bodies if not real]
    ok = not empty
    sig = _sig("t01", tuple(empty))
    note = "" if L.ok_lean else " [degraded: no lean]"
    det = ("all %d propositions have a real proof body%s"
           % (len(bodies), note)) if ok else (
        "empty/sorry-only bodies: %s%s" % (empty[:4], note))
    return ok, sig, det


def _T06(h: ProofHarness, L: LeanFile, ctx: dict):
    """ProofStateDebugger：定位缺陷到具体行（Lean 不可用 → 静态投影）。"""
    if not ctx.get("T01", {}).get("ok", False):
        return False, _sig("t06_blocked"), "blocked: no valid skeleton"
    targets = []
    for f in (L.pca.get("findings") or []):
        if isinstance(f, dict):
            loc = f.get("line") or f.get("defect_location") or f.get("name")
            targets.append(str(loc))
    if L.sorry_lines:
        targets += ["sorry@L%d" % x for x in L.sorry_lines[:5]]
    ok = h.memory_policy != "none" and bool(targets)
    sig = _sig("t06", tuple(targets), h.memory_policy)
    det = ("localized %d defect sites%s" % (len(targets), " [degraded: no lean]")
           if targets else "no defect site localized%s" % (" [degraded: no lean]"))
    if not ok and targets:
        det = "memory_policy=none → cannot reuse prior localization: " + det
    return ok, sig, det


def _T07(h: ProofHarness, L: LeanFile, ctx: dict):
    """SorryEliminator：sorry 是否被消除（Lean 不可用 → 只统计，不修复）。"""
    if not ctx.get("T06", {}).get("ok", False):
        return False, _sig("t07_blocked"), "blocked: goal not localized"
    if not h.allows("lean_compile"):
        return False, _sig("t07_nowl"), "lean_compile not whitelisted"
    ok = L.sorry_count == 0
    sig = _sig("t07", L.sorry_count)
    det = ("0 sorry%s" % " [degraded: no lean, static count]"
           if ok else "%d sorry remain at lines %s [degraded: no lean, cannot retry]"
           % (L.sorry_count, L.sorry_lines[:5]))
    return ok, sig, det


def _H02(h: ProofHarness, L: LeanFile, ctx: dict):
    """ConditionalRefactorer：axiom 是否为条件定理模式（`: Prop` 显式前提）。"""
    if not L.axioms:
        return True, _sig("h02_none"), "no axiom — nothing to refactor"
    # 条件形式：axiom X : Prop   （前提是一个命题，由定理以 (h : X) 消费）
    cond = [a for a in L.axiom_uniq if re.search(
        r"axiom\s+%s\s*:\s*Prop\b" % re.escape(a), L.code)]
    bare = [a for a in L.axiom_uniq if a not in cond]
    ratio = len(cond) / max(len(L.axiom_uniq), 1)
    # archive_prior 记忆让 agent 更愿意把「裸公理」判为可重构
    need = 0.6 if h.memory_policy == "archive_prior" else 0.85
    ok = ratio >= need
    sig = _sig("h02", len(cond), len(bare), h.memory_policy)
    det = ("%d/%d axioms in conditional (Prop) form — %.0f%% ≥ %.0f%%"
           % (len(cond), len(L.axiom_uniq), ratio * 100, need * 100)) if ok else (
        "%d/%d conditional (%.0f%% < %.0f%%); bare axioms: %s"
        % (len(cond), len(L.axiom_uniq), ratio * 100, need * 100, bare[:4]))
    return ok, sig, det


def _H05(h: ProofHarness, L: LeanFile, ctx: dict):
    """PerformativeHonestyDetector：真调 physical_content_audit（返回 findings/stats/gate）。"""
    if not h.allows("content_audit"):
        return False, _sig("h05_nowl"), "content_audit not whitelisted"
    if "error" in L.pca:
        return False, _sig("h05_err"), "audit error: %s" % L.pca["error"]
    gate = str(L.pca.get("gate") or "").upper()
    findings = L.pca.get("findings") or []
    blocks = [f for f in findings if str(f.get("severity", "")).upper() == "BLOCK"]
    warns = [f for f in findings if str(f.get("severity", "")).upper() == "WARN"]
    ok = gate != "BLOCK" and not blocks
    sig = _sig("h05", gate, len(blocks), len(warns))
    if ok:
        det = "gate=%s, no performative honesty (%d WARN: %s)" % (
            gate or "?", len(warns),
            ", ".join(sorted({f.get("type", "?") for f in warns}))[:80] or "-")
    else:
        det = "gate=BLOCK, %d blocking finding(s): %s" % (
            len(blocks), [f.get("type") or f.get("theorem") for f in blocks[:2]])
    return ok, sig, det


def _E01(h: ProofHarness, L: LeanFile, ctx: dict):
    """AxiomDependencyPrinter：静态替代 #print axioms（列出全部 axiom 声明与使用）。"""
    if not h.allows("lean_compile"):
        return False, _sig("e01_nowl"), "lean_compile not whitelisted"
    used = {a: len(re.findall(r"\b%s\b" % re.escape(a), L.code)) - 1
            for a in L.axiom_uniq}
    orphan = [a for a, c in used.items() if c <= 0]
    sig = _sig("e01", tuple(sorted(used.items())))
    det = ("%d axioms dumped, %d unreferenced *within this file* "
           "[degraded: no lean; static count is file-local]") % (len(used), len(orphan))
    if orphan:
        det += " orphans: %s" % orphan[:3]
    return True, sig, det          # 本步只要求「能列出」，orphan 交给 E02/E06


def _E02(h: ProofHarness, L: LeanFile, ctx: dict):
    """GoldenGateChecker：只依赖经典逻辑三件套。"""
    if not ctx.get("E01", {}).get("ok", False):
        return False, _sig("e02_skip"), "no axiom deps to check"
    non_classical = [a for a in L.axiom_uniq if a not in CLASSICAL_AXIOMS]
    ok = not non_classical
    sig = _sig("e02", tuple(non_classical))
    det = ("only classical axioms" if ok else
           "%d non-classical research-level axioms present: %s"
           % (len(non_classical), non_classical[:4]))
    return ok, sig, det


def _E06(h: ProofHarness, L: LeanFile, ctx: dict):
    """ChainClosureAuditor：端到端证据链闭合。"""
    chain = all(ctx.get(s, {}).get("ok", False) for s in PIPELINE[:-1])
    reasons = [s for s in PIPELINE[:-1] if not ctx.get(s, {}).get("ok", False)]
    sig = _sig("e06", chain, tuple(reasons))
    det = ("evidence chain CLOSED (%d propositions, 0 sorry, classical axioms only)"
           % len(L.theorems)) if chain else (
        "chain INCOMPLETE — blocked at: %s" % ", ".join(reasons))
    return chain, sig, det


_EXEC_REAL = {
    "P01": _P01, "P03": _P03, "T01": _T01, "T06": _T06, "T07": _T07,
    "H02": _H02, "H05": _H05, "E01": _E01, "E02": _E02, "E06": _E06,
}


def run_proof_real(harness: ProofHarness, lean_path: str,
                   memory: Optional[dict] = None) -> ProofRun:
    """在真实 Lean 文件上跑一轮 10-agent 证明审计。"""
    import time
    t0 = time.time()
    L = LeanFile(lean_path)
    L.ok_lean = False                     # 本机无 Lean 编译器
    ctx: dict = {}
    steps: list = []
    for sid in PIPELINE:
        ag = REGISTRY[sid]
        try:
            ok, sig, det = _EXEC_REAL[sid](harness, L, ctx)
        except Exception as e:
            ok, sig, det = False, _sig("err", sid), "agent error: %s: %s" % (type(e).__name__, e)
        st = Step(step_id=sid, agent=ag.name, tool=ag.tool, ok=ok,
                  output_sig=sig, detail=str(det)[:200],
                  duration_s=round(time.time() - t0, 3))
        ctx[sid] = {"ok": ok, "sig": sig, "detail": det}
        steps.append(st)
        # 只有 P01（命题根本没找到）才硬阻断；T01 失败仍继续跑后面的静态审计，
        # 否则一个 sorry-only 定理会让 H02/H05/E01/E02 全部拿不到结果。
        if not ok and sid == "P01":
            break
    return ProofRun(harness_name=harness.name,
                    harness_fingerprint=harness.fingerprint(),
                    steps=steps, wall_s=round(time.time() - t0, 3))


def run_fleet_real(harnesses: list, lean_path: str, memory=None, max_workers: int = 4) -> list:
    """N 路并行（每个 harness 一份），在同一个真实文件上。"""
    import concurrent.futures as cf
    out = [None] * len(harnesses)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_proof_real, h, lean_path, memory): i
                for i, h in enumerate(harnesses)}
        for fu in cf.as_completed(futs):
            i = futs[fu]
            try:
                out[i] = fu.result()
            except Exception as e:
                out[i] = ProofRun(harness_name=harnesses[i].name,
                                  harness_fingerprint=harnesses[i].fingerprint(),
                                  steps=[Step(step_id="ERR", agent="fleet", ok=False,
                                              detail="%s: %s" % (type(e).__name__, e))])
    return out


# ── 回归：V64 + CGICE ─────────────────────────────────────────────
DEFAULT_TARGETS = {
    "V64_A30": r"<YOUR_HOME>\Desktop\AI论文\右手中微子与时间荷对偶\右手中微子时间荷对偶20260626\A30_Formal_Verification.lean",
    "CGICE_V91": r"<YOUR_HOME>\Desktop\AI论文\cgice\cgice_proof.lean",
}


def _regress_one(name: str, path: str, verbose: bool = True) -> dict:
    from proof_harness import propose_edits
    from trajectory_diff import diff_runs, render_report

    if not Path(path).exists():
        return {"name": name, "error": "file not found: %s" % path}

    L = LeanFile(path)
    L.ok_lean = False
    hs = propose_edits(ProofHarness.baseline(), n=4)
    runs = run_fleet_real(hs, path, max_workers=4)
    arb = [arbitrate(r) for r in runs]
    diff = diff_runs(runs, step_order=PIPELINE)

    if verbose:
        print("\n" + "=" * 74)
        print("回归对象: %s" % name)
        print("  %s" % path)
        print("  规模: %d 行 / %d theorem+lemma / %d axiom(去重 %d) / %d sorry"
              % (L.n_lines, len(L.theorems), len(L.axioms), len(L.axiom_uniq), L.sorry_count))
        print("  physical_content_audit:", (L.pca.get("verdict") or L.pca.get("status") or
                                            ("error" if "error" in L.pca else "?")))
        print("=" * 74)
        print("%-24s %5s %5s %7s  %s" % ("harness", "steps", "ok", "lean", "verdict"))
        for r, a in zip(runs, arb):
            print("%-24s %5d %5d %7s  %s" % (
                r.harness_name, len(r.steps), sum(s.ok for s in r.steps),
                a["lean_ok"], a["verdict"]))
        # 打印最佳 run 的逐步 detail
        best = max(runs, key=lambda r: sum(s.ok for s in r.steps))
        print("\n最佳 run（%s）逐步:" % best.harness_name)
        for s in best.steps:
            print("  %-4s %-5s %s" % (s.step_id, "OK" if s.ok else "FAIL", s.detail[:110]))
        print()
        print(render_report(diff))

    return {
        "name": name, "path": path,
        "file_stats": {"lines": L.n_lines, "theorems": len(L.theorems),
                       "axioms": len(L.axioms), "axioms_uniq": len(L.axiom_uniq),
                       "sorry": L.sorry_count},
        "pca_verdict": L.pca.get("verdict") or L.pca.get("status"),
        "runs": [r.to_dict() for r in runs],
        "arbiter": arb,
        "diff": {k: v for k, v in diff.items() if k != "per_step"},
    }


def _self_test() -> int:
    print("=== MVP-1 真实现回归（无需 Lean 编译器；4 个编译类 agent 显式 degraded）===")
    results = {}
    for name, path in DEFAULT_TARGETS.items():
        results[name] = _regress_one(name, path)

    print("\n" + "=" * 74)
    print("回归结论")
    print("=" * 74)
    ok_cnt = 0
    for name, r in results.items():
        if "error" in r:
            print("  %-12s ERROR %s" % (name, r["error"]))
            continue
        fs = r["file_stats"]
        best_verdict = sorted([a["verdict"] for a in r["arbiter"]],
                              key=lambda v: {"PASS": 0, "WARN": 1, "BLOCK": 2}.get(v, 3))[0]
        # 期望：V64 有多少 axiom/sorry；CGICE 有 sorry → 必须 BLOCK
        expect = "BLOCK" if fs["sorry"] > 0 else None
        verdict_ok = (best_verdict == expect) if expect else True
        print("  %-12s %2d行 %2d定理 %2d公理 %2d sorry → 最佳 %s %s" % (
            name, fs["lines"], fs["theorems"], fs["axioms"], fs["sorry"],
            best_verdict, "✅" if verdict_ok else "❌ (期望 %s)" % expect))
        if verdict_ok:
            ok_cnt += 1

    print("\n[%s] MVP-1 self-test %s" % (
        "OK" if ok_cnt == len([r for r in results.values() if "error" not in r]) else "FAIL",
        "通过" if ok_cnt == len([r for r in results.values() if "error" not in r]) else "未通过"))
    return 0 if ok_cnt == len([r for r in results.values() if "error" not in r]) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="agent_fleet_real — 10 agent 真实现")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--lean", help="单个 Lean 文件路径")
    ap.add_argument("--output", help="JSON 输出")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    if a.lean:
        r = _regress_one(Path(a.lean).stem, a.lean)
        if a.output:
            json.dump(r, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("\n->", a.output)
    else:
        ap.print_help()
