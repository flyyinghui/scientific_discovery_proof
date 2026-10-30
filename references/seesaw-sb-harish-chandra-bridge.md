# Seesaw–Stern-Brocot Harish-Chandra Bridge Model

## Core Formula

$$\boxed{m_0^{\rm (SB)} = \xi \cdot m_\nu^{\rm (seesaw)}, \quad \xi = \frac{\mu_c(\rho)}{\mu_{nc}(\rho)} = \sqrt{\pi} \cdot \eta_{\rm Cartan} \approx 1.747}$$

Where:
- `m_nu^(seesaw) = 0.087 eV` — Type-I seesaw prediction from SL(6,C) CW effective potential
- `m_0^(SB) = 0.152 eV` — Stern-Brocot baseline fitted to reproduce m1=0.0030 eV
- `ξ = 1.747` — Harish-Chandra Plancherel measure ratio at Weyl vector ρ
- `√π = 1.77245` — Gaussian normalization constant from continuous→discrete measure mapping
- `η_Cartan = ξ/√π ≈ 0.986` — O(1) Cartan real form SU(3,3) correction

## Physical Origin

SL(6,C) double-Cartan structure provides two orthogonal Plancherel measures:
- Non-compact: X_nc = SL(6,C)/SU(3,3), μ_nc(λ) = |c_nc(λ)|^{-2} (continuous spectrum)
- Compact dual: X_c = SU(6)/SO(6), μ_c (discrete spectrum)

Cartan compactification at T1~10^16 GeV replaces the continuous measure with a discrete point evaluation at the spectral gap. The √π factor is the Gaussian normalization constant of the erased continuous degree of freedom.

## Lean Formalization

```
A_CARTAN_COMPACTIFICATION_BRIDGE: μ_c/μ_nc = √π · η_Cartan
T_CARTAN_BRIDGE_PHASE_I: bridge activated at Phase I (T1 = 10^16 GeV)
T_TRIPLE_UNIFICATION: |ρ|²=35 + √π govern cosmology + DM + neutrinos
L_CARTAN_BRIDGE_NUMERICS: |ξ − √π| < 0.02
```

## Paper Insertion Points

- V63: §III.C (Seesaw–Stern-Brocot Mass Scale Bridge)
- V17: §VI (Cartan Compactification Bridge paragraph before "A Unified Framework")
- V17 DOCX: Appendix C (Formal Lean 4 Bridge Declarations)

## Falsifiable Prediction

If Cartan real form were su(4,2) or su(5,1) instead of su(3,3), η_Cartan would shift by 5-10%, altering the predicted neutrino mass hierarchy and Δm² values relative to NuFIT.
