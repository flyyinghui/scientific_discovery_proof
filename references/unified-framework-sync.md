# Unified Framework Document Sync Checklist

**When**: After completing per-paper audit modifications, sync findings back to the SL(6,C) unified framework document.

## 7-Section Update Checklist

### §0 — Audit Summary
- [ ] Update date and engine line
- [ ] Add per-paper fix status (✅/🟡/⚠)
- [ ] Add verification report reference

### §1 — Lean Overview Table
- [ ] Update honest rating (A/B/C)
- [ ] Update axiom/theorem counts if they changed
- [ ] Add new audit findings column

### §8 — Logic Gap Status
- [ ] Update P0-7x status from ⚠→✅ or ⚠→🟡
- [ ] Add new P0 items discovered in this audit
- [ ] Update P2 items (kls_gap, bourgain, tensor, V_prime)

### §9 — Quality Assessment
- [ ] Update per-paper rating with justification
- [ ] Document key changes from previous version

### §10 — Lean Declaration Checklist
- [ ] Add per-paper audit annotation block
- [ ] List phantom references if any
- [ ] Add verdict line (PASS/CONDITIONAL/FAIL)

### §11 — Honesty Declaration
- [ ] Update fix progress table
- [ ] Add remaining work items for each paper
- [ ] Update publication track recommendations

### Footer
- [ ] Add verification report references
- [ ] Update generation metadata

## Per-Paper Sync Rules

| Event | Framework Update |
|------|------|
| New audit completed | Add §0 entry + §8 new P0 items |
| Per-paper fixes applied | Update §8 status + §9 rating + §11 progress |
| DeepSeek verification run | Add footer verification line |
| CGICE-specific audit | Update CGICE bridge sections (§4, §6) with declaration-vs-implementation notes |

## Parameter Consistency Check

After framework sync, verify these cross-paper parameters are still aligned:

```python
params = ['λ_KLS', 'λ_KLS_eff', 'g_TC²', 'g_TC', 'b₀', 'dim(M)', '|ρ|²',
          'm_ν(seesaw)', 'ξ(bridge)', 'H₀', 'DM:B', 'GW_f1', 'GW_f2', 'GW_f3']
```

## File Locations

- Main: `~/Desktop/六维流形时空理论/SL6C_Unified_Geometric_Dynamics_Framework.md`
- Desktop copy: `~/Desktop/SL6C_Unified_Geometric_Dynamics_Framework.md`
- Always sync both copies.

**Validated on**: V63+V16+V17 audit cycles (2026-08-07). File grew from 278→400 lines across 3 update rounds.
