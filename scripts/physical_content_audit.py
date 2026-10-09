#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""物理内容审计门控 — 检测「定义重言式」（definitional tautology trap）

把「0 sorry / 0 axiom 编译通过」与「物理内容非平凡」区分开。

V64 教训（2026-09-26 终审）：把物理对象直接定义为 S ≡ 谱底·‖φ‖²+V_top，
则 bound 变成重言式（35x+b ≥ 35x+b），是替换非推导——4/5 代理一致 P0。
检测信号：unfold 后定理体只剩 `rw [定义] + linarith`。

五类检测：
  1. 字面恒等重言式（conclusion 形如 X = X / X ≥ X / X ≤ X）      → BLOCK
  2. 定义重言式（rw/unfold 展开 conclusion 里的定义 + 无实质 tactic） → BLOCK
  3. 浅层证明（证明体无任何实质 tactic，如 calc/have/ring/exact）      → WARN
  4. total function 默认值（log/sInf/iSup 无保护假设，v2.19.0 原则 3）→ WARN
  5. vacuous 假设（False / P∧¬P / x<x 矛盾假设，v2.19.0 原则 5）       → WARN

实质 tactic = calc / have / ring / ring_nf / field_simp / by_contra /
              induction / cases / exact <非rfl> / linarith [假设] / apply / refine

用法：
  python physical_content_audit.py --lean proof.lean --output /tmp/content_audit.json
  python physical_content_audit.py --self-test

stdlib-only，可作 Stage 3.5 的独立门控（在 paper generation 前跑）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── 注释剥离 ─────────────────────────────────────────────────────

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


def _strip_line_comments(code: str) -> str:
    """剥离单行注释（-- ...），含整行注释。任何 -- 之后的内容都是注释。"""
    return '\n'.join(
        l.split('--', 1)[0] if '--' in l else l
        for l in code.splitlines()
    )


# ── 顶层声明识别 ────────────────────────────────────────────────

TOP_LEVEL_RE = re.compile(
    r'^(theorem|lemma|def|axiom|example|namespace|end|section|structure|class|'
    r'instance|inductive|abbrev|noncomputable|variable|open|import|#)\b'
)


def _extract_blocks(lean: str) -> list[dict]:
    """提取每个 theorem/lemma 块为 {kind, name, statement, body}。

    顶层声明 = 行首（无前导空格）以 TOP_LEVEL_RE 关键词开头。
    statement = 从声明到第一个 `:=` 之前（含 conclusion）；body = `:=` 之后。
    """
    code = _strip_line_comments(_strip_block_comments(lean))
    lines = code.splitlines()
    blocks = []
    current = None
    for line in lines:
        is_top = bool(line.strip()) and not line[0].isspace() and TOP_LEVEL_RE.match(line)
        if is_top:
            if current and current["kind"] in ("theorem", "lemma"):
                blocks.append(current)
            m = re.match(r'^(theorem|lemma)\s+', line)
            current = {"kind": m.group(1), "lines": [line]} if m else None
        elif current is not None:
            current["lines"].append(line)
    if current and current["kind"] in ("theorem", "lemma"):
        blocks.append(current)

    result = []
    for b in blocks:
        full = "\n".join(b["lines"])
        idx = full.find(":=")
        statement = full[:idx] if idx != -1 else full
        body = full[idx + 2:] if idx != -1 else ""
        # 提取 name
        m = re.search(r'^(?:theorem|lemma)\s+([\w.]+)', statement)
        name = m.group(1) if m else "?"
        result.append({"kind": b["kind"], "name": name, "statement": statement, "body": body})
    return result


def _extract_conclusion(statement: str) -> str:
    """提取 conclusion：最后一个顶层 `:`（排除 `:=`）之后的内容。"""
    depth = 0
    last_colon = -1
    for i, ch in enumerate(statement):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            if i + 1 < len(statement) and statement[i + 1] == "=":
                continue
            last_colon = i
    if last_colon == -1:
        return ""
    return statement[last_colon + 1:].strip()


# ── 实质 tactic 信号 ─────────────────────────────────────────────

SUBSTANTIVE_PATTERNS = [
    r'\bcalc\b',                          # 多步推导链
    r'\bhave\b',                          # 中间引理
    r'\bring_nf\b',                       # 多项式实质代数
    r'\bring\b',                          # 多项式实质代数
    r'\bfield_simp\b',                    # 域的实质代数
    r'\bby_contra\b',                     # 反证
    r'\binduction\b',                     # 归纳
    r'\bcases\b',                         # 分情况
    r'\bconstructor\b',                   # 构造
    r'\bapply\b',                         # 应用
    r'\brefine\b',                        # 精化
    r'\btrans\b',                         # 传递性推导
    r'\bexact\s+(?!rfl\b|trivial\b)',     # exact 引用非平凡项
    r'\b(?:n?linarith|omega)\s*\[',       # linarith/omega 带假设
    r'\bchange\b',                        # 目标变换
]


def _has_substantive(body: str) -> bool:
    """证明体是否含任何实质 tactic。"""
    return any(re.search(p, body) for p in SUBSTANTIVE_PATTERNS)


# ── 重言式检测 ───────────────────────────────────────────────────

_REL_OPS = "=≥≤↔"


def _is_identity_tautology(conclusion: str) -> bool:
    """检测 conclusion 是否字面恒等（X = X / X ≥ X / X ≤ X / X ↔ X，左右完全相同）。"""
    c = conclusion.strip()
    depth = 0
    i = 0
    while i < len(c):
        ch = c[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch in _REL_OPS:
            left = c[:i].strip()
            right = c[i + 1:].strip()
            if left and left == right:
                return True
        i += 1
    return False


def _detect_definitional_tautology(conclusion: str, body: str) -> bool:
    """检测定义重言式：rw/unfold 展开 conclusion 里出现的定义 + 无实质 tactic。

    V64 教训：`theorem bound : S ≥ 谱底·‖φ‖²+V_top := by rw [S]; linarith`，
    rw [S] 把 S 展开成 `谱底·‖φ‖²+V_top`，linarith 证的是恒等式（替换非推导）。
    """
    if not conclusion or not body.strip():
        return False
    expanded = set()
    for m in re.finditer(r'\b(?:rw|simp|rwa)\s*\[([^\]]*)\]', body):
        for name in m.group(1).split(','):
            nm = name.strip()
            if nm:
                expanded.add(nm)
    for m in re.finditer(r'\bunfold\s+([\w.]+)', body):
        expanded.add(m.group(1))
    # 展开的定义名出现在 conclusion 里
    defs_in_conclusion = [d for d in expanded if d and d in conclusion]
    if not defs_in_conclusion:
        return False
    # 且证明体无实质 tactic
    return not _has_substantive(body)


# ── Faithfulness 退化输入检测（v2.19.0, prove2me 原则 3/5）─────────

TOTAL_FUNCTION_GUARDS = [
    # (函数模式, 描述, 保护假设模式)
    (r'\b(?:Real\.)?log\b', 'Real.log（非正输入返回默认值 0）', r'0\s*<|positive|\(h\w*\s*:?\s*0\s*<'),
    (r'\bsInf\b', 'sInf（空集返回默认值 0）', r'nonempty|bddBelow|\(h\w*'),
    (r'\biSup\b', 'iSup（空集/无界返回默认值）', r'nonempty|bddAbove|\(h\w*'),
    (r'\biInf\b', 'iInf（空集/无界返回默认值）', r'nonempty|bddBelow|\(h\w*'),
]


def _detect_total_function_default(statement: str) -> str | None:
    """原则 3：total function 坏输入默认值。

    检测 statement 里出现 total function（log / sInf / iSup / iInf）但无对应保护
    假设（正性 / 非空 / 有界）。Lean 里这些函数在坏输入上返回默认值（通常 0）
    而非报错——若源材料的假设未显式化，形式化可能是错的（即使编译通过）。

    返回描述字符串（触发则非 None），否则 None。启发式，WARN 而非 BLOCK。
    """
    if not statement:
        return None
    for pattern, desc, guard in TOTAL_FUNCTION_GUARDS:
        if re.search(pattern, statement):
            if not re.search(guard, statement):
                return desc
    return None


def _detect_vacuous_hypothesis(statement: str) -> str | None:
    """原则 5：边缘输入 vacuous——检测不可满足假设 / 自反矛盾。

    三类：假设为 False、假设形如 P ∧ ¬P、自反严格不等式 x < x / x > x（矛盾）。
    x ≤ x / x ≥ x 是恒真，不触发。

    返回描述字符串（触发则非 None），否则 None。启发式，WARN 而非 BLOCK。
    """
    if not statement:
        return None
    if re.search(r':\s*False\b', statement):
        return '假设为 False（不可满足）'
    if re.search(r'∧\s*¬', statement):
        return '假设形如 P ∧ ¬P（自相矛盾）'
    for m in re.finditer(r'\(?\s*([A-Za-z_]\w*)\s*([<>])\s*\1\s*\)?', statement):
        if m.group(2) in ('<', '>'):
            return f'自反严格不等式 {m.group(1)} {m.group(2)} {m.group(1)}（矛盾）'
    return None


# ── 主审计 ───────────────────────────────────────────────────────

def audit(lean: str) -> dict:
    """审计 Lean 文件，返回 {findings, stats, gate}。"""
    blocks = _extract_blocks(lean)
    findings = []
    blocks_audited = 0
    for b in blocks:
        conclusion = _extract_conclusion(b["statement"])
        body = b["body"]
        blocks_audited += 1
        substantive = _has_substantive(body)

        if _is_identity_tautology(conclusion):
            findings.append({
                "type": "identity_tautology",
                "severity": "BLOCK",
                "theorem": b["name"],
                "reason": f"结论字面恒等：{conclusion[:80]}",
            })
        elif _detect_definitional_tautology(conclusion, body):
            findings.append({
                "type": "definitional_tautology",
                "severity": "BLOCK",
                "theorem": b["name"],
                "reason": (f"rw/unfold 展开 conclusion 里的定义后仅剩平凡重排，"
                           f"无实质 tactic（calc/have/ring/exact 均缺失）：{conclusion[:60]}"),
            })
        elif body.strip() and not substantive:
            findings.append({
                "type": "shallow_proof",
                "severity": "WARN",
                "theorem": b["name"],
                "reason": f"证明体无任何实质 tactic（可能是平凡引理，需人工判断）：{conclusion[:60]}",
            })

        # [v2.19.0] Faithfulness 退化输入检测（prove2me 原则 3/5）—— WARN 可叠加
        tfd = _detect_total_function_default(b["statement"])
        if tfd:
            findings.append({
                "type": "total_function_default",
                "severity": "WARN",
                "theorem": b["name"],
                "reason": f"total function 坏输入默认值：{tfd}，statement 无对应保护假设（原则 3）。",
            })
        vac = _detect_vacuous_hypothesis(b["statement"])
        if vac:
            findings.append({
                "type": "vacuous_hypothesis",
                "severity": "WARN",
                "theorem": b["name"],
                "reason": f"vacuous/不可满足假设：{vac}（原则 5）。",
            })

    blocks = [b for b in findings if b["severity"] == "BLOCK"]
    warns = [b for b in findings if b["severity"] == "WARN"]
    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")
    stats = {
        "theorems_audited": blocks_audited,
        "blocks": len(blocks),
        "warns": len(warns),
        "identity_tautologies": sum(1 for f in findings if f["type"] == "identity_tautology"),
        "definitional_tautologies": sum(1 for f in findings if f["type"] == "definitional_tautology"),
        "shallow_proofs": sum(1 for f in findings if f["type"] == "shallow_proof"),
        "total_function_defaults": sum(1 for f in findings if f["type"] == "total_function_default"),
        "vacuous_hypotheses": sum(1 for f in findings if f["type"] == "vacuous_hypothesis"),
    }
    return {"findings": findings, "stats": stats, "gate": gate}


# ── 自测 ─────────────────────────────────────────────────────────

SELF_TEST_LEAN = """import Mathlib

-- ① 字面恒等重言式（BLOCK）
def S := 35 * 1 + 1

theorem identity_taut : 35 * 1 + 1 = 35 * 1 + 1 := by
  rfl

-- ② 定义重言式（BLOCK）：rw [S] 展开结论里的定义，linarith 证恒等式
theorem def_taut : S ≥ 35 * 1 + 1 := by
  rw [S]
  linarith

-- ③ 浅层证明（WARN）：只有 norm_num，无实质 tactic
theorem shallow : 2 + 2 = 4 := by
  norm_num

-- ④ 实质证明（PASS）：calc 链 + ring，有实质数学内容
theorem substantive : (a b : ℝ) → (a + b)^2 = a^2 + 2*a*b + b^2 := by
  intro a b
  calc
    (a + b)^2 = a^2 + 2*a*b + b^2 := by ring

-- ⑤ total function 默认值（WARN）：Real.log 无 x > 0 保护假设（原则 3）
theorem log_unprotected (x : ℝ) : Real.log x = 0 := by
  have h : Real.log x = 0 := by simp [Real.log]
  exact h

-- ⑥ vacuous 假设（WARN）：假设 False 不可满足（原则 5）
theorem vacuous_false (h : False) : 1 = 2 := by
  cases h
"""


def _self_test() -> int:
    report = audit(SELF_TEST_LEAN)
    stats = report["stats"]
    print(f"审计: {stats['theorems_audited']} 个定理")
    print(f"  identity_tautologies={stats['identity_tautologies']}（期望 1）")
    print(f"  definitional_tautologies={stats['definitional_tautologies']}（期望 1）")
    print(f"  shallow_proofs={stats['shallow_proofs']}（期望 1）")
    print(f"  total_function_defaults={stats['total_function_defaults']}（期望 1）")
    print(f"  vacuous_hypotheses={stats['vacuous_hypotheses']}（期望 1）")
    print(f"  gate={report['gate']}（期望 BLOCK）")
    for f in report["findings"]:
        print(f"    [{f['severity']}] {f['theorem']}: {f['reason'][:70]}")

    assert stats["identity_tautologies"] == 1, "字面恒等检测失败"
    assert stats["definitional_tautologies"] == 1, "定义重言式检测失败"
    assert stats["shallow_proofs"] == 1, "浅层证明检测失败"
    assert stats["total_function_defaults"] == 1, "total function 默认值检测失败"
    assert stats["vacuous_hypotheses"] == 1, "vacuous 假设检测失败"
    assert report["gate"] == "BLOCK", "门控应为 BLOCK"
    # 实质定理不应被误报
    assert not any(f["theorem"] == "substantive" for f in report["findings"]), "实质定理被误报"
    print("\n自测通过 ✓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="物理内容审计门控（定义重言式检测）")
    ap.add_argument("--lean", help="Lean 4 证明文件")
    ap.add_argument("--output", default="/tmp/physical_content_audit.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.lean:
        print("用法: python physical_content_audit.py --lean proof.lean [--output ...] [--self-test]")
        return 2

    lean = Path(args.lean).read_text(encoding="utf-8", errors="replace")
    report = audit(lean)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 64)
    print("物理内容审计门控（定义重言式检测）")
    print("=" * 64)
    print(f"  审计定理数: {report['stats']['theorems_audited']}")
    print(f"  定义重言式 (BLOCK): {report['stats']['definitional_tautologies']}")
    print(f"  字面恒等 (BLOCK): {report['stats']['identity_tautologies']}")
    print(f"  浅层证明 (WARN): {report['stats']['shallow_proofs']}")
    print(f"  total function 默认值 (WARN): {report['stats']['total_function_defaults']}")
    print(f"  vacuous 假设 (WARN): {report['stats']['vacuous_hypotheses']}")
    for f in report["findings"]:
        mark = "🔴" if f["severity"] == "BLOCK" else "🟡"
        print(f"    {mark} [{f['type']}] {f['theorem']}: {f['reason'][:80]}")
    print(f"\n  最终 GATE: {report['gate']}")
    print(f"  Report: {args.output}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
