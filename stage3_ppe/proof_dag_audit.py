#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.5c — 证明 DAG 审计（增量嫁接自 LeanMarathon，stdlib-only）

从 Lean 文件提取「证明 DAG」：lemma / theorem 为节点，其证明体里引用的
其它声明名（lemma/theorem/axiom）为依赖边。检查 LeanMarathon blueprint 契约里
两个现有扁平审计（proof_consistency_audit.py）缺的新缺陷类：

  1. 冗余引理（lemma closeness）：某个 lemma/theorem 从未被任何「下游」（声明
     顺序在其之后）节点引用 —— 要么是冗余节点，要么某消费者漏了依赖。
  2. 未使用的 honest-axiom：声明的 axiom 从未被任何节点引用（表演性诚实变体）。

不同于 LeanMarathon「禁止 axiom」，本脚本**保留 honest-axiom**（物理证明里
λ_KLS、g_TC 等参数无法第一性导出是刻意设计），只做「依赖显式化」的可追踪审计。

用法：
  python proof_dag_audit.py --lean /path/to/proof.lean [--output /tmp/dag_report.json]

不改动现有管线；与 proof_consistency_audit.py / l2.py / lean_recursive_repair.py 并列。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DECL_KW = ("lemma", "theorem", "axiom", "def", "structure", "inductive", "class", "instance", "abbrev")
PROOF_KW = ("lemma", "theorem")
DEF_KW = ("def", "structure", "inductive", "class", "instance", "abbrev")
AXIOM_KW = ("axiom",)

# 声明头：可选 noncomputable/private/local 修饰 + 关键字 + 名字
DECL_RE = re.compile(
    r"^\s*(?:(?:noncomputable|private|local|protected|partial|unsafe)\s+)*"
    r"(lemma|theorem|axiom|def|structure|inductive|class|instance|abbrev)\s+"
    r"([A-Za-z][A-Za-z0-9_']*)",
    re.MULTILINE,
)

# 依赖名后缀：用于「悬空引用」检测（正文里出现但从未声明）。
# 只匹配 _axiom/_lemma/_theorem（用户命名约定里的全局声明引用）；
# 排除 _def —— 因为 `set x := ... with x_def` / `let x_def := ...` 是局部假设，会误报。
DEP_SUFFIX_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_']*(?:_axiom|_lemma|_theorem))\b")


def parse_declarations(text: str) -> list[dict]:
    """解析所有顶层声明，返回 [{kind, name, pos}]（按文件顺序）。"""
    decls = []
    for m in DECL_RE.finditer(text):
        kind, name = m.group(1), m.group(2)
        decls.append({"kind": kind, "name": name, "pos": m.start()})
    return decls


def node_body(text: str, decls: list[dict], idx: int) -> str:
    """返回第 idx 个声明的证明体（从声明头之后到下一个声明头之前）。"""
    start = DECL_RE.search(text, decls[idx]["pos"])
    header_end = start.end() if start else decls[idx]["pos"]
    next_pos = decls[idx + 1]["pos"] if idx + 1 < len(decls) else len(text)
    return text[header_end:next_pos]


def referenced_names(body: str, all_names: set[str]) -> set[str]:
    """返回 body 里引用的、且属于本文件声明的名字（整词匹配，排除自身由调用方处理）。"""
    found = set()
    for name in all_names:
        if re.search(rf"\b{re.escape(name)}\b", body):
            found.add(name)
    return found


def build_dag(text: str) -> dict:
    decls = parse_declarations(text)
    name_to_idx = {d["name"]: i for i, d in enumerate(decls)}
    all_names = set(name_to_idx)

    nodes = []
    edges = []  # (from_name, to_name) —— from 被 to 引用
    for i, d in enumerate(decls):
        node = {"index": i, "kind": d["kind"], "name": d["name"], "deps": []}
        if d["kind"] in PROOF_KW or d["kind"] in DEF_KW:
            body = node_body(text, decls, i)
            refs = referenced_names(body, all_names - {d["name"]})
            node["deps"] = sorted(refs)
            for ref in refs:
                edges.append({"from": ref, "to": d["name"]})
        nodes.append(node)
    return {"nodes": nodes, "edges": edges, "name_to_idx": name_to_idx}


def audit(text: str) -> dict:
    dag = build_dag(text)
    nodes = dag["nodes"]
    name_to_idx = dag["name_to_idx"]

    # 被引用计数（只统计「下游」：声明顺序在其之后的节点引用它）
    referenced_by = {n["name"]: [] for n in nodes}
    for e in dag["edges"]:
        if name_to_idx[e["from"]] < name_to_idx[e["to"]]:
            referenced_by[e["from"]].append(e["to"])

    redundant_lemmas = []   # 从未被下游引用的 lemma/theorem（排除最后一个 = 主结论）
    unused_axioms = []      # 从未被任何节点引用的 axiom
    dangling_refs = []      # 正文出现 _axiom/_lemma/_theorem/_def 但未声明

    last_proof_idx = max(
        (i for i, n in enumerate(nodes) if n["kind"] in PROOF_KW), default=None
    )

    for i, n in enumerate(nodes):
        if n["kind"] in PROOF_KW:
            if not referenced_by[n["name"]] and i != last_proof_idx:
                redundant_lemmas.append({"name": n["name"], "kind": n["kind"]})
        elif n["kind"] in AXIOM_KW:
            if not referenced_by[n["name"]]:
                unused_axioms.append({"name": n["name"]})

    # 悬空引用：整个文件里出现 _axiom/_lemma/_theorem/_def 后缀名但不在声明表
    # [2026-09-03] 先剥离 attribute 标签 (@[...])，避免 @[honest_axiom] 等被误报为引用
    text_for_dangling = re.sub(r"@\[[^\]]*\]", "", text)
    declared = set(name_to_idx)
    for m in DEP_SUFFIX_RE.finditer(text_for_dangling):
        name = m.group(1)
        if name not in declared:
            dangling_refs.append({"name": name, "pos": m.start()})

    # 门控：冗余引理/未用 axiom → WARN；悬空引用 → BLOCK（可能是漏声明或拼写错误）
    blocks = []
    warns = []
    if dangling_refs:
        blocks.append(f"{len(dangling_refs)} 个悬空引用（出现但未声明）")
    if redundant_lemmas:
        warns.append(f"{len(redundant_lemmas)} 个冗余引理（从未被下游使用）")
    if unused_axioms:
        warns.append(f"{len(unused_axioms)} 个未使用的 axiom")

    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    return {
        "gate": gate,
        "statistics": {
            "total_declarations": len(nodes),
            "proof_nodes": sum(1 for n in nodes if n["kind"] in PROOF_KW),
            "definitional_nodes": sum(1 for n in nodes if n["kind"] in DEF_KW),
            "axiom_nodes": sum(1 for n in nodes if n["kind"] in AXIOM_KW),
            "dag_edges": len(dag["edges"]),
        },
        "redundant_lemmas": redundant_lemmas,
        "unused_axioms": unused_axioms,
        "dangling_refs": dangling_refs,
        "blocks": blocks,
        "warns": warns,
        "nodes": [
            {"kind": n["kind"], "name": n["name"], "deps": n["deps"]} for n in nodes
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="证明 DAG 审计（Stage 3.5c）")
    ap.add_argument("--lean", required=True, help="Lean 证明文件路径")
    ap.add_argument("--output", default=None, help="JSON 报告输出路径（可选）")
    args = ap.parse_args()

    text = Path(args.lean).read_text(encoding="utf-8", errors="replace")
    report = audit(text)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== 证明 DAG 审计（Stage 3.5c）===")
    s = report["statistics"]
    print(f"声明 {s['total_declarations']} 个：证明节点 {s['proof_nodes']} / "
          f"定义节点 {s['definitional_nodes']} / axiom {s['axiom_nodes']} / DAG 边 {s['dag_edges']}")
    print(f"门控: {report['gate']}")
    for b in report["blocks"]:
        print(f"  [BLOCK] {b}")
    for w in report["warns"]:
        print(f"  [WARN]  {w}")
    if report["redundant_lemmas"]:
        names = ", ".join(r["name"] for r in report["redundant_lemmas"])
        print(f"  冗余引理: {names}")
    if report["unused_axioms"]:
        names = ", ".join(r["name"] for r in report["unused_axioms"])
        print(f"  未用 axiom: {names}")
    if report["dangling_refs"]:
        names = ", ".join(r["name"] for r in report["dangling_refs"])
        print(f"  悬空引用: {names}")
    if args.output:
        print(f"报告: {args.output}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
