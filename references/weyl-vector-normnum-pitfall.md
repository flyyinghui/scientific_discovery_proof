# Weyl Vector norm_num Verification Pitfall (2026-08-07)

**Pattern**: `norm_num` proofs on fraction-based vector definitions can claim wrong results because the definition itself encodes incorrect arithmetic.

**Case Study — V17 Lean**:
```lean4
def weyl_vector_SU6 : ℝ^6 := (5/2, 3/2, 1/2, -1/2, -3/2, -5/2)
theorem weyl_norm_sq_eq_35 : ‖weyl_vector_SU6‖² = 35 := by
  unfold weyl_vector_SU6
  norm_num
```

**Actual computation**: Σ(25+9+1+1+9+25)/4 = 70/4 = **17.5 ≠ 35**

The proof would FAIL if typechecked — `norm_num` computes 17.5 but the theorem claims 35.

**Root cause**: The Weyl vector for SU(6) with Euclidean norm needs (5,3,1,-1,-3,-5)/√2 to give ‖ρ‖²=35. The half-integer form (5/2,...) is the standard presentation in Killing normalization (where B=2n·Tr), but Euclidean norm_num uses standard ‖·‖².

**Fix**: `weyl_vector_SU6 := (5/√2, 3/√2, 1/√2, -1/√2, -3/√2, -5/√2)`

**Lesson**: ALWAYS manually verify the arithmetic of any `norm_num` theorem claiming specific integer values from fraction inputs. Compute ∑x_i² externally before accepting the Lean claim. `norm_num` is correct at computing — it just computes what you told it to, even if what you told it is wrong.
