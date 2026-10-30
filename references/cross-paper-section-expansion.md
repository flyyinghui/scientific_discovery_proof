# Cross-Paper Section Expansion Workflow

**Date**: 2026-08-06 | **Validated on**: V63 §III.B

## When to Use

When a paper has an empty/stub section that references results from another paper in the same framework, and both share a unified axiom system.

## 5-Step Procedure

### 1. Load Both Papers + Unified Axiom System

Read the target section (to confirm it's empty/stub), the source paper's relevant sections, and the cross-paper theorem relations document.

### 2. Extract Cross-References

From the unified axiom document, extract:
- Shared parameters (λ_KLS, g_TC, b₀, etc.)
- Temperature/energy scale correspondence table
- Theorem-level relations (MV/BR/CA/CO classification)
- Numerical validation matrix

### 3. Write Section with Nested Structure

Structure: (a) unifying mechanism → (b) per-phase parallel descriptions → (c) consistency checklist.

Each phase should:
- State energy/temperature scale
- Describe mechanism in THIS paper
- Cross-reference parallel mechanism in companion paper
- Provide common GW frequency or observable
- Cite specific theorem/section in both papers

### 4. Verify Parameter Consistency

Run this checklist before inserting:
- λ_KLS: same in both papers? (V17/V63: both 35; V14: uses 35/3 effective)
- g_TC: same fixed point? (g_TC² = 24π²/35 ≈ 6.77)
- b₀: same beta coefficient? (12 = (11/3)×6 − (2/3)×15×0.5)
- T₁, T₂, T₃: order-of-magnitude agreement?
- GW frequencies f₁, f₂, f₃: consistent?
- H₀, ρ_DM/ρ_vis: same predictions?

### 5. Insert into DOCX (FORWARD Order)

Insert paragraphs before a reference anchor (e.g., next section heading). Always iterate FORWARD:
```python
for text, is_bold in content:
    new_p = doc.add_paragraph()
    parent.insert(ref_idx, new_p._element)
    ref_idx += 1  # shift as we insert
```
First paragraph ends up FARTHEST from the anchor.

## Pitfalls

1. **Don't use reversed()** — silently reverses paragraph order.
2. **Don't nest model lookup** — the `model` dropdown in dynamic combos serializes as a dict with inner inputs promoted to top level.
3. **Cross-reference format**: `[V17, §IV.B]` for sections, `[V17, Theorem cdm_baryon_ratio_conditional]` for theorems.
4. **Temperature scales**: Use `~` for approximations, not `=` for exact matches.
