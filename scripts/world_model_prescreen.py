#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.6 增强 — JANUS 世界模型（预执行预测）+ 三标准评分（P0-①/② 落地）

对齐 arXiv:2610.13194（JANUS: Predict-Verify-Evolve，中科院计算所 AI 安全国重）：
  「共同进化世界模型」解决长程自主研究的反馈延迟——世界模型在**昂贵的 executor
  （LLM 变异 + Lean 编译 + DAG 审计）之前**做 refine/select/prune，用三标准打分
  预筛选候选，3.74× 样本效率加速。

P0-① 世界模型（预执行预测）：
  `WorldModel.predict()` 用 archive.jsonl 历史，预测一次 (strategy × condition)
  变异的期望 gain + 达成 0 sorry 的概率。有足够历史 + 预测无增益 + 0-sorry 概率低
  → PRUNE（跳过昂贵的 LLM 变异 + 编译）。**诚实边界**：世界模型是**预筛选器**，
  绝不替代 RSIHub 的冻结评估器（候选不能改写评分规则）——PRUNE 只省成本，
  幸存者仍走冻结评估器定最终分数。

P0-② 三标准评分（价值 + 信息增益 + 探索效用）：
  `three_criteria_score()` 把 JANUS 的三标准落到 Stage 3.6 的候选评估：
  ① 价值 value          — 冻结评估器分数（已有，由 stage36 传入，本模块只算增益）
  ② 信息增益 info_gain   — 该变异揭示的新信息量 = 盲区缺陷占比 + 新 condition 奖励
  ③ 探索效用 explore     — UCB 探索奖励（欠采样策略加分，补当前 Stage 3.6 缺的探索项）

与 stage36_evolution.py 的关系：本模块提供预测 + 评分；stage36 在每代变异前
调用 `WorldModel.predict()` 预筛选，在 gate 阶段调用 `three_criteria_score()`
把三标准记入 archive record。本模块 stdlib-only，可独立单测（--self-test）。

关键设计分离（对齐 JANUS 诚实边界）：
  「预测」由世界模型决定（预筛选），「结果」由冻结评估器决定（最终门控）。
  世界模型和冻结评估器是两个独立模块，候选改写不了任何一个。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from replay_strategies import ReplaySimulator, MUTATION_STRATEGIES, DEFECT_PRIORITY, defect_signature

# ── 世界模型超参 ─────────────────────────────────────────────────
MIN_HISTORY = 3            # 判定 PRUNE 所需的最小历史尝试次数
ZERO_SORRY_THRESHOLD = 0.5  # 达成 0 sorry 的概率低于此值才允许 PRUNE
J_SCORE_PROTECT_THRESHOLD = 0.5  # J-space 大脑支持度 ≥ 此值 → 保护候选不被历史剪枝


# ── P0-② 三标准评分 ──────────────────────────────────────────────

def three_criteria_score(defects: dict, strat_name: str, replay: ReplaySimulator,
                         frozen_score: float = 0.0, j_score: float | None = None) -> dict:
    """JANUS 三标准评分：价值 + 信息增益 + 探索效用。

    ① 价值 value           — 冻结评估器分数（由 stage36 传入 frozen_score）；
                             本函数额外返回 predicted_gain（历史期望增益）。
    ② 信息增益 info_gain    — 该变异揭示的新信息量：
        (a) 盲区缺陷占比：当前活跃缺陷中「历史从未修复成功」的类型占比
            （修好一个盲区 = 学到全新信息，价值高于重复已知修复）；
        (b) 新 condition 奖励：当前缺陷签名从未出现在 archive → +0.5。
    ③ 探索效用 explore      — UCB 探索奖励：欠采样策略加分
        sqrt(2·ln(N_total+1) / (n_strategy+1))，补 Stage 3.6 现在缺的探索项
        （Stage 2 有 UCB，Stage 3.6 进化循环里没有）。

    三标准**不替代**冻结评估器：它们只做预筛选排序 + 记录归档，
    最终接受/拒绝仍由 stage36 的冻结评估器分数 + 隐藏物理内容审计决定。
    """
    active = [k for k in DEFECT_PRIORITY if defects.get(k, 0) > 0]
    blinds = set(replay.blind_spots(defects))
    stats = replay.strategy_stats()
    cond = defect_signature(defects)

    # ② 信息增益
    blind_frac = (len(blinds & set(active)) / len(active)) if active else 0.0
    seen_conditions = {
        defect_signature(r.get("defects_before") or {})
        for r in replay.records
        if r.get("mutation_strategy") not in ("seed", "unknown", None, "")
    }
    new_condition = cond not in seen_conditions
    info_gain = blind_frac + (0.5 if new_condition else 0.0)

    # ③ 探索效用（UCB）
    n_total = sum(s.get("attempts", 0) for s in stats.values())
    n_strat = stats.get(strat_name, {}).get("attempts", 0)
    explore = math.sqrt(2 * math.log(n_total + 1) / (n_strat + 1)) if n_total > 0 else 1.0

    # ① 价值：冻结分数 + 期望增益（历史）
    s = stats.get(strat_name, {})
    predicted_gain = s.get("avg_gain", 0.0)

    result = {
        "condition": cond,
        "value": round(frozen_score, 1),
        "predicted_gain": round(predicted_gain, 2),
        "info_gain": round(info_gain, 3),
        "blind_frac": round(blind_frac, 3),
        "new_condition": new_condition,
        "exploration_utility": round(explore, 3),
        "total": round(frozen_score / 100.0 + 0.5 * info_gain + 0.3 * explore, 3),
    }
    # [v2.22.0] J-space 大脑支持度先验（报告字段，不参与三标准加权——它是先验非奖励准则）
    if j_score is not None:
        result["brain_support"] = round(j_score, 3)
    return result


# ── P0-① 世界模型（预执行预测）───────────────────────────────────

class WorldModel:
    """JANUS 世界模型：从 archive.jsonl 学习的确定性预执行预测器。

    预测一次 (strategy × condition) 变异的结果，在昂贵的 LLM 变异 + 编译之前
    决定 KEEP（值得执行）还是 PRUNE（历史证明无望，跳过省成本）。

    特征空间：mutation_strategy（动作）× condition（缺陷签名状态），
    即 replay_strategies.causal_rules() 的 (action, condition) 维度。
    无任何 LLM 参与——纯历史统计，确定性，候选者无法改写。
    """

    def __init__(self, replay: ReplaySimulator):
        self.replay = replay

    def predict(self, defects: dict, strat_name: str, j_score: float | None = None) -> dict:
        """预测 (strategy × condition) 变异结果，返回 verdict。

        predicted_gain   : 期望分数提升（优先 condition 级历史，退 strategy 级，再退 0）。
        zero_sorry_prob  : 达成 0 sorry 的概率（历史接受率，含 learn_on_pass）。
        j_score          : （可选）J-space 大脑支持度先验（v2.22.0）。≥ J_SCORE_PROTECT_THRESHOLD
                           时「保护」候选不被历史剪枝——大脑强支持说明概念已充分落地，
                           即使策略历史弱也值得一试。大脑支持弱（< 阈值）不改变剪枝判定。
        verdict          : KEEP（执行变异）/ PRUNE（跳过，历史证明无望）。
        """
        cond = defect_signature(defects)
        stats = self.replay.strategy_stats().get(strat_name, {})
        causal = {
            r["condition"]: r
            for r in self.replay.causal_rules()
            if r["action"] == strat_name
        }

        # 期望 gain：condition 级 → strategy 级 → 冷启动 0
        if cond in causal and causal[cond]["attempts"] > 0:
            predicted_gain = causal[cond]["avg_gain"]
            zero_sorry_prob = causal[cond]["success_rate"]
            n_hist = causal[cond]["attempts"]
        elif stats.get("attempts", 0) > 0:
            predicted_gain = stats.get("avg_gain", 0.0)
            zero_sorry_prob = stats.get("success_rate")
            n_hist = stats.get("attempts", 0)
        else:
            predicted_gain = 0.0
            zero_sorry_prob = None
            n_hist = 0

        # 剪枝判定（诚实边界：世界模型只是预筛选器，不替代冻结评估器）
        # 有足够历史 + 预测无增益 + 0-sorry 概率低 → PRUNE（省掉这次 LLM+编译）
        verdict = "KEEP"
        if n_hist >= MIN_HISTORY and predicted_gain <= 0.0:
            if zero_sorry_prob is None or zero_sorry_prob < ZERO_SORRY_THRESHOLD:
                verdict = "PRUNE"

        # [v2.22.0] J-space 先验保护：大脑强支持（j_score ≥ 阈值）→ 不被历史剪枝
        if j_score is not None and j_score >= J_SCORE_PROTECT_THRESHOLD:
            verdict = "KEEP"

        return {
            "condition": cond,
            "strategy": strat_name,
            "predicted_gain": round(predicted_gain, 2),
            "zero_sorry_prob": round(zero_sorry_prob, 3) if zero_sorry_prob is not None else None,
            "n_history": n_hist,
            "j_score_prior": round(j_score, 3) if j_score is not None else None,
            "verdict": verdict,
        }


def _self_test() -> int:
    """离线自测：构造假 archive，验证三标准评分 + 世界模型预测 + 剪枝。"""
    tmp = Path("/tmp/janus_worldmodel_selftest.jsonl")
    # 构造历史：axiomatize 在 sorry 条件下成功过 4 次；deduplicate 在 redundant 条件下失败 4 次
    records = []
    for i in range(4):
        records.append({
            "generation": i + 1, "mutation_strategy": "axiomatize", "accepted": True,
            "defects_before": {"sorry": 2, "admit": 0, "trivial_or_true_stub": 0,
                               "redundant_lemmas": 0, "unused_axioms": 0, "dangling_refs": 0},
            "defects": {"sorry": 0, "admit": 0, "trivial_or_true_stub": 0,
                        "redundant_lemmas": 0, "unused_axioms": 0, "dangling_refs": 0},
            "gain": 20,
        })
    for i in range(4):
        records.append({
            "generation": i + 5, "mutation_strategy": "deduplicate", "accepted": False,
            "defects_before": {"sorry": 0, "admit": 0, "trivial_or_true_stub": 0,
                               "redundant_lemmas": 3, "unused_axioms": 0, "dangling_refs": 0},
            "defects": {"sorry": 0, "admit": 0, "trivial_or_true_stub": 0,
                        "redundant_lemmas": 5, "unused_axioms": 0, "dangling_refs": 0},
            "gain": -10,
        })
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")

    replay = ReplaySimulator(tmp)
    wm = WorldModel(replay)

    print("=== 三标准评分（当前缺陷 sorry=2，策略 axiomatize，冻结分 60）===")
    defects_sorry = {"sorry": 2, "admit": 0, "trivial_or_true_stub": 0,
                     "redundant_lemmas": 0, "unused_axioms": 0, "dangling_refs": 0}
    sc = three_criteria_score(defects_sorry, "axiomatize", replay, frozen_score=60.0)
    print(json.dumps(sc, ensure_ascii=False, indent=2))

    print("\n=== 世界模型预测：axiomatize × sorry（有成功历史 → KEEP）===")
    p1 = wm.predict(defects_sorry, "axiomatize")
    print(json.dumps(p1, ensure_ascii=False, indent=2))

    print("\n=== 世界模型预测：deduplicate × redundant（有失败历史 → PRUNE）===")
    defects_red = {"sorry": 0, "admit": 0, "trivial_or_true_stub": 0,
                   "redundant_lemmas": 3, "unused_axioms": 0, "dangling_refs": 0}
    p2 = wm.predict(defects_red, "deduplicate")
    print(json.dumps(p2, ensure_ascii=False, indent=2))

    print("\n=== 世界模型预测：repair_dangling × dangling（冷启动 → KEEP）===")
    defects_dang = {"sorry": 0, "admit": 0, "trivial_or_true_stub": 0,
                    "redundant_lemmas": 0, "unused_axioms": 0, "dangling_refs": 1}
    p3 = wm.predict(defects_dang, "repair_dangling")
    print(json.dumps(p3, ensure_ascii=False, indent=2))

    # 断言
    assert p1["verdict"] == "KEEP", "有成功历史应 KEEP"
    assert p1["predicted_gain"] > 0, "axiomatize 期望增益应为正"
    assert p2["verdict"] == "PRUNE", "有失败历史且无增益应 PRUNE"
    assert p3["verdict"] == "KEEP", "冷启动应 KEEP"
    assert sc["info_gain"] >= 0.0 and sc["exploration_utility"] >= 0.0
    print("\n自测通过 ✓")
    tmp.unlink()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="JANUS 世界模型 + 三标准评分 自测")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(_self_test())
    print("用法: python world_model_prescreen.py --self-test")
    sys.exit(0)
