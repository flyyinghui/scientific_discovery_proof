# Stage 0 — MAF Symbolic Audit

**Math Agent Framework bridge for algebraic pre-verification of physical conjectures.**

## Overview

MAF (Math Agent Framework) provides deterministic symbolic verification that complements LLM-driven numerical exploration. It catches algebraic errors that numerical methods miss — such as sign errors, missing factors, and dimensional inconsistencies.

## What MAF Checks

| Level | Check | Method | Catches |
|:---|:---|---|:---|
| L1 | Symbolic identity | `sympy.simplify(LHS − RHS) == 0` | Algebraic sign errors, factor mistakes |
| L2 | FOC/SOC | `sympy.diff()` + `sympy.solve()` | Wrong extremum type (min vs max) |
| L3 | Boundary behavior | `sympy.limit(x→∞)` + `subs()` | Asymptotic violations |
| L4 | Counterexample search | `scipy.optimize` 50K iterations | Numerical counterexamples |
| L5 | Chain consistency | Cross-equation symbolic validation | Inconsistent parameter chains |

## Multi-Agent Adversarial Verification

```
Proposer: "Claim X follows from axioms A1–A5 via path P"
    ↓
Critic:   "Path P fails because of counterexample C"
    ↓
Judge:    "Claim ACCEPTED / REJECTED / NEEDS_REVISION (2–1 vote)"
```

## Integration

MAF co-calls with SciExplorer in three modes:
1. **Parallel (P0)**: MAF.symbolic_audit || SciExplorer.p0_validate
2. **Serial (P1)**: SciExplorer.p1_filter → MAF.verify_5level → expand/trim
3. **MAF-only**: Multi-agent adversarial verification on proof claims

## Dependencies

```bash
pip install sympy scipy numpy
```

## API

```python
from maf_bridge import MAFBridge
bridge = MAFBridge()

# Symbolic audit
result = bridge.symbolic_audit(conjecture_dict)
# → {'status': 'PASS'|'FAIL'|'COND', 'checks': [...], 'fatal_errors': [...]}

# 5-level verification
report = bridge.verify_5level(claims_list, param_ranges_dict)

# Adversarial verification
verdict = bridge.adversarial_verify(claim, context)
```

## Related

- **Framework**: math-agent-framework (D:\AI_for_Science\math-agent-framework\)
- **Integration doc**: `../references/papers.md` — MAF-SDP Integration details
