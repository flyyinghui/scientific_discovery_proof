# Triple-Paper Parallel Modification Pattern

**Validated**: 2026-08-06 on V17 × V63 × V16 (SL6C trilogy, 11 P0-P2 modifications).

## When to use

When a cross-paper review/audit document identifies modifications across 3 distinct papers, each with a DOCX manuscript + Lean formal proof file. The modifications are independent per paper (no inter-paper ordering dependency).

## Pattern

```
Parent agent:
  1. Read unified framework document (knowledge source)
  2. Spawn 3 parallel subagents via delegate_task(tasks=[...])
  3. Wait for all 3 to complete (~12 min total)
  4. Run single execute_code script for post-hoc numeric verification
  5. Report results
```

### Subagent template (per paper)

```
Goal: "Apply <PaperName> P0-P2 modifications: <list of items>"
Context: "
Paper path: <absolute path>
DOCX: <filename.docx>
Lean: <filename.lean>
Framework reference: <path to unified MD>

<PaperName>-specific modifications from the framework (Section 7):

<numbered list of specific modifications with:
  - What to change
  - Where to find it in the DOCX
  - Exact text to insert/replace
  - Verification criteria>
"
Toolsets: ["file", "terminal"]
```

## Key requirements for subagent context

1. **Exact file paths** — absolute paths, never relative
2. **Search anchors** — tell the subagent what paragraph/section text to search for
3. **Exact insertion text** — provide the full text to insert, not "add a note about X"
4. **Verification criteria** — what numbers to verify after insertion
5. **Pitfalls to avoid** — e.g., FORWARD order for paragraph insertion, match DOCX style

## Performance

| Metric | Sequential | Parallel (3 subagents) |
|--------|:----------:|:---------------------:|
| Wall time | ~25 min | **~12 min** |
| Token usage | ~4.5M (cumulative) | ~4.6M (parent + 3 children) |
| Error cascading | One failure blocks all | Failures isolated per paper |

## Post-modification verification

After all subagents complete, run a single `execute_code` script that independently recomputes ALL shared parameters across all three papers:

- λ_KLS, λ_KLS_eff
- b₀ (both Dirac and Weyl conventions)
- g_TC², g_TC
- N_e
- DM:B ratio
- Seesaw chain (m₀, M_R, m_D, m_ν)
- Σm_ν, Δm²₂₁, Δm²₃₂
- f₁, f₂, f₃

Flag any deviation >1% as P0. Flag any deviation >0.1% as P1.

## Pitfalls

1. **Subagent may miss text in complex DOCX formats.** If the subagent reports "text not found in DOCX," provide a larger search context with surrounding lines.
2. **Numeric values in the framework MD may have typos.** Always recompute from first principles in the verification step. (Example: framework wrote `(2/3)×15×(1/2)=5` for b₀ but correct Dirac formula is `(4/3)×15×(1/2)=10`.)
3. **Seesaw chain self-consistency is NOT transitive.** Verifying m_D ≠ verifying m_ν ≠ verifying m₀. Test ALL three links independently.
