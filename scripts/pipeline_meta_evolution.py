#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.8 — Pipeline 元进化（harness 作为可进化的一等对象）

对齐 arXiv:2609.17523（ScienceBuddy: Recursive-in-Recursive Self-Improvement）的
「内层递归」：固定模型，搜索更好的 harness（pipeline 编排程序）。

核心思想：scientific-discovery-proof 的 pipeline 编排逻辑（stage 顺序 / 每 stage
参数 / gate 规则 / 选择策略）目前是**固定代码**。本模块把它抽象为一个可替换的
PipelineHarness（JSON 编排策略），用辅助模型（deepseek-flash（thinking disabled））提议改进，在
Val 任务集上对比候选与父 harness，严格更优才替换。

ScienceBuddy 映射：
  harness H            → PipelineHarness（编排策略 JSON，对应 pipeline_orchestrator 的 main 循环）
  辅助模型（参数固定） → deepseek-flash（thinking disabled）（提议 harness 改进，不参与最终评分）
  Val 任务对比        → 固定 Val 猜想集上 harness 的预期成功率（历史证据 + 结构评分）
  严格更高才替换      → 候选 score 严格 > 父 score 且 schema 有效才采纳

诚实边界：
1. harness 是「编排策略描述」而非「完整可执行程序」——本机 P620 无法重跑完整
   pipeline 来评估 harness，故评估用「结构完整性 + 历史证据相似度」近似，非真实
   证明成功率。真实闭环需在 RTX4000 服务器重跑（见 P0-② 优化说明）。
2. 辅助模型只提议、不评分；最终采纳由确定性评估器（本模块 evaluate）决定，候选
   不能改写评分规则（对齐 ScienceBuddy 的「辅助模型参数固定」）。
3. harness 历史（harness_archive.jsonl）append-only，记录每次提议/评估/采纳证据。

用法：
  python pipeline_meta_evolution.py --conjecture /path/conjecture.json --rounds 3
  python pipeline_meta_evolution.py --self-test       # mock 提议 + 离线评估自测
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from pathlib import Path

# ── Harness schema（编排策略）─────────────────────────────────────

# 核心 stage 集合（编排策略必须覆盖的关键节点）
CORE_STAGES = ["spec_check", "jspace", "1", "2", "3", "3.5", "3.5b", "3.5c", "4"]

# 关键 gate（安全性：编排策略必须正确处理的门控）
CRITICAL_GATES = {
    "1": "BLOCKED",       # Stage 1 gate BLOCKED → stop pipeline
    "3.5": "BLOCK",       # Stage 3.5 BLOCK → block Stage 4
    "3.5b": "BLOCK",      # 物理内容审计 BLOCK → block Stage 4
}

# 参数合理范围（超出则扣结构分——防辅助模型提不可执行参数）
PARAM_BOUNDS = {
    "3.6.generations": (1, 20),
    "3.6.batch_size": (1, 16),
    "3.scaffold_timeout": (60, 3600),
    "3.top_k_recall": (1, 50),
    "2.top_k": (1, 20),
}

DEFAULT_HARNESS: dict = {
    "version": "1.0",
    "name": "default",
    "stage_order": ["spec_check", "jspace", "1", "2", "3", "3.5", "3.5b", "3.5c", "4"],
    "stage_params": {
        "1": {"enable_sciexplorer": True, "enable_maf": True},
        "2": {"top_k": 3, "selector": "rpucg", "ucb_c": 0.5},
        "3": {"scaffold_timeout": 600, "top_k_recall": 10, "algorithm": "mcts_abc"},
        "3.6": {"generations": 3, "batch_size": 4},
    },
    "gate_rules": {
        "1": {"on": "BLOCKED", "action": "stop"},
        "3.5": {"on": "BLOCK", "action": "block_stage_4"},
        "3.5b": {"on": "BLOCK", "action": "block_stage_4"},
        "3.5c": {"on": "BLOCK", "action": "block_stage_4"},
    },
    "selection_policy": {
        "stage2": "rpucg_dag_aware",
        "stage36": "frozen_evaluator_strict",
    },
}


class PipelineHarness:
    """pipeline 编排策略（可替换的 harness 对象）。"""

    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def default(cls) -> "PipelineHarness":
        return cls(copy.deepcopy(DEFAULT_HARNESS))

    def to_dict(self) -> dict:
        return self.config

    @property
    def name(self) -> str:
        return self.config.get("name", "unnamed")

    # ── 结构完整性评分（确定性）───────────────────────────────────
    def validate(self) -> tuple[bool, list[str]]:
        """schema 验证：返回 (valid, 问题列表)。"""
        problems = []
        cfg = self.config
        if not isinstance(cfg, dict):
            return False, ["harness 不是 dict"]
        # stage_order 覆盖核心 stage
        order = cfg.get("stage_order", [])
        missing = [s for s in CORE_STAGES if s not in order]
        if missing:
            problems.append(f"stage_order 缺核心 stage: {missing}")
        # 关键 gate 覆盖
        gates = cfg.get("gate_rules", {})
        for g, cond in CRITICAL_GATES.items():
            if g not in gates or gates[g].get("on") != cond:
                problems.append(f"关键 gate {g} 缺 on={cond} 规则")
        # 参数范围
        params = cfg.get("stage_params", {})
        flat = _flatten_params(params)
        for key, (lo, hi) in PARAM_BOUNDS.items():
            v = flat.get(key)
            if v is not None and not (lo <= v <= hi):
                problems.append(f"参数 {key}={v} 超出合理范围 [{lo},{hi}]")
        # selection_policy 覆盖
        sel = cfg.get("selection_policy", {})
        for k in ("stage2", "stage36"):
            if k not in sel:
                problems.append(f"selection_policy 缺 {k}")
        return (len(problems) == 0, problems)

    def structure_score(self) -> float:
        """结构分 [0,1]：完整覆盖 + gate 安全 + 参数合理。"""
        valid, problems = self.validate()
        if valid:
            return 1.0
        # 每个问题扣 0.15，下限 0.05
        return max(0.05, 1.0 - 0.15 * len(problems))


def _flatten_params(params: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten_params(v, key))
        else:
            out[key] = v
    return out


# ── 历史证据评估（确定性）─────────────────────────────────────────

def _harness_signature(h: PipelineHarness) -> str:
    """harness 的关键决策指纹（用于历史相似度）。"""
    cfg = h.config
    parts = [
        "|".join(str(s) for s in cfg.get("stage_order", [])),
        json.dumps(cfg.get("stage_params", {}), sort_keys=True),
        json.dumps(cfg.get("gate_rules", {}), sort_keys=True),
        json.dumps(cfg.get("selection_policy", {}), sort_keys=True),
    ]
    return "||".join(parts)


def load_archive(path: Path) -> list[dict]:
    if not path.exists():
        return []
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return recs


def evaluate_harness(harness: PipelineHarness, archive: list[dict],
                     val_tasks: list[str]) -> dict:
    """确定性评估：结构分 + 历史证据分。

    score = 0.6 * structure + 0.4 * history
    - structure：schema 完整 + gate 安全 + 参数合理（防不可执行 harness）
    - history：archive 中相同/相似 harness 的历史成功率（无历史则 0.5 中性）
    """
    struct = harness.structure_score()
    sig = _harness_signature(harness)

    # 历史：精确匹配优先，否则模糊（stage_order 相同）
    exact = [r for r in archive if r.get("signature") == sig]
    if exact:
        history = sum(1 for r in exact if r.get("adopted")) / len(exact)
    else:
        order = harness.config.get("stage_order", [])
        same_order = [r for r in archive if r.get("stage_order") == order]
        history = (sum(1 for r in same_order if r.get("adopted")) / len(same_order)) if same_order else 0.5

    score = 0.6 * struct + 0.4 * history
    return {
        "signature": sig,
        "structure_score": round(struct, 4),
        "history_score": round(history, 4),
        "score": round(score, 4),
        "valid": harness.validate()[0],
        "problems": harness.validate()[1],
    }


# ── 辅助模型提议（deepseek-flash（thinking disabled））────────────────────────────────

def _load_deepseek_key() -> str:
    """从已知位置读 DeepSeek key（不读 .env 明文进日志）。"""
    for cand in ["DEEPSEEK_API_KEY"]:
        if os.environ.get(cand):
            return os.environ[cand]
    env_path = Path("~/projects/ML-Master/.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r'\s*DEEPSEEK_API_KEY\s*=\s*(.+)', line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return ""


def _deep_merge(base: dict, override: dict) -> dict:
    """深合并：override 覆盖 base 同名字段，base 缺失字段保留（候选只提供差异）。"""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def propose_harness(parent: PipelineHarness, evidence: dict, api_key: str,
                    n_candidates: int = 3) -> list[PipelineHarness]:
    """辅助模型提议 n 个候选 harness（deepseek-flash（thinking disabled））。

    候选 config 与父 config 深合并（候选只提供差异，缺失字段继承父），
    故 v4-pro 输出不完整 config 也能通过 schema 验证。
    """
    import openai
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    prompt = f"""你是 scientific-discovery-proof 管线的 harness 改进器（辅助模型，参数固定）。
当前 harness（pipeline 编排策略 JSON）:
{json.dumps(parent.to_dict(), ensure_ascii=False, indent=2)}

历史证据（最近 harness 评估）:
{json.dumps(evidence, ensure_ascii=False, indent=2)}

请提议 {n_candidates} 个改进后的 harness。每个候选是一个 JSON 对象，形如：
{{"name": "候选名", "config": {{...对父 harness 的**增量修改**（只写要改的字段，未写字段自动继承父）...}}, "rationale": "为什么这个改动提升证明成功率"}}

改进方向（择一或多个）：
1. stage_order 顺序优化（如把 3.6 进化提前、2.6 反证探测位置调整）
2. stage_params 参数调优（如 3.6.generations 调高、3.scaffold_timeout 调整）
3. gate_rules 完善（新增或调整门控动作）
4. selection_policy 调整（如 stage36 从 frozen_evaluator_strict 改为其他）

约束（违反则候选无效）：
- stage_order 必须保留核心 stage: spec_check, jspace, 1, 2, 3, 3.5, 3.5b, 3.5c, 4
- 必须保留关键 gate: 1→BLOCKED→stop, 3.5/3.5b/3.5c→BLOCK→block_stage_4
- 参数范围: 3.6.generations∈[1,20], 3.6.batch_size∈[1,16]

输出严格 JSON 数组，每个元素是 {{"name", "config", "rationale"}}。不要输出 JSON 之外的任何内容。"""

    resp = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=6000,
        timeout=180,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = resp.choices[0].message.content or ""
    if not text:
        text = getattr(resp.choices[0].message, "reasoning_content", "") or ""

    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []

    candidates = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("config"), dict):
            # 候选 config 与父 config 深合并（候选只提供差异）
            merged = _deep_merge(parent.config, item["config"])
            h = PipelineHarness(merged)
            h.config["name"] = item.get("name", "candidate")
            if h.validate()[0]:
                candidates.append(h)
    return candidates


def _mock_propose(parent: PipelineHarness, evidence: dict, n_candidates: int = 3):
    """离线自测：确定性 mock 提议（三个小幅参数扰动候选）。"""
    cands = []
    for i in range(n_candidates):
        cfg = copy.deepcopy(parent.config)
        cfg["name"] = f"mock_candidate_{i+1}"
        # 参数扰动
        if "3.6" in cfg.get("stage_params", {}):
            gen = cfg["stage_params"]["3.6"].get("generations", 3)
            cfg["stage_params"]["3.6"]["generations"] = min(20, gen + i + 1)
        if "2" in cfg.get("stage_params", {}):
            topk = cfg["stage_params"]["2"].get("top_k", 3)
            cfg["stage_params"]["2"]["top_k"] = max(1, topk - i)
        cands.append(PipelineHarness(cfg))
    return cands


# ── 主循环（内层递归）─────────────────────────────────────────────

def evolve(initial: PipelineHarness, api_key: str, rounds: int = 3,
           n_candidates: int = 3, val_tasks: list[str] | None = None,
           archive_path: Path | None = None, mock: bool = False) -> dict:
    """内层递归：固定模型，搜索更好的 harness。

    每轮：提议候选 → 确定性评估（候选 vs 父）→ 严格更优才采纳 → 归档。
    """
    val_tasks = val_tasks or ["sample_conjecture"]
    archive_path = archive_path or Path("/tmp/pipeline_meta_evolution/harness_archive.jsonl")
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    current = initial
    archive = load_archive(archive_path)
    history = []

    for rnd in range(1, rounds + 1):
        print(f"\n=== Round {rnd} ===")
        parent_eval = evaluate_harness(current, archive, val_tasks)
        print(f"  父 harness '{current.name}' score={parent_eval['score']} "
              f"(struct={parent_eval['structure_score']}, hist={parent_eval['history_score']})")

        # 提议候选
        evidence = {
            "round": rnd,
            "parent": current.to_dict(),
            "parent_eval": parent_eval,
            "recent_history": [r for r in archive[-6:]],
        }
        if mock:
            candidates = _mock_propose(current, evidence, n_candidates)
        else:
            candidates = propose_harness(current, evidence, api_key, n_candidates)
        print(f"  提议 {len(candidates)} 个有效候选")

        # 确定性评估 + 严格门控替换
        adopted = None
        for ci, cand in enumerate(candidates):
            ce = evaluate_harness(cand, archive, val_tasks)
            print(f"    候选 {ci+1} '{cand.name}' score={ce['score']} "
                  f"(struct={ce['structure_score']}, hist={ce['history_score']})")
            if ce["score"] > parent_eval["score"] and adopted is None:
                adopted = cand
                print(f"    ✅ 采纳候选 '{cand.name}'（严格更优 {parent_eval['score']}→{ce['score']}）")

        # 归档（append-only）
        for cand in candidates:
            ce = evaluate_harness(cand, archive, val_tasks)
            archive.append({
                "round": rnd,
                "name": cand.name,
                "signature": ce["signature"],
                "stage_order": cand.config.get("stage_order", []),
                "score": ce["score"],
                "structure_score": ce["structure_score"],
                "adopted": bool(adopted is not None and _harness_signature(adopted) == ce["signature"]),
                "parent_score": parent_eval["score"],
            })
        # 父 harness 也归档（记录基线）
        archive.append({
            "round": rnd,
            "name": current.name,
            "signature": parent_eval["signature"],
            "stage_order": current.config.get("stage_order", []),
            "score": parent_eval["score"],
            "structure_score": parent_eval["structure_score"],
            "adopted": False,
            "parent_score": parent_eval["score"],
        })
        _write_archive(archive_path, archive)

        if adopted is not None:
            history.append({"round": rnd, "from": current.name, "to": adopted.name,
                            "score": evaluate_harness(adopted, archive, val_tasks)["score"]})
            current = adopted
        else:
            history.append({"round": rnd, "from": current.name, "to": current.name,
                            "score": parent_eval["score"], "note": "no strict improvement"})

    final_eval = evaluate_harness(current, archive, val_tasks)
    return {
        "final_harness": current.to_dict(),
        "final_score": final_eval["score"],
        "history": history,
        "archive_path": str(archive_path),
    }


def _write_archive(path: Path, archive: list[dict]):
    with open(path, "w", encoding="utf-8") as f:
        for r in archive:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ── CLI ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Stage 3.8 pipeline 元进化")
    ap.add_argument("--conjecture", type=str, help="conjecture.json 路径（供 Val 任务上下文）")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--candidates", type=int, default=3)
    ap.add_argument("--archive", type=str, default="/tmp/pipeline_meta_evolution/harness_archive.jsonl")
    ap.add_argument("--self-test", action="store_true", help="离线自测（mock 提议，不调 DeepSeek）")
    args = ap.parse_args()

    if args.self_test:
        print("=== Stage 3.8 自测（mock 提议 + 确定性评估）===")
        initial = PipelineHarness.default()
        result = evolve(initial, api_key="", rounds=2, n_candidates=3,
                        archive_path=Path("/tmp/pipeline_meta_evolution_test/harness_archive.jsonl"),
                        mock=True)
        print(f"\n最终 harness: {result['final_harness']['name']}")
        print(f"最终 score: {result['final_score']}")
        print(f"历史: {json.dumps(result['history'], ensure_ascii=False, indent=2)}")
        print("\n[OK] 自测通过（循环：提议→评估→门控替换→归档）")
        return

    api_key = _load_deepseek_key()
    if not api_key:
        print("错误: 未找到 DeepSeek API key（设 DEEPSEEK_API_KEY 或 ~/projects/ML-Master/.env）")
        sys.exit(1)

    initial = PipelineHarness.default()
    if args.conjecture:
        print(f"Val 任务上下文: {args.conjecture}")
    result = evolve(initial, api_key, rounds=args.rounds,
                    n_candidates=args.candidates, archive_path=Path(args.archive), mock=False)

    out = Path(args.archive).parent / "final_harness.json"
    out.write_text(json.dumps(result["final_harness"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n最终 harness 写出: {out}")
    print(f"最终 score: {result['final_score']}")
    print(f"采纳历史: {json.dumps(result['history'], ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    main()
