#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3 增强 — Best-First Tree Search（BFTS）+ LLM 综合选择（P1 落地）

对齐 AI-Scientist-v2（SakanaAI/AI-Scientist-v2, "Workshop-Level Automated
Scientific Discovery via Agentic Tree Search"）的 best-first tree search
（journal.py + parallel_agent.py）：multi-draft 并行 + metric 优先展开 +
debug/improve 分支 + LLM 综合选择最佳。

核心缺口：Stage 3 现有 MCTS + ABC（蜂群）——MCTS 用 UCB 权衡探索/利用，
ABC 用蜂群并行采样。它们都缺 AI-Scientist-v2 BFTS 的三个增量：
  1. multi-draft 并行：每轮同时生成多个独立草稿候选（而非单一展开）
  2. debug/improve 分支：候选按 is_buggy 分流——编译失败 → debug（修编译），
     编译通过但有 sorry → improve（减 sorry），两者用不同 prompt 口径
  3. LLM 综合选择最佳（node_selection_spec）：不只按 sorry_count 单一 metric
     选最佳，而是 LLM 综合结构完整性 / 证据链 / 命名空间覆盖 / 下游可引用性

与现有模块的关系：
  - 本模块提供「证明候选树」的 BFTS 数据结构 + 展开策略 + LLM 综合选择；
  - 不替代 Stage 3.6 冻结评估器（RSIHub）与 Stage 3.5 物理内容审计——
    BFTS 只决定「先展开谁 / 下一轮生成什么」，最终接受仍由冻结评估器 +
    隐藏物理内容审计决定（对齐 external-framework-grafting 教训 #7）。

诚实边界：
  1. BFTS 是搜索**策略**，不是评估器：它按「当前最优优先」贪心展开，可能
     陷入局部最优（这是 best-first 的固有风险）；MCTS 的 UCB 探索项正是为此
     而设。两者可共存：BFTS 提供多草稿 + 分流，MCTS 提供探索/利用权衡。
  2. LLM 综合选择（node_selection_spec）只做「候选排序 + 归档建议」，最终
     接受/拒绝由确定性门控（编译 EXIT=0 + 0 sorry/axiom）决定。
  3. debug/improve 分支的 prompt 口径差异是启发式（debug=修编译错误，
     improve=减 sorry），不产生新的形式化保证。

用法：
  python bfts_search.py --candidates candidates.json --output bfts_tree.json
  python bfts_search.py --self-test    # 离线自测（mock 节点 + 展开 + 选择）
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── 证明候选节点（对应 AI-Scientist journal.Node）─────────────────

class ProofNode:
    """证明树中的一个候选节点。"""

    def __init__(self, code: str = "", sorry_count: int = 0, axiom_count: int = 0,
                 exit_code: int = 1, structure_score: float = 0.0,
                 parent_id: str | None = None, node_id: str | None = None,
                 namespace_coverage: float = 0.0, evidence_chain: float = 0.0):
        self.code = code
        self.sorry_count = sorry_count
        self.axiom_count = axiom_count
        self.exit_code = exit_code
        self.structure_score = structure_score
        self.namespace_coverage = namespace_coverage
        self.evidence_chain = evidence_chain
        self.parent_id = parent_id
        self.node_id = node_id or f"n{abs(hash(code)) % 100000:05d}" if code else (
            node_id or "n00000")
        self.children: list[str] = []

    @property
    def is_buggy(self) -> bool:
        """编译失败 = buggy（对应 AI-Scientist is_buggy = exc_type is not None）。"""
        return self.exit_code != 0

    @property
    def stage_name(self) -> str:
        """候选分类：draft（无父）/ debug（父 buggy）/ improve（父非 buggy）。"""
        if self.parent_id is None:
            return "draft"
        # 父节点 buggy 与否决定 debug 还是 improve（简化口径：父节点需传入，
        # 这里按父节点 id 前缀标记；完整实现由 journal 维护）
        return "debug" if getattr(self, "_parent_is_buggy", False) else "improve"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "sorry_count": self.sorry_count,
            "axiom_count": self.axiom_count,
            "exit_code": self.exit_code,
            "is_buggy": self.is_buggy,
            "stage_name": self.stage_name,
            "structure_score": self.structure_score,
            "namespace_coverage": self.namespace_coverage,
            "evidence_chain": self.evidence_chain,
            "children": self.children,
            "code_len": len(self.code),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProofNode":
        n = cls(
            code=d.get("code", ""),
            sorry_count=d.get("sorry_count", 0),
            axiom_count=d.get("axiom_count", 0),
            exit_code=d.get("exit_code", 1),
            structure_score=d.get("structure_score", 0.0),
            parent_id=d.get("parent_id"),
            node_id=d.get("node_id"),
            namespace_coverage=d.get("namespace_coverage", 0.0),
            evidence_chain=d.get("evidence_chain", 0.0),
        )
        n.children = d.get("children", [])
        return n


# ── 节点优先级（best-first 的 metric）─────────────────────────────

def node_priority(node: ProofNode) -> tuple:
    """best-first 展开优先级：编译通过 > 低 sorry > 低 axiom > 高结构分。

    返回元组按 heapq 最小堆排序（数字越小越优先）：
      (0 if compiles else 1, sorry_count, axiom_count, -structure_score)
    """
    return (
        0 if node.exit_code == 0 else 1,
        node.sorry_count,
        node.axiom_count,
        -node.structure_score,
    )


# ── 证明树（对应 AI-Scientist journal.Journal）────────────────────

class ProofJournal:
    """证明候选树：draft_nodes / buggy_nodes / good_nodes + best-first 展开。"""

    def __init__(self):
        self.nodes: dict[str, ProofNode] = {}
        self.draft_root_ids: list[str] = []

    def add(self, node: ProofNode) -> None:
        self.nodes[node.node_id] = node
        if node.parent_id is None:
            self.draft_root_ids.append(node.node_id)
        elif node.parent_id in self.nodes:
            self.nodes[node.parent_id].children.append(node.node_id)

    @property
    def draft_nodes(self) -> list[ProofNode]:
        return [self.nodes[i] for i in self.draft_root_ids]

    @property
    def buggy_nodes(self) -> list[ProofNode]:
        return [n for n in self.nodes.values() if n.is_buggy]

    @property
    def good_nodes(self) -> list[ProofNode]:
        return [n for n in self.nodes.values() if not n.is_buggy]

    def best_first_next(self) -> ProofNode | None:
        """best-first：从所有未展开（无子节点）的候选里选 metric 最优的。"""
        frontier = [n for n in self.nodes.values() if not n.children]
        if not frontier:
            return None
        return min(frontier, key=node_priority)

    def best_by_metric(self) -> ProofNode | None:
        """纯 metric 最佳（回退：不调 LLM 时用）。"""
        if not self.nodes:
            return None
        return min(self.nodes.values(), key=node_priority)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "draft_root_ids": self.draft_root_ids,
            "n_draft": len(self.draft_nodes),
            "n_buggy": len(self.buggy_nodes),
            "n_good": len(self.good_nodes),
        }


# ── 确定性 metric 选择（回退：无 API key 时）──────────────────────

def _metric_select(journal: ProofJournal) -> dict:
    best = journal.best_by_metric()
    if best is None:
        return {"selected_id": None, "reasoning": "empty journal"}
    return {
        "selected_id": best.node_id,
        "reasoning": (
            f"metric best-first: compiles={best.exit_code == 0}, "
            f"sorry={best.sorry_count}, axiom={best.axiom_count}, "
            f"structure={best.structure_score:.2f}"
        ),
    }


# ── LLM 综合选择（node_selection_spec：不只 metric）───────────────

def _llm_select(journal: ProofJournal, api_key: str) -> dict:
    """LLM 综合选择最佳候选：不只 sorry_count，综合结构完整性/证据链/覆盖。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    candidates = []
    for n in journal.nodes.values():
        candidates.append({
            "id": n.node_id,
            "compiles": n.exit_code == 0,
            "sorry_count": n.sorry_count,
            "axiom_count": n.axiom_count,
            "structure_score": round(n.structure_score, 3),
            "namespace_coverage": round(n.namespace_coverage, 3),
            "evidence_chain": round(n.evidence_chain, 3),
            "code_len": len(n.code),
        })

    prompt = (
        "You are an experienced proof-reviewer evaluating candidate Lean proofs to "
        "select the best one. Do NOT rely on sorry_count alone — a proof with slightly "
        "more sorry but a cleaner evidence chain and full namespace coverage may be "
        "the better base for further repair. Consider: structural completeness, "
        "evidence-chain integrity (no trivial stubs), namespace coverage, and "
        "downstream citability.\n\n"
        "Candidates:\n" + json.dumps(candidates, ensure_ascii=False, indent=2) + "\n\n"
        "Return a JSON object with exactly:\n"
        "  - selected_id: string (one of the candidate ids)\n"
        "  - reasoning: 2-3 sentence justification (why this one over the others)\n"
        "Return ONLY the JSON object."
    )

    resp = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024, temperature=0.3,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = resp.choices[0].message.content
    if not text:
        return _metric_select(journal)

    # 容错解析
    import re as _re
    s = text.find('{')
    e = text.rfind('}')
    try:
        obj = json.loads(text[s:e + 1])
        if obj.get("selected_id") in journal.nodes:
            return {"selected_id": obj["selected_id"],
                    "reasoning": obj.get("reasoning", "")}
    except (json.JSONDecodeError, ValueError):
        pass
    # 正则兜底
    m = _re.search(r'"selected_id"\s*:\s*"([^"]+)"', text)
    if m and m.group(1) in journal.nodes:
        return {"selected_id": m.group(1), "reasoning": "regex fallback"}
    return _metric_select(journal)


# ── 主搜索函数 ────────────────────────────────────────────────────

def search(candidates: list[dict], use_mock: bool = False) -> dict:
    """从候选证明列表构建 BFTS 树，返回 best-first 展开顺序 + 最佳选择。"""
    journal = ProofJournal()
    for c in candidates:
        node = ProofNode(
            code=c.get("code", ""),
            sorry_count=c.get("sorry_count", 0),
            axiom_count=c.get("axiom_count", 0),
            exit_code=c.get("exit_code", 1),
            structure_score=c.get("structure_score", 0.0),
            parent_id=c.get("parent_id"),
            node_id=c.get("node_id"),
            namespace_coverage=c.get("namespace_coverage", 0.0),
            evidence_chain=c.get("evidence_chain", 0.0),
        )
        if node.parent_id and c.get("parent_is_buggy"):
            node._parent_is_buggy = c["parent_is_buggy"]
        journal.add(node)

    # best-first 展开顺序（贪心 pop 最优未展开节点）
    expansion_order = []
    j_copy = ProofJournal()
    for n in journal.nodes.values():
        j_copy.add(ProofNode.from_dict(n.to_dict()))
    while True:
        nxt = j_copy.best_first_next()
        if nxt is None:
            break
        expansion_order.append({
            "node_id": nxt.node_id,
            "priority": list(node_priority(nxt)),
            "stage_name": nxt.stage_name,
            "is_buggy": nxt.is_buggy,
        })
        # 模拟展开：标记该节点已展开（给它一个虚拟子节点占位）
        nxt.children.append("__expanded__")

    # 最佳选择
    api_key = _load_api_key()
    if use_mock or not api_key:
        selection = _metric_select(journal)
        mode = 'metric'
    else:
        try:
            selection = _llm_select(journal, api_key)
            mode = 'llm'
        except Exception as e:
            print(f"[BFTS] ⚠️ LLM 选择失败 ({e}) — 回退 metric")
            selection = _metric_select(journal)
            mode = 'metric-fallback'

    return {
        "stage": 3,
        "name": "Best-First Tree Search",
        "source": "AI-Scientist-v2 (SakanaAI, Agentic Tree Search)",
        "mode": mode,
        "journal": journal.to_dict(),
        "expansion_order": expansion_order,
        "selection": selection,
        "debug_improve_branch": {
            "description": "is_buggy → debug (fix compilation); non-buggy with sorry → improve (reduce sorry)",
            "n_debug": len(journal.buggy_nodes),
            "n_improve": len([n for n in journal.good_nodes if n.sorry_count > 0]),
        },
        "timestamp": datetime.now().isoformat(),
    }


def _load_api_key() -> str:
    for env_path in [
        '~/projects/cityhdg/spatial_agent/.env',
        os.path.expanduser('~/.hermes/.env'),
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('DEEPSEEK_API_KEY='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('DEEPSEEK_API_KEY', '')


# ── 离线自测 ──────────────────────────────────────────────────────

def self_test() -> int:
    """离线自测：验证 BFTS 展开顺序 + debug/improve 分流 + metric 选择。"""
    candidates = [
        # 编译失败（buggy → debug）
        {"node_id": "draft1", "code": "skeleton", "exit_code": 1,
         "sorry_count": 5, "axiom_count": 3, "structure_score": 0.2},
        # 编译通过但有 sorry（improve）
        {"node_id": "draft2", "code": "compiles", "exit_code": 0,
         "sorry_count": 3, "axiom_count": 2, "structure_score": 0.5},
        # 编译通过，0 sorry，但还有 axiom
        {"node_id": "draft3", "code": "no_sorry", "exit_code": 0,
         "sorry_count": 0, "axiom_count": 5, "structure_score": 0.7},
        # 最优：0 sorry 0 axiom
        {"node_id": "draft4", "code": "golden", "exit_code": 0,
         "sorry_count": 0, "axiom_count": 0, "structure_score": 0.9},
    ]

    result = search(candidates, use_mock=True)

    # 验证：best-first 展开顺序应把 draft4（0,0,0,-0.9）排最前，draft1 排最后
    order_ids = [e["node_id"] for e in result["expansion_order"]]
    expected_first = "draft4"  # 最优优先
    expected_last = "draft1"   # buggy 最后

    ok_order = (order_ids[0] == expected_first and order_ids[-1] == expected_last)
    ok_selection = result["selection"]["selected_id"] == "draft4"
    # debug = 编译失败(draft1) = 1；improve = 编译通过且有 sorry(draft2) = 1
    # （draft3/draft4 已 0 sorry，属于 axiom-ablation/完成，不计入 improve）
    ok_branch = (result["debug_improve_branch"]["n_debug"] == 1
                 and result["debug_improve_branch"]["n_improve"] == 1)

    print(f"  [{'PASS' if ok_order else 'FAIL'}] best-first 展开顺序: "
          f"{order_ids} (首={expected_first} 尾={expected_last})")
    print(f"  [{'PASS' if ok_selection else 'FAIL'}] metric 选择: "
          f"{result['selection']['selected_id']}")
    print(f"  [{'PASS' if ok_branch else 'FAIL'}] debug/improve 分流: "
          f"debug={result['debug_improve_branch']['n_debug']} "
          f"improve={result['debug_improve_branch']['n_improve']}")

    all_ok = ok_order and ok_selection and ok_branch
    print("\n" + ("✅ 全部自测通过" if all_ok else "❌ 存在失败用例"))
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Best-First Tree Search (Stage 3, AI-Scientist-v2 P1)")
    ap.add_argument('--candidates', default=None, help='Path to candidates JSON (list of proof candidates)')
    ap.add_argument('--output', default='/tmp/bfts_tree.json', help='Output JSON path')
    ap.add_argument('--mock', action='store_true', help='Use metric-only selection (no API)')
    ap.add_argument('--self-test', action='store_true', help='Run offline self-test and exit')
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not args.candidates or not Path(args.candidates).exists():
        print("❌ 需要 --candidates <candidates.json>（或 --self-test）")
        return 1

    candidates = json.loads(Path(args.candidates).read_text(encoding='utf-8'))
    result = search(candidates, args.mock)

    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Best-First Tree Search (Stage 3, AI-Scientist-v2 P1)")
    print("=" * 60)
    print(f"  mode={result['mode']}  "
          f"nodes={len(result['journal']['nodes'])}  "
          f"draft={result['journal']['n_draft']}  "
          f"buggy={result['journal']['n_buggy']}  "
          f"good={result['journal']['n_good']}")
    print(f"  selected={result['selection']['selected_id']}")
    print(f"  reasoning: {result['selection']['reasoning'][:120]}")
    print(f"  expansion order (best-first): "
          f"{[e['node_id'] for e in result['expansion_order']]}")
    print(f"\n  Output: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
