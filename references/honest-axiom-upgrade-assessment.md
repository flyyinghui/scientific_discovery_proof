# Honest-Axiom Upgrade Assessment Methodology

**Validated**: 2026-08-07 | MathCode V2.0 (146K .lean files) × V16/V17 Lean files

## Purpose

Systematically evaluate which [honest-axiom] declarations in a Lean proof can be upgraded to rigorous [theorem] proofs using available formal proof libraries.

## 4-Step Procedure

### Step 1: Scan Available Libraries

```bash
# Find relevant typeclasses
grep -rl "SmoothManifold|RiemannianMetric|LieGroup|MeasureSpace" <mathcode_path>/

# Find relevant theorems
grep -rl "spectral_gap|poincare|ricci|curvature" <mathcode_path>/
```

### Step 2: Check Proof Completeness

For each candidate theorem:
```bash
grep -c "sorry" <file>.lean
```

Classification: 0 sorries = PROVEN, 1-3 sorries = SKELETON, all sorries = STUB.

### Step 3: Three-Way Classification

| Class | Criteria | Action |
|-------|----------|--------|
| **UPGRADE** | Typeclass exists + proof complete | Replace [honest-axiom] with [theorem] |
| **REFACTOR** | Typeclass exists + proof incomplete | Replace hand-rolled structure with proper typeclass, keep [honest-axiom] |
| **CANNOT UPGRADE** | Typeclass missing or proof is `sorry` stub | Add detailed annotation explaining WHY |

### Step 4: Annotate Cannot-Upgrade Items

For each CANNOT UPGRADE item, add a structured comment:
```lean4
-- UPGRADE 3 ASSESSMENT (date): This remains [honest-axiom] because:
-- 1. [library name] provides [typeclass name] but [specific gap]
-- 2. [theorem name] in [file] is itself `sorry`
-- 3. [mathlib version] has [partial support] but does not yet [missing capability]
-- 4. A full proof would require: [estimated work]
-- STATUS: KEPT AS [honest-axiom]. [literature status]. [OPEN PROBLEM if applicable].
```

## Validated Results (V16, 2026-08-07)

| Item | Classification | Action Taken |
|------|:---:|------|
| SL6C structure | REFACTOR | Hand-rolled → SmoothManifoldWithCorners `deriving` |
| Weyl vector \|\|ρ\|\|²=35 | UPGRADE | [honest-axiom] → `norm_num` theorem |
| ricci_nonpositive | CANNOT UPGRADE | Ricci operator is placeholder stub in MathCode |
| mixing_inequality_axiom | CANNOT UPGRADE | spectral_gap_estimate is `sorry` in MathCode |
| bourgain_physical_analogy | CANNOT UPGRADE | No convex-geometry formalization exists |

## Pitfalls

1. Typeclass existence ≠ proof existence. MathCode has `SmoothManifoldWithCorners` but `canonical_connection_unique` is `sorry`.
2. LLM-generated Lean code for upgrades often has API errors (e.g., `Real.log_exp` argument type mismatch). Always verify against Mathlib4 docs.
3. The Weyl vector Euclidean norm ≠ Killing norm. (5/2,3/2,1/2,-1/2,-3/2,-5/2) has Euclidean ‖ρ‖²=17.5, NOT 35. Must use (5,3,1,-1,-3,-5)/√2 for Euclidean norm=35.
