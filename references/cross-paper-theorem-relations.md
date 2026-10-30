# Cross-Paper Theorem Relationship Analysis

Extends `cross-paper-convergence.md` from parameter-level to theorem-level analysis.
Use when comparing 2+ papers sharing a theoretical framework at the proof/theorem
level, not just the parameter level.

## Four Relationship Types

### 1. Mutual Validation (互验证)
Two theorems from different papers independently derive the same result via
different paths. The independence of the derivation paths STRENGTHENS the
framework. Rate by validation strength: "极强" (two geometric paths) >
"强" (~1% agreement, different methods) > "一致".

### 2. Bridging (桥接)
A theorem in one paper connects a concept to one in another paper that the
other paper uses but does not derive. The key test: does the bridging theorem
provide the MATHEMATICAL justification for a cross-paper connection? If the
connection is stated but not derived, flag it as "phenomenological bridge"
(weaker) rather than "derived bridge" (stronger).

### 3. Causal (因果)
One theorem's result is a PREREQUISITE for another. The timeline must be
physically consistent: energy scales must decrease monotonically along the
causal chain, and intermediate states must be physically plausible.

### 4. Complementary (互补)
Two theorems address different aspects of the same phenomenon (e.g.,
microscopic vs macroscopic, particle vs cosmology, algebraic vs geometric).
Complementary theorems do NOT validate each other — they fill different gaps.

## Procedure

### Step 1: Extract all theorems from each paper's Lean file
```bash
grep -n "^theorem " paper.lean | wc -l  # count
grep -n "^theorem " paper.lean | head -20  # list
```

### Step 2: Build a cross-reference matrix
For each pair of theorems (one from each paper), classify:
- Same concept? → Mutual Validation or Tension
- One provides foundation for the other? → Causal
- One connects a gap the other leaves? → Bridging
- Different levels addressing same phenomenon? → Complementary

### Step 3: Score convergence
- Parameter-level: exact match / <0.1% / <1% / >5% (tension)
- Derivation path: geometric↔geometric / geometric↔phenomenological / fitted↔fitted
- Independence: shared axioms count fewer → stronger independence

### Step 4: Document tensions
When theorems genuinely conflict:
1. Identify which paper's value is correct (via SciExplorer validation)
2. Classify as P0 (fatal — numerically wrong) / P1 (reconcilable — different regime) / P2 (cosmetic — naming)
3. Propose fix for the erroneous paper
4. Flag for cross-reference addition

### Step 5: Generate the unified diagram
Produce an ASCII/Unicode diagram showing:
- Shared mathematical foundation at top
- Each paper's unique contribution in parallel columns
- Convergence points at bottom with exact numerical values

## Pitfalls

1. **Same name, different object.** `b_0` in V17/V63 is the gauge beta function coefficient. `b_0` in SPSGAN is a Betti number. Always trace the definition chain — never assume same-name = same-thing.

2. **Independence is a strength, not a gap.** When V14 derives H_0=67.42 without using g_TC (while V17 uses it), this is NOT a missing cross-reference — it is independent validation. Do not force parameter alignment where geometric independence is the point.

3. **"Derived" vs "Postulated" must be audited.** Many Lean theorems declare `:=True` stubs or `axiom` wrappers labeled as `theorem`. Read the actual proof body — if it's `exact axiom_X`, it's a postulate, not a theorem. Mark these honestly in the relationship matrix.

4. **Missing cross-references are P1, not P0.** When two papers share concepts but don't cite each other, it's a coordination gap — not a mathematical error. Fix by adding bidirectional cross-references, not by changing equations.

5. **Causal chains must preserve energy scales.** T1 (10^16 GeV) → T2 (10^13 GeV) → T3 (meV) must monotonically decrease. Any reversal in the causal chain is a P0 error.

## Example: V17-V63-V14 Triple Analysis (2026-08-05)

Applied to six-dimensional spacetime (V17), neutrino condensation (V63),
and triple gravitational waves (V14). Key result: all 8 SciExplorer P0 checks
pass across all three papers. 0 fatal contradictions. 5 mutual validations,
6 bridges, 4 causal chains, 3 complementary pairs, 3 tensions (all P1/P2).
