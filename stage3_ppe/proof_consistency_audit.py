#!/usr/bin/env python3
"""
Formal Proof Consistency Audit — Stage 3.5 审计门
=================================================
在 PPE 形式化证明完成后、AI-Scientist 论文生成前，对 Lean 4 证明做
自洽性 + 诚实性 + 数学正确性三重审计。

固化自 CGICE V9.1 / 三峰 V16 / V17 三轮终审 (2026-08-16) 暴露的六类 P0：
  1. 公理自洽性（爆炸原理检测）
  2. 表演性诚实（注释标签 vs 真实 attribute）
  3. 公理计数不一致
  4. 定理存在性（声称 vs 实际）
  5. := by trivial 空壳（假证明）
  6. 离散谱 vs 连续谱（数学类别错误）

Usage:
  python proof_consistency_audit.py --lean proof.lean [--paper paper.txt]
      [--expected-axioms 14] [--expected-theorems 3]
"""

import argparse, json, re, sys
from pathlib import Path
from datetime import datetime


def is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("--") or s.startswith("/-") or s.startswith("-/")


def audit(lean_path: str, paper_path: str = None,
          expected_axioms: int = None, expected_theorems: int = None) -> dict:
    lean = Path(lean_path).read_text(encoding="utf-8", errors="replace")
    # 去除块注释（/- ... -/，含多行 docstring），避免 docstring 中间行被误判为 active 代码
    lean = re.sub(r'/-.*?-/', '', lean, flags=re.S)
    lines = lean.splitlines()

    # ── 提取 active 声明（排除注释行） ────────────────────────
    active = [l for l in lines if not is_comment(l)]

    def count_active(pat):
        return sum(1 for l in active if re.search(pat, l))

    axioms = [l.strip() for l in active if re.match(r'^\s*axiom\s', l)]
    theorems = [l.strip() for l in active if re.match(r'^\s*theorem\s', l)]
    lemmas = [l.strip() for l in active if re.match(r'^\s*lemma\s', l)]

    n_axiom = len(axioms)
    n_theorem = len(theorems)
    n_lemma = len(lemmas)
    n_sorry = count_active(r'\bsorry\b')
    n_admit = count_active(r'\badmit\b')
    n_trivial = count_active(r':=\s*by\s+trivial\b')
    n_true_stub = count_active(r':=\s*True\b')

    findings = []
    blocks = []   # 阻断级
    warns = []    # 警告级

    # ── 检测 2: 表演性诚实 ──────────────────────────────────
    real_attr = sum(1 for l in active if l.strip().startswith('@['))
    # 两种注释标签格式（严格区分）：
    # (a) '-- @[honest_axiom]'：伪装成 Lean attribute 的注释 —— 表演性诚实候选
    # (b) '-- [honest-axiom]'：诚实的概念标签注释 —— 诚实披露，非表演性诚实
    comment_attr_pseudo = sum(1 for l in lines if '-- @[' in l or '--@[' in l)
    comment_attr_honest = sum(1 for l in lines if '-- [honest-axiom]' in l or '--[honest-axiom]' in l)
    if comment_attr_pseudo > 0 and real_attr == 0:
        msg = (f"表演性诚实：{comment_attr_pseudo} 处 '-- @[...]' 注释伪装成 attribute，"
               f"但 0 处真实 Lean attribute。论文不得声称 'declared as @[honest_axiom]'。")
        warns.append(msg)
        findings.append({"type": "performative_honesty", "severity": "WARN",
                         "comment_attrs": comment_attr_pseudo, "real_attrs": real_attr, "msg": msg})
    elif comment_attr_honest > 0 and real_attr == 0:
        # 诚实标签：'-- [honest-axiom]' 是概念标签注释，非 attribute 伪装。
        # 这是诚实披露（若论文明确声明"honest-axiom 是注释标签非 attribute"），不 WARN。
        findings.append({"type": "honest_axiom_comment_labels", "severity": "INFO",
                         "comment_labels": comment_attr_honest, "real_attrs": real_attr,
                         "msg": f"{comment_attr_honest} 处 '-- [honest-axiom]' 概念标签注释"
                                f"（诚实披露，非 attribute 伪装；确认论文未声称 @[honest_axiom]）"})

    # ── 检测 5: := by trivial 空壳 ───────────────────────────
    if n_trivial > 0:
        msg = f"{n_trivial} 处 ':=' by trivial' 空壳证明（编译通过但零数学内容）。"
        warns.append(msg)
        findings.append({"type": "trivial_stub", "severity": "WARN",
                         "count": n_trivial, "msg": msg})
    if n_true_stub > 0:
        msg = f"{n_true_stub} 处 ':=' True' 空壳命题（隐藏 sorry）。"
        warns.append(msg)
        findings.append({"type": "true_stub", "severity": "WARN",
                         "count": n_true_stub, "msg": msg})

    # ── 检测 5b: active admit（等同 sorry，未完成证明） ────────
    # admit 与 sorry 语义相同（接受未证命题），但论文常声称 "0 sorry"
    # 而隐瞒 admit。需单独标记。
    if n_admit > 0:
        msg = (f"{n_admit} 处 active 'admit'（等同 sorry，未完成证明）。"
               f"若论文声称 '0 sorry'，必须同时披露 admit 数量。")
        warns.append(msg)
        findings.append({"type": "active_admit", "severity": "WARN",
                         "count": n_admit, "msg": msg})

    # ── 检测 3: 公理计数不一致 ──────────────────────────────
    if expected_axioms is not None and expected_axioms != n_axiom:
        msg = (f"公理计数不一致：论文声称 {expected_axioms}，Lean 实测 {n_axiom}。"
               f"必须统一为实测数。")
        warns.append(msg)
        findings.append({"type": "axiom_count_mismatch", "severity": "WARN",
                         "claimed": expected_axioms, "actual": n_axiom, "msg": msg})
    if expected_theorems is not None and expected_theorems != n_theorem:
        msg = (f"定理计数不一致：论文声称 {expected_theorems}，Lean 实测 {n_theorem}。")
        warns.append(msg)
        findings.append({"type": "theorem_count_mismatch", "severity": "WARN",
                         "claimed": expected_theorems, "actual": n_theorem, "msg": msg})

    # ── 检测 4: 定理存在性（论文声称 vs Lean 实际） ──────────
    if paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
        # 提取论文中 "theorem X" 或 "theorem x_..." 声称
        claimed = set(re.findall(r'\btheorem\s+`([A-Za-z_][A-Za-z0-9_]*)`', paper))
        declared = set(re.findall(r'^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)', lean, re.M))
        missing = claimed - declared
        # 过滤：编号（"theorem 2"）、英文常见词（"theorem X states/and/..."）
        _EN_WORDS = {'and','or','the','a','an','of','for','in','on','is','are','was','were',
                     'states','shows','proves','establishes','gives','yields','follows','that',
                     'this','it','we','our','which','with','from','by','to','at','as'}
        missing = {m for m in missing if not re.match(r'^\d+$', m) and m.lower() not in _EN_WORDS}
        if missing:
            msg = (f"定理虚假声称：论文提到 {len(missing)} 个 Lean 中不存在的定理: "
                   f"{sorted(missing)[:8]}")
            blocks.append(msg)
            findings.append({"type": "phantom_theorem", "severity": "BLOCK",
                             "missing": sorted(missing), "msg": msg})

    # ── 检测 1: 公理自洽性（等式链矛盾检测） ────────────────
    # 提取 "F t = expr" 或 "F t ≠ expr" 形式的等式（F 是函数名，可带参数）
    # lhs 匹配函数应用形式（如 I_cycle t，而非单个 t）
    eq_map = {}   # 左端标识 -> set of 右端表达式
    neq_pairs = []
    for ax in axioms:
        m = re.match(r'axiom\s+\w+\s*(?:\([^)]*\))?\s*:\s*(.*)', ax)
        if not m:
            continue
        body = m.group(1)
        # 找 "F args = Y"（F 后跟参数，捕获完整函数应用）
        for eqm in re.finditer(r'([A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)*)\s*=\s*([^,;\n]+)', body):
            lhs = eqm.group(1).strip()
            rhs = eqm.group(2).strip()
            # 跳过单字母 lhs、下划线开头 lhs（如 _CC t 是 Λ_CC t 的截断误匹配）、含算符的 lhs
            if len(lhs) <= 1 or ' ' not in lhs or lhs.startswith('_'):
                continue
            if lhs not in eq_map:
                eq_map[lhs] = set()
            eq_map[lhs].add(rhs)
        for neqm in re.finditer(r'([A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)*)\s*≠\s*([^,;\n]+)', body):
            lhs = neqm.group(1).strip()
            rhs = neqm.group(2).strip()
            if len(lhs) <= 1 or ' ' not in lhs or lhs.startswith('_'):
                continue
            neq_pairs.append((lhs, rhs))

    # 检测同名函数应用的 "= 和 ≠" 冲突（简化启发式）
    for lhs, rhs in neq_pairs:
        if lhs in eq_map and eq_map[lhs]:
            msg = (f"公理自洽性警告：`{lhs}` 同时被声明为等于 {sorted(eq_map[lhs])[:3]} "
                   f"和不等于 `{rhs}`。需人工验证是否矛盾（可能触发爆炸原理）。")
            warns.append(msg)
            findings.append({"type": "axiom_consistency_suspect", "severity": "WARN",
                             "lhs": lhs, "eq": sorted(eq_map[lhs])[:3],
                             "neq": rhs, "msg": msg})

    # ── 检测 6: 离散谱 vs 连续谱 ────────────────────────────
    # 检测 "spectrum ... = k * lambda" 或 "lambda_k = k * lambda" 等差谱声称
    spectrum_claim = re.search(
        r'(spectrum|spectral)[^.\n]{0,120}(k\s*[:*]?\s*\w+|\w+\s*=\s*k\s*\*\s*\w+)',
        lean, re.I)
    noncompact_hint = re.search(r'non[- ]?compact|SL\([^)]*\)/SU\(', lean, re.I)
    # 澄清：文件已区分「连续自由谱 (Harish-Chandra)」vs「离散束缚态 (Witten 势阱)」
    spectrum_clarified = re.search(r'absolutely\s+continuous|bound\s+states?|Harish[- ]?Chandra', lean, re.I)
    if spectrum_claim and noncompact_hint and not spectrum_clarified:
        msg = ("离散谱 vs 连续谱：文件同时声称离散谱（等差 λ_k=k·λ）"
               "和非紧对称空间。非紧空间谱是连续的（Plancherel 测度），"
               "离散谱声称是数学类别错误。")
        warns.append(msg)
        findings.append({"type": "discrete_spectrum_on_noncompact", "severity": "WARN",
                         "msg": msg})

    # ── 汇总 ────────────────────────────────────────────────
    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    report = {
        "audit_time": datetime.now().isoformat(),
        "lean_file": lean_path,
        "paper_file": paper_path,
        "stats": {
            "axioms": n_axiom,
            "theorems": n_theorem,
            "lemmas": n_lemma,
            "active_sorry": n_sorry,
            "active_admit": n_admit,
            "trivial_stubs": n_trivial,
            "true_stubs": n_true_stub,
            "real_attributes": real_attr,
            "comment_attributes_pseudo": comment_attr_pseudo,
            "comment_attributes_honest": comment_attr_honest,
        },
        "gate": gate,
        "blocks": blocks,
        "warns": warns,
        "findings": findings,
    }
    return report


def main():
    ap = argparse.ArgumentParser(description="Formal Proof Consistency Audit (Stage 3.5)")
    ap.add_argument("--lean", required=True, help="Lean 4 proof file")
    ap.add_argument("--paper", help="Paper text (for phantom theorem detection)")
    ap.add_argument("--expected-axioms", type=int, help="Claimed axiom count from paper")
    ap.add_argument("--expected-theorems", type=int, help="Claimed theorem count from paper")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()

    report = audit(args.lean, args.paper, args.expected_axioms, args.expected_theorems)

    out_path = args.output or "/tmp/proof_consistency_audit.json"
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Formal Proof Consistency Audit (Stage 3.5)")
    print("=" * 60)
    s = report["stats"]
    print(f"  axioms={s['axioms']}  theorems={s['theorems']}  lemmas={s['lemmas']}")
    print(f"  sorry={s['active_sorry']}  admit={s['active_admit']}  "
          f"trivial_stubs={s['trivial_stubs']}  true_stubs={s['true_stubs']}")
    print(f"  real_attrs={s['real_attributes']}  pseudo_attrs={s['comment_attributes_pseudo']}  honest_labels={s['comment_attributes_honest']}")
    print(f"\n  GATE: {report['gate']}")
    for b in report["blocks"]:
        print(f"  🔴 BLOCK: {b}")
    for w in report["warns"]:
        print(f"  🟡 WARN: {w}")
    print(f"\n  Report: {out_path}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
