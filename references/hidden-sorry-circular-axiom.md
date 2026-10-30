# Hidden Sorry — Circular Axiom Diagnostic Pattern (2026-08-07)

## Pattern Definition

A `.lean` file reports "0 active sorry" but contains unproven claims. The pattern:

```lean4
theorem T : P := by
  exact axiom_A   -- ← the entire proof

axiom axiom_A : P  -- ← axiom IS the theorem conclusion
```

The `axiom` simply restates the theorem's conclusion. Nothing is proved — the theorem is circular.

## Detection

```bash
# Find axioms whose conclusion matches a neighboring theorem
grep -A2 "^axiom " *.lean | grep -B1 "^theorem "
```

Or: search for `exact.*axiom` in theorem proof bodies.

## Case Study: V16 N_e_formula_axiom

```lean4
theorem N_e_value : N_e φ_i_phase φ_f_phase = 160 := by
  unfold N_e
  have h : ∫ x in φ_i_phase..φ_f_phase, V x / V_prime x = 160 := by
    exact N_e_formula_axiom φ_i_phase φ_f_phase   -- ← CIRCULAR
  exact h

axiom N_e_formula_axiom (φ_i φ_f : ℝ) : ∫ x in φ_i..φ_f, V x / V_prime x = 160
```

The axiom IS the theorem. Fix: replace with derivation from upstream physics (λ_KLS → threshold → N_e).

## Fix Procedure

1. Identify the physical derivation path the axiom should encode
2. Replace the circular axiom with a proper derivation chain
3. Tag any remaining phenomenological inputs (`t_freeze`, `t0`) with `[phenomenological]`
4. The proof should contain NO `exact <axiom-that-restates-conclusion>` calls
