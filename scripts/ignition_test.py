#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 3.6+ 点火测试（ignition test）—— AIDE² Level 2 诊断（2026-10-12）。

测试「发现的 agent 是否成为更好的改进者」（RSI Level 1 → Level 2 的唯一可操作判据）。

方法（诚实、可操作、离线）：
1. 读 archive.jsonl，按 generation 分前/后两半。
2. 前半段（早期策略）vs 后半段（后期策略）的接受率 + 平均 gain。
3. 后期接受率/平均 gain 显著高于早期 → 策略在改进（点火弱信号，Level 2 候选）；
   否则 → 净正（Level 1）。

诚实边界：
- 这是「策略效率随时间的趋势」诊断，不是「改进自身改进能力」的严格证明。
- AIDE² 的点火测试（发现的 agent 重坐外层循环达同样天花板步数更少）是更强的判据，
  需要完整的 agent 重跑；本脚本用「接受率趋势」作为离线代理。
- Level 3（拐点/智能爆炸）本脚本永不声称。

用法：
  python ignition_test.py --archive /tmp/stage36/archive.jsonl [--output /tmp/ignition.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def run(archive_path: Path) -> dict:
    records = [
        json.loads(line)
        for line in archive_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # 排除 Gen 0 种子（不是变异产物）
    gens = [r for r in records if r.get("generation", 0) > 0]
    if len(gens) < 2:
        return {
            "verdict": "insufficient data",
            "rsi_level": None,
            "reason": "需要至少 2 代变异记录才能判断策略效率趋势",
        }

    n = len(gens)
    half = n // 2
    early, late = gens[:half], gens[half:]

    def acc_rate(rs):
        acc = sum(1 for r in rs if r.get("accepted"))
        return acc / len(rs) if rs else 0.0

    def avg_gain(rs):
        gains = [r.get("gain", 0.0) for r in rs]
        return statistics.mean(gains) if gains else 0.0

    early_acc = acc_rate(early)
    late_acc = acc_rate(late)
    early_gain = avg_gain(early)
    late_gain = avg_gain(late)

    # 点火判据：后期接受率显著高于早期（≥15 个百分点）或后期平均 gain 显著更高（≥5 分）
    acc_improved = late_acc - early_acc >= 0.15
    gain_improved = late_gain - early_gain >= 5.0
    ignition = acc_improved or gain_improved

    verdict = (
        "ignition (Level 2 candidate — improving its own improvement efficiency)"
        if ignition
        else "net-positive (Level 1 — no ignition signal)"
    )
    return {
        "verdict": verdict,
        "rsi_level": 2 if ignition else 1,
        "early_acceptance_rate": round(early_acc, 3),
        "late_acceptance_rate": round(late_acc, 3),
        "early_avg_gain": round(early_gain, 1),
        "late_avg_gain": round(late_gain, 1),
        "n_generations": n,
        "ignition_signal": ignition,
        "note": "策略效率随时间的趋势诊断；非「改进自身改进能力」的严格证明",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="AIDE² Level 2 ignition test（点火测试）")
    ap.add_argument("--archive", required=True, help="archive.jsonl 路径")
    ap.add_argument("--output", default=None, help="输出 JSON 路径（可选）")
    args = ap.parse_args()

    result = run(Path(args.archive))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
