# Cross-Paper Convergence Methodology

Systematic technique for verifying consistency across multiple papers sharing a common theoretical framework. Developed and validated across V17 (6D spacetime), V63 (neutrino condensation), and V13 (triple GW).

## Procedure

### Step 1: Extract Shared Parameter Matrix

Build a matrix of all parameters claimed by each paper. Include numeric values, derivation status (DERIVED/CONDITIONALLY DERIVED/POSTULATED/FITTED), and source location.

```
Parameter | V17 | V63 | V13 | Status
b0        | 12  | 12  | —   | MATCH
g_TC      | 2.60| 2.60| —   | MATCH (geometric path independent)
lambda_KLS| 35/3| 35/3| 35/3| MATCH
dim(M)    | 35  | 35  | 35  | MATCH
H0        |67.42|  —  |67.42| MATCH
CDM/baryon| 5.0 |  —  | 5.0 | MATCH
```

### Step 2: Classify Derivation Paths

For each shared prediction, trace its derivation chain in each paper:
- **Geometric path**: Derived from group structure, spectral gap, topological invariants
- **Phenomenological path**: Derived from effective action, FRG, coupling constants
- **Input parameter**: Taken as an observational input

The key insight: when a geometric path and a phenomenological path converge on the same prediction WITHOUT sharing parameters, the geometric path is MORE FUNDAMENTAL and the convergence STRENGTHENS the framework.

### Step 3: Identify Independence as Strength

When a parameter is absent from one derivation path (e.g., g_TC absent from geometric GW derivation), this is NOT a gap — it is independence that validates the framework. Do not force parameter alignment where geometry already provides a more fundamental derivation.

### Step 4: Document Mismatches

When values genuinely conflict across papers:
1. Identify which paper has the correct value (via SciExplorer validation)
2. Flag as P0 (fatal) or P1 (reconcilable)
3. Fix the erroneous paper
4. Add cross-reference

### Step 5: Add Bidirectional Cross-References

Each paper should cite the others at convergence points:
- V17 §III.D cites V63 for FRG fixed point derivation
- V63 §VI cites V17 for 3-phase cosmology timeline
- V13 cites V17/V63 for H0 and CDM/baryon convergence

## Pitfalls

1. **Do not force parameter alignment where independence is a feature.** The absence of g_TC from V13's geometric GW derivation is a strength, not a gap to fill.
2. **Same name, different meaning.** b0 in SPSGAN is a Betti number (topology), while b0 in V17/V63 is a gauge beta function coefficient. Always trace the definition chain. Similarly, `kappa` in V63 served both as FRG instanton enhancement (3266.67) and mass hierarchy parameter (1.10) until renamed to `kappa_inst`/`kappa_geo`.
3. **"Derived" claims need audit.** Papers often claim derivation when parameters are actually fitted. Use SciExplorer P0 + MAF symbolic audit to verify.
4. **Split GGUFs from Unsloth are incompatible with standard tooling.** This is not a cross-paper issue but a practical deployment constraint documented here for future model loading tasks.
5. **GW peak frequency assignment mismatch.** When multiple papers assign different physical processes to overlapping frequency bands (e.g., V17 assigns high-f peak to CDM crystallization at 1e2 Hz, V14 assigns it to geometric inflation at 4.5e11 Hz), build an explicit cross-paper frequency-to-process mapping table. Do not assume convergence until every peak's physical origin is reconciled across all papers.
6. **DOCX-vs-Lean count drift.** Paper abstracts routinely claim stale theorem/axiom counts that diverge from grep-verified Lean counts by 30-60%. Always independently verify before claiming cross-paper consistency.

## Validated Instances

| Instance | Papers | Key Finding |
|----------|--------|-------------|
| V17/V63 b0 | Both | 39→12 corrected via SciExplorer |
| V17/V63/V13 H0 | All three | 67.42 matches across all derivations |
| V13 GW independence | V13 vs V17/V63 | Geometric path independent of g_TC = strength |
| V63 kappa error | V63 | ln(M_R/m0)=54.62 → κ_geo=1.10 via SciExplorer |
