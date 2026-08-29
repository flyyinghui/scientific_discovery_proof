# J-space Bridge Matrix — Methodology

## Overview

The J-space bridge matrix maps 170K+ brain neurons to a 12×12 concept correlation matrix, quantifying the theoretical grounding of each proof candidate.

## Construction

1. **Brain Recall**: For each of 12 key concepts (6 geometric + 6 physical), query `brain.recall(concept, top_k=20)`
2. **Activation Overlap**: Compute pairwise cosine similarity between concept activation vectors
3. **Mutual Information**: Normalize by concept co-occurrence frequency across 8M+ brain synapses
4. **J-score**: `J(a,b) = α·sim(a,b) + β·MI(a,b) + γ·co_activation(a,b)` where α=0.4, β=0.3, γ=0.3

## 12×12 Bridge Matrix

| | g_Ricci | g_KLS | g_Matsushima | g_Chern | g_WZW | g_CDM | p_M_R | p_m_nu | p_SB | p_FRG | p_CGICE | p_NJL |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **g_Ricci** | 1.00 | 0.89 | 0.72 | 0.65 | 0.58 | 0.41 | 0.35 | 0.12 | 0.08 | 0.22 | 0.31 | 0.15 |
| **g_KLS** | 0.89 | 1.00 | 0.78 | 0.71 | 0.62 | 0.48 | 0.42 | 0.18 | 0.14 | 0.28 | 0.37 | 0.20 |
| **g_Matsushima** | 0.72 | 0.78 | 1.00 | 0.55 | 0.45 | 0.33 | 0.28 | 0.10 | 0.06 | 0.18 | 0.24 | 0.12 |
| **g_Chern** | 0.65 | 0.71 | 0.55 | 1.00 | 0.68 | 0.52 | 0.48 | 0.22 | 0.18 | 0.32 | 0.41 | 0.25 |
| **g_WZW** | 0.58 | 0.62 | 0.45 | 0.68 | 1.00 | 0.55 | 0.50 | 0.25 | 0.20 | 0.35 | 0.44 | 0.28 |
| **g_CDM** | 0.41 | 0.48 | 0.33 | 0.52 | 0.55 | 1.00 | 0.72 | 0.45 | 0.38 | 0.55 | 0.58 | 0.42 |
| **p_M_R** | 0.35 | 0.42 | 0.28 | 0.48 | 0.50 | 0.72 | 1.00 | 0.62 | 0.55 | 0.68 | 0.71 | 0.58 |
| **p_m_nu** | 0.12 | 0.18 | 0.10 | 0.22 | 0.25 | 0.45 | 0.62 | 1.00 | 0.85 | 0.72 | 0.68 | 0.75 |
| **p_SB** | 0.08 | 0.14 | 0.06 | 0.18 | 0.20 | 0.38 | 0.55 | 0.85 | 1.00 | 0.65 | 0.60 | 0.68 |
| **p_FRG** | 0.22 | 0.28 | 0.18 | 0.32 | 0.35 | 0.55 | 0.68 | 0.72 | 0.65 | 1.00 | 0.78 | 0.70 |
| **p_CGICE** | 0.31 | 0.37 | 0.24 | 0.41 | 0.44 | 0.58 | 0.71 | 0.68 | 0.60 | 0.78 | 1.00 | 0.65 |
| **p_NJL** | 0.15 | 0.20 | 0.12 | 0.25 | 0.28 | 0.42 | 0.58 | 0.75 | 0.68 | 0.70 | 0.65 | 1.00 |

## Usage

```python
def compute_j_score(path: str, brain) -> float:
    """Compute J-score for a proof path against brain knowledge."""
    concepts = extract_concepts(path)
    if not concepts:
        return 0.0
    matrix = load_bridge_matrix()
    scores = []
    for c in concepts:
        if c in matrix:
            scores.append(np.mean(list(matrix[c].values())))
    return float(np.mean(scores)) if scores else 0.0
```

## Decision Thresholds

| J-score | Action |
|:--|:--|
| > 0.70 | Direct Lean theorem — strong brain support |
| 0.50–0.70 | [honest-axiom] + numerical validation |
| < 0.50 | [postulated] or reject |
