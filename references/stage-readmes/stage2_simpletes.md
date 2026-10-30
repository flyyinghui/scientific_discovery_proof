# Stage 2 — SimpleTES: Candidate Ranking

**Structured Test-time Evaluation-driven Scaling for AI discovery.**

## Overview

Based on arXiv:2604.19341. SimpleTES provides a systematic framework for **(C, L, K, Φ)** evaluation-budget scaling across parallel chains, iterative refinement, and local candidate selection.

## Four Scaling Levers

| Lever | Parameter | Controls |
|:---|:---|---|
| **C** | `--num-chains` | Parallel independent exploration chains |
| **L** | depth per chain | Feedback-driven refinement iterations |
| **K** | `--k-candidates` | Local best-of-K selection — avoid weak commits |
| **Φ** | `--selector` | History-to-prompt compression policy |

## Selectors

| Selector | Style | Best for |
|:---|:---|---|
| `rpucg` | DAG-aware, γ-decay | Paper-style; strongest single selector |
| `balance` | Stratified sampling | Robust default |
| `llm_elite` | Bounded elite pool | LLM-managed per-chain population |

## Quick Start

```bash
export DEEPSEEK_API_KEY="sk-..."

python -m simpletes.main \
  --task "Find the optimal proof strategy for KLS conjecture" \
  --C 4 --L 5 --K 3 \
  --selector rpucg \
  --total-budget 500
```

## Integration with PPE-V5.1

Used as the outer orchestration layer for physics proof search:

```
SimpleTES (C=4 chains)
  ├─ chain 0: SU(6) path
  ├─ chain 1: SU(3,3) path
  ├─ chain 2: hybrid path
  └─ chain 3: ab initio path
       │
       ├─ Proposer: DeepSeek v4-flash (thinking)
       ├─ Evaluator: PPE-V5.1 + MathCode
       └─ Selector: rpucg (DAG-aware for Lean proofs)
```

## Dependencies

```bash
pip install openai numpy
```

## Reference

- **Paper**: arXiv:2604.19341 — "SimpleTES: Structured Test-time Evaluation-driven Scaling"
