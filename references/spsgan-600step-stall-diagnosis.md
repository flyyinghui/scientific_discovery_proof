# SPSGAN 600-Step Evolution Stall — Diagnosis & Fix

**Date**: 2026-08-07 | **Code**: space-time-12-d-5-SPSGAN_CUDA.py (22,979行)

## Symptom
Simulation runs 600+ steps with all cosmic phases stuck at `quantum_foam`.
CSV output shows `trace_A_matter = trace_A_bh = trace_A_de = 0.0` throughout.

## Root Causes (3 simultaneous failures)

### P0-1: THETA_STABLE = THETA_CRIT → Zero Phase Gap

```
Config.THETA_STABLE = 11.667  (L9556)
Config.THETA_CRIT  = 11.667  (L9557)
→ Both equal → no crystalline/matter intermediate phase
```

`update_from_trace_A` at L1285 had a LOCAL hardcode THETA_STABLE=11.0, but main loop reads Config values (both 11.667). The only gap was in a code path not used by the main simulation.

**Fix**: `THETA_STABLE = 11.0` in Config (L9556). This creates a gap (11.0 → 11.667) for phase transitions.

### P0-2: trace_A Decays Too Slowly

CSV data (775 steps):
- trace_A: 63.5 → 52.8 (Δ=-10.7, ~0.014/step)
- To reach THETA_CRIT=11.667 needs ~4000 more steps

**Fix**: Add geometric decay accelerator in `update_cosmic_phase_and_partitions`:
```python
decay_rate = 0.003
trace_A_val *= math.exp(-dt * decay_rate * 150.0)
```

### P0-3: KLS PID Target Mismatch

```python
KLSPIDController(target_gap=2.0)  # L15837 class default
# Should be: target_gap=11.667 (λ_KLS_eff)
```

**Fix**: Change default from 2.0 → 11.667 in both:
- `KLSPIDController.__init__` default (L10087)
- `SL6C_CosmicSimulation.__init__` instantiation (L15837)

### P0-4: b₀ Formula Error

```
Config.B0_BETA = 34.0  # Used C₂(adj)=12, should use h^∨=6
# Correct: b₀ = (11/3)×h^∨ − (4/3)×Nf×½ = 22−10 = 12
```

## Diagnostic CSV Analysis Pattern

When analyzing cosmic simulation CSVs:
1. Check `current_phase` column — if all identical, phase logic is frozen
2. Check `trace_A_matter/bh/de` — all zero means never left QUANTUM_FOAM
3. Check `THETA_stable` and `THETA_crit` — if equal, no gap
4. Check `expansion_rate` and `universe_radius` — if constant, cosmology frozen
5. Check `KLS_spectral_gap` vs `target_gap` — if different by >5×, PID is fighting

## Full Fix List

| # | Location | Before | After |
|:--:|------|------|------|
| 1 | L9556 | THETA_STABLE=11.667 | 11.0 |
| 2 | L9544 | B0_BETA=34 | 12 |
| 3 | L10087 | target_gap=2.0 | 11.667 |
| 4 | L15837 | target_gap=2.0 | 11.667 |
| 5 | L1285 | local hardcode | read from Config |
| 6 | L15913 | trace_A stored raw | with decay accelerator |
