#!/usr/bin/env python3
"""
milestone_curation.py — 里程碑 curation（prove2me mission_captain 机制）
==========================================================================
把猜想 JSON 的关键支持定理显式化为「权威里程碑」（milestone），供
faithfulness_readback.py 审计和管线追踪。

prove2me 语义：captain 把关键支持定理设为里程碑（lemma-level sub-targets with
authoritative statements），每个里程碑有忠实于源材料的 statement。这里：
  1. 若 conjecture.json 已有 `milestones` 字段 → 验证关联一致性（每个 milestone
     的 references 必须指向有效的 axiom/lemma/target）。
  2. 若没有 → 从 targets[].required_lemmas 自动提名里程碑（被目标显式依赖的
     关键引理 = 权威里程碑候选）。

用法:
  python milestone_curation.py --conjecture conjecture.json [--output milestones.json]
  也可作为模块导入: from milestone_curation import curate_milestones
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


def _index_conjecture(conjecture: dict) -> dict:
    """建立 axiom/lemma/target 的 id → statement 索引。"""
    idx = {"axioms": {}, "lemmas": {}, "targets": {}}
    for ax in conjecture.get("axioms", []):
        if isinstance(ax, dict) and ax.get("id"):
            idx["axioms"][ax["id"]] = ax
    for lm in conjecture.get("lemmas", []):
        if isinstance(lm, dict) and lm.get("id"):
            idx["lemmas"][lm["id"]] = lm
    for tg in conjecture.get("targets", []):
        if isinstance(tg, dict) and tg.get("id"):
            idx["targets"][tg["id"]] = tg
    return idx


def _auto_nominate(conjecture: dict, idx: dict) -> list:
    """从 targets[].required_lemmas 提名里程碑（关键支持定理）。"""
    milestones = []
    seen = set()
    for tg in conjecture.get("targets", []):
        for lid in tg.get("required_lemmas", []):
            if lid in seen:
                continue
            seen.add(lid)
            lm = idx["lemmas"].get(lid)
            if lm:
                milestones.append({
                    "id": f"MS_{lid}",
                    "title": lm.get("name", lid),
                    "statement": lm.get("statement", ""),
                    "references": [lid],
                    "status": lm.get("status", "unproven"),
                })
    return milestones


def curate_milestones(conjecture: dict) -> dict:
    idx = _index_conjecture(conjecture)

    explicit = conjecture.get("milestones", [])
    issues = []
    if explicit:
        # 验证显式里程碑的关联一致性
        milestones = []
        for ms in explicit:
            refs = ms.get("references", [])
            for r in refs:
                if not any(r in idx[kind] for kind in idx):
                    issues.append(f"里程碑 {ms.get('id','?')} 引用未知 id: {r}")
            milestones.append(ms)
        mode = "explicit"
    else:
        milestones = _auto_nominate(conjecture, idx)
        mode = "auto-nominated"

    return {
        "curation": "milestone_curation",
        "time": datetime.now().isoformat(),
        "mode": mode,
        "n_milestones": len(milestones),
        "milestones": milestones,
        "issues": issues,
        "gate": "WARN" if issues else "PASS",
    }


def main():
    ap = argparse.ArgumentParser(description="里程碑 curation（prove2me mission_captain）")
    ap.add_argument("--conjecture", required=True, help="conjecture.json 路径")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    args = ap.parse_args()

    conjecture = json.loads(Path(args.conjecture).read_text(encoding="utf-8"))
    report = curate_milestones(conjecture)

    out = args.output or "/tmp/milestones.json"
    Path(out).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Milestone Curation (prove2me mission_captain)")
    print("=" * 60)
    print(f"  mode={report['mode']}  milestones={report['n_milestones']}")
    for ms in report["milestones"]:
        print(f"    [{ms['id']}] {ms['title']} (refs={ms.get('references', [])})")
    for i in report["issues"]:
        print(f"  ⚠️ {i}")
    print(f"  gate={report['gate']}")
    print(f"\n  Output: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
