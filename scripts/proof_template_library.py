#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证明模式模板库（P5 记忆冻结复用落地）

把「隐性证明模式」（条件定理重构 / 诚实公理化 / 黄金门控等）冻结为机器可复用的
few-shot 模板（proof_templates.json），新猜想证明时按缺陷类型检索注入 mutate prompt。

对齐 RSIAgent「记忆冻结复用」：探索后冻结已验证的正确模式，测试时零参数复用。

用法：
  from proof_template_library import load_templates, select_templates, render_few_shot
  templates = load_templates()
  sel = select_templates(templates, defects={"sorry": 2, "admit": 0})
  shot = render_few_shot(sel)  # 注入 mutate prompt 的 few-shot 文本

自测：python proof_template_library.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TEMPLATES_PATH = Path(__file__).resolve().parent / "proof_templates.json"


def load_templates(path: Path | None = None) -> list[dict]:
    """加载模板库。容错：文件缺失返回空列表。"""
    p = path or TEMPLATES_PATH
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data.get("templates", []) if isinstance(data, dict) else []


def select_templates(templates: list[dict], defects: dict, max_n: int = 3) -> list[dict]:
    """按当前缺陷类型检索最相关的模板。

    匹配规则：模板 defect_types 与当前活跃缺陷（值 > 0）的重叠数。
    重叠越多越相关；无重叠时（如空壳缺陷但模板库没有精确匹配）回退到「通用模式」
    （trigger 含「证明体」/「tactic」的模板）。返回最多 max_n 个，按重叠数降序。
    """
    active = {k for k, v in (defects or {}).items() if v and v > 0}

    # 无活跃缺陷时返回空（无需注入模板）
    if not active:
        return []

    def relevance(tpl: dict) -> int:
        types = set(tpl.get("defect_types", []))
        return len(types & active)

    # 优先精确匹配
    scored = [(relevance(tpl), tpl) for tpl in templates]
    scored = [x for x in scored if x[0] > 0]

    if not scored:
        # 回退：返回前 max_n 个「通用模式」模板（trigger 含 tactic/证明体/sorry）
        generic = [t for t in templates
                   if any(k in t.get("trigger", "") for k in ("tactic", "证明体", "sorry", "axiom"))]
        return generic[:max_n]

    scored.sort(key=lambda x: -x[0])
    return [tpl for _, tpl in scored[:max_n]]


def render_few_shot(selected: list[dict]) -> str:
    """把选中的模板渲染成 few-shot 文本（注入 mutate prompt）。"""
    if not selected:
        return ""
    blocks = []
    for tpl in selected:
        blocks.append(
            f"【已冻结证明模式】{tpl.get('id')}（来源: {tpl.get('source', '')}）\n"
            f"  触发: {tpl.get('trigger', '')}\n"
            f"  模式: {tpl.get('pattern', '')}\n"
            f"  修复前:\n```lean\n{tpl.get('few_shot_before', '')}\n```\n"
            f"  修复后:\n```lean\n{tpl.get('few_shot_after', '')}\n```"
        )
    return "\n\n".join(blocks)


def _self_test() -> int:
    templates = load_templates()
    print(f"模板库加载: {len(templates)} 个模板")
    for t in templates:
        print(f"  - {t['id']:30s} 缺陷类型={','.join(t['defect_types'])}")
    # 检索测试：sorry 缺陷应命中 honest_axiom_declare / lemma_decompose 等
    sel = select_templates(templates, {"sorry": 2, "admit": 1})
    ids = [t["id"] for t in sel]
    print(f"\n检索（sorry=2, admit=1）→ {ids}")
    assert "honest_axiom_declare" in ids, "应命中诚实公理化模板"
    # 空壳缺陷应命中 trivial_stub_replace / tactic_body_complete
    sel2 = select_templates(templates, {"trivial_or_true_stub": 3})
    ids2 = [t["id"] for t in sel2]
    print(f"检索（trivial=3）→ {ids2}")
    assert "trivial_stub_replace" in ids2, "应命中空壳替换模板"
    # 渲染测试
    shot = render_few_shot(sel[:1])
    assert "已冻结证明模式" in shot and "```lean" in shot
    print(f"\nfew-shot 渲染 OK（{len(shot)} 字符）")
    # 无活跃缺陷 → 空
    assert select_templates(templates, {"sorry": 0}) == []
    print("\n自测通过 ✓")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="证明模式模板库自测")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(_self_test())
    print("用法: python proof_template_library.py --self-test")
    sys.exit(0)
