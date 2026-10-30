# Appendix B Audit Methodology — Systematic Mathematical Verification of Paper Appendices

Systematic workflow for auditing formal-proof appendices in physics papers. Developed
and validated on the triple GW V14 paper Appendix B (2026-08-05), discovering 6 errors
(4 P0-FATAL, 2 P1-MAJOR).

## When to Use

When a paper's appendix claims to summarize formal proof results (Lean, Coq, etc.)
and you need to verify every mathematical claim against:
- The actual formal proof file
- Independent numerical computation (Python + SymPy)
- Standard physics (dimensional analysis, order-of-magnitude checks)

## 6-Step Audit Procedure

### Step 1: Extract All Claims from Appendix
Read the DOCX appendix section. For each paragraph, extract:
- Every equation with numeric values
- Every claimed derivation (e.g., "X follows from Y")
- Every "exact match" or "precise agreement" claim
- Every "parameter-free" claim

### Step 2: Cross-Reference with Formal Proof File
For each claim, find the corresponding Lean declaration:
- `theorem` → genuine proof (verify the proof body is non-trivial)
- `axiom` / `[honest-axiom]` → NOT derived, this is an input
- `def` with `:=` → definition, may still carry implicit assumptions
- `:= by norm_num` → trivial arithmetic, NOT a substantive proof

**Red flag**: When a paper appendix says "X is derived" but the Lean proof declares X as an axiom.

### Step 3: Independent Numerical Verification
For every equation with numeric values, compute independently:
```python
import math, sympy as sp
# Verify claim, not just trust the stated result
```

**Red flags**:
- Numeric values that differ by >10 orders of magnitude from physical expectation
- "Exact matches" where both sides use the same free parameters (circular)
- Missing intermediate steps between asserted values

### Step 4: Symbolic Audit (MAF P0)
Apply the MAF bridge symbolic audit to catch:
- Algebraic errors (misapplied formulas, sign errors)
- Dimensional inconsistencies (mixing Hz, GeV, dimensionless quantities)
- Circular definitions (A defined from B, B defined from A)

### Step 5: Severity Classification

| Severity | Definition | Action |
|:--------:|------------|--------|
| **P0-FATAL** | Claim is mathematically false. The derivation as written is invalid. | DELETE the claim, rewrite from scratch. |
| **P1-MAJOR** | Claim overstates what is proven. "Derived" when actually "postulated". | REWRITE to honest language: "postulated" / "calibrated" / "[honest-axiom]". |
| **P2-MINOR** | Claim is correct but missing rigor or intermediate steps. | ADD missing steps, cite sources. |
| **P3-COSMETIC** | Notation inconsistency, missing definition. | FIX notation. |

### Step 6: Honest Rewrite
Replace the original appendix with a corrected version that:
1. States what IS mathematically proven (with Lean theorem references)
2. States what IS honestly postulated (with [honest-axiom] tags)
3. States what IS calibrated/fitted (with "phenomenological" tags)
4. Includes a verification status summary table
5. Documents all errors found in the original (Table of Corrections)

## Key Findings from V14 Appendix B Audit

### Errors Found (6 total)
1. **Spectral gap formula (P0)**: Used λ_gap ~ (log N)^4/t_P instead of λ_KLS = 35/3
2. **GW frequency derivation (P0)**: N_e values (60,100,160) hand-picked to match desired frequencies
3. **z_eff = e^160 (P0)**: No justification, not in Lean proof
4. **Arithmetic error (P0)**: (6.04e45)^2/e^640 claimed = 2.07e-27; actual = 3.58e-187 (off by 160 orders)
5. **"Exact match" (P1)**: Circular — both sides used same free parameters
6. **"Parameter-free" (P1)**: Lean proof has 28 axioms, 14 [honest-axiom]

### Detection Methods That Caught Each Error
1. Cross-reference with Lean proof + Harish-Chandra spectral geometry
2. Cross-reference with Lean proof (f_peak declared as axiom, not theorem)
3. Grep Lean proof for "z_eff" or "redshift" — absent
4. Independent Python: `(6.04e45)**2 / math.exp(640)` → direct computation
5. Parameter dependency analysis: trace all numbers back to axioms
6. Count axiom declarations in Lean file: `grep -c 'axiom\|honest_axiom' *.lean`

## Pitfalls

1. **Paper appendix can diverge from Lean proof.** The appendix text and the formal proof are separate artifacts written at different times. Always verify against the ACTUAL Lean file, not the appendix description of it.
2. **"theorem" in Lean ≠ proven.** A Lean `theorem` whose proof body is `:= by {norm_num}` or `:= by {exact axiom_X}` is not proving anything — it's restating an axiom.
3. **Numeric "verification" by construction.** If two numbers match because both are computed from the SAME free parameter, it's not verification — it's tautology.
4. **Dimensional analysis catches silent errors.** Always check: does the claimed formula have correct units? If λ_gap should be Hz and the formula gives Hz, is the magnitude physically plausible?
5. **The (log N)^4/t_P trap.** This formula appears in mixing-time bounds for convex bodies in R^n. It has NO CONNECTION to the KLS spectral gap on symmetric spaces. Do not use it for spectral gap derivations.
6. **DOCX abstract counts are stale.** The paper's abstract and the Lean file diverge over revisions. Always `grep -c 'theorem ' *.lean` and `grep -c 'axiom ' *.lean` independently — never trust the abstract's claimed counts. Update both the DOCX and the Lean header comment to match.
