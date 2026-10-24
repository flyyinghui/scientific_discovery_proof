#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J-space Bridge — 动态桥接矩阵 + J-score（v2.22.0，落地 P0-①/②）

替代 references/jspace-bridge-matrix.md 里那张**硬编码的 12×12 快照**（脑 170K 神经元
时的静态估计值，从未真正计算过）。本模块用 `brain.recall()` 的真实语义检索结果
**动态重算** J-score，把「大脑支持度」从文档宣传变成可执行的门控信号。

J-score 三成分（对齐 reference doc 的公式 J = α·sim + β·MI + γ·co_activation）：
  α=0.4, β=0.3, γ=0.3

  sim(a,b)         — 概念代表向量的余弦相似度（语义接近度）。
                     代表向量 = brain.recall(a) 的 top-k 结果 embedding 的相似度加权平均。
  MI(a,b)          — 互信息代理 = 召回 neuron id 集合的 Jaccard 共现（知识图谱重叠）。
  co_activation(a,b) — 共同激活 = 共同召回比例（同时被激活的频率）。

诚实边界：
1. **动态 J-score 的值域 ≠ 硬编码矩阵的值域**。硬编码矩阵（0.08–0.89）是脑 170K 时的
   估计快照；动态重算后，sim∈[0,1]、MI（Jaccard）在 181K 神经元下通常很小（top-20
   召回集合很少重叠）、co_act∈[0,1]。因此**决策阈值（0.70/0.50）需要按当前脑重新标定**，
   本模块会输出 `calibration_hint`（基于实际 J-score 分布），而非沿用旧阈值盲判。
2. 大脑加载昂贵（181K 神经元 ~35–170s），本模块**懒加载** brain 并缓存概念签名；
   建议作为**一次性子进程**运行（加载一次 → 算全部概念 J-score → 退出），不要内联进
   每代进化循环（那会让每代都重新加载 181K 神经元）。
3. 无 brain 可用时优雅降级（返回 0.0 + note），不阻断管线——J-score 是「先验支持度」
   信号，不是硬门控（硬门控由 Stage 3.5 审计负责）。

用法：
  python jspace_bridge.py --conjecture /path/conjecture.json --output /tmp/jspace.json
  python jspace_bridge.py --concepts "Ricci curvature,KLS spectral gap" --output /tmp/jspace.json
  python jspace_bridge.py --self-test        # 用 mock brain 离线自测（不加载 181K 神经元）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# J = α·sim + β·MI + γ·co_activation
ALPHA, BETA, GAMMA = 0.4, 0.3, 0.3

# 12 个 SL(6,C) 框架核心概念（label, brain.recall 查询串）
DEFAULT_CONCEPTS: list[tuple[str, str]] = [
    ("g_Ricci",      "Ricci curvature scalar curvature Einstein manifold"),
    ("g_KLS",        "Kannan-Lovasz-Simonovits spectral gap Bakry-Emery curvature dimension"),
    ("g_Matsushima", "Matsushima formula L2 cohomology Betti number decomposition"),
    ("g_Chern",      "Chern class Chern-Weil theory characteristic class"),
    ("g_WZW",        "Wess-Zumino-Witten model conformal field theory boundary"),
    ("g_CDM",        "cold dark matter topological defect Kibble-Zurek"),
    ("p_M_R",        "Majorana mass seesaw right-handed neutrino mass scale"),
    ("p_m_nu",       "neutrino mass sum hierarchy oscillation"),
    ("p_SB",         "Stern-Brocot tree flavor charge ratio continued fraction"),
    ("p_FRG",        "functional renormalization group Wetterich equation fixed point"),
    ("p_CGICE",      "cosmic geometric information cycle equation dynamical"),
    ("p_NJL",        "Nambu-Jona-Lasinio condensation chiral symmetry breaking"),
]

# 参考决策阈值（诚实边界：动态 J-score 值域不同，这些阈值需按当前脑重标定，见 calibration_hint）
THRESHOLD_DIRECT = 0.70
THRESHOLD_HONEST = 0.50


class JSpaceBridge:
    """动态 J-space 桥接：用 brain.recall() 真实检索结果计算 J-score。"""

    def __init__(self, data_dir: str = "~/projects/neural_memory_data",
                 brain=None, top_k: int = 20):
        self.data_dir = data_dir
        self.top_k = top_k
        self._brain = brain  # 可注入 mock brain（自测），None 则懒加载真实大脑
        self._sig_cache: dict[str, tuple | None] = {}

    # ── 大脑懒加载 ────────────────────────────────────────────────
    @property
    def brain(self):
        if self._brain is None:
            sys.path.insert(0, "~/ai_for_science")
            try:
                from neural_memory_brain import NeuralMemoryBrain
            except ImportError:
                from neural_memory_brain.brain import NeuralMemoryBrain
            self._brain = NeuralMemoryBrain(data_dir=self.data_dir)
        return self._brain

    @property
    def brain_loaded(self) -> bool:
        return self._brain is not None

    # ── 概念签名 ──────────────────────────────────────────────────
    def _concept_signature(self, concept: str):
        """返回 (代表向量, 召回 neuron id 集合)。

        代表向量 = brain.recall(concept, top_k) 结果的 embedding 按 similarity 加权平均。
        召回 id 集合 = recall 返回的 neuron id（用于 MI / co_activation 共现计算）。
        """
        if concept in self._sig_cache:
            return self._sig_cache[concept]
        try:
            results = self.brain.recall(concept, top_k=self.top_k)
        except Exception:
            self._sig_cache[concept] = (None, set())
            return self._sig_cache[concept]

        vecs, weights, ids = [], [], set()
        for r in results:
            nid = r.get("id")
            neuron = self.brain.graph.neurons.get(nid) if nid else None
            emb = getattr(neuron, "embedding", None) if neuron is not None else None
            if nid is not None and emb is not None:
                ids.add(nid)
                vecs.append(np.asarray(emb, dtype=np.float32))
                w = float(r.get("similarity", r.get("activation", 0.0)))
                weights.append(max(w, 0.0))
        if not vecs:
            self._sig_cache[concept] = (None, ids)
            return self._sig_cache[concept]
        vecs = np.stack(vecs)
        w = np.asarray(weights, dtype=np.float32)
        wsum = float(w.sum())
        w = w / wsum if wsum > 0 else np.full(len(w), 1.0 / len(w), dtype=np.float32)
        sig = (vecs.T @ w, ids)
        self._sig_cache[concept] = sig
        return sig

    # ── J-score 三成分 + 合成 ─────────────────────────────────────
    def j_score_pair(self, a: str, b: str) -> dict:
        """概念对 (a,b) 的 J-score + 三成分分解。"""
        va, ida = self._concept_signature(a)
        vb, idb = self._concept_signature(b)
        if va is None or vb is None:
            return {"j": 0.0, "sim": 0.0, "mi": 0.0, "co_activation": 0.0, "valid": False}

        na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
        sim = float(np.dot(va, vb) / (na * nb + 1e-12)) if na > 0 and nb > 0 else 0.0
        # 诚实边界：J-score 是「支持度」，负余弦相似度 = 无语义支持，归零（而非拖负）
        sim = max(0.0, sim)

        inter, union = len(ida & idb), len(ida | idb)
        mi = (inter / union) if union else 0.0
        co_act = inter / max(1, min(len(ida), len(idb)))

        j = float(ALPHA * sim + BETA * mi + GAMMA * co_act)
        return {"j": round(j, 4), "sim": round(sim, 4), "mi": round(mi, 4),
                "co_activation": round(co_act, 4), "valid": True}

    # ── 桥接矩阵 + 单概念 / 路径 J-score ──────────────────────────
    def build_matrix(self, concepts: list[str]) -> list[list[float]]:
        n = len(concepts)
        return [[1.0 if i == j else self.j_score_pair(concepts[i], concepts[j])["j"]
                 for j in range(n)] for i in range(n)]

    def concept_j_score(self, concept: str, concepts: list[str]) -> float:
        """单概念 J-score = 该概念与其余概念的 J 均值（对齐 reference 的 compute_j_score 行均值）。"""
        others = [c for c in concepts if c != concept]
        if not others:
            return 1.0
        vals = [self.j_score_pair(concept, c)["j"] for c in others]
        return float(np.mean(vals))

    def path_j_score(self, concepts: list[str]) -> float:
        """证明路径 J-score = 各概念 J-score 的均值。"""
        if not concepts:
            return 0.0
        vals = [self.concept_j_score(c, concepts) for c in concepts]
        return float(np.mean(vals))

    # ── 决策 + 标定 ──────────────────────────────────────────────
    def decision(self, j: float) -> str:
        if j > THRESHOLD_DIRECT:
            return "direct_theorem"
        if j >= THRESHOLD_HONEST:
            return "honest_axiom"
        return "postulated_or_reject"

    def calibrate(self, matrix: list[list[float]]) -> dict:
        """基于实际 J-score 分布给出阈值重标定提示（诚实边界）。

        旧阈值 0.70/0.50 来自硬编码矩阵（估计值）。动态重算后值域不同，
        这里按当前分布的 P50/P80/P95 建议新阈值，不盲目沿用旧阈值。
        """
        off_diag = [v for i, row in enumerate(matrix) for j, v in enumerate(row) if i != j and v > 0]
        if not off_diag:
            return {"note": "no valid off-diagonal J-scores computed"}
        arr = np.array(off_diag)
        return {
            "note": "dynamic J-scores differ from hardcoded snapshot range; thresholds below are data-driven suggestions",
            "observed_range": [round(float(arr.min()), 4), round(float(arr.max()), 4)],
            "suggested_direct_threshold": round(float(np.percentile(arr, 80)), 4),
            "suggested_honest_threshold": round(float(np.percentile(arr, 50)), 4),
            "legacy_thresholds": {"direct": THRESHOLD_DIRECT, "honest": THRESHOLD_HONEST},
        }


# ── 猜想概念提取 ─────────────────────────────────────────────────

def extract_concepts(conjecture: dict, concepts: list[tuple[str, str]] = None) -> list[str]:
    """从 conjecture.json 提取相关的规范概念标签。

    扫描 claims/axioms 的文本，命中的规范概念（或其关键词）才纳入路径 J-score。
    无命中则返回全部规范概念（保守：全部纳入）。
    """
    concepts = concepts or DEFAULT_CONCEPTS
    text_parts = []
    for claim in conjecture.get("claims", []):
        text_parts.append(str(claim.get("description", "")))
        text_parts.append(str(claim.get("id", "")))
    for ax in conjecture.get("axioms", []):
        text_parts.append(str(ax if isinstance(ax, str) else ax.get("statement", ax)))
    for t in conjecture.get("targets", []):
        text_parts.append(str(t if isinstance(t, str) else t.get("description", t)))
    blob = " ".join(text_parts).lower()

    hit_labels = []
    for label, query in concepts:
        # 用 query 的关键词（取长词）匹配 conjecture 文本
        kws = [w for w in query.lower().split() if len(w) > 4]
        if any(kw in blob for kw in kws) or label.lower() in blob:
            hit_labels.append(label)
    return hit_labels or [label for label, _ in concepts]


# ── mock brain（自测，不加载 181K 神经元）───────────────────────

class _MockNeuron:
    def __init__(self, nid, embedding):
        self.embedding = np.asarray(embedding, dtype=np.float32)
        self.content = f"mock concept {nid}"


class _MockGraph:
    def __init__(self):
        self.neurons = {}


class _MockBrain:
    """确定性 mock：3 概念在 6 个 neuron 上，A/B 有重叠、C 孤立。"""

    def __init__(self):
        rng = np.random.RandomState(42)
        self.graph = _MockGraph()
        # 方向性嵌入：n0-n3 指向同一方向（相关簇），n4-n5 指向另一方向（孤立簇），
        # 模拟真实语义嵌入「相关概念方向接近、无关概念方向正交」的行为。
        base = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        other = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
        self._emb = {}
        for i in range(4):
            self._emb[f"n{i}"] = (base + 0.1 * rng.randn(4).astype(np.float32))
        for i in range(4, 6):
            self._emb[f"n{i}"] = (other + 0.1 * rng.randn(4).astype(np.float32))
        for nid, emb in self._emb.items():
            self.graph.neurons[nid] = _MockNeuron(nid, emb)
        self._concept_map = {
            "A": ["n0", "n1", "n2"],
            "B": ["n1", "n2", "n3"],   # 与 A 重叠 n1,n2
            "C": ["n4", "n5"],          # 孤立
        }

    def recall(self, query, top_k=10):
        ids = self._concept_map.get(query, ["n0"])
        return [{"id": nid, "content": self.graph.neurons[nid].content,
                 "similarity": 0.8, "activation": 0.8} for nid in ids]


# ── 主流程 ──────────────────────────────────────────────────────

def run(conjecture_path: Path | None, concepts_arg: list[str] | None,
        output_path: Path | None, brain=None, use_mock: bool = False) -> dict:
    bridge = JSpaceBridge(brain=_MockBrain() if use_mock else brain)

    if concepts_arg:
        concepts = concepts_arg
    elif conjecture_path is not None and conjecture_path.exists():
        conj = json.loads(conjecture_path.read_text(encoding="utf-8"))
        concepts = extract_concepts(conj)
    else:
        concepts = [label for label, _ in DEFAULT_CONCEPTS]

    if not bridge.brain_loaded and not use_mock:
        # 尝试加载真实大脑（一次性子进程场景）
        pass  # brain 属性会在首次 _concept_signature 时懒加载

    matrix = bridge.build_matrix(concepts)
    per_concept = {c: round(bridge.concept_j_score(c, concepts), 4) for c in concepts}
    path_j = round(bridge.path_j_score(concepts), 4)
    calibration = bridge.calibrate(matrix)

    result = {
        "concepts": concepts,
        "n_concepts": len(concepts),
        "path_j_score": path_j,
        "path_decision": bridge.decision(path_j),
        "per_concept_j_score": per_concept,
        "bridge_matrix": {c: {d: round(matrix[i][j], 4) for j, d in enumerate(concepts)}
                          for i, c in enumerate(concepts)},
        "calibration": calibration,
        "brain_source": "mock" if use_mock else ("injected" if brain is not None else "lazy-load"),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _self_test() -> int:
    """mock brain 自测：验证 J-score 三成分 + 对称性 + 决策。"""
    bridge = JSpaceBridge(brain=_MockBrain())
    ab = bridge.j_score_pair("A", "B")
    ac = bridge.j_score_pair("A", "C")
    print("J(A,B):", json.dumps(ab, ensure_ascii=False))
    print("J(A,C):", json.dumps(ac, ensure_ascii=False))

    # A 与 B 重叠 2 个 neuron，A 与 C 零重叠 → J(A,B) 应显著大于 J(A,C)
    assert ab["j"] > ac["j"], "有重叠的概念对应有更高 J-score"
    assert ab["mi"] > ac["mi"], "A/B 共现（Jaccard）应高于 A/C"
    assert ab["co_activation"] > ac["co_activation"], "A/B 共同激活应高于 A/C"

    # 对称性
    ba = bridge.j_score_pair("B", "A")
    assert abs(ab["j"] - ba["j"]) < 1e-6, "J-score 应对称"

    # 矩阵 + 路径 J-score + 决策
    concepts = ["A", "B", "C"]
    matrix = bridge.build_matrix(concepts)
    path_j = bridge.path_j_score(concepts)
    print(f"path_j_score({concepts}) = {path_j}")
    print("decision:", bridge.decision(path_j))
    print("calibration:", json.dumps(bridge.calibrate(matrix), ensure_ascii=False))

    # 提取概念（mock conjecture）
    conj = {"claims": [{"description": "Ricci curvature drives spectral gap", "id": "c1"}],
            "axioms": [{"statement": "Majorana seesaw mass scale"}], "targets": []}
    extracted = extract_concepts(conj)
    print("extracted concepts:", extracted)
    assert "g_Ricci" in extracted or "p_M_R" in extracted, "应从 conjecture 提取到概念"

    # 端到端 run（mock）
    out = run(None, ["A", "B", "C"], None, brain=_MockBrain(), use_mock=True)
    print("run() path_j_score:", out["path_j_score"], "decision:", out["path_decision"])

    print("\n自测通过 ✓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="J-space Bridge 动态桥接矩阵 + J-score")
    ap.add_argument("--conjecture", help="conjecture.json 路径（提取相关概念）")
    ap.add_argument("--concepts", help="逗号分隔的概念查询串（覆盖 conjecture 提取）")
    ap.add_argument("--output", help="输出 JSON 路径")
    ap.add_argument("--self-test", action="store_true", help="mock brain 离线自测")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    concepts_arg = [c.strip() for c in args.concepts.split(",") if c.strip()] if args.concepts else None
    result = run(Path(args.conjecture) if args.conjecture else None, concepts_arg,
                 Path(args.output) if args.output else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
