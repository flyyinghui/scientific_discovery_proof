# Stage 3 — PPE-V5.1Hybrid: Deep Formal Proof

**Physics Proof Engine — unified formal proof pipeline for theoretical physics.**

## Overview

Six-phase pipeline:
1. **PreProof Audit** — engineering cybernetics diagnostic
2. **Brain Bridging** — 3-iteration neural memory (170K+ neurons)
3. **MCTS + ABC Discovery** — dual-algorithm proof search
4. **Dual Verification Gates** — MathCode formal + numerical validation
5. **Bayesian Verdict** — PyMC hierarchical evidence synthesis
6. **Auto Paper Generation** — Nature figures + academic writing

## J-space Bridge Matrix

Maps 170K+ brain neurons to a 12×12 concept correlation matrix, quantifying theoretical grounding:

| Concept | g_Ricci | g_KLS | g_Chern | g_WZW | p_M_R | p_m_nu | p_FRG | p_CGICE |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| g_KLS | 0.89 | — | — | — | — | — | — | — |
| g_Chern | 0.65 | 0.71 | — | 0.68 | — | — | 0.32 | 0.41 |
| p_M_R | 0.35 | 0.42 | 0.48 | 0.50 | — | 0.62 | 0.68 | 0.71 |
| p_m_nu | 0.12 | 0.18 | 0.22 | 0.25 | 0.62 | — | 0.72 | 0.68 |

**J-score thresholds**:
- > 0.70 → Direct Lean theorem (strong brain support)
- 0.50–0.70 → [honest-axiom] + numerical validation
- < 0.50 → [postulated] or reject

## Dual Algorithm Search

### MCTS (Monte Carlo Tree Search)
- 4 phases: Selection → Expansion → Simulation → Backpropagation
- UCB1 with brain J-score prior
- Effective branching factor: ~75% (with MAF 5-level filter)

### ABC (Artificial Bee Colony)
- Employed bees: exploit neighborhood of good proofs
- Onlooker bees: probabilistic selection by fitness
- Scout bees: random exploration of uncovered regions

## MathCode Verification

Three-tool verification pipeline:
- `axiom_checker`: validates axiom consistency
- `proof_stats`: theorem/lemma/strategy statistics
- `sorry_analyzer`: zero-sorry gate enforcement

## Stage 3.5 Consistency Audit (v2.1.0)

MathCode 三工具只"数数"（axiom/sorry 计数），不"查矛盾"。`proof_consistency_audit.py`
在证明完成后执行六类 P0 检测（见 `../references/formal-proof-consistency-audit.md`）：

| 缺陷类 | 严重度 |
|---|---|
| 公理自相矛盾（爆炸原理 X=Y vs X≠Y） | BLOCK |
| 表演性诚实（`-- @[honest_axiom]` 注释 vs 真实 attribute） | WARN |
| 公理/定理计数不一致 | WARN |
| 定理虚假声称（论文 "fully verified" vs Lean 缺失） | BLOCK |
| `:= by trivial` / `:= True` 空壳 | WARN |
| 离散谱 vs 非紧空间连续谱 | BLOCK |

```bash
python proof_consistency_audit.py \
  --lean proof.lean --paper paper.txt \
  --expected-axioms 14 --output audit.json
```

## Dependencies

```bash
pip install openai networkx numpy pymc
# Requires: Lean 4, MathCode V2, Neural Memory Brain
```

## See Also

- `jspace_bridge.py` — Bridge matrix computation utility
- `../references/papers.md` — Full methodology references
