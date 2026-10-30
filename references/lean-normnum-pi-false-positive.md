# Lean `norm_num` + `ring` False-Positive with π

**Discovered**: 2026-08-11 | CGICE v9 paper review  
**Impact**: P0 — can "prove" mathematically false identities, making entire Lean proof chains invalid

## The Trap

`norm_num` operates on ℚ/ℤ rational arithmetic and CANNOT evaluate π (a real constant). `ring` rearranges algebraic expressions. Together, they can produce a "proof" of identities that are mathematically false when containing π:

```lean
-- This COMPILES but is FALSE!
have h_false : 6*π/35 = 35/(6*π) := by
  norm_num
  ring
```

**Why it compiles**: `norm_num` normalizes rational constants (6, 35) but leaves π untouched. `ring` rearranges to `36*π^2 = 1225`, which `norm_num` cannot evaluate because π^2 is a real expression. The proof "succeeds" because the goal has been transformed to a form that Lean accepts as trivially true (an identity it cannot disprove).

## Numerical Verification

Always independently verify π identities numerically:

```python
import math
α = 6*math.pi/35          # ≈ 0.539
λ = 35/(6*math.pi)        # ≈ 1.857
print(f"α = {α:.4f}, λ = {λ:.4f}, equal = {abs(α-λ) < 1e-10}")
# Output: α = 0.5387, λ = 1.8567, equal = False
```

The two values are **reciprocals**: α × λ = 1.0000, not equals.

## Detection Pattern

When auditing Lean proofs, flag any `norm_num` + `ring` sequence that involves:
1. `π` (pi) — `norm_num` cannot evaluate
2. `Real.sqrt` — same limitation
3. `Real.exp` / `Real.log` — transcendental functions

**Grep command**: `grep -A2 'norm_num' *.lean | grep -B1 'ring'`

## Case Study: CGICE v9 α = λ₁/(2π)

The Lean code at L162-164:
```lean
have hα' : α = λ₁ / (2*π) := by
    rw [hα, hλ]   -- α = 6π/35, λ₁ = 35/3
    norm_num
    ring
```

- α = 6π/35 ≈ 0.539 (calibrated parameter)
- λ₁/(2π) = (35/3)/(2π) = 35/(6π) ≈ 1.857
- 0.539 ≠ 1.857 → FALSE identity

This false step propagated through the entire T1 (master equation) and T3 (duality) proofs, ultimately forcing I_eq = I_cycle and trivializing the dynamics (dI/dt = 0).

## Fix Pattern

1. **Remove** the `norm_num` + `ring` block
2. **Re-derive** without the false identity, or
3. **Postulate** the result as an independent honest-axiom (as done for CGICE A16)

## Related Pitfalls

- Pitfall #22: LLM-generated Lean code API errors — similar category of "Lean accepts but is wrong"
- Pitfall #24: "norm_num can't detect false equalities involving π" — same root cause
