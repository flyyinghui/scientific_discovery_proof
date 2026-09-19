#!/usr/bin/env python3
"""
Curriculum Planner — Stage 2.5 课程规划器 (v2.8.0, from RSIAgent)
=================================================================
在 SimpleTES 候选排名 (Stage 2) 之后、PPE 形式化证明 (Stage 3) 之前，
生成「证明变体任务队列」，指导证明链的主动探索方向。

映射自 RSIAgent (arXiv:2609.15364) 的 Curriculum Agent：
  - 主动决定「下一步探索什么」，而非被动走固定证明管线
  - 生成前置技能 / 信息性变体 / 失败驱动练习 / 压力测试案例
  - 目标：在 PPE 证明前暴露隐藏约束、边界条件、未挑战假设

五大证明变体任务类型：
  1. weaken_premise     弱化前提 —— 移除一条 honest-axiom，检验定理是否仍成立
  2. strengthen_premise 强化前提 —— 增加边界条件，检验证明链鲁棒性
  3. boundary_case      边界反例 —— 主动搜索反例（对应 MAF 50K 反例的课程化）
  4. axiom_recombine    公理重组合 —— 不同 honest-axiom 子集组合（找最小充分集）
  5. stress_test        压力测试 —— 移除关键 axiom，确认定理坍塌（验证 axiom 必要性）

Usage:
  python curriculum_planner.py --conjecture conjecture.json \\
      [--ranked stage2_ranked_candidates.json] [--archive archive.jsonl] \\
      [--output stage25_curriculum.json] [--mock]
"""

import argparse, json, os, re, sys
from pathlib import Path
from datetime import datetime

# ── 证明变体任务模板 ────────────────────────────────────────

TASK_TEMPLATES = {
    "weaken_premise": (
        "Weakening premise: suppose {axiom} does NOT hold. Does {target} still follow? "
        "If yes, {axiom} is redundant (remove it); if no, {axiom} is load-bearing. "
        "Formalize the conditional theorem WITHOUT {axiom} and check 0-sorry."
    ),
    "strengthen_premise": (
        "Strengthening premise: add the boundary condition {condition} to {target}. "
        "Does the proof chain remain valid? Identify any hidden assumption that "
        "breaks when {condition} is enforced."
    ),
    "boundary_case": (
        "Boundary case: search for a counterexample to {target} at the boundary "
        "{boundary}. If a counterexample exists, {target} must be re-scoped to a "
        "conditional theorem; if none, record the boundary as verified."
    ),
    "axiom_recombine": (
        "Axiom recombination: find the minimal subset of honest-axioms that still "
        "implies {target}. Drop each axiom in turn and re-verify. Output the "
        "minimal sufficient axiom set."
    ),
    "stress_test": (
        "Stress test: remove the load-bearing axiom {axiom} and confirm {target} "
        "collapses (can no longer be proven). This verifies {axiom} is genuinely "
        "necessary, not a performative-honesty decoration."
    ),
}


def _load_api_key() -> str:
    for env_path in [
        '~/.hermes/.env',
        os.path.expanduser('~/.hermes/.env'),
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('DEEPSEEK_API_KEY='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('DEEPSEEK_API_KEY', '')


def _extract_axioms(conjecture: dict):
    """从 conjecture.json 提取 honest-axiom 列表。"""
    axioms = []
    for ax in conjecture.get('axioms', []):
        if isinstance(ax, dict):
            axioms.append({
                'id': ax.get('id', f"A{len(axioms)+1}"),
                'description': ax.get('description', ''),
            })
        else:
            axioms.append({'id': f"A{len(axioms)+1}", 'description': str(ax)})
    return axioms


def _load_archive(archive_path: str):
    """从 archive.jsonl 读取历史证据链（可选）。"""
    if not archive_path or not Path(archive_path).exists():
        return []
    entries = []
    with open(archive_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _mock_curriculum(conjecture: dict) -> list:
    """无 API key 时的确定性课程生成（基于模板 + 公理列表）。"""
    name = conjecture.get('name', 'conjecture')
    target = conjecture.get('target', conjecture.get('goal', 'main_result'))
    axioms = _extract_axioms(conjecture)
    if not axioms:
        axioms = [{'id': 'A1', 'description': 'core premise'}]

    tasks = []
    # 对每个公理生成 weaken_premise + stress_test（针对公理的必要性）
    for ax in axioms[:3]:  # 最多 3 个，避免爆炸
        tasks.append({
            'id': f"weaken_{ax['id'].lower()}",
            'type': 'weaken_premise',
            'axiom': ax['id'],
            'target': target,
            'instruction': TASK_TEMPLATES['weaken_premise'].format(
                axiom=ax['id'], target=target),
        })
        tasks.append({
            'id': f"stress_{ax['id'].lower()}",
            'type': 'stress_test',
            'axiom': ax['id'],
            'target': target,
            'instruction': TASK_TEMPLATES['stress_test'].format(
                axiom=ax['id'], target=target),
        })
    # 边界 + 强化 + 重组合（全局）
    tasks.append({
        'id': 'boundary_global',
        'type': 'boundary_case',
        'target': target,
        'boundary': 'degenerate parameter limit',
        'instruction': TASK_TEMPLATES['boundary_case'].format(
            target=target, boundary='degenerate parameter limit'),
    })
    tasks.append({
        'id': 'strengthen_global',
        'type': 'strengthen_premise',
        'target': target,
        'condition': 'non-degeneracy of the vacuum configuration',
        'instruction': TASK_TEMPLATES['strengthen_premise'].format(
            target=target, condition='non-degeneracy of the vacuum configuration'),
    })
    tasks.append({
        'id': 'recombine_minimal',
        'type': 'axiom_recombine',
        'target': target,
        'instruction': TASK_TEMPLATES['axiom_recombine'].format(target=target),
    })
    return tasks


def _llm_curriculum(conjecture: dict, ranked: dict, archive: list, api_key: str) -> list:
    """用 DeepSeek v4-flash 生成课程（结合排名 + 历史证据）。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 历史失败模式摘要（供课程规划器避开已知盲区）
    history_summary = []
    for e in archive[-20:]:
        history_summary.append({
            'mutation_strategy': e.get('mutation_strategy', e.get('strategy', '?')),
            'defects': e.get('defects_before', e.get('defects', [])),
            'success': e.get('success', e.get('accepted', False)),
        })

    prompt = (
        "You are the curriculum planner for a formal-proof pipeline. Given a physics "
        "conjecture, the ranked candidate proofs, and the historical repair evidence, "
        "propose a queue of proof-variant tasks that will expose hidden constraints, "
        "boundary conditions, and unchallenged assumptions BEFORE the formal proof runs.\n\n"
        "Conjecture:\n" + json.dumps(conjecture, ensure_ascii=False, indent=2) + "\n\n"
        "Ranked candidates:\n" + json.dumps(ranked, ensure_ascii=False, indent=2) + "\n\n"
        "Historical repair evidence (last 20):\n" + json.dumps(history_summary, ensure_ascii=False, indent=2) + "\n\n"
        "Return a JSON array of tasks. Each task must have:\n"
        "  - id: string\n"
        "  - type: one of weaken_premise | strengthen_premise | boundary_case | axiom_recombine | stress_test\n"
        "  - axiom: (optional) the axiom id being challenged\n"
        "  - target: the target theorem\n"
        "  - instruction: one-sentence concrete instruction\n"
        "Generate 5-8 tasks spanning all 5 types. Return ONLY the JSON array."
    )

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096, temperature=0.4,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = resp.choices[0].message.content
    if not text:
        return _mock_curriculum(conjecture)

    # 容错解析（brace-counting）
    s = text.find('[')
    e = text.rfind(']')
    if s < 0 or e < 0:
        return _mock_curriculum(conjecture)
    try:
        tasks = json.loads(text[s:e+1])
        if isinstance(tasks, list) and tasks:
            return tasks
    except json.JSONDecodeError:
        pass
    return _mock_curriculum(conjecture)


def plan(conjecture_path: str, ranked_path: str = None,
         archive_path: str = None, use_mock: bool = False) -> dict:
    """生成证明变体课程。返回 curriculum dict。"""
    conjecture = json.loads(Path(conjecture_path).read_text(encoding='utf-8'))

    ranked = {}
    if ranked_path and Path(ranked_path).exists():
        ranked = json.loads(Path(ranked_path).read_text(encoding='utf-8'))

    archive = _load_archive(archive_path) if archive_path else []

    api_key = _load_api_key()
    if use_mock or not api_key:
        tasks = _mock_curriculum(conjecture)
        mode = 'mock'
    else:
        try:
            tasks = _llm_curriculum(conjecture, ranked, archive, api_key)
            mode = 'llm'
        except Exception as e:
            print(f"[Curriculum] ⚠️ LLM 生成失败 ({e}) — 回退 mock 模板")
            tasks = _mock_curriculum(conjecture)
            mode = 'mock-fallback'

    curriculum = {
        'stage': 2.5,
        'name': 'Curriculum Planner',
        'source': 'RSIAgent (arXiv:2609.15364)',
        'mode': mode,
        'target': conjecture.get('target', conjecture.get('goal', 'main_result')),
        'n_tasks': len(tasks),
        'tasks': tasks,
        'timestamp': datetime.now().isoformat(),
    }
    return curriculum


def main():
    ap = argparse.ArgumentParser(description="Curriculum Planner (Stage 2.5, RSIAgent)")
    ap.add_argument('--conjecture', required=True, help='Path to conjecture.json')
    ap.add_argument('--ranked', default=None, help='Path to stage2_ranked_candidates.json')
    ap.add_argument('--archive', default=None, help='Path to archive.jsonl (historical evidence)')
    ap.add_argument('--output', default='/tmp/stage25_curriculum.json', help='Output JSON path')
    ap.add_argument('--mock', action='store_true', help='Use deterministic mock (no API)')
    args = ap.parse_args()

    curriculum = plan(args.conjecture, args.ranked, args.archive, args.mock)

    Path(args.output).write_text(json.dumps(curriculum, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Curriculum Planner (Stage 2.5, RSIAgent)")
    print("=" * 60)
    print(f"  mode={curriculum['mode']}  target={curriculum['target']}")
    print(f"  tasks={curriculum['n_tasks']}")
    for t in curriculum['tasks']:
        print(f"    [{t['type']}] {t['id']}: {t['instruction'][:70]}")
    print(f"\n  Output: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
