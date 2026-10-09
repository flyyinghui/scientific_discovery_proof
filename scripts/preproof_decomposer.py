#!/usr/bin/env python3
"""
Pre-Proof Decomposer — Stage 2.7 前向证明分解 (v2.11.0, from Stellar Colosseum)
==============================================================================
在 PPE 形式化证明 (Stage 3) 之前，把猜想分解为「编号 section 骨架 + 依赖 DAG」，
使 Stage 3 能按依赖顺序并行生成各 section 的 Lean 片段，失败 section 局部重试。
映射自 Colosseum (arXiv:2609.15983) 的 Decomposition and Parallel Proof
Construction (4.2.2)。

与 Stage 3.5c `proof_dag_audit.py`（证明后 backward 提取 DAG）互补：
本脚本是**前向**分解——证明前生成 section 骨架 + 依赖图，指导并行求解。

输出：
  - sections          ：编号 section 子问题（含数学内容 + 依赖）
  - dependency_graph  ：{section_id: [依赖的 section_id]}
  - parallel_batches  ：拓扑排序后的可并行批次（每批内依赖已满足，可并行求解）
  - skeleton          ：proof skeleton 文本（供 Stage 3 脚手架）

Usage:
  python preproof_decomposer.py --conjecture conjecture.json \
      [--strategy stage05_strategies.json] [--output stage27_decomposition.json] [--mock]
"""

import argparse, json, os, re, sys
from pathlib import Path
from datetime import datetime
from collections import deque


def _load_api_key() -> str:
    for env_path in [
        '.env',
        os.path.expanduser('~/.hermes/.env'),
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('DEEPSEEK_API_KEY='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('DEEPSEEK_API_KEY', '')


def _conjecture_summary(conjecture: dict) -> dict:
    axioms = []
    for ax in conjecture.get('axioms', []):
        if isinstance(ax, dict):
            axioms.append(ax.get('id', '') + ': ' + ax.get('description', ''))
        else:
            axioms.append(str(ax))
    return {
        'name': conjecture.get('name', 'conjecture'),
        'target': conjecture.get('target', conjecture.get('goal', 'main_result')),
        'axioms': axioms[:20],
        'description': conjecture.get('description', conjecture.get('statement', ''))[:800],
    }


def _load_strategy(strategy_path: str) -> dict:
    if not strategy_path or not Path(strategy_path).exists():
        return {}
    data = json.loads(Path(strategy_path).read_text(encoding='utf-8'))
    sel = data.get('selected') or (data.get('strategies', [])[0] if data.get('strategies') else {})
    return sel


def _mock_decompose(conj: dict, strategy: dict) -> list:
    """确定性分解：标准三段骨架（前提 → 中间引理 → 目标）。"""
    target = conj['target']
    mechanism = strategy.get('mechanism', f'derivation of {target}')
    lemmas = strategy.get('required_lemmas', ['intermediate lemma'])
    sections = [
        {
            'id': 'S1', 'title': 'Setup and notation',
            'content': f'Fix all variables and state the standing assumptions. '
                       f'Declare the honest-axioms needed for {target}.',
            'depends_on': [],
            'reusability': 'low',
        },
    ]
    for i, lem in enumerate(lemmas, start=2):
        sections.append({
            'id': f'S{i}', 'title': f'Intermediate lemma: {lem}',
            'content': f'Establish {lem} using the setup of S1.',
            'depends_on': ['S1'],
            'reusability': 'high',
        })
    sections.append({
        'id': f'S{len(sections)+1}', 'title': f'Main result: {target}',
        'content': f'Assemble the lemmas to prove {target} via {mechanism}.',
        'depends_on': [s['id'] for s in sections[1:]],
        'reusability': 'high',
    })
    return sections


def _llm_decompose(conj: dict, strategy: dict, api_key: str) -> list:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    prompt = (
        "You are a proof decomposer for a formal-proof pipeline. Turn the selected proof "
        "strategy into a numbered, SECTIONED proof skeleton. Each section is a subproblem "
        "with the mathematical content it must establish. Specify dependency edges "
        "(which completed sections each section may use). Document order = exposition; "
        "dependency graph = work order.\n\n"
        "Conjecture:\n" + json.dumps(conj, ensure_ascii=False, indent=2) + "\n\n"
        "Selected strategy:\n" + json.dumps(strategy, ensure_ascii=False, indent=2) + "\n\n"
        "Return a JSON array of sections. Each section must have:\n"
        "  - id: string (S1, S2, ...)\n"
        "  - title: short title\n"
        "  - content: the mathematical content to establish there\n"
        "  - depends_on: array of section ids it may use\n"
        "  - reusability: 'high' (reusable core lemma another proof could import), "
        "'medium' (useful but narrow), or 'low' (bookkeeping step — should be rare)\n"
        "Sections must form a DAG (no cycles).\n"
        "REDUCTION REUSE RULE (prove2me): decompose into REUSABLE core lemmas, not trivial "
        "steps. A bare 'have ... exact ...' transfer is NOT a section. Each section must be a "
        "self-contained, mathematically meaningful result. Over-decomposing into trivial "
        "non-reusable lemmas creates overhead and is discouraged. Return ONLY the JSON array."
    )

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096, temperature=0.4,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = resp.choices[0].message.content or ""
    s, e = text.find('['), text.rfind(']')
    if s < 0 or e < 0:
        return _mock_decompose(conj, strategy)
    try:
        sections = json.loads(text[s:e+1])
        if isinstance(sections, list) and sections:
            return sections
    except json.JSONDecodeError:
        pass
    return _mock_decompose(conj, strategy)


def _topological_batches(sections: list) -> list:
    """按依赖图拓扑排序，产出可并行批次（每批内依赖已满足）。"""
    ids = [s['id'] for s in sections]
    deps = {s['id']: set(s.get('depends_on', [])) for s in sections}
    # 只保留已知 section 的依赖（忽略外部）
    for k in deps:
        deps[k] = {d for d in deps[k] if d in ids}

    batches = []
    remaining = set(ids)
    while remaining:
        # 依赖已全部满足的 section
        ready = sorted([sid for sid in remaining if not (deps[sid] & remaining)])
        if not ready:
            # 环或悬空依赖：兜底全部加入
            ready = sorted(remaining)
        batches.append(ready)
        remaining -= set(ready)
    return batches


def decompose(conjecture_path: str, strategy_path: str = None,
              use_mock: bool = False) -> dict:
    conjecture = json.loads(Path(conjecture_path).read_text(encoding='utf-8'))
    conj = _conjecture_summary(conjecture)
    strategy = _load_strategy(strategy_path)

    api_key = _load_api_key()
    if use_mock or not api_key:
        sections = _mock_decompose(conj, strategy)
        mode = 'mock'
    else:
        try:
            sections = _llm_decompose(conj, strategy, api_key)
            mode = 'llm'
        except Exception as e:
            print(f"[Decomposer] ⚠️ LLM 生成失败 ({e}) — 回退 mock")
            sections = _mock_decompose(conj, strategy)
            mode = 'mock-fallback'

    dep_graph = {s['id']: s.get('depends_on', []) for s in sections}
    batches = _topological_batches(sections)

    # proof skeleton 文本
    skeleton_lines = ["-- Proof skeleton (Stage 2.7, Colosseum forward decomposition)", ""]
    for s in sections:
        dep = ', '.join(s.get('depends_on', [])) or '(none)'
        skeleton_lines.append(f"-- {s['id']} [{s.get('title','')}]  depends_on: {dep}")
        skeleton_lines.append(f"--   {s.get('content','')}")
        skeleton_lines.append("")

    result = {
        'stage': 2.7,
        'name': 'Pre-Proof Decomposer',
        'source': 'Stellar Colosseum (arXiv:2609.15983)',
        'mode': mode,
        'target': conj['target'],
        'strategy': strategy.get('id', 'none'),
        'n_sections': len(sections),
        'reusability_distribution': {
            level: sum(1 for s in sections if s.get('reusability') == level)
            for level in ('high', 'medium', 'low')
        },
        'sections': sections,
        'dependency_graph': dep_graph,
        'parallel_batches': batches,
        'skeleton': '\n'.join(skeleton_lines),
        'timestamp': datetime.now().isoformat(),
    }
    return result


def main():
    ap = argparse.ArgumentParser(description="Pre-Proof Decomposer (Stage 2.7, Colosseum)")
    ap.add_argument('--conjecture', required=True, help='Path to conjecture.json')
    ap.add_argument('--strategy', default=None, help='Path to stage05_strategies.json (selected route)')
    ap.add_argument('--output', default='/tmp/stage27_decomposition.json')
    ap.add_argument('--mock', action='store_true', help='Use deterministic mock (no API)')
    args = ap.parse_args()

    result = decompose(args.conjecture, args.strategy, args.mock)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Pre-Proof Decomposer (Stage 2.7, Colosseum)")
    print("=" * 60)
    print(f"  mode={result['mode']}  target={result['target']}  strategy={result['strategy']}")
    print(f"  sections={result['n_sections']}")
    print(f"  parallel_batches={result['parallel_batches']}")
    print(f"\n  Skeleton:")
    for s in result['sections']:
        dep = ', '.join(s.get('depends_on', [])) or '(none)'
        print(f"    {s['id']} [{s.get('title','')}] <- {dep}")
    print(f"\n  Output: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
