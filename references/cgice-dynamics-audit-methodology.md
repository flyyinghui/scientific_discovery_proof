# CGICE Dynamics "Name-Borrowing" Detection Methodology

**Validated**: 2026-08-07 | V63×V17×V16 CGICE unified review

## Problem

Papers claim to be based on "CGICE dynamics" or "CGICE 4-SDE system" but only implement a tiny fraction of the framework — typically just a single beta-function correction term. The paper title, abstract, and introduction use the full CGICE name to claim dynamical depth, while the actual code/Lean only contains a projection.

## 4-Step Detection Procedure

### Step 1: List All Claimed Equations

Extract every equation that the paper CLAIMS to implement. For CGICE, the standard 4-SDE system is:

| Equation | Name | Component |
|:--:|------|------|
| CGICE-1 | Langevin geometric evolution | dφ = -∇V dt + √(2D) dW_t |
| CGICE-2 | Covariance stimulated dissipation | ⟨δF·δA⟩ = -γ⟨F·A⟩dt |
| CGICE-3 | Time-info-charge transport | ∂_tI + ∇(I·v) = g_TC·Ω_CS |
| CGICE-4 | Information cycle closure | ∮dS_info = 0 |

### Step 2: Grep Each Equation in Lean + MD

For each equation, grep the core mathematical symbol/operator:

```bash
# CGICE-1: Langevin noise term
grep -i "langevin\|dW_t\|stochastic\|wiener" *.lean *.md

# CGICE-2: Stimulated dissipation  
grep -i "stimulated\|δF.*δA\|covariance.*dissipation" *.lean *.md

# CGICE-3: Charge transport
grep -i "Q_CS\|Chern.Simons\|F∧F\|topological.*charge" *.lean *.md

# CGICE-4: Information closure
grep -i "∮dS_info\|information.*cycle.*closure\|dS_info.*=.*0" *.lean *.md
```

### Step 3: Classify Each Equation

| Classification | Definition | Example |
|:--:|------|------|
| **IMPLEMENTED** | Full equation exists in Lean with axioms/theorems | CGICE-3 beta projection in V63 |
| **DECLARED** | Structure/type exists but never solved | CGICE_System struct in V17 |
| **ABSENT** | Zero grep matches — equation never mentioned | CGICE-1,2,4 in V16 |
| **DECORATIVE** | Equation stated in text but drives zero results | ∮dS_info=0 in V17 |

### Step 4: Dependency Check

If you DELETE all CGICE references from the paper, do the core results change?

| Test | V63 | V17 | V16 |
|------|:--:|:--:|:--:|
| Remove CGICE → seesaw m_ν changes? | No | — | — |
| Remove CGICE → Ω_GW=Ω_DM changes? | — | — | No |
| Remove CGICE → phase transitions change? | — | No | — |

If the answer is "No" for all core results, the paper has **zero CGICE dependency** — it's pure name-borrowing.

## Results: V63×V17×V16 CGICE Audit

| Paper | CGICE-1 | CGICE-2 | CGICE-3 | CGICE-4 | Δ if removed |
|------|:--:|:--:|:--:|:--:|:--:|
| V63 | ✗ | ✗ | Partial (beta only) | ✗ | 0 |
| V17 | Declared | Declared | Declared | Decorative | 0 |
| V16 | ✗ | ✗ | ✗ | ✗ | 0 |

**Conclusion**: All three papers have CGICE score = 0/4. None of their core results depend on CGICE dynamics.

## Modification Templates

### For paper abstract:
> "The **CGICE-inspired** beta-function modification..." (not "The CGICE dynamics...")

### For Lean header:
```lean
-- [CGICE AUDIT] CGICE 4-SDE IMPLEMENTATION STATUS:
--   CGICE-1, CGICE-2, CGICE-4: NOT IMPLEMENTED
--   CGICE-3: PARTIAL (beta-function projection only)
```

### For discussion/conclusion:
> "The full CGICE 4-SDE system is declared as a framework but not numerically solved. Results below use only the CGICE-3 beta-function projection."
