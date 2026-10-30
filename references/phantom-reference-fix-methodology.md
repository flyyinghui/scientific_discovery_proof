# Phantom Reference Fix Methodology (Lean)

Validated on V17 (6D_Spacetime_Formal_Proof_V17.lean, 2026-08-13): 12 phantom
references fixed by honest-axiomatization, taking the file from "uncompilable"
to "compilable-modulo-real-compiler".

## What a phantom reference is

A `theorem` whose proof body calls `exact <undefined_symbol>` (or `:= <undefined_symbol>`)
where `<undefined_symbol>` is NEVER declared anywhere in the file. Distinct from the
"self-referential axiom" pattern (`theorem T := exact axiom_T` where axiom_T restates T):

| Pattern | Symptom | Fix |
|---------|---------|-----|
| **Phantom** | `exact foo` but `foo` undeclared → compile error | Declare `axiom foo : <type>` matching the call |
| **Self-referential** | `theorem T := exact axiom_T`, axiom_T restates T | Derive from upstream, or downgrade to honest-axiom |

Both are detected by `grep`-ing the file for identifiers used in `exact`/`:=`/`simp`
that have no matching `axiom`/`def`/`theorem` declaration. A phantom is a *missing*
declaration; a self-referential axiom is a *useless* declaration. Fix them differently.

## Detection script

```python
import re
text = open(path, encoding="utf-8").read()
# Find exact/simp/:= uses of symbols, then check each has a declaration
for m in re.finditer(r'exact\s+([A-Za-z_]\w*)\b', text):
    sym = m.group(1)
    if not re.search(r'\b(axiom|theorem|def|lemma|noncomputable def)\s+' + re.escape(sym) + r'\b', text):
        print(f"PHANTOM: {sym} used in exact but never declared")
```

## Fix pattern (no Lean compiler on the machine)

For each phantom `exact foo arg1 arg2` inside `theorem T (params) : goal := by`:

1. **Read the FULL theorem signature** (from `theorem` keyword to `:= by`) to get the
   exact goal type and the available bound variables.

2. **Declare the axiom just above the theorem**, matching the goal type EXACTLY:
   ```lean
   -- [honest-axiom] [P1] [FRAMEWORK ALIGNMENT <date>] <one-line reason>
   axiom foo (<implicit params>) (<explicit args>) : <goal type>
   ```

3. **Match the `exact` call's argument arity** — the declared axiom must accept exactly
   the arguments the `exact` call passes.

4. **Implicit vs explicit parameters** — this is where no-compiler type-matching breaks:
   - If `exact foo h_strong_concave h_ricci_min` passes only TWO args but the goal
     mentions `V_eff` and `K`, then `V_eff`/`K` must be declared as IMPLICIT `{...}`,
     not explicit `(...)` — otherwise the call has too few args.
   - Pattern: goal-only variables → `{...}`; hypothesis/argument variables → `(...)`.

5. **Unused params in the call** — drop them. If `exact mckean_singer_theorem` passes
   ZERO args but you originally planned `(t1 t2 : ℝ)`, the call can only synthesize
   params already visible in the goal. Keep only what the goal actually mentions.
   (V17 case: mckean_singer_index_invariance's goal was `trace t1 - trace t1 = 0`,
   so the axiom needed only `{t1}`, not `(t1 t2)`.)

6. **`:= <phantom>` (not `exact`)** — e.g. `have h : X ≥ Y := d3_projection_factor`.
   Declare the axiom with exactly the `have` target's type. Note V17 had TWO distinct
   projection symbols: `d3_projection_factor` (≥-form, used in witten_kls_gap) and
   `A_DIM3_projection` (= form, used elsewhere) — they are DIFFERENT identifiers, both
   must be declared; do not assume one subsumes the other.

7. **`simp [dim_SL_n_ℂ, dim_SU_p_q]`** — declare each as a bare equality axiom:
   `axiom dim_SL_n_ℂ : dim_ℝ (SL(6, ℂ)) = 70` etc.

## Honest-axiom vs sorry

Declaring a phantom as `axiom` is mathematically equivalent to `sorry`, BUT it is the
honest choice: a named, tagged `[honest-axiom]` declaration states "this is a postulate",
whereas a bare `exact undefined_symbol` is a gap pretending to be a proof. Do not leave
phantoms as `sorry` — name them and tag their scope.

## Verification without a compiler

After fixing all phantoms, re-run the detection script (expect zero phantom hits), then
spot-check each declaration's type against its use site by reading both. The
verification subagent should report a per-phantom table: name + declaration line +
use line + type-match ✓/✗. Flag any axiom with an unsynthesizable implicit param
(like V17's `index_theorem_proportionality_conjecture` keeping `E : VectorBundle X`
that the `exact` call never supplies — `D_op` is synthesizable from the goal, `E` is not).

## Post-fix cleanup: stale "phantom" comments

After fixing, grep the file for stale comments that still say "never defined" /
"remain undefined" / "phantom" — these now CONTRADICT the fix and must be updated to
"now axiomatized as honest-axioms". V17 had 3 such stale comments (L589, L2069, L2737)
that survived the fix and were only caught by the verification pass.
