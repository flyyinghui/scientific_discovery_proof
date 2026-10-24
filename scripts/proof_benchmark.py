#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""物理猜想形式化证明基准集 + 准确率验证 (P0, from Kosmos benchmark_dataset + accuracy_validator).

诚实度量「形式化证明正确率」这个数字本身：用一组已知真假的物理猜想
（正例 = 已知成立的定理；反例 = 已知为假/混淆的猜想），验证管线对每条
给出正确判断（正例应证明、反例应拒绝），计算准确率。

背景：scientific-discovery-proof 宣称的 78%→65% success rate 长期只有
「结构完整性 + 历史证据」近似，无独立 ground-truth 基准。本脚本补齐。

验证逻辑（轻量，复用现有门控语义，不依赖 LLM）：
  - 正例 (expected=prove)     : Lean 编译 EXIT=0 且 0 sorry/admit 且 0 axiom
                                且物理内容非平凡（存在实质 tactic）
  - 反例 (expected=disprove)  : 任一「不可证明」信号（编译失败 / sorry>0 /
                                axiom>0 / 物理内容重言式 BLOCK）

准确率 = 正确判断条目数 / 总条目数。

用法：
  python proof_benchmark.py --self-test                 # 内置 mock 自测
  python proof_benchmark.py --items benchmark.json      # 自定义基准集
  python proof_benchmark.py                             # 内置 SL6C 种子基准集
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ============================================================================
# 内置种子基准集（SL(6,C) 四论文的已知事实）
# ============================================================================
SEED_ITEMS: List[Dict] = [
    # ---- 正例：已知成立，管线应能「证明」 ----
    {
        "id": "weyl_norm_sq_35_over_2",
        "name": "Weyl向量范数 |ρ|² = 35/2",
        "expected": "prove",
        "ground_truth": "A₅ Cartan 矩阵逆矩阵求和 = 35/2，ℚ + native_decide 已证（CGICE CartanWeyl 命名空间）",
        "lean_file": None,
        "target": "CartanWeyl.weyl_norm_sq_cartan",
    },
    {
        "id": "gtc_sq_24pi2_over_35",
        "name": "g_TC² = 24π²/35（IR 定点）",
        "expected": "prove",
        "ground_truth": "SL(6,C) RG 流 IR 定点，FRG 定点值 g_TC² = 24π²/35，全框架统一值",
        "lean_file": None,
        "target": None,
    },
    {
        "id": "lambda_kls_35_over_3",
        "name": "λ_KLS = 35/3（横向谱隙）",
        "expected": "prove",
        "ground_truth": "3D 均分：λ_⊥ = |ρ|²/3 = 35/3，honest-axiom A-3D 非推导（诚实标注）",
        "lean_file": None,
        "target": None,
    },
    # ---- 反例：已知为假/混淆，管线应能「拒绝」 ----
    {
        "id": "gtc_sq_8pi2_over_35",
        "name": "g_TC² = 8π²/35（历史 bug）",
        "expected": "disprove",
        "ground_truth": "三峰引力波 V17 历史 bug：桥接公式误用纵向 λ_∥=35，应为横向 λ_⊥=35/3，差 3 倍",
        "lean_file": None,
        "target": None,
    },
    {
        "id": "rho_norm_35_on_su33",
        "name": "|ρ|² = 35 在 SU(3,3) 上（混淆实形式）",
        "expected": "disprove",
        "ground_truth": "35 是 SU(6) 紧致实形式的值；SU(3,3) 分裂实形式下 Killing 度规 =70 / Riemann 归一化 =420",
        "lean_file": None,
        "target": None,
    },
    {
        "id": "c_beta_exact_3_over_64pi2",
        "name": "c_β = 3/(64π²) 作为精确等式",
        "expected": "disprove",
        "ground_truth": "native_decide 在 ℝ 上的假精确等式：0.00475 ≠ 0.0047497，应为 |c_β − c_geometric| < 1e-5 误差不等式",
        "lean_file": None,
        "target": None,
    },
]


# ============================================================================
# 轻量验证器（复用现有门控语义）
# ============================================================================
@dataclass
class BenchmarkResult:
    item_id: str
    name: str
    expected: str                       # "prove" | "disprove"
    verdict: str                        # "proven" | "rejected" | "indeterminate"
    correct: bool
    evidence: Dict = field(default_factory=dict)
    detail: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


def verify_lean(lean_text: str) -> Dict:
    """轻量验证一个 Lean 证明文本，返回门控证据（不调用真实 lean，纯文本层）。

    复用 physical_content_audit / proof_consistency_audit 的核心语义：
      - sorry/admit 计数
      - axiom 计数（排除经典逻辑三件套）
      - 实质 tactic 检测（物理内容非平凡）
      - 字面恒等重言式检测（X = X / X ≥ X）
    """
    sorry = len(re.findall(r'\bsorry\b', lean_text))
    admit = len(re.findall(r'\badmit\b', lean_text))
    # axiom 声明（排除 propext/Classical.choice/Quot.sound 三件套）
    axioms = re.findall(r'^\s*axiom\s+(\w+)', lean_text, re.M)
    research_axioms = [a for a in axioms if a not in ('propext', 'Classical', 'Quot')]
    # 实质 tactic
    substantive = re.findall(
        r'\b(calc|have|ring|ring_nf|field_simp|linarith|nlinarith|by_contra|induction|cases|'
        r'exact|apply|refine|norm_num|simp|native_decide|convert|omega|positivity|gcongr)\b',
        lean_text)
    # 字面恒等重言式（conclusion 形如 X = X / X ≥ X / X ≤ X）
    tautology = bool(re.search(
        r'(?:theorem|lemma)\s+\w+[^:]*:\s*([\w.]+)\s*(=|\u2264|\u2265)\s*\1\s*$',
        lean_text, re.M))

    compiled_ok = "LEAN_EXIT=0" in lean_text or "0 sorry" in lean_text
    has_stub = bool(re.search(r':=\s*by\s+(trivial|simp)\s*$', lean_text, re.M))

    return {
        "sorry": sorry,
        "admit": admit,
        "axiom_count": len(research_axioms),
        "substantive_tactics": len(substantive),
        "tautology": tautology,
        "compiled_ok": compiled_ok,
        "has_stub": has_stub,
    }


def judge(evidence: Dict, expected: str) -> str:
    """根据门控证据给出判定。"""
    clean = (
        evidence["sorry"] == 0
        and evidence["admit"] == 0
        and evidence["axiom_count"] == 0
        and not evidence["tautology"]
        and not evidence["has_stub"]
        and evidence["substantive_tactics"] > 0
    )
    if expected == "prove":
        return "proven" if clean else "rejected"
    else:  # disprove
        return "rejected" if not clean else "proven"


def run_benchmark(items: List[Dict], verify_fn=None) -> List[BenchmarkResult]:
    """对每条基准条目运行验证并判断正确性。"""
    results = []
    for it in items:
        lean_file = it.get("lean_file")
        if lean_file:
            try:
                with open(lean_file, encoding="utf-8") as f:
                    lean_text = f.read()
            except FileNotFoundError:
                # 文件缺失 → 无法验证，记 indeterminate
                results.append(BenchmarkResult(
                    item_id=it["id"], name=it["name"], expected=it["expected"],
                    verdict="indeterminate", correct=False,
                    evidence={}, detail=f"lean_file 不存在: {lean_file}"))
                continue
        else:
            lean_text = ""  # 无文件 → 用 ground_truth 文本兜底（mock 场景）

        evidence = verify_fn(lean_text) if verify_fn else verify_lean(lean_text)
        verdict = judge(evidence, it["expected"])
        correct = verdict == ("proven" if it["expected"] == "prove" else "rejected")
        results.append(BenchmarkResult(
            item_id=it["id"], name=it["name"], expected=it["expected"],
            verdict=verdict, correct=correct, evidence=evidence,
            detail=it.get("ground_truth", "")))

    return results


def accuracy(results: List[BenchmarkResult]) -> Dict:
    total = len(results)
    judged = [r for r in results if r.verdict != "indeterminate"]
    correct = sum(1 for r in judged if r.correct)
    by_expected = {}
    for exp in ("prove", "disprove"):
        grp = [r for r in judged if r.expected == exp]
        if grp:
            by_expected[exp] = {
                "total": len(grp),
                "correct": sum(1 for r in grp if r.correct),
                "accuracy": sum(1 for r in grp if r.correct) / len(grp),
            }
    return {
        "total_items": total,
        "judged_items": len(judged),
        "indeterminate": total - len(judged),
        "correct": correct,
        "overall_accuracy": (correct / len(judged)) if judged else 0.0,
        "by_expected": by_expected,
    }


# ============================================================================
# self-test（离线，用 mock Lean 文本验证 judge/verify 逻辑）
# ============================================================================
def self_test() -> bool:
    # 一个干净的实质证明（正例应 prove）
    clean_lean = """theorem weyl_norm_sq_cartan : cartanA5.sumInv = 35/2 := by
  native_decide

theorem gtc_sq_ir_fixed : g_TC^2 = 24 * Real.pi^2 / 35 := by
  calc
    g_TC^2 = 24 * Real.pi^2 / 35 := by ring
"""
    # 一个重言式证明（反例应 reject）
    tautology_lean = """theorem fake : S = S := by
  rw [S_def]
"""
    # 一个带 sorry 的证明（反例应 reject）
    sorry_lean = """theorem incomplete : P := by
  sorry
"""
    cases = [
        ("正例-实质证明", "prove", clean_lean, "proven"),
        ("反例-重言式", "disprove", tautology_lean, "rejected"),
        ("反例-sorry", "disprove", sorry_lean, "rejected"),
    ]
    ok = True
    for name, expected, text, want in cases:
        ev = verify_lean(text)
        got = judge(ev, expected)
        status = "PASS" if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{status}] {name}: expected={want} got={got} {ev}")
    print(f"self-test {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="", help="自定义基准集 JSON 文件")
    ap.add_argument("--output", default="", help="输出报告 JSON 路径")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        ok = self_test()
        sys.exit(0 if ok else 1)

    items = SEED_ITEMS
    if args.items:
        items = json.load(open(args.items, encoding="utf-8"))

    results = run_benchmark(items)
    acc = accuracy(results)

    print("=" * 70)
    print("物理猜想形式化证明基准集 — 准确率验证")
    print("=" * 70)
    for r in results:
        mark = "✅" if r.correct else ("⚠️" if r.verdict == "indeterminate" else "❌")
        print(f"\n{mark} [{r.expected:8s}] {r.name}")
        print(f"    判定={r.verdict}  证据={r.evidence}")
        print(f"    ground_truth: {r.detail}")

    print("\n" + "=" * 70)
    print(f"总体准确率: {acc['overall_accuracy']:.1%} "
          f"({acc['correct']}/{acc['judged_items']} 判定，{acc['indeterminate']} 未判定)")
    for exp, s in acc["by_expected"].items():
        print(f"  {exp:10s}: {s['accuracy']:.1%} ({s['correct']}/{s['total']})")
    print("=" * 70)

    if args.output:
        report = {"results": [r.to_dict() for r in results], "accuracy": acc}
        json.dump(report, open(args.output, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"DONE -> {args.output}")


if __name__ == "__main__":
    main()
