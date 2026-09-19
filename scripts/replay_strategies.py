#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.6 增强 — Dream-RSI 风格 Replay Simulator + 变异策略显式化（P0-P2 落地）

对齐 arXiv 2609.14858 (Dream-RSI) 的核心洞察：
  「积累的发现历史本身就是一个可重放的模拟器。」

P0  replay simulator  : 把 archive.jsonl 从「被动记录」升级为「主动重放预筛选器」——
                         统计各变异策略的历史成功率 + 对各类缺陷的修复率，排序推荐。
P1  off-policy 反馈    : 变异前用历史数据做廉价预筛选（盲区检测 + 成功先例注入），
                         减少无效变异的 LLM 调用与编译浪费。
P2  变异策略显式化      : 把单一「诊断→修复」拆成多个可独立评估的变异策略，
                         用 ε-greedy 在探索与利用之间动态选择。

与 stage36_evolution.py 的关系：本模块只提供策略定义 + 历史统计 + 排序；
stage36_evolution.py 负责在每代调用 rank_strategies 选择策略并定制 mutate prompt。
本模块 stdlib-only，可独立单测（见 main() 的 --self-test）。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

# ── P2：变异策略显式化 ─────────────────────────────────────────────
# 每个策略声明它「针对性修复」的缺陷类型（与 evaluate_lean 的 defects 键对齐）。
# targets 里排前面的缺陷类型优先级更高（用于冷启动排序）。
MUTATION_STRATEGIES: dict[str, dict] = {
    "repair_dangling": {
        "desc": "修复悬空引用 / 补齐缺失声明",
        "targets": ["dangling_refs"],
        "focus": (
            "优先修复所有悬空引用（出现但未声明的 _axiom/_lemma/_theorem 名字）："
            "为每个悬空名字补齐声明，或改正拼写使其指向已存在的声明。"
        ),
    },
    "axiomatize": {
        "desc": "把 sorry/admit 改写为诚实公理（附文献引用注释）",
        "targets": ["sorry", "admit"],
        "focus": (
            "优先处理所有 sorry/admit：能补真实证明体的用真实策略体（nlinarith/field_simp/ring/exact），"
            "无法从第一性原理导出的，改写为显式 axiom 声明并附文献引用注释。"
        ),
    },
    "tactic_complete": {
        "desc": "补全 tactic 证明体（消除 := by trivial / := True 空壳）",
        "targets": ["trivial_or_true_stub"],
        "focus": (
            "优先消除所有 := by trivial 和 := True 空壳：替换为真实策略体"
            "（calc 链 / nlinarith / field_simp / ring / exact ..._axiom / native_decide）。"
        ),
    },
    "lemma_decompose": {
        "desc": "把过长定理分解为中间引理",
        "targets": ["sorry", "trivial_or_true_stub"],
        "focus": (
            "优先把过长或未完成的定理证明分解为若干中间引理，先证引理再用引理拼装主定理，"
            "从而消除 sorry / 空壳。"
        ),
    },
    "deduplicate": {
        "desc": "删除冗余引理 / 未用 axiom / 悬空引用",
        "targets": ["redundant_lemmas", "unused_axioms"],
        "focus": (
            "优先清理结构缺陷：删除从未被下游引用的冗余引理、从未被使用的 axiom；"
            "若某冗余引理其实是主结论的依赖，补上缺失的引用边。"
        ),
    },
}

# 缺陷严重性排序（用于冷启动 + 盲区排序），与 evaluate_lean 扣分一致
DEFECT_PRIORITY = [
    "dangling_refs",       # -50
    "sorry",               # -20
    "admit",               # -15
    "trivial_or_true_stub",# -10
    "redundant_lemmas",    # -5
    "unused_axioms",       # -3
]


def defect_signature(defects: dict) -> str:
    """P3（RSIAgent 因果三元组）：把缺陷 dict 压成「condition 签名」。

    签名 = 活跃缺陷类型的有序组合键（如 'sorry>0&admit>0'），无活跃缺陷为 'clean'。
    这是 RSIAgent 因果记忆 actions→conditions→consequences 里的「condition」维度——
    记录「在什么缺陷状态下尝试了某修复动作」，而非只记录「尝试了什么动作」。
    """
    active = [k for k in DEFECT_PRIORITY if defects.get(k, 0) and defects.get(k, 0) > 0]
    return "&".join(active) if active else "clean"


class ReplaySimulator:
    """P0：从 archive.jsonl 构造重放模拟器，统计历史变异模式。"""

    def __init__(self, archive_path: str | Path | None = None):
        self.records: list[dict] = []
        if archive_path:
            self.load(archive_path)

    def load(self, archive_path: str | Path) -> int:
        """读 archive.jsonl（每行一条 record），返回加载条数。容错缺字段的旧记录。"""
        p = Path(archive_path)
        if not p.exists():
            return 0
        self.records = []
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self.records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return len(self.records)

    def strategy_stats(self) -> dict[str, dict]:
        """各变异策略的 {attempts, accepted, success_rate, avg_gain, last_used}。

        只有带 mutation_strategy 且 mutation_strategy != 'seed' 的 record 才计入。
        """
        stats: dict[str, dict] = defaultdict(
            lambda: {"attempts": 0, "accepted": 0, "gains": [], "last_used": None}
        )
        for r in self.records:
            strat = r.get("mutation_strategy", "unknown")
            if strat in ("seed", "unknown", None, ""):
                continue
            s = stats[strat]
            s["attempts"] += 1
            if r.get("accepted"):
                s["accepted"] += 1
            gain = r.get("gain", 0.0)  # score 提升（accepted 时 parent→child 差值）
            if isinstance(gain, (int, float)):
                s["gains"].append(gain)
            s["last_used"] = r.get("timestamp")
        out = {}
        for strat, s in stats.items():
            rate = (s["accepted"] / s["attempts"]) if s["attempts"] else None
            avg_gain = (sum(s["gains"]) / len(s["gains"])) if s["gains"] else 0.0
            out[strat] = {
                "attempts": s["attempts"],
                "accepted": s["accepted"],
                "success_rate": round(rate, 3) if rate is not None else None,
                "avg_gain": round(avg_gain, 2),
                "last_used": s["last_used"],
            }
        return out

    def defect_repair_rate(self) -> dict[str, dict[str, float]]:
        """各策略对各类缺陷的修复率 = 修复该缺陷的次数 / 尝试次数。

        依据 record 里的 defects_before / defects_after 差值判断「是否修复了某类缺陷」。
        """
        repair: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for r in self.records:
            strat = r.get("mutation_strategy", "unknown")
            if strat in ("seed", "unknown", None, ""):
                continue
            before = r.get("defects_before") or {}
            after = r.get("defects") or {}
            for key in DEFECT_PRIORITY:
                b = before.get(key, 0)
                a = after.get(key, 0)
                repair[strat][key].append(1 if (a < b) else 0)
        out = {}
        for strat, by_defect in repair.items():
            out[strat] = {
                key: round(sum(v) / len(v), 3) if v else None
                for key, v in by_defect.items()
            }
        return out

    def rank_strategies(self, defects: dict, epsilon: float = 0.15) -> list[dict]:
        """P0+P2：ε-greedy 排序推荐策略，返回 [{name, score, reason, ...}]（高分在前）。

        评分 = 历史成功率 × (1 + 0.5 × 针对性)，针对性 = 策略 targets 与当前活跃缺陷的重叠数。
        冷启动（无历史）按缺陷严重性 + 针对性排序。
        """
        active = [k for k in DEFECT_PRIORITY if defects.get(k, 0) > 0]
        if not active:
            return []

        stats = self.strategy_stats()
        repair = self.defect_repair_rate()

        scored = []
        for name, cfg in MUTATION_STRATEGIES.items():
            targeted = sum(1 for t in cfg["targets"] if t in active)
            s = stats.get(name, {})
            if s.get("success_rate") is not None:
                success = s["success_rate"]
                # 若该策略对当前活跃缺陷的历史修复率为 0，惩罚（历史证明无效）
                for t in cfg["targets"]:
                    if t in active:
                        rr = repair.get(name, {}).get(t)
                        if rr == 0.0:
                            success *= 0.5
            else:
                success = 0.5  # 无历史先验
            # 针对性是硬门槛：完全不针对当前缺陷的策略几乎不推荐（除非探索）
            if targeted == 0:
                score = 0.05 * success
            else:
                score = success * (0.5 + 0.5 * targeted)
            scored.append({
                "name": name,
                "score": round(score, 3),
                "targeted": targeted,
                "success_rate": s.get("success_rate"),
                "attempts": s.get("attempts", 0),
                "avg_gain": s.get("avg_gain", 0.0),
                "desc": cfg["desc"],
                "focus": cfg["focus"],
            })

        scored.sort(key=lambda x: (-x["score"], -x["targeted"]))
        return scored

    def blind_spots(self, defects: dict) -> list[str]:
        """P1：历史盲区检测 —— 当前活跃缺陷中，历史上从未被任何策略成功修复过的类型。"""
        active = [k for k in DEFECT_PRIORITY if defects.get(k, 0) > 0]
        repair = self.defect_repair_rate()
        # 某缺陷类型历史最高修复率
        ever_repaired = defaultdict(float)
        for strat, by_defect in repair.items():
            for key, rate in by_defect.items():
                if rate is not None:
                    ever_repaired[key] = max(ever_repaired[key], rate)
        blind = [k for k in active if ever_repaired.get(k, 0.0) == 0.0]
        return blind

    def causal_rules(self) -> list[dict]:
        """P3（RSIAgent 因果记忆）：从 archive 提取 actions→conditions→consequences 三元组。

        每条规则 = (action=mutation_strategy, condition=缺陷签名, consequence=成功率/gain)。
        相比 strategy_stats（只看动作）和 defect_repair_rate（只看动作×缺陷），
        causal_rules 额外引入「condition」维度——同一动作在不同缺陷状态下效果不同。
        """
        rules: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"attempts": 0, "accepted": 0, "gains": []})
        for r in self.records:
            strat = r.get("mutation_strategy", "unknown")
            if strat in ("seed", "unknown", None, ""):
                continue
            before = r.get("defects_before") or {}
            cond = defect_signature(before)
            key = (strat, cond)
            rules[key]["attempts"] += 1
            if r.get("accepted"):
                rules[key]["accepted"] += 1
            gain = r.get("gain", 0.0)
            if isinstance(gain, (int, float)):
                rules[key]["gains"].append(gain)
        out = []
        for (strat, cond), s in rules.items():
            out.append({
                "action": strat,
                "condition": cond,
                "attempts": s["attempts"],
                "accepted": s["accepted"],
                "success_rate": round(s["accepted"] / s["attempts"], 3) if s["attempts"] else None,
                "avg_gain": round(sum(s["gains"]) / len(s["gains"]), 2) if s["gains"] else 0.0,
            })
        out.sort(key=lambda x: (-(x["success_rate"] if x["success_rate"] is not None else -1.0),
                                 -x["attempts"]))
        return out

    def condition_match(self, defects: dict) -> list[dict]:
        """P3：返回当前缺陷状态下「相同 condition」的历史因果规则（可复用经验）。

        用途：变异前把「历史相同缺陷签名下的成功先例」注入诊断 prompt，
        让修复计划借鉴「在同样缺陷组合下被证明有效的动作」。
        """
        cond = defect_signature(defects)
        return [r for r in self.causal_rules() if r["condition"] == cond]

    def choose(self, defects: dict, epsilon: float = 0.15) -> dict | None:
        """P2：ε-greedy 选择单个策略。返回策略 dict 或 None（无活跃缺陷）。"""
        ranked = self.rank_strategies(defects, epsilon)
        if not ranked:
            return None
        if random.random() < epsilon:
            # 探索：随机选一个（含针对性为 0 的）
            return random.choice(list(MUTATION_STRATEGIES.values())) | {"name": random.choice(list(MUTATION_STRATEGIES))}
        return ranked[0]


def _self_test() -> int:
    """离线自测：构造假 archive，验证统计 + 排序 + 盲区。"""
    tmp = Path("/tmp/replay_selftest.jsonl")
    records = [
        {"generation": 1, "mutation_strategy": "axiomatize", "accepted": True,
         "defects_before": {"sorry": 2, "admit": 0}, "defects": {"sorry": 0, "admit": 0}, "gain": 20},
        {"generation": 2, "mutation_strategy": "axiomatize", "accepted": False,
         "defects_before": {"sorry": 0, "admit": 1}, "defects": {"sorry": 0, "admit": 1}, "gain": 0},
        {"generation": 3, "mutation_strategy": "deduplicate", "accepted": True,
         "defects_before": {"redundant_lemmas": 3}, "defects": {"redundant_lemmas": 0}, "gain": 15},
        {"generation": 4, "mutation_strategy": "repair_dangling", "accepted": False,
         "defects_before": {"dangling_refs": 1}, "defects": {"dangling_refs": 2}, "gain": -50},
    ]
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")

    rs = ReplaySimulator(tmp)
    print("加载记录:", len(rs.records))
    print("\n=== 策略统计 ===")
    print(json.dumps(rs.strategy_stats(), ensure_ascii=False, indent=2))
    print("\n=== 缺陷修复率 ===")
    print(json.dumps(rs.defect_repair_rate(), ensure_ascii=False, indent=2))

    defects = {"sorry": 1, "dangling_refs": 1, "redundant_lemmas": 0, "admit": 0,
               "trivial_or_true_stub": 0, "unused_axioms": 0}
    print("\n=== 排序（defects: sorry=1, dangling=1）===")
    for r in rs.rank_strategies(defects, epsilon=0.0):
        print(f"  {r['name']:16s} score={r['score']:.3f} targeted={r['targeted']} "
              f"succ={r['success_rate']} attempts={r['attempts']}")

    print("\n=== 历史盲区 ===")
    print(rs.blind_spots(defects))

    # 验证 repair_dangling 对 dangling_refs 的失败历史被惩罚
    assert rs.strategy_stats()["repair_dangling"]["success_rate"] == 0.0
    print("\n自测通过 ✓")
    tmp.unlink()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Replay Simulator 自测")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(_self_test())
    print("用法: python replay_strategies.py --self-test")
    sys.exit(0)
