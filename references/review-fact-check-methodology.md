# Reviewer Feedback Triage — 3-Level Filter Methodology

**Validated**: 2026-08-07 | V16×V17×V63, 2 reviewer documents, ~22 claims evaluated

## Core Principle

A reviewer document is a HYPOTHESIS to be verified, not a to-do list.

## 3-Level Filter

### Level 1: Fact-Check Each Claim

For each claim in the reviewer document:
1. Verify against CURRENT DOCX+Lean — not the version the reviewer may have read
2. Recompute any arithmetic the reviewer cites
3. Check whether the issue was already fixed in a prior round

Common failure modes:
- Reviewer based on EXPIRED version (g_TC=0.5 claims after 2026-08-06 fix)
- Reviewer used wrong physical scale (confused CW UV boundary φ₀~10^16 with seesaw condensation scale φ₀~1.67×10^14)
- Reviewer cited a parameter from wrong paper (V16 doesn't use g_TC at all, reviewer attributed V17's old value)
- Reviewer arithmetic is wrong (claimed M_R=4.8×10^15 when paper uses 1.67×10^14)

### Level 2: Classify Valid Claims

| Severity | Criteria | Example |
|:---:|------|------|
| P0 | Would block publication, numerical contradiction | "g_TC has two values in same paper" |
| P1 | Major concern, needs explicit clarification | "H₀ claimed as prediction but is calibration" |
| P2 | Minor, improvement suggestion | "f₁ has no direct detectability" |

### Level 3: Generate Clean Issue List

Output a structured MD with:
1. Only VALID issues (rejected claims in separate section with reasoning)
2. Priority-ranked fix list
3. Verification checklist
4. Clear "before/after" modification targets

## Templates

- `三论文审阅_客观问题清单_20260807.md` — 14 objective issues from 15 claims (1 rejected)
- `DM统一性审阅_客观问题清单_20260807.md` — 4 objective issues from 8 claims (4 rejected)

## Rejection Template

```markdown
| R-N | 指控 | 驳回理由 |
|-----|------|----------|
| R-1 | [reviewer claim] | **事实错误**: [specific reason with recomputed numbers] |
| R-2 | [reviewer claim] | **基于过期版本**: [what was fixed and when] |
```

## Pitfalls

1. Do NOT include subjective ratings ("score 2/10") in the objective issue list
2. Do NOT include editorial advice ("不建议打包投稿") as fix items
3. Always run the unified numerical verification AFTER generating the issue list — it catches things the reviewer missed
