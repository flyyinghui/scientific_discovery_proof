#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProofHarness — 证明 agent 的「harness 层」对象（Harness² Propose 阶段的载体）

对齐 Google Research Harness²（Propose–Probe–Compose）：
  Harness = 模型**外面**那一层（prompt / tools / memory / 编排 / 并行度）。
  Harnessing = 自动改写这一层让同一个模型更会干活。
  本模块只定义「可被改写的那一层」，不碰证明逻辑本身。

与 scientific-discovery-proof 的关系：
  现有 Stage 3.6 的 `stage36_evolution.py` 优化的是**证明代码**（mutate Lean 片段）；
  本模块优化的是**生成证明的那个 agent 的 harness**（prompt 模板 / 工具白名单 /
  记忆注入策略 / 脚手架开关 / 并行度）。两者正交，是它的元层。

关键设计分离（对齐 harness2 的「无 verifier」前提 + 本技能的「Lean 硬验证」）：
  · Harness **不含**任何打分/判定字段 —— 它不知道该证明对不对。
  · 判定只发生在 Arbiter（agent_fleet.arbitrate）里，且只有它能读 Lean 编译结果。
  · 因此 `ProofHarness` 可以被 Composer 自由组合，而不会把 verifier 泄漏进精炼路径。

四个可改写维度（Proposer 从这里提编辑）：
  ① prompt_style      concise / detailed / fewshot
  ② memory_policy     none / recent / archive_prior
  ③ scaffold_phase    是否三阶段脚手架（stub → tactic → full）
  ④ tool_whitelist    可用工具子集（lean_compile / mathlib_lookup / dag_audit ...）

用法：
    from proof_harness import ProofHarness, propose_edits
    hs = ProofHarness.baseline()
    variants = propose_edits(hs, n=4)          # Proposer：提 4 个 harness 编辑
    prompt = variants[0].render_prompt(conjecture)

自测：
    python proof_harness.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# ── 可改写维度的取值域 ──────────────────────────────────────────────
PROMPT_STYLES = ("concise", "detailed", "fewshot")
MEMORY_POLICIES = ("none", "recent", "archive_prior")
SCAFFOLD_MODES = (True, False)

# 工具白名单候选（对应技能里真实的 scripts/）
ALL_TOOLS = (
    "lean_compile",          # Lean 4 编译（Arbiter 独占调用权）
    "mathlib_lookup",        # mathlib_api_lookup.py
    "dag_audit",             # proof_dag_audit.py
    "content_audit",         # physical_content_audit.py
    "readback",              # faithfulness_readback.py
    "template_library",      # proof_template_library.py
)

# ── prompt 模板（三种风格）────────────────────────────────────────
_TMPL_CONCISE = """\
Be concise. No explanation, no commentary, no preamble. Output ONLY Lean 4 code.

Formalize and prove the following conjecture in Lean 4 (mathlib).
State the weakest stable form of the claim; do not hard-code observed constants.
Conjecture:
{conjecture}

{memory_block}
Return ONLY the Lean code.
"""

_TMPL_DETAILED = """\
You are formalizing a physics conjecture into Lean 4 against mathlib.
Rules that must hold in your output:
  1. The statement must be the weakest stable form of the claim (the shape of the truth),
     never a constant reverse-engineered from the observation.
  2. Every implicit assumption must appear explicitly in the signature, not be silently
     strengthened inside the proof.
  3. Do not define the physical object as the very identity you then "prove" —
     that is a definition tautology, not a derivation.
  4. Prefer `def`/`abbrev` for objects, `Prop`-valued for predicates, `theorem` only for
     what is actually discharged; use `axiom X : Prop` + a `_conditional` form when the
     premise is a research-level open problem.
  5. If a step is genuinely unprovable today, isolate it as an honest axiom and say so.

Conjecture:
{conjecture}

{memory_block}
Produce the Lean 4 file. No `sorry`, no `admit`.
"""

_TMPL_FEWSHOT = """\
Formalize and prove in Lean 4 (mathlib). Follow the pattern of the examples below —
they come from previously accepted proofs of the same defect family.

--- example 1 (conditional theorem pattern) ---
axiom bridgeHypothesis : Prop
theorem main_conditional (h : bridgeHypothesis) : <claim> := by
  <forward inference, no sorry>

--- example 2 (honest axiom with explicit premise) ---
axiom openProblemPremise : Prop
theorem result_conditional (h : openProblemPremise) : <claim> := by
  <real reasoning>

Conjecture:
{conjecture}

{memory_block}
Return ONLY the Lean code, matching the pattern above.
"""

_TEMPLATES = {
    "concise": _TMPL_CONCISE,
    "detailed": _TMPL_DETAILED,
    "fewshot": _TMPL_FEWSHOT,
}


@dataclass
class ProofHarness:
    """证明 agent 的可改写外层。刻意不含任何打分字段。"""

    name: str = "baseline"
    prompt_style: str = "concise"        # PROMPT_STYLES
    memory_policy: str = "none"          # MEMORY_POLICIES
    scaffold_phase: bool = True          # 三阶段脚手架
    tool_whitelist: list = field(default_factory=lambda: list(ALL_TOOLS))
    parallelism: int = 1                 # 该 harness 内部并行度
    lineage: str = "root"                # 从哪个 harness 变异而来（审计用）

    # ── 构造 ────────────────────────────────────────────────────
    @classmethod
    def baseline(cls) -> "ProofHarness":
        return cls(name="baseline", prompt_style="concise", memory_policy="none",
                   scaffold_phase=True, tool_whitelist=list(ALL_TOOLS),
                   parallelism=1, lineage="root")

    @classmethod
    def from_dict(cls, d: dict) -> "ProofHarness":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> dict:
        return asdict(self)

    # ── 指纹（Composer 去重 / archive 对齐用）────────────────────
    def fingerprint(self) -> str:
        payload = json.dumps({
            "prompt_style": self.prompt_style,
            "memory_policy": self.memory_policy,
            "scaffold_phase": self.scaffold_phase,
            "tool_whitelist": sorted(self.tool_whitelist),
            "parallelism": self.parallelism,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()[:12]

    # ── 渲染 prompt ─────────────────────────────────────────────
    def render_prompt(self, conjecture: str, memory: Optional[dict] = None) -> str:
        tmpl = _TEMPLATES.get(self.prompt_style, _TMPL_CONCISE)
        memory_block = self._render_memory(memory or {})
        return tmpl.replace("{conjecture}", conjecture.strip()).replace(
            "{memory_block}", memory_block)

    def _render_memory(self, memory: dict) -> str:
        if self.memory_policy == "none":
            return ""
        if self.memory_policy == "recent":
            last = memory.get("last_failure")
            if not last:
                return ""
            return ("Previous attempt failed at step `%s` with: %s\nDo not repeat that move.\n"
                    % (last.get("step"), last.get("reason", "")[:300]))
        if self.memory_policy == "archive_prior":
            priors = memory.get("archive_priors") or []
            if not priors:
                return ""
            lines = ["Successful precedent for the same defect signature (reuse the move):"]
            for p in priors[:3]:
                lines.append("  - strategy=%s  gain=%.2f  produced 0-sorry" % (
                    p.get("strategy", "?"), float(p.get("gain", 0.0))))
            return "\n".join(lines) + "\n"
        return ""

    # ── 工具门（Arbiter 之外谁都不能越过白名单）─────────────────
    def allows(self, tool: str) -> bool:
        return tool in self.tool_whitelist

    def has_compile_right(self) -> bool:
        """只有白名单含 lean_compile 的 harness 才能请求编译 —— 但结果只能由 Arbiter 读。"""
        return self.allows("lean_compile")


# ── Proposer：提出 harness 编辑（Harness² 的第一段）────────────────
_EDIT_SPACE = [
    ("prompt_style", "concise", "detailed"),
    ("prompt_style", "detailed", "fewshot"),
    ("memory_policy", "none", "archive_prior"),
    ("memory_policy", "recent", "archive_prior"),
    ("scaffold_phase", True, False),
    ("parallelism", 1, 2),
    ("parallelism", 2, 4),
]


def propose_edits(base: ProofHarness, n: int = 4) -> list:
    """提 n 个互不重复的 harness 变体。

    刻意做成「单维编辑」而非随机组合 —— 这样轨迹差异能归因到**具体哪一个维度**，
    否则多维亚变会导致分歧步无法解释（这是 MVP-0 的关键设计取舍）。
    """
    out, seen = [], {base.fingerprint()}
    out.append(base)  # 基线始终在候选集里（单调性保证）

    for dim, frm, to in _EDIT_SPACE:
        if len(out) >= n:
            break
        d = base.to_dict()
        cur = d.get(dim)
        # 允许正向或反向编辑
        if cur == to:
            d[dim] = frm
        elif cur == frm:
            d[dim] = to
        else:
            continue
        if dim == "scaffold_phase":
            name = "scaffold_on" if d[dim] else "scaffold_off"
        elif dim == "parallelism":
            name = "wide_p%d" % d[dim]
        else:
            name = "%s_%s" % (dim, d[dim])
        h = ProofHarness.from_dict(d)
        h.name = name
        h.lineage = base.fingerprint()
        if h.fingerprint() in seen:
            continue
        seen.add(h.fingerprint())
        out.append(h)

    # 若单维编辑不够 n 个，用组合补齐（仍标 lineage）
    while len(out) < n:
        d = base.to_dict()
        d["prompt_style"] = PROMPT_STYLES[len(out) % len(PROMPT_STYLES)]
        d["memory_policy"] = MEMORY_POLICIES[len(out) % len(MEMORY_POLICIES)]
        h = ProofHarness.from_dict(d)
        h.name = "combo_%d" % len(out)
        h.lineage = base.fingerprint()
        if h.fingerprint() in seen:
            h.parallelism = min(8, h.parallelism + 1)
        seen.add(h.fingerprint())
        out.append(h)
    return out[:n]


# ── 自测 ────────────────────────────────────────────────────────
def _self_test() -> int:
    base = ProofHarness.baseline()
    print("baseline:", base.name, "fingerprint:", base.fingerprint())
    print("  prompt_style=%s memory=%s scaffold=%s parallel=%d tools=%d" % (
        base.prompt_style, base.memory_policy, base.scaffold_phase,
        base.parallelism, len(base.tool_whitelist)))

    vs = propose_edits(base, n=4)
    print("\nProposer 产出 %d 个变体:" % len(vs))
    fps = set()
    for h in vs:
        assert h.fingerprint() not in fps, "变体指纹重复: %s" % h.name
        fps.add(h.fingerprint())
        print("  %-20s style=%-8s mem=%-13s scaffold=%-5s p=%d lineage=%s" % (
            h.name, h.prompt_style, h.memory_policy, h.scaffold_phase,
            h.parallelism, h.lineage))

    # prompt 渲染
    for style in PROMPT_STYLES:
        h = ProofHarness(prompt_style=style, memory_policy="archive_prior")
        p = h.render_prompt("g_TC^2 = 24*pi^2/35",
                            {"archive_priors": [{"strategy": "axiomatize", "gain": 0.31}]})
        assert "g_TC^2" in p, "conjecture 未注入"
        assert "{memory_block}" not in p, "记忆占位符未替换"
        print("  render[%s] %d chars, memory=%s" % (
            style, len(p), "yes" if "precedent" in p else "no"))

    # 记忆策略
    h = ProofHarness(memory_policy="none")
    assert h.render_prompt("X") .count("precedent") == 0
    h2 = ProofHarness(memory_policy="recent")
    assert "Do not repeat" in h2.render_prompt("X", {"last_failure": {"step": "T06", "reason": "typeclass"}})

    # 工具门
    h3 = ProofHarness(tool_whitelist=["mathlib_lookup"])
    assert h3.has_compile_right() is False
    assert h3.allows("mathlib_lookup") is True
    print("  tool gate OK（无 lean_compile 的 harness 不能请求编译）")

    print("\n[OK] proof_harness self-test 全部通过")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ProofHarness — harness 层定义与 Proposer")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--show-baseline", action="store_true")
    ap.add_argument("--propose", type=int, default=0, help="输出 n 个变体的 JSON")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(_self_test())
    if a.show_baseline:
        print(json.dumps(ProofHarness.baseline().to_dict(), ensure_ascii=False, indent=1))
    if a.propose:
        vs = propose_edits(ProofHarness.baseline(), a.propose)
        print(json.dumps([v.to_dict() for v in vs], ensure_ascii=False, indent=1))
    if not (a.self_test or a.show_baseline or a.propose):
        ap.print_help()
