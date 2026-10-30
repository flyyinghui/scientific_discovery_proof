# V63 Seesaw Chain P0-6 Fix — Diagnosis & Procedure

**Date**: 2026-08-06 | **Session**: SL(6,C) trilogy revision

## The Error

V63 claimed: `m_D = sqrt(8.70e-11 * 8.0e13) = 63.12 GeV` with `y_nu = 0.363`, `m_nu = 0.152 eV`.

All three numbers are wrong:
- Correct: `m_D = 83.43 GeV` (+24%)
- Correct: `y_nu = 0.480` (+32%)
- Correct: `m_nu = 0.087 eV` (-43%)

The text also claimed `8.70e-2 eV = 0.152 eV` which is arithmetically impossible (8.70e-2 = 0.087 ≠ 0.152).

## Root Cause

The seesaw chain was computed with three inconsistent arithmetic steps. The `0.152 eV` value is actually the Stern-Brocot baseline `m0_SB` (fitted from m1=0.003 eV), NOT the seesaw prediction. The paper conflated two distinct quantities.

## Fix Procedure

1. **DOCX**: Replace all `63.12` → `83.43`, `0.363` → `0.480`, `0.152` → `0.087` in seesaw context
2. **DOCX**: Add honesty note: `m_nu_seesaw(0.087) ≠ m0_SB(0.152)` by factor `ξ = 1.747`
3. **Lean**: Update `A_V63_SEESAW_CORRECTED` header and values
4. **Lean**: Update header comments mentioning stale values (`4.58e13`, `0.363`)

## Bridge Model

The gap `ξ = 1.747 ≈ √π · η_Cartan` is the Harish-Chandra Plancherel measure bridge — see `seesaw-sb-harish-chandra-bridge.md`.

## Common Pitfall

After fixing the main text, appendices and supplements routinely retain stale values. Always grep the ENTIRE DOCX + ALL supplements for old values after any numerical fix: `63.12|0.363|4.58e13|0.152|2.41e-5`.
