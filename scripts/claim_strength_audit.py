#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文声称强度审计 — 过度声称检测 (P1-2, from Kosmos failure_detector.py over-interpretation).

检测论文中「声称强度」与「Lean 证据强度」的失配：
  - 强声称词 (prove/establish/demonstrate/confirm...)  + 弱证据 (多 axiom / honest-axiom
    / 条件定理 / 校准值)  → 过度声称（对应「预测度诚实化」原则）
  - hedged 词 (suggest/indicate/propose...) + 强证据 → 过度谦虚（可选提示）

与 Hallucination Clipping (v2.3.0 数值核对) + physical_content_audit (v2.15.0 重言式)
互补：本脚本是**词表层**检测（声称措辞 vs 证据链强度），不涉及数值。

证据强度分级（Lean 证据链，由强到弱）：
  L0 强   : 0 axiom + 0 sorry + 黄金门控干净（#print axioms 仅三件套）
  L1 中   : 条件定理（axiom ... : Prop 显式前提）或 少量 honest-axiom
  L2 弱   : 多 research axiom / 校准值 / 唯象拟合

用法：
  python claim_strength_audit.py --paper paper.txt --lean proof.lean --output audit.json
  python claim_strength_audit.py --self-test
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple


# 强声称词（声称了演绎证明/严格建立）
STRONG_CLAIMS = [
    "prove", "proves", "proved", "proven", "proof",
    "establish", "establishes", "established",
    "demonstrate", "demonstrates", "demonstrated",
    "confirm", "confirms", "confirmed",
    "verify", "verifies", "verified",
    "derive", "derives", "derived", "derivation",
    "conclusively", "rigorously",
]
# hedged 词（声称了推测/建议）
HEDGED_CLAIMS = [
    "suggest", "suggests", "suggested",
    "indicate", "indicates", "indicated",
    "propose", "proposes", "proposed",
    "conjecture", "conjectures", "conjectured",
    "appear", "appears", "appeared",
    "may", "might", "could", "possibly", "potential",
    "preliminary", "tentative", "exploratory",
    "hypothesize", "hypothesized",
]


@dataclass
class ClaimFinding:
    sentence: str
    claim_word: str
    claim_strength: str        # "strong" | "hedged"
    evidence_level: str        # "L0" | "L1" | "L2" | "unknown"
    overclaim: bool
    detail: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


def evidence_level(lean_text: str) -> str:
    """从 Lean 文本提取证据链强度等级。"""
    sorry = len(re.findall(r'\bsorry\b', lean_text))
    admit = len(re.findall(r'\badmit\b', lean_text))
    axioms = re.findall(r'^\s*axiom\s+(\w+)', lean_text, re.M)
    research_axioms = [a for a in axioms if a not in ('propext', 'Classical', 'Quot')]
    # 条件定理（axiom ... : Prop 显式前提）— 比无条件 axiom 更诚实
    conditional = bool(re.search(r'axiom\s+\w+[^:]*:\s*Prop', lean_text))
    # 校准/唯象标记
    calibrated = bool(re.search(
        r'(calibrat|phenomenolog|fitted?|fit\s+to|tuned)', lean_text, re.I))

    if sorry > 0 or admit > 0:
        return "L2"  # 未完成证明
    if len(research_axioms) > 3 or calibrated:
        return "L2"  # 多 axiom / 校准
    if research_axioms or conditional:
        return "L1"  # 条件定理 / 少量 honest-axiom
    return "L0"      # 黄金门控干净


def audit(paper_text: str, lean_text: str) -> List[ClaimFinding]:
    """扫描论文声称句，对比 Lean 证据强度。"""
    level = evidence_level(lean_text)
    findings: List[ClaimFinding] = []

    # 按句子切分
    sentences = re.split(r'(?<=[.!?])\s+', paper_text)
    for sent in sentences:
        if len(sent) < 10:
            continue
        low = sent.lower()
        strong_hit = next((w for w in STRONG_CLAIMS if re.search(r'\b' + w + r'\b', low)), None)
        hedged_hit = next((w for w in HEDGED_CLAIMS if re.search(r'\b' + w + r'\b', low)), None)

        if strong_hit:
            # 强声称 + 弱证据 = 过度声称
            overclaim = level in ("L1", "L2")
            if overclaim:
                detail = (f"强声称词但证据链为 {level}"
                          "（多 axiom/校准/条件定理）→ 建议降级为 conditional/suggest 措辞")
            else:
                detail = f"强声称词但证据链为 {level} → 合理"
            findings.append(ClaimFinding(
                sentence=sent.strip()[:160],
                claim_word=strong_hit,
                claim_strength="strong",
                evidence_level=level,
                overclaim=overclaim,
                detail=detail,
            ))
        elif hedged_hit and level == "L0":
            # hedged + 强证据 = 过度谦虚（可选提示，不判过度声称）
            findings.append(ClaimFinding(
                sentence=sent.strip()[:160],
                claim_word=hedged_hit,
                claim_strength="hedged",
                evidence_level="L0",
                overclaim=False,
                detail="hedged 措辞但证据链 L0（黄金门控干净）→ 可升级为更强措辞（可选）",
            ))

    return findings


# ============================================================================
# self-test
# ============================================================================
def self_test() -> bool:
    strong_paper = ("We rigorously prove that the spectral gap equals 35/3. "
                    "This conclusively establishes the mechanism. "
                    "We derive the fixed point from first principles.")
    # L0 证据（干净）
    l0_lean = """theorem gap : spectral_gap = 35/3 := by
  calc
    spectral_gap = 35/3 := by ring
"""
    # L2 证据（多 axiom + 校准）
    l2_lean = """axiom a1 : P1
axiom a2 : P2
axiom a3 : P3
axiom a4 : P4
-- calibrated to match m_tau scale
theorem gap : spectral_gap = 35/3 := by
  exact a1
"""

    ok = True
    # L0 证据 + 强声称 → 不应过度声称
    f1 = audit(strong_paper, l0_lean)
    over1 = any(f.overclaim for f in f1)
    print(f"[{'PASS' if not over1 else 'FAIL'}] L0证据+强声称: overclaim={over1} "
          f"({len(f1)} 句强声称)")
    if over1:
        ok = False

    # L2 证据 + 强声称 → 应检测到过度声称
    f2 = audit(strong_paper, l2_lean)
    over2 = any(f.overclaim for f in f2)
    print(f"[{'PASS' if over2 else 'FAIL'}] L2证据+强声称: overclaim={over2} "
          f"({sum(1 for f in f2 if f.overclaim)} 句过度声称)")
    if not over2:
        ok = False

    print(f"self-test {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="", help="论文文本文件")
    ap.add_argument("--lean", default="", help="Lean 证明文件")
    ap.add_argument("--output", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(0 if self_test() else 1)

    if not args.paper or not args.lean:
        print("错误：需提供 --paper 和 --lean，或 --self-test")
        sys.exit(1)

    paper = open(args.paper, encoding="utf-8").read()
    lean = open(args.lean, encoding="utf-8").read()
    level = evidence_level(lean)
    findings = audit(paper, lean)

    print("=" * 68)
    print(f"论文声称强度审计（Lean 证据链等级: {level}）")
    print("=" * 68)
    over = [f for f in findings if f.overclaim]
    print(f"检测到 {len(findings)} 个声称句，其中 {len(over)} 个疑似过度声称\n")
    for f in findings:
        mark = "⚠️" if f.overclaim else ("ℹ️" if f.claim_strength == "hedged" else "✅")
        print(f"{mark} [{f.claim_word}] {f.sentence}")
        print(f"     {f.detail}\n")

    verdict = "BLOCK（存在过度声称，需降级措辞）" if over else "PASS"
    print(f"判定: {verdict}")
    print("=" * 68)

    if args.output:
        json.dump({"evidence_level": level,
                   "overclaim_count": len(over),
                   "findings": [f.to_dict() for f in findings]},
                  open(args.output, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"DONE -> {args.output}")


if __name__ == "__main__":
    main()
