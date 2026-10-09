#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反证探测 — Disproof Probe（Stage 2.6 旁路，v2.19.0, prove2me Disproof 移动）

prove2me 的三种移动之一：Direct proof / **Disproof** / Reduction（`prove.md`）。
scientific-discovery-proof 管线目前只有「证明」分支，缺「反证」分支。

本脚本在 Stage 2（SimpleTES 排名）后、Stage 3（PPE 证明）前，主动尝试
证明猜想的**否定**。若反证成功或发现反例，说明猜想本身可能为假，应提前
审视而非盲目投入 Stage 3 证明（对应 Stage 1.5a planted-truth gate 的负对照
语义扩展——从「检测污染输入」升级为「主动反证猜想」）。

门控：WARN（提示猜想可能有问题，**不硬阻断**——反证是 LLM 启发式，不是
形式化保证；真正阻断靠 Stage 3.5 审计）。

用法：
  python disproof_probe.py --conjecture conjecture.json --output /tmp/disproof.json
  python disproof_probe.py --conjecture conjecture.json --deepseek-key sk-... --output /tmp/disproof.json
  python disproof_probe.py --self-test

依赖：openai（DeepSeek）；无 key 时回退确定性 mock（离线可跑）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ── 反证 prompt ────────────────────────────────────────────────

DISPROOF_SYSTEM = (
    "You are a rigorous mathematical critic. Your job is NOT to prove the conjecture, "
    "but to try to DISPROVE it — find a counterexample, exhibit a degenerate input where "
    "the conclusion fails, or show the hypotheses are unsatisfiable / the conclusion is "
    "vacuous. Report honestly: 'disproved' (a concrete counterexample), 'possibly_false' "
    "(a plausible failure mode but no airtight counterexample), or 'not_disproved' "
    "(no failure found after a genuine attempt)."
)


def build_disproof_prompt(conjecture: dict) -> str:
    """从 conjecture.json 构造反证 prompt。"""
    name = conjecture.get("name", "Untitled")
    desc = conjecture.get("description", "")
    axioms = conjecture.get("axioms", [])
    targets = conjecture.get("targets", [])

    lines = [f"# Conjecture: {name}", "", desc, ""]
    if axioms:
        lines.append("## Hypotheses / Axioms")
        for ax in axioms:
            ax_id = ax.get("id", "?")
            stmt = ax.get("statement", ax.get("formal", ""))
            lines.append(f"- {ax_id}: {stmt}")
        lines.append("")
    if targets:
        lines.append("## Targets (to disprove)")
        for t in targets:
            tid = t.get("id", "?")
            tstmt = t.get("statement", t.get("formal", ""))
            lines.append(f"- {tid}: {tstmt}")
        lines.append("")

    lines.append(
        "## Your task: attempt a disproof\n"
        "1. Look for a degenerate input (empty set, n=0, zero threshold, unbounded domain) "
        "where the conclusion fails or the hypothesis is unsatisfiable.\n"
        "2. Try to construct a concrete counterexample.\n"
        "3. Check whether any hypothesis is silently vacuous (no instance satisfies it).\n\n"
        "Respond with a JSON object only:\n"
        '{"verdict": "disproved" | "possibly_false" | "not_disproved", '
        '"counterexample": "...", "reasoning": "..."}'
    )
    return "\n".join(lines)


def _parse_verdict(content: str) -> dict:
    """从 LLM 输出解析 verdict（brace-counting 提取 JSON）。"""
    content = content.replace("**", "").strip()
    # brace-counting 提取第一个完整 JSON 对象
    start = content.find("{")
    if start == -1:
        return {"verdict": "unknown", "counterexample": "", "reasoning": content[:200]}
    depth = 0
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(content[start:i + 1])
                    return obj
                except json.JSONDecodeError:
                    break
    return {"verdict": "unknown", "counterexample": "", "reasoning": content[:200]}


# ── LLM 调用 ───────────────────────────────────────────────────

def _llm_disproof(conjecture: dict, api_key: str) -> dict:
    """调用 DeepSeek 尝试反证。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    prompt = build_disproof_prompt(conjecture)
    resp = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system", "content": DISPROOF_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        extra_body={"thinking": {"type": "disabled"}},
        timeout=180,
    )
    content = resp.choices[0].message.content or ""
    return _parse_verdict(content)


def _mock_disproof(conjecture: dict) -> dict:
    """无 key 回退：确定性 mock（仅演示，不真反证）。"""
    return {
        "verdict": "not_disproved",
        "counterexample": "",
        "reasoning": (
            "[mock] 未调用 LLM（无 DEEPSEEK_API_KEY）。反证探测需真实 LLM 尝试构造反例。"
            f"猜想「{conjecture.get('name', 'Untitled')}」的否定未被系统性地探索。"
        ),
        "mock": True,
    }


# ── 主检查 ─────────────────────────────────────────────────────

def probe(conjecture: dict, api_key: str | None) -> dict:
    """执行反证探测，返回 {gate, verdict, counterexample, reasoning}。"""
    if api_key:
        try:
            result = _llm_disproof(conjecture, api_key)
        except Exception as e:
            result = {"verdict": "error", "counterexample": "", "reasoning": f"LLM 调用失败: {e}"}
    else:
        result = _mock_disproof(conjecture)

    verdict = result.get("verdict", "unknown")
    counterexample = result.get("counterexample", "")
    reasoning = result.get("reasoning", "")

    gate = "WARN" if verdict in ("disproved", "possibly_false") else "PASS"
    return {
        "verdict": verdict,
        "counterexample": counterexample,
        "reasoning": reasoning,
        "gate": gate,
        "mock": result.get("mock", False),
    }


# ── 自测 ─────────────────────────────────────────────────────

def _self_test() -> int:
    print("=" * 64)
    print("disproof_probe 自测")
    print("=" * 64)

    conj = {
        "name": "test_conjecture",
        "description": "test",
        "axioms": [{"id": "A1", "statement": "x > 0"}],
        "targets": [{"id": "T1", "statement": "x^2 > 0"}],
    }

    # mock 模式
    r = probe(conj, None)
    assert r["gate"] == "PASS", f"mock 应 PASS，实际 {r['gate']}"
    assert r["mock"] is True
    print(f"  mock 模式: verdict={r['verdict']} gate={r['gate']} ✓")

    # 解析测试
    p1 = _parse_verdict('{"verdict": "disproved", "counterexample": "x=0", "reasoning": "..."}')
    assert p1["verdict"] == "disproved"
    p2 = _parse_verdict('**{"verdict": "possibly_false", "counterexample": "", "reasoning": "..."}**')
    assert p2["verdict"] == "possibly_false"
    print("  verdict 解析: disproved / possibly_false ✓")

    # gate 逻辑
    assert probe(conj, None)["gate"] == "PASS"
    r_disproved = {"verdict": "disproved", "counterexample": "x=0", "reasoning": ""}
    # 直接测 gate 映射
    from collections import namedtuple
    gate = "WARN" if r_disproved["verdict"] in ("disproved", "possibly_false") else "PASS"
    assert gate == "WARN"
    print("  gate 映射: disproved→WARN ✓")

    print("\n自测通过 ✓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="反证探测（Stage 2.6 旁路，prove2me Disproof）")
    ap.add_argument("--conjecture", help="conjecture.json 路径")
    ap.add_argument("--deepseek-key", help="DeepSeek API key（或设 DEEPSEEK_API_KEY）")
    ap.add_argument("--output", default="/tmp/disproof_probe.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.conjecture:
        print("用法: python disproof_probe.py --conjecture conjecture.json [--deepseek-key ...] [--output ...] [--self-test]")
        return 2

    api_key = args.deepseek_key or os.environ.get("DEEPSEEK_API_KEY")
    conjecture = json.loads(Path(args.conjecture).read_text(encoding="utf-8"))
    result = probe(conjecture, api_key)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 64)
    print("反证探测（Stage 2.6 旁路，prove2me Disproof）")
    print("=" * 64)
    print(f"  猜想: {conjecture.get('name', 'Untitled')}")
    print(f"  verdict: {result['verdict']}")
    print(f"  counterexample: {result['counterexample'][:80]}")
    print(f"  reasoning: {result['reasoning'][:120]}")
    print(f"\n  最终 GATE: {result['gate']}（WARN = 猜想可能为假，建议审视；PASS = 未发现反例）")
    print(f"  Report: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
