# Circular Reasoning Patterns in Lean Formal Proofs

**Taxonomy of 5 patterns** detected in SL(6,C) trilogy audit (2026-08-07).

## P1: Self-Referential Axiom

`theorem T : X = Y := by exact axiom_A` where `axiom_A : X = Y`

| Detection | `grep "theorem.*:= by" *.lean \| grep "exact"` |
| Fix | Add `@[axiom_restatement]` annotation; downgrade theorem to lemma |
| V17 instances | T2_KLS_Spectral_Gap, spectral_gap_emerges, top_charge_eq, g_TC_sq_formula (7+) |
| V63 instances | T_CGICE_DECONFINEMENT, T_CGWB_VALIDATED, T_MONGE_TIME_EMERGENCE, T_SEESAW_SB_BRIDGE (4) |
| V16 instances | kls_gap_value (proves 35=35), bourgain_slice (P→P tautology) |

## P2: Phantom Dependency

Theorem proof body references a symbol never defined anywhere in the file.

| Detection | `grep "exact\\|:=" *.lean`, then verify each referenced symbol has a `def`/`axiom`/`theorem` |
| Fix | Delete the phantom reference and mark theorem as `@[unproven]`, OR define the symbol |
| V17 instances | 12 phantom references: witten_bochner_formula, d3_projection_factor, bakry_emery_cd_spectral_gap, brenier_mccann_geodesic_theorem, heat_kernel_spectral_bound, index_theorem_proportionality_conjecture, mckean_singer_theorem, symmetric_space_scalar_curvature, symmetric_space_ricci_norm, dimension_quotient_theorem, dim_SL_n_C, dim_SU_p_q |

## P3: Circular Parameter Chain

Parameter X "derives" Y, but X was back-calculated from target Y.

| Detection | Trace parameter definitions backward — check if any are defined as functions of downstream results |
| Fix | Mark chain as "phenomenological calibration, not independent derivation" |
| V63 instance | Seesaw: m_ν(target) → M_R → m_D → y_ν → "with y_ν, compute m_ν" |
| V16 instance | N_e: t_freeze = t0/exp(160/λ_KLS), then N_e = λ_KLS·ln(t0/t_freeze) = 160 |
| V17 instance | N_e = (70/6)·ln(1+10^6) ≈ 161 where N=70 from dim(T*M), T_final chosen to match target |

## P4: Name-Borrowing

Paper claims framework F, but only a single projection of F is implemented.

| Detection | List all equations of F → grep each in code → classify IMPLEMENTED/DECLARED/ABSENT |
| Fix | Rename: "F-inspired [projection]" or add implementation status table |
| All 3 papers | CGICE: 4-SDE claimed, only CGICE-3 beta projection exists (and only in V63) |

## P5: P→P Tautology

`theorem (h : P) : P := by exact h` — zero information content.

| Detection | `grep "theorem.*:= by" *.lean \| grep "exact h"` |
| Fix | Delete or add `@[tautology]` annotation |
| V16 instance | bourgain_slice_differential_redshift |

## Cross-Pattern Severity

| Pattern | Severity | Impact |
|------|:--:|------|
| P2 (Phantom) | 🔴 P0 | Lean uncompilable; all downstream derivations hollow |
| P3 (Circular Chain) | 🔴 P0 | Core results are post-dictions, not predictions |
| P4 (Name-Borrowing) | 🔴 P0 | Paper claims a framework it doesn't contain |
| P1 (Self-Referential) | 🟡 P1 | Misleading labeling; proof has zero derivation |
| P5 (Tautology) | 🟢 P2 | Embarrassing but harmless |

**Validated on**: V63×V17×V16 SL(6,C) trilogy (~10,500 Lean lines, 2026-08-07). ~200 circular assertions detected.
