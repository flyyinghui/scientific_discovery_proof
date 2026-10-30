# V63 Neutrino Condensation — Cross-Paper Modification Patterns

Discovered during the 2026-08-06 V63→V17 dual-modification session. These
patterns are specific to V63's unique structure (Honest Scope §VIII, Supplement
S1-S3, inline SciExplorer validation).

## 1. b₀ Reconciliation: Gauge Beta vs Effective CW Loop Count

V63 has a unique subtlety NOT present in V17 or V14:

- **Main text §II.C**: b₀ = 12 (pure SU(6) gauge + Nf=15, coset scalars are
  geometric coordinates, not dynamical DOF).
- **Supplement S2.1**: b₀ ~ 17.8 (includes 35 adjoint scalars contributing
  +(1/6)*35 = +5.83 to the one-loop count).

These are NOT contradictory — they describe DIFFERENT physical quantities:
- b₀ = 12: gauge coupling beta function coefficient (governs running of g_TC).
- b₀ ~ 17.8: effective loop-counting parameter for the Coleman-Weinberg
  potential when summing over ALL field fluctuations tangent to the manifold.

**Fix pattern**: Do NOT "correct" one to match the other. Instead, add an
explicit clarifying note in S2.1: "This b₀ ~ 17.8 is the effective CW
loop-counting parameter; the gauge beta function coefficient remains b₀ = 12
as derived in §II.C and clarified in Appendix A."

**Verification**: Both values should remain in the document with explicit
cross-references between them. Removing either would create a consistency gap.

## 2. kappa Naming Collision — Already in Pitfall #8, Applied Here

V63 has TWO distinct quantities named "kappa":
- **kappa_inst ≈ 3266.67**: FRG instanton enhancement factor, calibrated to
  reproduce g_TC^2 = 24pi^2/35 from the IR fixed-point condition.
- **kappa_geo ≈ 1.10**: Geodesic-length mass hierarchy parameter in the
  Stern-Brocot formula m_alpha = m_0 * exp(-kappa_geo * GY_alpha).

**Fix pattern**: Rename ALL occurrences:
- FRG context: `kappa` → `kappa_inst`
- Mass hierarchy context: `kappa` → `kappa_geo`

**Grep command**: `grep -n 'kappa' *.md *.docx | grep -v 'kappa_inst\|kappa_geo'`
to find remaining bare usages.

## 3. SciExplorer Inline Validation Block

V63's DOCX (lines 243-267 in extracted text) contains an INLINE SciExplorer
validation report with 6 checks (3 PASS, 3 FAIL). This is different from
standalone validation reports. Key findings:

- [PASS] CW Minimum: phi_min exists, V_min negative.
- [FAIL] Beta RG Flow: g runs to 0.43, not 2.60 — confirms need for non-perturbative FRG.
- [FAIL] FRG Fixed Point: beta(g_TC) = 0.0979 ≠ 0 — the instanton calibration lands near but not AT zero.
- [FAIL] Seesaw Mass: m_D = 110.3 GeV (not 63.12) in the SciExplorer run — unit discrepancy.
- [PASS] Stern-Brocot Hierarchy.
- [PASS] Two-Scale Consistency.

**Critical finding**: The Stern-Brocot kappa definition error was caught here.
Earlier drafts assumed kappa = ln(M_R/m_0) ~ O(50), but the correct value is
kappa_geo = ln(m_0/m_tau) = 1.10 (O(1) geodesic-length parameter).

**Pattern**: When modifying V63, always check the inline SciExplorer block for
diagnostic data that may not appear in standalone reports.

## 4. VIII Honest Scope Structure (V63-Specific)

V63 §VIII contains detailed self-critical analysis NOT present in V17:
- VIII.A: Honest kappa=3266.67 calibration declaration (admits it's fitted).
- VIII.B: Two-scale hierarchy — admits Lambda_unif/phi_0 ≈ 77 is a free parameter.
- VIII.C: Delta m^2 ~3x NuFIT deviation — admits absolute scale mismatch.
- VIII.D: Postulates and Discussion — impact summary table with 7 assumptions rated by severity.

**Modification rule**: When inserting cross-references to V17, anchor them
BEFORE the FUTURE WORK paragraph, NOT inside the Honest Scope subsections.
The Honest Scope is self-critical; V17 references would be out of place there.

## 5. Supplement Section Structure (S1-S3)

V63 uses a Supplement numbering scheme (S1, S2, S3) for detailed derivations:
- S1: One-Loop CW Effective Potential — Complete Derivation
- S2: Wetterich FRG Flow and IR Fixed Point Generation
- S3: Type-I Seesaw Mass Matrix Diagonalization

These are NOT appendices — they are supplementary derivations referenced from
the main text. Modification of supplement content should NOT introduce
cross-references to V17 (supplements are self-contained derivations).
Cross-references belong in the main text sections (I-VIII).

## 6. Abstract Count Discrepancies

V63's abstract was particularly stale:
- Claimed: "47 theorems, 36 lemmas, 122 axioms, 17 definitions, 1 corollary"
- Actual (grep on Neutrino_Condensation_proof_63.lean): 26 theorems, 30 lemmas,
  66 axioms, 7 code-level sorries, 0 :=True stubs
- Also claimed "2,362 lines (1,730 code lines)" — actual: 2,379 lines.

This is worse than V17's drift (which only had stale theorem and line counts).
V63's abstract was a factor-of-2 off on axiom count.

**Verification command** for V63:
```bash
grep -c '^theorem ' Neutrino_Condensation_proof_63.lean
grep -c '^lemma ' Neutrino_Condensation_proof_63.lean
grep -c '^axiom\|^honest_axiom' Neutrino_Condensation_proof_63.lean
grep -c 'sorry' Neutrino_Condensation_proof_63.lean
wc -l Neutrino_Condensation_proof_63.lean
```
