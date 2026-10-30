# Numerical Review Correction + Cross-Paper Sync Patterns

Validated 2026-08-18 on the CGICE V9.1 MathCalc review (4 P0 + 4 P1 + 2 P2 errors
propagated across 7 files: CGICE MD+DOCX+Lean, SL6C framework, V16 MD+DOCX+Lean).

## The "definitional vs physical-claim" audit split

Review insight: **definitional arithmetic is usually all correct; the numbers
that carry physics claims are usually wrong.** On CGICE V9.1: 14 definitional
identities (τ=6π/35, α reciprocal, Λ=1225/18π) all correct, but 4 physical-claim
numbers (N_e, g_TC flow, Landau pole, μ_crit) all wrong. When auditing, recompute
BOTH categories separately — do not let "all the simple arithmetic checked out"
give a false sense that the physical numbers are fine.

## Recurring P0 physics error classes (grep for these)

1. **Energy-scaling exponent vs dimension.** A 2n-dimensional phase space volume
   scales as Vol ∝ E^n (the n-dim configuration space), NOT E^(2n). So
   N_e = (n/6)·ln(...) not (2n/6). CGICE: 70-dim phase space → exponent 35,
   N_e = 161 → 80.6.
2. **One-loop RG integral factor 2.** dg/dlnμ = b₀g³/8π² integrates (∫g⁻³dg =
   -g⁻²/2) to g = g₀/√(1 - b₀g₀²/(4π²)·ln(μ/M)) — denominator 4π², NOT 8π².
   The paper's 8π² solution corresponds to dg/dlnμ = b₀g³/16π².
3. **Landau pole sign.** b₀ > 0 ⇒ dg/dlnμ > 0 ⇒ pole is in the ULTRAVIOLET
   (ln(μ/M) = +4π²/(b₀g₀²)), theory is IR-free. Any "IR Landau pole at 10⁴ GeV"
   claim is a sign error; correct is ~10²² GeV.
4. **μ_crit formula.** Correct one-loop critical-coupling scale is
   μ_crit = M·exp[(4π²/b₀)(1/g₀² - 1/g_crit²)] — needs the 1/b₀ factor and the
   (1/g₀² - 1/g_crit²) form, NOT (1 - 1/g_crit). For b₀>0 it is UV (~10²¹ GeV),
   never 10⁻⁹ eV.

## Cross-paper sync order

A numerical fix must reach EVERY file sharing the framework. Order:
1. **MD first** (authoritative formulas + a `[P0-N FIX 2026-08-18]` annotation).
2. **Lean** (the `def`/`axiom`/`theorem` numeric literals — e.g. `(70/6)`→`(35/6)`,
   `= 161`→`= 80.6`, plus the matching `t_freeze` def so the chain stays self-consistent).
3. **DOCX** (text runs via python-docx `run.text` replace + insert one
   "correction note" paragraph near the abstract). NOTE: OMML formula values are
   NOT extractable via `p.text` — don't waste time hunting numbers that live in
   Word equations; put the corrected formula in the note and point to the MD.

Recompile the Lean after the numeric edit (values-only edits still compile:
verified 8728 jobs / 0 sorry after N_e fix).

## String-replace pitfalls (bit twice this session)

- **Prefix-match bug**: replacing `"N_e=160"` also matches the prefix of
  `"N_e=160.3"` → produces `"N_e=80.6.3"`. Use longer unique context, or replace
  the longer `.3` variant FIRST, then the plain one. After any bulk replace,
  grep for the mangled form (`80.6.3`, `80.6.3/161`).
- **Residual check must distinguish CURRENT value from HISTORICAL annotation.**
  Old values kept inside fix annotations are INTENTIONAL and should stay:
  `"原160.3/161双值"`, `"旧0.44/0.2727已修正为0.21"`, `"非0.9497"`. When the final
  grep still finds the old number, verify each hit is an annotation context, not
  a live value. Do not "clean" annotations.

## Independent recomputation is mandatory

Before transcribing ANY review-provided number or formula, recompute it in
Python (the review docs themselves carry arithmetic errors — see SKILL.md
Pitfall 40). This session confirmed all four P0 numbers independently before
editing.
