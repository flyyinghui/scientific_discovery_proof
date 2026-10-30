# CGICE 4-SDE Implementation Audit Methodology

**Validated**: CGICE unified review V63×V17×V16, 2026-08-07; CGICE v9 standalone, 2026-08-11

## The "Name-Borrowing" Pattern

Papers claiming "CGICE dynamics" but implementing only a fraction of the claimed system.

### The Full CGICE 4-SDE System

| Equation | Physics | 
|----------|------|
| CGICE-1 | Langevin geometric evolution: dχ = -∇V dt + √(2D)dW_t |
| CGICE-2 | Covariance stimulated dissipation: ⟨δF·δA⟩ = -γ⟨F·A⟩dt |
| CGICE-3 | Time-information-charge transport: ∂_tI + ∇(I·v) = g_TC·Ω_CS |
| CGICE-4 | Information cycle closure: ∮dS_info = 0 |

## Audit Procedure (4 Steps)

### Step 1: List All Claimed Equations
Extract every equation from the paper's dynamics section. Count them.

### Step 2: Grep Each Equation in Lean + MD
For each equation, search for its key symbols in both the Lean proof and MD paper.

| Status | Meaning |
|------|------|
| IMPLEMENTED | Found in Lean with proof body (not just axiom) |
| DECLARED | Found as `axiom` or type declaration, zero code |
| ABSENT | Not found in either Lean or MD |

### Step 3: Classify the Paper's CGICE Status

| Category | Definition | Example |
|------|------|------|
| **Full 4-SDE** | All 4 eqs implemented | None in current papers |
| **Beta-only** | Only CGICE-3 beta projection | V63 |
| **Declaration-only** | Structure declared, zero solved | V17 |
| **Citation-only** | CGICE mentioned in refs only | V16 |
| **Name-borrowing** | Claims CGICE but implements unrelated | CGICE v9 (4-SDE claimed, T1 only) |

### Step 4: FRG Flow Reachability Check

For any paper claiming an FRG fixed point at g_TC²:
1. Compute g² at the relevant scale from beta function
2. Compare to claimed fixed point
3. If gap > 10×: mark as "TARGET, not REACHED"

## CGICE v9 Case Study (2026-08-11)

### Claimed
14 axioms, 4-equation CGICE dynamical system, Lean 4 verification of 4 theorems

### Actual
- CGICE-1 through CGICE-4: DESCRIBED in prose, ZERO numerical implementation
- Master equation (CGICE-4 proxy): proven in Lean but based on FALSE identity α=λ₁/(2π)
- T4 (topological charge conservation): "under development"

### Discovery: α = λ₁/(2π) False-Positive
```lean
hα' : α = λ₁ / (2*π)  -- norm_num + ring "proved" this
-- α = 6π/35 ≈ 0.539, λ₁/(2π) = 35/(6π) ≈ 1.857
-- They're RECIPROCALS, not equal!
```
See `references/lean-normnum-pi-false-positive.md` for full analysis.

### Fix Applied
- Removed false α=λ₁/(2π) equality
- Master equation → A16 (postulated, not derived)
- Added A17 to prevent trivial dI/dt=0
- T3 proof body → `sorry` (needs reconstruction)
