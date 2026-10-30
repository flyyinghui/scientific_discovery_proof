# SPSGAN ↔ Unified Framework Parameter Crosscheck Template

**Use when**: A CUDA simulation codebase (SPSGAN, PINN, etc.) shares parameters with a theoretical framework document.

## Procedure

### 1. Extract canonical parameters from framework

Read the unified framework MD. Build a parameter table:

| Parameter | Canonical Value | Source |
|------|------|------|
| g_TC | 2.60 | FRG IR fixed point |
| λ_KLS | 35 | Harish-Chandra spectral geometry |
| λ_KLS_eff | 35/3≈11.667 | 3D equipartition |
| b₀ | 12 | (11/3)×h^∨−(4/3)×Nf×½, h^∨=6 |
| THETA_STABLE | 11.0 | Strong log-concavity boundary |
| THETA_CRIT | 11.667 | Weak Poincaré failure |
| GW f₁/f₂/f₃ | 4.5e11/1.71/1e-9 Hz | Phenomenological |
| H₀ | 67.42 | Planck 2018 calibration |
| DM:B | 5:1 | DOF counting 75/15 |

### 2. Grep code for every parameter

```bash
grep -n "g_TC\\|G_TC\\|lambda_KLS\\|THETA_\\|B0_BETA\\|target_gap" simulation.py
```

Build a comparison table:

| Parameter | Framework Value | Code Value | Deviation |
|------|:--:|:--:|:--:|
| g_TC | 2.60 | 2.60 | ✓ |
| THETA_STABLE | 11.0 | 11.667 | **✗ (kills phase gap)** |
| THETA_CRIT | 11.667 | 11.667 | ✓ |
| b₀ | 12 | 34 | **✗ (3× error, C₂≠h^∨)** |
| KLS_PID target | 11.667 | 2.0 | **✗ (6× error)** |

### 3. Check threshold inequalities

The most insidious pattern: two thresholds that should differ are equal.

```python
# BAD — zero phase gap:
THETA_STABLE = 11.667
THETA_CRIT  = 11.667

# GOOD — phase gap exists:
THETA_STABLE = 11.0
THETA_CRIT  = 11.667
```

Also check: **local hardcodes** that override Config values.

```python
# L1285 — local override bypasses Config:
THETA_STABLE = 11.0   # hardcoded, ignores Config.THETA_STABLE
```

### 4. Check trace_A evolution rate

```python
# From CSV: trace_A decay rate
Δ = trace_A[0] - trace_A[-1]         # e.g., 63.5 - 52.8 = 10.7
rate = Δ / len(steps)                 # e.g., 10.7/775 = 0.014/step
steps_to_threshold = (trace_A[-1] - THETA_CRIT) / rate  # (52.8-11.7)/0.014 ≈ 2940
```

If `steps_to_threshold > 2000` → simulation won't exit quantum_foam within current run.

### 5. Verify phase decomposition is active

Check CSV: if `trace_A_matter`, `trace_A_bh`, `trace_A_de` are all zero → `safe_partition_update` never leaves QUANTUM_FOAM branch.

### 6. Fix & validate

```bash
python -c "import py_compile; py_compile.compile('simulation.py', doraise=True)"
python -c "
import re
with open('simulation.py') as f:
    c = f.read()
s = float(re.search(r'THETA_STABLE\s*=\s*([\d.]+)', c).group(1))
cr = float(re.search(r'THETA_CRIT\s*=\s*([\d.]+)(?!ICAL)', c).group(1))
print(f'THETA_STABLE({s}) < THETA_CRIT({cr}): {s < cr}')
"
```

**Validated on**: SPSGAN d-5 (22,979 lines) vs SL(6,C) Unified Framework (2026-08-07). Found 4 parameter mismatches causing 600-step phase evolution stall.
