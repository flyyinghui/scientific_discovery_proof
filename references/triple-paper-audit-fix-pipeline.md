# Triple-Paper Audit + Fix Pipeline

**Full-cycle workflow** validated on V63×V17×V16 (2026-08-07). 53 issues resolved in ~45 minutes.

## Pipeline Stages

### Phase 1: Parallel Audit (3 subagents, ~7 min)

```python
delegate_task(tasks=[
  {"goal": "Audit V63 Lean+MD for circular reasoning...", "context": "...", "toolsets": ["file","terminal"]},
  {"goal": "Audit V17 Lean+DOCX for circular reasoning...", "context": "...", "toolsets": ["file","terminal"]},
  {"goal": "Audit V16 Lean+MD for circular reasoning...", "context": "...", "toolsets": ["file","terminal"]},
])
```

Each subagent receives: framework parameter table, audit checklist, exact file paths.

### Phase 2: Synthesize Review (~3 min)

Read all 3 subagent outputs. Cross-reference findings. Generate structured review with:
- P0/P1/P2 severity classification
- Exact file paths and line numbers
- Cross-cutting checks (λ_KLS, g_TC, seesaw, GW, H₀)

### Phase 3: Parallel Fixes (3 subagents, ~12 min)

Each subagent handles one paper's full fix set. Key rules:
- Pass `toolsets=["file","terminal"]` — NOT `["patch"]` (patch on binary DOCX fails)
- DOCX edits: use python-docx only, never `sed` or `zip`
- Report all changes when done

### Phase 4: Unified Numeric Verification (~2 min)

Single `execute_code` script that independently recomputes all shared parameters.

### Phase 5: DeepSeek V4 Pro Final Validation (~5 min)

```python
delegate_task(goal="Verify modifications across Lean+MD+DOCX...", ...)
```

## P0 Recurring Pitfalls

1. **Subagent DOCX destruction**: Subagent unzips DOCX → can't repack (MSYS lacks `zip`) → DOCX left broken. Defense: parent always has recovery script ready.
2. **Stale values in appendices**: After every fix round, `grep` for OLD values across entire DOCX+Lean+MD. Appendices survive 3+ rounds.
3. **LaTeX double-escaping**: `patch` tool doubles LaTeX backslashes in MD files. Fix with bytes-level replace in `execute_code`.
4. **execute_code line-prefix corruption**: `read_file` in execute_code returns `NN|` prefix. Strip before writing back.

## Time Budget

| Phase | Time | Parallel? |
|------|:--:|:--:|
| Audit (3 papers) | 7 min | Yes (3 subagents) |
| Synthesize | 3 min | No |
| Fixes (3 papers) | 12 min | Yes (3 subagents) |
| Numeric verify | 2 min | No |
| DeepSeek verify | 5 min | Yes (1 subagent) |
| **Total** | **~45 min** | |

For CGICE-specific audits, add a Phase 0: "List all claimed equations → grep each → classify IMPLEMENTED/DECLARED/ABSENT" (~5 min per paper).

**Validated on**: V63×V17×V16 (2026-08-07). 53 issues: 19 P0 + 19 P1 + 15 P2.
