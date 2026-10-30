# Hybrid Review Multi-Paper Pipeline

**Validated**: 2026-08-06 | V16×V17×V63, 53 issues (19 P0/19 P1/15 P2)
**Extended**: 2026-08-07 | Circular reasoning audit variant, 3 papers, 303s parallel audit

## When to Use Which Variant

- **Full pipeline** (4 phases below): When you have a review document listing N modifications across M papers — the modification-application pipeline.
- **Circular reasoning audit** (3-phase variant): When you need to detect self-referential axioms, phantom dependencies, and circular parameter chains WITHOUT applying fixes. Use the patterns in [`references/circular-reasoning-patterns.md`](references/circular-reasoning-patterns.md). This variant: Phase 1 (parallel subagent audit focusing on P1/P2/P3 patterns) → Phase 2 (synthesize findings into audit report) → Phase 3 (unified numerical verification). No fix phase. Validated 2026-08-07: 3 subagents × ~150s each = 303s wall time for ~10,500 Lean lines across 3 papers.

## 4-Phase Pipeline (Modification-Application Variant)

### Phase 1: Parallel Subagent Audit (3 papers, ~7 min)

```python
delegate_task(tasks=[
  {goal: "Audit V16: read DOCX+Lean, flag ALL numerics/cross-refs/stale-values",
   context: "Paper path, unified framework values to cross-check", toolsets: ["file","terminal"]},
  {goal: "Audit V17: ...", ...},
  {goal: "Audit V63: ...", ...},
])
```

Each subagent checks: (a) numerical self-consistency within paper, (b) cross-paper parameter consistency against shared framework, (c) stale values from prior fixes, (d) Lean-DOCX alignment on theorem/axiom counts and parameter values, (e) reference completeness.

### Phase 2: Synthesize Review (1 min)

Read subagent outputs, cross-reference their findings, generate a structured review with P0/P1/P2 severity classification, file paths, and line numbers. Key cross-cutting checks:
- λ_KLS: same value in all 3 papers?
- b₀, g_TC: consistent derivation?
- DM:B, H₀: same labeling convention (calibrated vs predicted)?
- Seesaw chain, SB masses: same numerics?

### Phase 3: Parallel Subagent Fixes (~12 min)

⚠️ **DOCX repacking caution**: Subagents on Windows/MSYS cannot repack DOCX after XML edits (no `zip` command). They may unzip the file to `_docx_tmp/` and leave it broken. After subagents complete, check: `ls *.docx` — if the main file is missing, restore from `*_BACKUP.docx` and use `execute_code` with the script in [`references/docx-repack-windows.md`](references/docx-repack-windows.md) to repack. Prevention: tell subagents "If you cannot repack, leave modified XML at _docx_tmp/word/document.xml for parent to repack."

### Phase 4: Unified Numeric Verification (1 min)

Run `python references/unified-numerical-verification.py` (see [`references/unified-numerical-verification.py`](references/unified-numerical-verification.py)) as a single `execute_code` call. The script recomputes ALL shared parameters independently and flags any deviation. Key checks:
- λ_KLS, λ_KLS_eff
- b₀ from C₂(adj)
- g_TC², g_TC from both D1 relation and FRG
- Seesaw: m_D, y_ν, m_ν
- SB: m₁,m₂,m₃, Δm², χ²
- Bridge: ξ, η_Cartan
- GW: f₁,f₂,f₃ consistency
- DM:B tension check

## Pitfalls Discovered

1. **V4Flash review catches what hybrid review misses**: A thinking-mode LLM review often identifies cross-cutting convention issues (λ_KLS=35 vs 35/3 usage) that per-paper audits miss because each paper is internally consistent but the convention mapping breaks at the cross-paper level.

2. **Two rounds minimum**: The first hybrid review catches structural errors (C₂(adj), false theorems, stale counts). The second round (V4Flash/thinking) catches semantic drift (which λ_KLS enters g_TC², whether H₀ is prediction or calibration, whether seesaw m₀ is input or output). Budget for at least 2 rounds.

3. **DOCX + Lean dual verification**: After every round of fixes, verify BOTH the DOCX and Lean were updated. Subagents sometimes fix one and miss the other.

4. **Stale values survive 2+ rounds**: Even after P0-6 seesaw fix and V4Flash review, V63 still had ξ=1.766 in DOCX vs 1.747 in Lean. The very last round caught it. Conclusion: always run a final `grep` for OLD values after every fix round.

## Validated Numbers

53 issues found across first review round, 9 residual after second round, 0 after third.
