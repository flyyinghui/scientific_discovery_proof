#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""猜想 JSON 前置规范检查 — Target 强度分层 + 平凡化排除声明（v2.19.0, prove2me 二次评估 P0-①②）

把 V64 教训（「0 sorry / 0 axiom 编译通过 ≠ 物理推导成立」）从「事后检测」
（physical_content_audit.py）前移到「猜想定义时的前置声明」。

来源：prove2me `references/mission_description.md` §3 Target + §6 Formalization scope。

两个前置字段（conjecture.json 可选字段）：
  1. `target_strength`: 目标强度分层
     - "weakest_stable"      → 目标 = 最弱稳定陈述（断言真相的形状，非硬编码常数）→ PASS
     - "hardcoded_constant"  → 目标硬编码常数（会被下一个改进推翻）→ WARN
     - 缺失                  → 未声明 → WARN
  2. `anti_trivialization`: 一句话排除平凡化形式化
     - 存在 → PASS
     - 缺失 → WARN（提示排除 vacuous hypothesis / trivial-true definition /
               hard-coded special case）

门控：本检查只产生 PASS / WARN，**不 BLOCK**（它是前置规范，不是硬门控；
平凡化的实质检测由 physical_content_audit.py 事后兜底）。

用法：
  python conjecture_spec_check.py --conjecture conjecture.json --output /tmp/spec_check.json
  python conjecture_spec_check.py --self-test

stdlib-only，可作 Stage 1 前的独立提示。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── 主检查 ─────────────────────────────────────────────────────

TRIVIALIZATION_HINTS = [
    "vacuous hypothesis（假设无实例可满足）",
    "trivial-true definition（定义使结论平凡为真）",
    "hard-coded special case（硬编码的易解特例）",
]


def check(conjecture: dict) -> dict:
    """检查 conjecture.json 的前置规范字段，返回 {findings, stats, gate}。"""
    findings = []
    name = conjecture.get("name", "Untitled")

    # ① target_strength
    ts = conjecture.get("target_strength", "").strip()
    if not ts:
        findings.append({
            "type": "target_strength_missing",
            "severity": "WARN",
            "reason": (
                "猜想未声明 target_strength（目标强度分层）。建议声明目标是最弱稳定陈述"
                "（断言真相的形状）还是硬编码常数——硬编码常数的目标会被下一个改进推翻"
                "（V64 教训：S := 谱底·‖φ‖²+V 这类硬编码定义是 faithfulness gap）。"
            ),
        })
    elif ts == "hardcoded_constant":
        findings.append({
            "type": "target_hardcoded_constant",
            "severity": "WARN",
            "reason": (
                "目标声明为 hardcoded_constant（硬编码常数）。此类目标会被下一个改进推翻，"
                "且易诱发「把物理对象定义为常数恒等式」的重言式（V64 教训）。若常数有独立"
                "来源（如几何推导），请在 anti_trivialization 里说明其来源。"
            ),
        })
    elif ts == "weakest_stable":
        pass  # PASS，无需记录
    else:
        findings.append({
            "type": "target_strength_unknown",
            "severity": "WARN",
            "reason": f"target_strength 取值未知：{ts!r}（应为 weakest_stable 或 hardcoded_constant）。",
        })

    # ② anti_trivialization
    at = conjecture.get("anti_trivialization", "").strip()
    if not at:
        findings.append({
            "type": "anti_trivialization_missing",
            "severity": "WARN",
            "reason": (
                "猜想未声明 anti_trivialization（平凡化排除）。建议一句话排除："
                + " / ".join(TRIVIALIZATION_HINTS)
                + "。这是「前置声明」——在定义猜想时就排除平凡化形式化，"
                "而非等编译通过后再抓重言式（后者由 physical_content_audit.py 兜底）。"
            ),
        })

    warns = [f for f in findings if f["severity"] == "WARN"]
    gate = "WARN" if warns else "PASS"
    stats = {
        "conjecture": name,
        "target_strength": ts or "(missing)",
        "anti_trivialization": "present" if at else "(missing)",
        "warns": len(warns),
    }
    return {"findings": findings, "stats": stats, "gate": gate}


# ── 自测 ─────────────────────────────────────────────────────

def _self_test() -> int:
    print("=" * 64)
    print("conjecture_spec_check 自测")
    print("=" * 64)

    # ① 缺失两个字段 → WARN ×2
    r1 = check({"name": "missing_both"})
    assert r1["gate"] == "WARN", "缺失字段应 WARN"
    assert r1["stats"]["warns"] == 2, f"应有 2 个 WARN，实际 {r1['stats']['warns']}"
    print(f"  缺失两字段: gate={r1['gate']} warns={r1['stats']['warns']} ✓")

    # ② hardcoded_constant → WARN
    r2 = check({"name": "hardcoded", "target_strength": "hardcoded_constant",
                "anti_trivialization": "exclude trivial"})
    assert r2["gate"] == "WARN", "硬编码常数应 WARN"
    assert any(f["type"] == "target_hardcoded_constant" for f in r2["findings"])
    print(f"  硬编码常数: gate={r2['gate']} ✓")

    # ③ weakest_stable + anti_trivialization → PASS
    r3 = check({"name": "good", "target_strength": "weakest_stable",
                "anti_trivialization": "exclude vacuous hypothesis and trivial-true definition"})
    assert r3["gate"] == "PASS", "完整字段应 PASS"
    assert r3["stats"]["warns"] == 0
    print(f"  完整字段: gate={r3['gate']} warns={r3['stats']['warns']} ✓")

    print("\n自测通过 ✓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="猜想 JSON 前置规范检查（Target 强度分层 + 平凡化排除）")
    ap.add_argument("--conjecture", help="conjecture.json 路径")
    ap.add_argument("--output", default="/tmp/conjecture_spec_check.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.conjecture:
        print("用法: python conjecture_spec_check.py --conjecture conjecture.json [--output ...] [--self-test]")
        return 2

    conjecture = json.loads(Path(args.conjecture).read_text(encoding="utf-8"))
    report = check(conjecture)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 64)
    print("猜想 JSON 前置规范检查（Target 强度分层 + 平凡化排除）")
    print("=" * 64)
    print(f"  猜想: {report['stats']['conjecture']}")
    print(f"  target_strength: {report['stats']['target_strength']}")
    print(f"  anti_trivialization: {report['stats']['anti_trivialization']}")
    for f in report["findings"]:
        mark = "🔴" if f["severity"] == "BLOCK" else "🟡"
        print(f"    {mark} [{f['type']}] {f['reason'][:100]}")
    print(f"\n  最终 GATE: {report['gate']}（WARN 不阻断，仅前置提示）")
    print(f"  Report: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
