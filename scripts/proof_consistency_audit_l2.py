#!/usr/bin/env python3
"""
Formal Proof Consistency Audit — L2 结构层（阶段 B 落地）
=========================================================
把 Stage 3.5 六类 P0 审计从"一次性门控"升级为"深度感知"（Meta^n depth-aware 思想）：

  L1 机械层（proof_consistency_audit.py，stdlib-only，快）：
    确定性缺陷——表演性诚实 / 公理计数不一致 / 定理存在性 / by-trivial 空壳
    （这些是"局部、机械可查"的，直接给 WARN/BLOCK）

  L2 LLM 结构层（本脚本）：
    结构性缺陷——公理自相矛盾（ex-falso）/ 离散谱 vs 连续谱
    （这些是"跨公理、需数学判断"的，L1 只能给候选标记，L2 用 LLM 确认）

对应 Meta^n Appendix E.2 的 depth-aware trace payload：
  depth≤2（浅层）= L1 机械，逐条查缺陷
  depth≥3（深层）= L2 结构，读审计报告 + 公理依赖图做跨公理判断

Usage:
  python proof_consistency_audit_l2.py --lean proof.lean [--paper paper.txt]
      [--expected-axioms 14] [--output l2_report.json] [--demo]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

L1_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "proof_consistency_audit.py")

# L1 机械层能确定性判定的缺陷类（直接 BLOCK/WARN，无需 LLM）
L1_MECHANICAL_TYPES = {
    "performative_honesty", "axiom_count_mismatch", "theorem_count_mismatch",
    "phantom_theorem", "trivial_stub", "true_stub", "active_admit",
}
# L1 只能给候选标记、需 L2 LLM 结构判断的缺陷类
L2_CANDIDATE_TYPES = {
    "axiom_consistency_suspect",       # 公理自相矛盾候选
    "discrete_spectrum_on_noncompact",  # 离散谱 vs 连续谱候选
}


class DeepSeekLLM:
    def __init__(self, model: str = "deepseek-v4-flash"):
        self.model = model
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            for p in ["/mnt/d/123321/CityHDGanalysis/Spatial_Reasoning_Agent/.env"]:
                if os.path.exists(p):
                    with open(p) as f:
                        for line in f:
                            if line.startswith("DEEPSEEK_API_KEY"):
                                self.api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未找到")
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

    def generate(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return resp.choices[0].message.content or ""


class MockLLM:
    """离线 demo：模拟结构判断（返回确认/否决 JSON）。"""

    def generate(self, prompt: str) -> str:
        if "contradiction" in prompt.lower() and "≠" in prompt:
            return '{"verdict": "BLOCK", "confidence": 0.9, "reason": "demo: the axioms assert both equality and inequality for the same function application, enabling ex-falso."}'
        if "spectrum" in prompt.lower() and "non-compact" in prompt.lower():
            return '{"verdict": "BLOCK", "confidence": 0.85, "reason": "demo: discrete spectrum claimed on a non-compact symmetric space without a confining potential is a category error."}'
        if "silently strengthened" in prompt.lower():
            return '{"findings": []}'
        if "MISMATCH between what the PAPER" in prompt:
            return '{"mismatches": []}'
        if "LACKS an assumption" in prompt:
            return '{"findings": []}'
        return '{"verdict": "WARN", "confidence": 0.5, "reason": "demo: insufficient evidence to escalate."}'


# ======================================================================
# L1 调用（subprocess，读 JSON 报告）
# ======================================================================

def run_l1(lean_path: str, paper_path: str = None,
           expected_axioms: int = None, expected_theorems: int = None) -> dict:
    if not os.path.exists(L1_SCRIPT):
        return {"error": f"L1 script not found: {L1_SCRIPT}"}
    cmd = [sys.executable, L1_SCRIPT, "--lean", lean_path,
           "--output", "/tmp/l1_audit.json"]
    if paper_path:
        cmd += ["--paper", paper_path]
    if expected_axioms is not None:
        cmd += ["--expected-axioms", str(expected_axioms)]
    if expected_theorems is not None:
        cmd += ["--expected-theorems", str(expected_theorems)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    p = Path("/tmp/l1_audit.json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"error": "L1 did not produce output"}


# ======================================================================
# L2 结构判断
# ======================================================================

def extract_l2_candidates(l1_report: dict) -> list:
    """从 L1 报告提取 L2 候选项（公理矛盾候选 + 离散谱候选）。"""
    candidates = []
    for f in l1_report.get("findings", []):
        if f.get("type") in L2_CANDIDATE_TYPES:
            candidates.append(f)
    return candidates


def _strip_block_comments(lean: str) -> str:
    """嵌套感知块注释剥离（正确处理 /- ... -/ 嵌套，含 /-- doc 注释）。"""
    out = []
    depth = 0
    i = 0
    n = len(lean)
    while i < n:
        if lean[i:i + 2] == '/-':
            depth += 1
            i += 2
        elif lean[i:i + 2] == '-/' and depth > 0:
            depth -= 1
            i += 2
        elif depth == 0:
            out.append(lean[i])
            i += 1
        else:
            i += 1
    return ''.join(out)


def _active_lines(lean: str) -> list:
    """剥离注释后返回 active（非注释）行。"""
    code = _strip_block_comments(lean)
    return [l for l in code.splitlines()
            if not (l.strip().startswith("--") or l.strip().startswith("/-")
                    or l.strip().startswith("-/"))]


def _extract_axioms(lean: str) -> str:
    """提取 active axiom 声明（供 L2 判断上下文）。"""
    axioms = [l.strip() for l in _active_lines(lean) if re.match(r'^\s*axiom\s', l)]
    return "\n".join(axioms[:60]) or "(no axioms)"


def _extract_theorems(lean: str) -> str:
    """提取 active theorem 声明（供定向证伪）。"""
    thms = [l.strip() for l in _active_lines(lean) if re.match(r'^\s*theorem\s', l)]
    return "\n".join(thms[:40]) or "(no theorems)"


def _extract_lemmas(lean: str) -> str:
    """提取 active lemma 声明（供定向证伪）。"""
    lms = [l.strip() for l in _active_lines(lean) if re.match(r'^\s*lemma\s', l)]
    return "\n".join(lms[:40]) or "(no lemmas)"


def _extract_paper_claims(paper: str) -> str:
    """提取论文的主声明（摘要 + "we prove/establish" 句）。"""
    if not paper:
        return "(no paper provided)"
    lines = paper.splitlines()
    claims = []
    for l in lines:
        if re.search(r'\b(we\s+(prove|establish|show|construct|derive)|we\s+introduce|main\s+(result|theorem|contribution))', l, re.I):
            claims.append(l.strip()[:200])
    # 摘要前 500 字兜底
    if not claims:
        head = paper[:800]
        claims.append("(abstract excerpt) " + head.replace("\n", " ")[:600])
    return "\n".join(claims[:10]) or "(no claims found)"


AXIOM_CONTRADICTION_PROMPT = """You are a structural auditor for Lean 4 formal proofs.
Determine whether the following candidate is a GENUINE axiom contradiction (ex-falso):
a system where two axioms jointly imply `False` (e.g. the same function application is
asserted both equal and unequal). If so, it is a BLOCK-level defect — the proof is unsound
despite `0 sorry`.

Candidate finding:
{finding}

Relevant axiom declarations (active):
{axioms}

Respond with strict JSON only:
{{"verdict": "BLOCK" | "WARN", "confidence": 0.0-1.0,
  "reason": "one-sentence justification, cite the conflicting axioms"}}
"""

SPECTRUM_PROMPT = """You are a structural auditor for Lean 4 formal proofs.
Determine whether the following candidate is a GENUINE mathematical category error:
a claim of a DISCRETE spectrum (lambda_k = k * lambda) on a NON-COMPACT symmetric space
(such as SL(6,C)/SU(6) or SL(6,C)/SU(3,3)), where the free Laplace-Beltrami spectrum is
CONTINUOUS (Plancherel measure), unless a confining potential is explicitly imposed.
If the file does NOT clarify "absolutely continuous free spectrum + discrete bound states
from a confining potential", it is a BLOCK-level category error.

Candidate finding:
{finding}

Respond with strict JSON only:
{{"verdict": "BLOCK" | "WARN", "confidence": 0.0-1.0,
  "reason": "one-sentence justification"}}
"""

# ======================================================================
# P0-1 (Colosseum) 定向证伪三检测 — 映射 Colosseum 的 3 个新缺陷类
# ======================================================================

STRENGTHENED_HYPOTHESIS_PROMPT = """You are a targeted falsification auditor (Colosseum-style)
for Lean 4 formal proofs. Your task: find theorems whose CONCLUSION is stronger than their
stated HYPOTHESES justify — a "silently strengthened hypothesis" or "silently strengthened
conclusion". A theorem `theorem T (h : H) : C` is suspect if proving `C` actually requires
assumptions NOT captured in `H` (so the theorem statement is false in general, or the proof
must secretly import extra axioms).

Examine these active theorem declarations and proof bodies:

{theorems}

Return strict JSON with a LIST of findings (empty list if none):
{{"findings": [
  {{"theorem": "name", "verdict": "BLOCK" | "WARN", "confidence": 0.0-1.0,
    "missing_hypothesis": "what assumption is silently needed",
    "reason": "one sentence"}}
]}}
"""

PROVED_VS_TARGET_PROMPT = """You are a targeted falsification auditor (Colosseum-style)
for Lean 4 formal proofs. Your task: detect a MISMATCH between what the PAPER claims to prove
and what the LEAN file actually proves. The paper's abstract/main claims may state a target
(e.g. "we prove X") but the Lean main theorem may prove a weaker/different statement Y.

Paper abstract/main claims:
{paper_claims}

Lean main theorems (top-level `theorem` declarations):
{lean_theorems}

Return strict JSON with a LIST of mismatches (empty list if none):
{{"mismatches": [
  {{"paper_claim": "...", "lean_theorem": "...", "verdict": "BLOCK" | "WARN",
    "confidence": 0.0-1.0, "reason": "one sentence"}}
]}}
"""

MISSING_ASSUMPTION_PROMPT = """You are a targeted falsification auditor (Colosseum-style)
for Lean 4 formal proofs. Your task: find LEMMAS that are USED BY A DOWNSTREAM THEOREM but
whose statement LACKS an assumption that the downstream proof silently relies on. This is the
"missing assumption for a later section" defect: the lemma is too weak to justify the step
that cites it, so the downstream theorem is unsound.

Examine these lemma declarations and note which theorem uses each:

{lemmas}

Return strict JSON with a LIST of findings (empty list if none):
{{"findings": [
  {{"lemma": "name", "used_by": "theorem name", "verdict": "BLOCK" | "WARN",
    "confidence": 0.0-1.0, "missing_assumption": "...", "reason": "one sentence"}}
]}}
"""


def judge_candidate(llm, lean: str, candidate: dict) -> dict:
    """用 LLM 判断单个 L2 候选是否升级为 BLOCK。"""
    t = candidate.get("type")
    if t == "axiom_consistency_suspect":
        prompt = AXIOM_CONTRADICTION_PROMPT.format(
            finding=json.dumps(candidate, ensure_ascii=False),
            axioms=_extract_axioms(lean))
    elif t == "discrete_spectrum_on_noncompact":
        prompt = SPECTRUM_PROMPT.format(finding=json.dumps(candidate, ensure_ascii=False))
    else:
        return {"verdict": "WARN", "confidence": 0.0,
                "reason": f"unknown candidate type {t}"}

    raw = llm.generate(prompt)
    # 容错解析：清 markdown 代码围栏，取首 { 到尾 }
    raw = raw.strip().replace("```json", "").replace("```", "")
    m = re.search(r'\{.*\}', raw, re.S)
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"verdict": "WARN", "confidence": 0.0,
                "reason": f"LLM returned unparseable: {raw[:120]}"}


def _parse_json(raw: str) -> dict:
    """容错解析 LLM 返回的 JSON（清围栏，取首 { 到尾 }）。"""
    raw = raw.strip().replace("```json", "").replace("```", "")
    m = re.search(r'\{.*\}', raw, re.S)
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def run_targeted_falsification(lean: str, paper: str, llm) -> list:
    """P0-1 (Colosseum)：定向证伪三检测。

    映射 Colosseum 定向证伪的 3 个新缺陷类（②静默强化假设 / ⑤证明命题≠目标 / ⑥缺失下游假设）。
    返回 [(check_type, verdict, detail_dict), ...]。"""
    results = []

    # ① strengthened hypothesis（静默强化假设）
    thms = _extract_theorems(lean)
    if thms != "(no theorems)":
        raw = llm.generate(STRENGTHENED_HYPOTHESIS_PROMPT.format(theorems=thms))
        for item in _parse_json(raw).get("findings", []):
            results.append(("strengthened_hypothesis", item.get("verdict", "WARN"), item))

    # ② proved vs target（证明命题 ≠ 目标命题，需 paper）
    if paper:
        claims = _extract_paper_claims(paper)
        raw = llm.generate(PROVED_VS_TARGET_PROMPT.format(
            paper_claims=claims, lean_theorems=thms))
        for item in _parse_json(raw).get("mismatches", []):
            results.append(("proved_vs_target_mismatch", item.get("verdict", "WARN"), item))

    # ③ missing downstream assumption（下游缺失假设）
    lms = _extract_lemmas(lean)
    if lms != "(no lemmas)":
        raw = llm.generate(MISSING_ASSUMPTION_PROMPT.format(lemmas=lms))
        for item in _parse_json(raw).get("findings", []):
            results.append(("missing_downstream_assumption", item.get("verdict", "WARN"), item))

    return results


def run_l2(lean_path: str, paper_path: str = None,
           expected_axioms: int = None, expected_theorems: int = None,
           llm=None) -> dict:
    """完整 L2 流程：L1 机械审计 → 提取 L2 候选 → LLM 结构判断 → L2 报告。"""
    lean = Path(lean_path).read_text(encoding="utf-8", errors="replace")

    l1 = run_l1(lean_path, paper_path, expected_axioms, expected_theorems)
    if "error" in l1:
        return {"error": l1["error"]}

    candidates = extract_l2_candidates(l1)
    l2_judgments = []
    escalated = []   # 从 WARN 升级到 BLOCK 的缺陷
    for c in candidates:
        j = judge_candidate(llm, lean, c)
        j["candidate_type"] = c.get("type")
        l2_judgments.append(j)
        if j.get("verdict") == "BLOCK":
            escalated.append(c.get("type"))

    # ── P0-1 (Colosseum) 定向证伪三检测 ──
    paper = None
    if paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
    tf_results = run_targeted_falsification(lean, paper, llm)
    tf_findings = [{"check": t, "verdict": v, **d}
                   for t, v, d in tf_results]
    tf_blocks = [f"[{t}] {d.get('reason', '')[:120]}" for t, v, d in tf_results
                 if v == "BLOCK"]
    tf_warns = [f"[{t}] {d.get('reason', '')[:120]}" for t, v, d in tf_results
                if v != "BLOCK"]

    # 合并 L1 gate 与 L2 升级
    l1_blocks = [b for b in l1.get("blocks", [])]
    l1_warns = [w for w in l1.get("warns", [])]
    final_blocks = list(l1_blocks) + tf_blocks
    final_warns = [w for w in l1_warns
                   if not any(c.get("type") in escalated
                              and c.get("msg") == w for c in candidates)]
    final_warns = final_warns + tf_warns

    report = {
        "l2_time": None,
        "lean_file": lean_path,
        "l1_gate": l1.get("gate"),
        "l1_mechanical": {
            "blocks": l1_blocks,
            "warns": [w for w in l1_warns],
            "stats": l1.get("stats", {}),
        },
        "l2_candidates_found": len(candidates),
        "l2_judgments": l2_judgments,
        "l2_escalated": escalated,
        "targeted_falsification": tf_findings,
        "final_gate": "BLOCK" if (final_blocks or escalated) else
                      ("WARN" if final_warns else "PASS"),
        "final_blocks": final_blocks,
        "final_warns": final_warns,
    }
    return report


# ======================================================================
# main
# ======================================================================

def main():
    ap = argparse.ArgumentParser(description="L2 结构层审计（Meta^n 深度感知）")
    ap.add_argument("--lean", required=True, help="Lean 4 proof file")
    ap.add_argument("--paper", help="Paper text (phantom theorem detection)")
    ap.add_argument("--expected-axioms", type=int)
    ap.add_argument("--expected-theorems", type=int)
    ap.add_argument("--output", default="/tmp/l2_audit.json")
    ap.add_argument("--demo", action="store_true", help="用 MockLLM 离线验证")
    args = ap.parse_args()

    llm = MockLLM() if args.demo else DeepSeekLLM()
    report = run_l2(args.lean, args.paper, args.expected_axioms, args.expected_theorems, llm)
    report["l2_time"] = __import__("datetime").datetime.now().isoformat()

    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 64)
    print("Formal Proof Consistency Audit — L2 结构层")
    print("=" * 64)
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return 2
    print(f"  L1 gate: {report['l1_gate']}")
    print(f"  L2 候选数: {report['l2_candidates_found']}")
    for j in report["l2_judgments"]:
        print(f"    [{j.get('candidate_type')}] -> {j.get('verdict')} "
              f"(conf={j.get('confidence')}) {j.get('reason', '')[:80]}")
    print(f"  L2 升级为 BLOCK: {report['l2_escalated'] or '无'}")
    tf = report.get("targeted_falsification", [])
    if tf:
        print(f"  定向证伪 (P0-1 Colosseum): {len(tf)} 项")
        for f in tf:
            mark = "🔴" if f.get("verdict") == "BLOCK" else "🟡"
            print(f"    {mark} [{f.get('check')}] {f.get('reason', '')[:90]}")
    print(f"\n  最终 GATE: {report['final_gate']}")
    print(f"  Report: {args.output}")
    return 0 if report["final_gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
