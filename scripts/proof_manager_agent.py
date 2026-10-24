#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3.9 — Proof Manager Agent（证明管理器 agent，P0 落地）

对齐 AI-Scientist（Nature 2026, Chris Lu / Cong Lu / Robert Tjarko Lange et al.
"Towards end-to-end automation of AI research"）的 Experiment Manager Agent
（AgentManager）：**跨阶段元协调器**。

核心缺口：scientific-discovery-proof 的 Stage 目前是固定顺序硬走
（−1→0→1→2→2.5→3→3.5→3.6→3.7→4），缺少一个「元层判断」——
「这个证明策略卡死了吗？该推进、重试、还是放弃？」之前只能靠固定
max_iterations 硬截断，没有 LLM 层面的「阶段是否完成 / 是否推进」判断。

AI-Scientist 的 AgentManager 用 LLM 做三个判断（FunctionSpec）：
  1. stage_config      —— 生成下一阶段配置（name/description/goals/max_iterations）
  2. stage_progress    —— 评估是否推进到下一阶段（ready_for_next_stage/reasoning/
                          recommendations/suggested_focus）
  3. stage_completion  —— 评估当前阶段是否完成（is_complete/missing_criteria）

映射到「证明型」四阶段（对应 AI-Scientist main_stage_dict 的元结构）：
  Stage 1: skeleton_implementation  骨架实现（编译可能失败）
  Stage 2: compile_fix             修复编译（达到 EXIT=0）
  Stage 3: sorry_reduction         减少 sorry/admit（达到 0）
  Stage 4: axiom_ablation          公理消融（达到 0 axiom）

阶段继承（AI-Scientist「best_implementation 传递」）：stage N+1 用 stage N 的
最佳证明作为 base——对应「证明骨架 → 完整证明」的增量深化，与 Stage 3 的
三阶段脚手架（Scaffolding→Transition→Full-Scale）互补（后者是单 stage 内的
生成口径，本模块是跨 stage 的推进判断）。

诚实边界：
  1. LLM 只**建议**（is_complete / ready_for_next_stage / abandon），最终通过由
     **确定性黄金门控**决定：编译 EXIT==0 + sorry_count==0 + axiom_count==0
     + 物理内容审计非平凡（physical_content_audit 无 BLOCK）。LLM 判断的是
     「是否值得继续投入 + 该往哪走」，不是「证明是否成立」。
  2. 本模块不替代 Stage 3.5 一致性审计 / 3.6 冻结评估器 / 3.7 策略优化器——
     它是它们的「元层协调器」，决定什么时候调用它们、调用多少轮、何时放弃。
  3. 四阶段是「证明型」语义（骨架/编译/减 sorry/消融），与 AI-Scientist 的
     「实验型」四阶段（baseline_tuning/creative_research）语义不同——只移植
     「阶段化 + 继承 + LLM 推进判断」的元结构，不移植 ML 实验的 goal 文案。
  4. 放弃判断（abandon）是诚实降级：达到 max_iterations 且无实质进展时，
     建议放弃或重标定猜想，而非硬走到底浪费预算。

用法：
  python proof_manager_agent.py --state stage36_report.json --output manager_decision.json
  python proof_manager_agent.py --self-test    # 离线自测（确定性门控 + mock LLM 决策）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── 证明四阶段（映射 AI-Scientist main_stage_dict）────────────────

PROOF_STAGES = {
    1: {
        "name": "skeleton_implementation",
        "goal": (
            "Produce a working proof skeleton: state the main target theorem and "
            "the honest-axioms it depends on. Compilation MAY still fail at this stage."
        ),
        "done_when": "skeleton exists (theorem statement + axiom list present)",
        "metric": "skeleton_present",
    },
    2: {
        "name": "compile_fix",
        "goal": (
            "Fix all compilation errors until the Lean file compiles with EXIT=0. "
            "Do NOT yet worry about sorry/admit count."
        ),
        "done_when": "compiles (EXIT=0)",
        "metric": "exit_code == 0",
    },
    3: {
        "name": "sorry_reduction",
        "goal": (
            "Eliminate every sorry/admit/trivial stub until sorry_count == 0. "
            "Each remaining gap becomes an honest-axiom with a literature citation."
        ),
        "done_when": "sorry_count == 0 and admit_count == 0",
        "metric": "sorry_count == 0",
    },
    4: {
        "name": "axiom_ablation",
        "goal": (
            "Ablate every research-grade axiom to a conditional theorem or remove it, "
            "until axiom_count == 0 and #print axioms shows only the classical triad "
            "(propext / Classical.choice / Quot.sound)."
        ),
        "done_when": "axiom_count == 0 (golden gate: classical triad only)",
        "metric": "axiom_count == 0",
    },
}

# 黄金门控（确定性，LLM 无权绕过）
GOLDEN_GATE = {
    "compile": "exit_code == 0",
    "no_sorry": "sorry_count == 0",
    "no_admit": "admit_count == 0",
    "no_axiom": "axiom_count == 0",
    "non_trivial": "physical_content_audit has no BLOCK",
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


def _parse_json_field(text: str, key: str):
    """从 LLM 返回文本容错提取某字段（先整段 JSON，再正则兜底）。"""
    if not text:
        return None
    s = text.find('{')
    e = text.rfind('}')
    if s >= 0 and e > s:
        try:
            obj = json.loads(text[s:e + 1])
            if key in obj:
                return obj[key]
        except json.JSONDecodeError:
            pass
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*("[^"]*"|true|false|\d+)', text)
    if m:
        v = m.group(1)
        if v == 'true':
            return True
        if v == 'false':
            return False
        return v.strip('"')
    return None


# ── 确定性门控（最终判定，非 LLM）────────────────────────────────

def golden_gate_verdict(state: dict) -> tuple[bool, list[str]]:
    """根据证明状态做确定性门控：返回 (全部通过, 未通过的 gate 列表)。"""
    failed = []
    if state.get("exit_code") != 0:
        failed.append(GOLDEN_GATE["compile"])
    if state.get("sorry_count", 1) != 0:
        failed.append(GOLDEN_GATE["no_sorry"])
    if state.get("admit_count", 1) != 0:
        failed.append(GOLDEN_GATE["no_admit"])
    if state.get("axiom_count", 1) != 0:
        failed.append(GOLDEN_GATE["no_axiom"])
    if state.get("physical_content_block", False):
        failed.append(GOLDEN_GATE["non_trivial"])
    return (len(failed) == 0, failed)


def infer_stage(state: dict) -> int:
    """根据证明状态推断当前处于哪个证明阶段（确定性，非 LLM）。"""
    if not state.get("skeleton_present", False):
        return 1
    if state.get("exit_code") != 0:
        return 2
    if state.get("sorry_count", 1) != 0 or state.get("admit_count", 1) != 0:
        return 3
    if state.get("axiom_count", 1) != 0 or state.get("physical_content_block", False):
        return 4
    return 5  # 全通过（超出四阶段 = 完成）


# ── 确定性 mock 决策（无 API key 时的回退）───────────────────────

def _mock_decision(state: dict) -> dict:
    """确定性 mock：按「阶段 → 无进展迭代数」推决策，不调 LLM。"""
    stage = infer_stage(state)
    iters = state.get("iterations_in_stage", 0)
    max_iters = state.get("max_iterations", 10)
    stage_cfg = PROOF_STAGES.get(stage, PROOF_STAGES[4])

    # 无进展迭代数 = 当前 stage 内迭代数（简化口径）
    stalled = iters >= max_iters

    if stage == 5:
        return {
            "action": "advance_to_stage_4_paper",
            "ready_for_next_stage": True,
            "reasoning": "Golden gate fully satisfied: compiles, 0 sorry/admit/axiom, non-trivial.",
            "recommendations": ["Proceed to Stage 4 paper generation."],
        }
    if stalled:
        return {
            "action": "abandon_or_rescope",
            "ready_for_next_stage": False,
            "reasoning": (
                f"Stalled {iters} iterations in stage {stage} "
                f"({stage_cfg['name']}) with no golden-gate progress. "
                "Recommend rescoping the conjecture or abandoning this proof path."
            ),
            "recommendations": [
                "Rescope the target to a weaker conditional theorem",
                "or abandon and try an alternative proof strategy (see strategy_explorer.py).",
            ],
        }
    return {
        "action": "retry_current_stage",
        "ready_for_next_stage": False,
        "reasoning": (
            f"Stage {stage} ({stage_cfg['name']}) not yet complete: "
            f"{stage_cfg['metric']} unsatisfied. Continue with a focused repair."
        ),
        "recommendations": [
            f"Focus on: {stage_cfg['goal']}",
        ],
    }


# ── LLM 决策（deepseek-flash，thinking disabled）──────────────────

def _llm_decision(state: dict, api_key: str) -> dict:
    """用 deepseek-flash 做跨阶段元判断（三个 eval 合一）。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    stage = infer_stage(state)
    stage_cfg = PROOF_STAGES.get(stage, PROOF_STAGES[4])
    gated, failed = golden_gate_verdict(state)

    prompt = (
        "You are the proof-manager agent (Experiment Manager analog) for a formal-proof "
        "pipeline. Given the current proof state, decide the next action. You may only "
        "ADVISE — the final accept/reject is decided by the deterministic golden gate "
        "(compile EXIT=0 + 0 sorry/admit/axiom + non-trivial physical content).\n\n"
        "Current proof state:\n" + json.dumps(state, ensure_ascii=False, indent=2) + "\n\n"
        f"Inferred proof stage: {stage} ({stage_cfg['name']})\n"
        f"Stage goal: {stage_cfg['goal']}\n"
        f"Stage done-when: {stage_cfg['done_when']}\n"
        f"Golden gate passed: {gated}\n"
        f"Golden gate still failing: {failed}\n\n"
        "Return a JSON object with exactly these keys:\n"
        "  - ready_for_next_stage: boolean\n"
        "  - action: one of retry_current_stage | advance_to_next_stage | "
        "abandon_or_rescope | advance_to_stage_4_paper\n"
        "  - reasoning: 1-2 sentence justification\n"
        "  - recommendations: array of 1-3 concrete strings\n"
        "  - suggested_focus: one string naming the single most important gap to close\n"
        "Return ONLY the JSON object."
    )

    resp = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048, temperature=0.3,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = resp.choices[0].message.content
    if not text:
        return _mock_decision(state)

    decision = {
        "ready_for_next_stage": bool(_parse_json_field(text, "ready_for_next_stage")),
        "action": _parse_json_field(text, "action") or "retry_current_stage",
        "reasoning": _parse_json_field(text, "reasoning") or "",
        "recommendations": _parse_json_field(text, "recommendations") or [],
        "suggested_focus": _parse_json_field(text, "suggested_focus") or "",
    }
    # 黄金门控是硬顶：LLM 不能因「推进」就放行未过门控的证明
    if not gated and decision.get("action") in ("advance_to_stage_4_paper",):
        decision["action"] = "retry_current_stage"
        decision["reasoning"] += " [overridden by golden gate: still failing " + ", ".join(failed) + "]"
    return decision


# ── 主决策函数 ────────────────────────────────────────────────────

def decide(state: dict, use_mock: bool = False) -> dict:
    """核心：给定证明状态，返回跨阶段元决策。"""
    stage = infer_stage(state)
    gated, failed = golden_gate_verdict(state)

    api_key = _load_api_key()
    if use_mock or not api_key:
        decision = _mock_decision(state)
        mode = 'mock'
    else:
        try:
            decision = _llm_decision(state, api_key)
            mode = 'llm'
        except Exception as e:
            print(f"[ProofManager] ⚠️ LLM 决策失败 ({e}) — 回退 mock")
            decision = _mock_decision(state)
            mode = 'mock-fallback'

    # 黄金门控是最终权威：无论 LLM/mock 说什么，未过门控不得 advance_to_stage_4
    if not gated and decision.get("action") == "advance_to_stage_4_paper":
        decision["action"] = "retry_current_stage"
        decision["reasoning"] = "Golden gate not satisfied: " + ", ".join(failed)

    return {
        "stage": 3.9,
        "name": "Proof Manager Agent",
        "source": "AI-Scientist (Nature 2026, Towards end-to-end automation of AI research)",
        "mode": mode,
        "inferred_stage": stage,
        "inferred_stage_name": PROOF_STAGES.get(stage, {}).get("name", "complete"),
        "golden_gate": {"passed": gated, "failing": failed},
        "decision": decision,
        "stage_inheritance": {
            "description": "stage N+1 inherits stage N best proof as base (AI-Scientist best_implementation passing)",
            "next_stage_base": PROOF_STAGES.get(stage + 1, {}).get("name", "none"),
        },
        "timestamp": datetime.now().isoformat(),
    }


# ── 离线自测 ──────────────────────────────────────────────────────

def self_test() -> int:
    """离线自测：验证四阶段推断 + 黄金门控 + mock 决策的一致性。"""
    cases = [
        # (name, state, expected_stage, expected_gate_passed, expected_action)
        ("no skeleton", {"skeleton_present": False, "exit_code": 1, "sorry_count": 5,
                         "admit_count": 2, "axiom_count": 3, "physical_content_block": False,
                         "iterations_in_stage": 1, "max_iterations": 10}, 1, False, "retry_current_stage"),
        ("compiles but has sorry", {"skeleton_present": True, "exit_code": 0, "sorry_count": 3,
                                    "admit_count": 1, "axiom_count": 2, "physical_content_block": False,
                                    "iterations_in_stage": 2, "max_iterations": 10}, 3, False, "retry_current_stage"),
        ("0 sorry but has axiom", {"skeleton_present": True, "exit_code": 0, "sorry_count": 0,
                                   "admit_count": 0, "axiom_count": 5, "physical_content_block": False,
                                   "iterations_in_stage": 1, "max_iterations": 10}, 4, False, "retry_current_stage"),
        ("golden gate full pass", {"skeleton_present": True, "exit_code": 0, "sorry_count": 0,
                                   "admit_count": 0, "axiom_count": 0, "physical_content_block": False,
                                   "iterations_in_stage": 0, "max_iterations": 10}, 5, True, "advance_to_stage_4_paper"),
        ("stalled in stage 2", {"skeleton_present": True, "exit_code": 1, "sorry_count": 2,
                                "admit_count": 1, "axiom_count": 3, "physical_content_block": False,
                                "iterations_in_stage": 11, "max_iterations": 10}, 2, False, "abandon_or_rescope"),
        ("content trivial despite 0 sorry", {"skeleton_present": True, "exit_code": 0, "sorry_count": 0,
                                             "admit_count": 0, "axiom_count": 0, "physical_content_block": True,
                                             "iterations_in_stage": 3, "max_iterations": 10}, 4, False, "retry_current_stage"),
    ]

    all_ok = True
    for name, state, exp_stage, exp_gate, exp_action in cases:
        stage = infer_stage(state)
        gated, _ = golden_gate_verdict(state)
        decision = _mock_decision(state)
        ok = (stage == exp_stage and gated == exp_gate
              and decision["action"] == exp_action)
        if not ok:
            all_ok = False
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: "
              f"stage={stage}(exp {exp_stage}) gate={gated}(exp {exp_gate}) "
              f"action={decision['action']}(exp {exp_action})")

    print("\n" + ("✅ 全部自测通过" if all_ok else "❌ 存在失败用例"))
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Proof Manager Agent (Stage 3.9, AI-Scientist P0)")
    ap.add_argument('--state', default=None, help='Path to proof-state JSON')
    ap.add_argument('--output', default='/tmp/manager_decision.json', help='Output JSON path')
    ap.add_argument('--mock', action='store_true', help='Use deterministic mock (no API)')
    ap.add_argument('--self-test', action='store_true', help='Run offline self-test and exit')
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not args.state or not Path(args.state).exists():
        print("❌ 需要 --state <proof-state.json>（或 --self-test）")
        return 1

    state = json.loads(Path(args.state).read_text(encoding='utf-8'))
    result = decide(state, args.mock)

    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))

    d = result["decision"]
    print("=" * 60)
    print("Proof Manager Agent (Stage 3.9, AI-Scientist P0)")
    print("=" * 60)
    print(f"  mode={result['mode']}  inferred_stage={result['inferred_stage']} "
          f"({result['inferred_stage_name']})")
    print(f"  golden_gate.passed={result['golden_gate']['passed']} "
          f"failing={result['golden_gate']['failing']}")
    print(f"  action={d['action']}  ready={d.get('ready_for_next_stage')}")
    print(f"  reasoning: {d['reasoning'][:120]}")
    for r in (d.get('recommendations') or []):
        print(f"    → {r}")
    print(f"\n  Output: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
