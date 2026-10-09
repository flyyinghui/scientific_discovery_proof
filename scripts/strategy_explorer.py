#!/usr/bin/env python3
"""
Strategy Explorer — Stage 0.5 证明策略探索 (v2.11.0, from Stellar Colosseum)
============================================================================
在 MAF 符号审计 (Stage 0) 之前，探索替代证明策略 + readiness gate 选路，
而非锁定第一个可行想法。映射自 Colosseum (arXiv:2609.15983) 的
Strategy Exploration and Readiness (4.2.1)。

每条策略候选包含（Colosseum typed schema）：
  - mechanism          ：核心约化/机制（重构、约化、中间目标、已知结果关联）
  - required_lemmas    ：所需中间引理
  - expected_bottleneck：预期主要技术难点
  - falsifiable_test   ：可证伪测试（如何判断该路线走不通）

Readiness Gate 判断路线是否「成熟到可分解」（Colosseum 4.2.1 三条件）：
  1. 中心约化/机制是否稳定
  2. 未决声明是否精确到可指派给证明 section
  3. 是否无未决桥接会改变目标或证明架构
输出每条策略的 readiness 评分 + 排序，选最成熟的路线喂给 Stage 3。

Usage:
  python strategy_explorer.py --conjecture conjecture.json \
      [--paper paper.txt] [--output stage05_strategies.json] [--mock]
"""

import argparse, json, os, re, sys
from pathlib import Path
from datetime import datetime


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
    """提取猜想的关键信息。"""
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


# ── mock 策略（无 API 时的确定性候选） ────────────────────────

def _mock_strategies(conj: dict) -> list:
    target = conj['target']
    axioms = conj['axioms'] or ['core premise']
    return [
        {
            'id': 'route_1_direct',
            'mechanism': f'Direct derivation of {target} from the stated axioms via algebraic manipulation',
            'required_lemmas': ['intermediate identity', 'monotonicity bound'],
            'expected_bottleneck': 'the central algebraic identity may not close',
            'falsifiable_test': f'SymPy cannot reduce LHS-RHS of {target} to 0 under {axioms[0]}',
        },
        {
            'id': 'route_2_reduction',
            'mechanism': f'Reduction of {target} to a known theorem by a change of variables',
            'required_lemmas': ['the reduction map', 'the known theorem statement'],
            'expected_bottleneck': 'reduction map may not preserve the key invariant',
            'falsifiable_test': 'the reduction map fails to be well-defined on the domain',
        },
        {
            'id': 'route_3_constructive',
            'mechanism': f'Constructive existence argument for the object behind {target}',
            'required_lemmas': ['existence lemma', 'uniqueness lemma'],
            'expected_bottleneck': 'existence requires a compactness/choice argument',
            'falsifiable_test': 'a counterexample construction defeats the existence claim',
        },
    ]


# ── LLM 策略生成 + readiness gate ────────────────────────────

def _llm_strategies(conj: dict, api_key: str, paper: str) -> list:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    prompt = (
        "You are a proof-strategy explorer for a formal-proof pipeline. Given a physics "
        "conjecture, propose 3-5 DISTINCT proof routes (reformulations, reductions, "
        "intermediate targets, connections to known results). Do NOT draft the proof; "
        "expose what each route would require and where the difficulty lies.\n\n"
        "Conjecture summary:\n" + json.dumps(conj, ensure_ascii=False, indent=2) + "\n\n"
        + (("Paper context (abstract/claims):\n" + paper[:2000] + "\n\n") if paper else "")
        + "Return a JSON array. Each route must have:\n"
        "  - id: string\n"
        "  - mechanism: one-sentence core reduction/approach\n"
        "  - required_lemmas: array of strings (intermediate claims needed)\n"
        "  - expected_bottleneck: one sentence on the main technical difficulty\n"
        "  - falsifiable_test: one sentence on how to tell this route is wrong\n"
        "Return ONLY the JSON array."
    )

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096, temperature=0.6,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = resp.choices[0].message.content or ""
    s, e = text.find('['), text.rfind(']')
    if s < 0 or e < 0:
        return _mock_strategies(conj)
    try:
        routes = json.loads(text[s:e+1])
        if isinstance(routes, list) and routes:
            return routes
    except json.JSONDecodeError:
        pass
    return _mock_strategies(conj)


def _readiness_gate(strategies: list, api_key: str) -> list:
    """给每条策略打分 readiness（0-1）。无 API 时用确定性启发式。"""
    # 确定性启发式：机制描述越具体（含约化/引理/反例测试），readiness 越高
    def heuristic(s):
        score = 0.3
        mech = s.get('mechanism', '')
        if re.search(r'reduc|reformulat|construct|change of variable|known theorem', mech, re.I):
            score += 0.2
        if s.get('required_lemmas'):
            score += 0.2
        if s.get('expected_bottleneck'):
            score += 0.15
        if s.get('falsifiable_test'):
            score += 0.15
        return round(min(score, 0.95), 2)

    if not api_key:
        for s in strategies:
            s['readiness'] = heuristic(s)
            s['ready'] = s['readiness'] >= 0.6
        return strategies

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    prompt = (
        "You are a readiness gate for proof decomposition. Score each candidate proof route "
        "on whether it is concrete enough to DECOMPOSE into section-level subproblems. "
        "A route is READY when: (1) its central reduction/mechanism is stable, "
        "(2) its unresolved claims are precise enough to assign to proof sections, "
        "(3) no unresolved bridge is likely to change the target or architecture. "
        "Score readiness 0.0-1.0 per route (NOT whether the proof is complete).\n\n"
        "Routes:\n" + json.dumps(strategies, ensure_ascii=False, indent=2) + "\n\n"
        'Return a JSON object: {"scores": {"route_id": 0.0-1.0, ...}}'
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024, temperature=0.2,
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = resp.choices[0].message.content or ""
        m = re.search(r'\{.*\}', text, re.S)
        scores = json.loads(m.group(0)).get('scores', {}) if m else {}
    except Exception:
        scores = {}

    for s in strategies:
        rid = s.get('id', '')
        s['readiness'] = round(float(scores.get(rid, heuristic(s))), 2)
        s['ready'] = s['readiness'] >= 0.6
    return strategies


def explore(conjecture_path: str, paper_path: str = None, use_mock: bool = False) -> dict:
    conjecture = json.loads(Path(conjecture_path).read_text(encoding='utf-8'))
    conj = _conjecture_summary(conjecture)

    paper = ''
    if paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding='utf-8', errors='replace')

    api_key = _load_api_key()
    if use_mock or not api_key:
        strategies = _mock_strategies(conj)
        mode = 'mock'
    else:
        try:
            strategies = _llm_strategies(conj, api_key, paper)
            mode = 'llm'
        except Exception as e:
            print(f"[StrategyExplorer] ⚠️ LLM 生成失败 ({e}) — 回退 mock")
            strategies = _mock_strategies(conj)
            mode = 'mock-fallback'

    strategies = _readiness_gate(strategies, '' if use_mock else api_key)
    strategies.sort(key=lambda s: s.get('readiness', 0), reverse=True)

    result = {
        'stage': 0.5,
        'name': 'Strategy Explorer',
        'source': 'Stellar Colosseum (arXiv:2609.15983)',
        'mode': mode,
        'target': conj['target'],
        'n_strategies': len(strategies),
        'strategies': strategies,
        'selected': strategies[0] if strategies else None,
        'timestamp': datetime.now().isoformat(),
    }
    return result


def main():
    ap = argparse.ArgumentParser(description="Strategy Explorer (Stage 0.5, Colosseum)")
    ap.add_argument('--conjecture', required=True, help='Path to conjecture.json')
    ap.add_argument('--paper', default=None, help='Paper text (optional context)')
    ap.add_argument('--output', default='/tmp/stage05_strategies.json')
    ap.add_argument('--mock', action='store_true', help='Use deterministic mock (no API)')
    args = ap.parse_args()

    result = explore(args.conjecture, args.paper, args.mock)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Strategy Explorer (Stage 0.5, Colosseum)")
    print("=" * 60)
    print(f"  mode={result['mode']}  target={result['target']}")
    print(f"  strategies={result['n_strategies']}")
    for s in result['strategies']:
        mark = '✅' if s.get('ready') else '⏳'
        print(f"    {mark} {s['id']}  readiness={s.get('readiness')}  {s['mechanism'][:50]}")
    print(f"\n  Selected: {result['selected']['id'] if result['selected'] else 'None'}")
    print(f"  Output: {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
