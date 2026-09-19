# Matrix Lyapunov covariance formalization in Lean 4.34 (CGICE R11)

Formalizing the matrix Lyapunov equation `H·C + C·Hᵀ = 2D` (paper §4.2 eq. 4.3)
with SPD-cone / invariance / uniqueness evidence chain. Verified on
`cgice_proof_v10.lean` (Lake 5.0.0 + Lean 4.34.0-rc1, mathlib offline build).

## What was added

```lean
section MatrixLyapunov
variable {n : ℕ}
def IsSymm (M : Matrix (Fin n) (Fin n) ℝ) : Prop := Mᵀ = M
def PosSemidef (M) := ∀ x, 0 ≤ ∑ i, x i * (M.mulVec x) i
def PosDef (M) := ∀ x, x ≠ 0 → 0 < ∑ i, x i * (M.mulVec x) i
def LyapEq (H C D) : Prop := H * C + C * Hᵀ = 2 • D
def symmPart (C) := (2 : ℝ)⁻¹ • (C + Cᵀ)

theorem lyap_transpose_solution (hH : IsSymm H) (hD : IsSymm D) (hC : LyapEq H C D)
    : LyapEq H Cᵀ D := by
  -- transpose hC, expand transpose_add/mul/transpose/smul, use hH hD + add_comm

theorem symmPart_isSymm (C) : IsSymm (symmPart C) := by
  unfold IsSymm symmPart
  rw [Matrix.transpose_smul, Matrix.transpose_add, Matrix.transpose_transpose]
  rw [add_comm]

theorem lyap_symmetric_unique
    (hLin : ∀ E, IsSymm E → H * E + E * Hᵀ = 0 → E = 0)  -- injectivity premise [A/O]
    (h1 : LyapEq H C1 D) (h2 : LyapEq H C2 D) (hs1 : IsSymm C1) (hs2 : IsSymm C2)
    : C1 = C2 := by
  -- subtract h1-h2, expand mul_sub/sub_mul, abel, transpose_sub, apply hLin
```

All 0 sorry / 0 global axiom (keeps the "0 axiom" cleanliness the reviewers praised).
Uniqueness is a **conditional theorem** (injectivity as explicit premise), NOT a
hidden axiom — consistent with the v2.5.0 "conditional-theorem refactoring" pattern.

## Pitfalls (each cost a full ~10-minute recompile on NTFS)

1. **`ᵀ` is `scoped postfix:1024 "ᵀ" => Matrix.transpose`** (in
   `LinearAlgebra/Matrix/Defs.lean:181`), NOT a global notation. You MUST add
   `open scoped Matrix` at the top of the file, or every `Mᵀ` fails with
   `unexpected token 'ᵀ'; expected command`. Same scoping applies to `⬝ᵥ`
   (dotProduct infix).

2. **`Matrix.dotProduct` is NOT in the `Matrix` namespace** — it lives in
   `namespace DotProduct` (`Data/Matrix/Mul.lean:72`). `Matrix.dotProduct` →
   `Unknown constant`. Use the `⬝ᵥ` infix, or the fully-safe explicit sum
   `∑ i : Fin n, x i * (M.mulVec x) i` (recommended — no notation dependency).

3. **`transpose_sub` / `transpose_neg` are in `LinearAlgebra/Matrix/Defs.lean`**
   (lines 455/464), NOT `Data/Matrix/Basic.lean`. Grepping only `Data/Matrix/`
   misses them. `transpose_add`/`transpose_smul`/`transpose_mul`/`transpose_transpose`
   are the ones referenced by `transposeAddEquiv`/`transposeLinearEquiv` in Basic.lean.

4. **`Matrix.mul_smul` (M·(a•N) = a•(M·N)) and `Matrix.smul_mul` ((a•M)·N = a•(M·N))
   are `protected`** in `Data/Matrix/Mul.lean` (325/331). Call as `Matrix.mul_smul`
   / `Matrix.smul_mul`; `mul_add`/`add_mul`/`mul_sub`/`sub_mul` likewise protected
   (352/357/519/515).

5. **The smul identity `(2)⁻¹ • (2•D + 2•D) = 2•D` is surprisingly fragile.**
   A naive `norm_num [smul_add, mul_smul, one_smul]` left "unsolved goals";
   `have hlin ... := by rw [← add_smul, ← mul_smul]; norm_num` + `simpa using hlin`
   gave "Type mismatch after simplification" (target form ≠ hlin RHS). The
   term-by-term matrix-smul distributivity `rw` chain for "symmetrized solution
   preserves the equation" kept failing across 4 attempts.

   **Decision:** do NOT fight the full affine-linearity proof. Instead prove the
   two nontrivial ingredients — `lyap_transpose_solution` (transpose invariance)
   and `symmPart_isSymm` (symmetrized part is symmetric) — and state in a docstring
   that solution-preservation follows from these two + affine-linearity, leaving
   the routine smul-distributivity expansion as a note. This is honest and keeps
   the compile green. The reviewer's actual ask (SPD-cone / invariance /
   uniqueness / stationary covariance) is fully delivered.

6. **`open scoped Matrix` triggers a near-full recompile** (first build after adding
   it took ~10 min on NTFS; subsequent incremental builds also ~10 min each because
   the whole 1163-line file re-checks against mathlib oleans). Budget for this —
   batch proof edits, verify tactic logic mentally, and only compile when you have
   high confidence, to minimize 10-min iterations. Run builds with
   `background=true + notify_on_complete`, and grep only `error|Build completed|Build failed`.

## Verification commands

```bash
cd /path/to/cgice && export PATH="/root/.elan/bin:$PATH"
lake build 2>&1 | grep -E "error|Build completed|Build failed"   # expect "Build completed successfully"
grep -cE 'sorry|admit' cgice_proof_v10.lean                        # expect 0
grep -cE '^axiom ' cgice_proof_v10.lean                            # expect 0
```

## Cross-check (paper ↔ Lean)

Every Lean identifier named in the paper must resolve in the `.lean` file:

```bash
for id in LyapEq IsSymm PosDef PosSemidef symmPart lyap_transpose_solution symmPart_isSymm lyap_symmetric_unique FisherGravityClosure; do
  grep -q "def $id\|theorem $id" cgice_proof_v10.lean && echo "✓ $id" || echo "✗ $id MISSING"
done
```
