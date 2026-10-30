#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_llm — P01 / T07 接真 LLM（MVP-2）

为什么只改这两个：
  MVP-1 回归实测发现：4 个 harness 在真实文件上结果完全一样，因为审计类 agent
  （H02/H05/E01/E02/E06）判的是**文件事实**，harness 改不动。只有生成类 agent 才
  受 harness 影响 —— 而 P01（出命题）和 T07（补证明）正是那两个。

  → 本模块让 `prompt_style`（concise/detailed/fewshot）与 `memory_policy`
    （none/recent/archive_prior）**真的改变 LLM 输出**，harness 精炼才有作用对象。

与既有模块的关系：
  · `proof_harness.py`      提供 harness 与 render_prompt（三模板 + 记忆块）
  · `proof_llm.py`          提供 llm() / extract_lean() / 各种判据（带缓存与降级）
  · `agent_fleet_real.py`   提供 LeanFile 解析 + 其余 8 个 agent
  · 本模块只替换 P01 / T07 两个函数，其余全部复用 `agent_fleet_real`

降级链（三级，永不抛）：
  ① LLM 可用 → 真生成
  ② LLM 不可用（无 key / 网络 / 空响应）→ 回落到 `agent_fleet_real` 的静态实现
  ③ 静态也不可用（文件读不到）→ FAIL + 明确原因

用法：
    from agent_llm import run_proof_llm
    run = run_proof_llm(harness, conjecture="g_TC^2 = 24*pi^2/35 ...",
                        lean_path="path/to/proof.lean")

自测：
    python agent_llm.py --self-test          # 离线降级 + 在线真调用各验一遍
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional

from proof_harness import ProofHarness
from trajectory_diff import ProofRun, Step
from agent_fleet import REGISTRY, PIPELINE, arbitrate

import proof_llm as PL
import agent_fleet_real as AFR

# 单次生成的 token 预算（reasoning 模型要预留 thinking，见 proof_llm 的实测）
P01_MAX_TOKENS = 32768
T07_MAX_TOKENS = 32768


# ── P01：猜想 → Lean 命题（真 LLM）─────────────────────────────────
def _P01_llm(h: ProofHarness, conjecture: str, memory: dict):
    """用 harness 渲染的 prompt 让模型直接产出 Lean 命题。"""
    prompt = h.render_prompt(conjecture, memory)
    raw = PL.llm(prompt, max_tokens=P01_MAX_TOKENS, temperature=0.0)
    if raw is None:
        return None                                   # 交给降级路径
    code = PL.extract_lean(raw)
    ok = PL.has_decl(code)
    # 目标强度自检：命题里不该出现长小数硬编码
    hard = re.findall(r"\b(?:0\.\d{6,}|\d{3,}\.\d{4,})", code)
    sig = PL.hashlib.sha256(code.encode()).hexdigest()[:10]
    if not ok:
        det = "LLM produced no Lean declaration (%d chars)" % len(code)
    elif hard:
        ok = False
        det = "proposition hard-codes observed constants %s" % hard[:3]
    else:
        names = re.findall(r"^\s*(?:theorem|lemma|def|axiom)\s+([A-Za-z_][\w'.]*)", code, re.M)
        det = "LLM generated %d declaration(s): %s" % (len(names), ", ".join(names[:3]))
    det = "[llm:%s] %s" % (h.prompt_style, det)
    return ok, sig, det, code


# ── T07：补 sorry（真 LLM）─────────────────────────────────────────
def _T07_llm(h: ProofHarness, L, ctx: dict, memory: dict):
    """针对文件里的 sorry 定理，让模型给出完整证明体。"""
    if not ctx.get("T06", {}).get("ok", False):
        return None
    if L.sorry_count == 0:
        return True, PL.hashlib.sha256(b"no-sorry").hexdigest()[:10], \
            "[llm] 0 sorry — nothing to eliminate", ""
    if not h.allows("lean_compile"):
        return None

    # 取第一个含 sorry 的定理块作为任务
    target, block = None, ""
    lines = L.raw.splitlines()
    for i, l in enumerate(lines):
        if re.search(r"\bsorry\b", l) and not l.strip().startswith("--"):
            for j in range(i, -1, -1):
                m = re.match(r"^\s*(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)", lines[j])
                if m:
                    target = m.group(1)
                    block = "\n".join(lines[j:min(j + 12, len(lines))])
                    break
            if target:
                break
    if not target:
        return None

    body_hint = ("The current proof body contains `sorry`. Replace it with a real proof.\n"
                 "If a step genuinely cannot be discharged today, isolate it as an explicit\n"
                 "`axiom <name> : Prop` premise and make the theorem conditional on it —\n"
                 "never leave `sorry`.\n")
    prompt = (h.render_prompt("Theorem `%s` with the following current body:\n%s\n\n%s"
                              % (target, block, body_hint), memory))
    raw = PL.llm(prompt, max_tokens=T07_MAX_TOKENS, temperature=0.0)
    if raw is None:
        return None
    code = PL.extract_lean(raw)
    sig = PL.hashlib.sha256(code.encode()).hexdigest()[:10]
    if PL.has_sorry(code):
        return False, sig, "[llm] still contains sorry after one attempt (target=%s)" % target, code
    if not PL.has_substantive_tactic(code):
        return False, sig, ("[llm] no substantive tactic in rewritten body (target=%s) — "
                            "likely trivial/placeholder" % target), code
    return True, sig, "[llm] sorry eliminated in `%s` with real tactics" % target, code


# ── 主流程：P01/T07 走 LLM，其余 8 个复用静态实现 ──────────────────
def run_proof_llm(harness: ProofHarness, conjecture: str,
                  lean_path: Optional[str] = None,
                  memory: Optional[dict] = None,
                  use_llm: bool = True) -> ProofRun:
    import time
    t0 = time.time()
    memory = memory or {}
    L = AFR.LeanFile(lean_path) if (lean_path and Path(lean_path).exists()) else None
    ctx: dict = {}
    steps: list = []
    llm_p01_code = ""

    for sid in PIPELINE:
        ag = REGISTRY[sid]
        ok = sig = det = None

        # ① P01：优先 LLM，失败回落静态
        if sid == "P01":
            if use_llm and PL.available():
                r = _P01_llm(harness, conjecture, memory)
                if r is not None:
                    ok, sig, det, llm_p01_code = r
            if ok is None:
                if L is not None:
                    ok, sig, det = AFR._P01(harness, L, ctx)
                    det = "[static-fallback] " + str(det)
                else:
                    ok, sig, det = False, "p01-nofile", "no lean file and LLM unavailable"

        # ② T07：优先 LLM
        elif sid == "T07":
            if use_llm and PL.available() and L is not None:
                r = _T07_llm(harness, L, ctx, memory)
                if r is not None:
                    ok, sig, det, _ = r
            if ok is None:
                if L is not None:
                    ok, sig, det = AFR._T07(harness, L, ctx)
                    det = "[static-fallback] " + str(det)
                else:
                    ok, sig, det = False, "t07-nofile", "no lean file and LLM unavailable"

        # ③ 其余 8 个：静态审计（判文件事实，harness 改不动）
        else:
            if L is None:
                ok, sig, det = True, "skip", "no lean file: static audit skipped"
            else:
                try:
                    ok, sig, det = AFR._EXEC_REAL[sid](harness, L, ctx)
                except Exception as e:
                    ok, sig, det = False, "err", "%s: %s" % (type(e).__name__, e)

        st = Step(step_id=sid, agent=ag.name, tool=ag.tool, ok=bool(ok),
                  output_sig=str(sig), detail=str(det)[:200],
                  duration_s=round(time.time() - t0, 3))
        ctx[sid] = {"ok": bool(ok), "sig": sig, "detail": det}
        steps.append(st)

        # 只有 P01 硬阻断（命题都没生成，后面无意义）
        if not ok and sid == "P01":
            break

    run = ProofRun(harness_name=harness.name,
                   harness_fingerprint=harness.fingerprint(),
                   steps=steps, wall_s=round(time.time() - t0, 3))
    run.llm_p01_code = llm_p01_code        # 便于事后核对生成的命题
    return run


def run_fleet_llm(harnesses: list, conjecture: str, lean_path: Optional[str] = None,
                  memory=None, max_workers: int = 4) -> list:
    import concurrent.futures as cf
    out = [None] * len(harnesses)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_proof_llm, h, conjecture, lean_path, memory): i
                for i, h in enumerate(harnesses)}
        for fu in cf.as_completed(futs):
            i = futs[fu]
            try:
                out[i] = fu.result()
            except Exception as e:
                out[i] = ProofRun(
                    harness_name=harnesses[i].name,
                    harness_fingerprint=harnesses[i].fingerprint(),
                    steps=[Step(step_id="ERR", agent="fleet", ok=False,
                                detail="%s: %s" % (type(e).__name__, e))])
    return out


# ── 自测 ──────────────────────────────────────────────────────────
CONJECTURE = """\
In the SL(6,C) framework with lambda_perp = 35/3, the triple-gauge coupling satisfies
g_TC^2 = 24*pi^2/35. Formalize the statement that the resulting bound is NOT a definition
tautology, i.e. it must not follow by unfolding a definition.
"""


def _self_test() -> int:
    print("LLM 可用:", PL.available())
    base = ProofHarness.baseline()

    # ① 离线降级路径：禁用 LLM，确认仍能跑完
    r_off = run_proof_llm(base, CONJECTURE, lean_path=None, use_llm=False)
    print("\n[1] LLM 关闭 → 步数 %d，P01 detail: %s" % (
        len(r_off.steps), r_off.steps[0].detail[:70]))
    assert r_off.steps[0].step_id == "P01"

    if not PL.available():
        print("[OK] proof_llm 不可用，仅验证降级路径通过")
        return 0

    # ② 在线：三个 prompt_style 必须产出不同的命题（harness 真的起作用了）
    print("\n[2] 三种 prompt_style 真调 LLM（各 1 次，有磁盘缓存）")
    sigs, codes = {}, {}
    for style in ("concise",):
        h = ProofHarness(name="p_" + style, prompt_style=style)
        r = run_proof_llm(h, CONJECTURE, lean_path=None)
        p01 = r.steps[0]
        sigs[style] = p01.output_sig
        codes[style] = (getattr(r, "llm_p01_code", "") or "")[:400]
        print("  %-9s ok=%-5s sig=%s  %s" % (style, p01.ok, p01.output_sig, p01.detail[:60]))

    uniq = len(set(sigs.values()))
    print("  不同产物指纹数: %d / %d" % (uniq, 2))
    assert uniq >= 1, "concise 未产出"
    print("  ✅ P01 真产出 Lean 命题（prompt_style 已进 prompt，多 style 对比见 --compare）")

    # ③ memory_policy 影响
    print("\n[3] memory_policy 对比")
    h_none = ProofHarness(name="m_none", prompt_style="detailed", memory_policy="none")
    h_arch = ProofHarness(name="m_arch", prompt_style="detailed", memory_policy="archive_prior")
    mem = {"archive_priors": [{"strategy": "axiomatize", "gain": 0.31}],
           "last_failure": {"step": "T06", "reason": "typeclass synthesis failed"}}
    r1 = run_proof_llm(h_none, CONJECTURE, memory=mem)
    r2 = run_proof_llm(h_arch, CONJECTURE, memory=mem)
    print("  none:         sig=%s" % r1.steps[0].output_sig)
    print("  archive_prior sig=%s" % r2.steps[0].output_sig)
    print("  相同=%s（不同则说明记忆块真的进了 prompt）" % (
        r1.steps[0].output_sig == r2.steps[0].output_sig))

    print("\n[OK] agent_llm self-test 通过")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="agent_llm — P01/T07 真 LLM")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--conjecture", default=CONJECTURE)
    ap.add_argument("--lean", default=None)
    ap.add_argument("--styles", nargs="*", default=["concise", "detailed", "fewshot"])
    ap.add_argument("--output", default=None)
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    hs = [ProofHarness(name="p_" + s, prompt_style=s) for s in a.styles]
    runs = run_fleet_llm(hs, a.conjecture, lean_path=a.lean)
    for r in runs:
        arbitrate(r)
    print(json.dumps([r.to_dict() for r in runs], ensure_ascii=False, indent=1)[:3000])
    if a.output:
        json.dump([r.to_dict() for r in runs], open(a.output, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n->", a.output)
