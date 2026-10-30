# Cross-Paper Audit & Modification Checklist Generation — Full Workflow

Proven 9-phase pipeline for auditing multiple papers sharing a unified mathematical
framework. Validated on the SL(6,C) V17×V63×V14 trilogy (2026-08-05), producing a
20-item prioritized modification checklist across 3 papers.

## When to Use

When you need to systematically audit 2+ papers sharing a common theoretical
foundation (same gauge group, same core parameters, overlapping physical domains)
and generate a consolidated, priority-ranked modification list.

## 9-Phase Pipeline

### Phase 1: Load Unified Axiom System
- Read the cross-paper unified axiom document (DOCX or MD)
- Extract the shared parameter matrix (lambda_KLS, g_TC, b0, dim, H0, ratios)
- Note any parameters declared as P0/P1/P2 severity

### Phase 2: Lean File Grep Extraction
Run for EACH paper's `.lean` file:
```bash
grep -c 'theorem '  <file>.lean
grep -c 'lemma '    <file>.lean
grep -c 'axiom '    <file>.lean
grep -c 'sorry'     <file>.lean
grep -c '\[honest.axiom\]' <file>.lean
```
Extract all numeric constant definitions (lambda_KLS, g_TC, b0, dim, H0, CDM ratio).
Compare against what the paper's DOCX abstract claims.

### Phase 3: SciExplorer P0 Pre-Validation
Run all 8 standard checks (see sciexplorer-p0-prevalidation.md):
1. CW minimum existence
2. Beta function coefficient (C2(adj) audit)
3. FRG fixed point existence
4. Seesaw parameter self-consistency
5. Mass hierarchy formula
6. Dimension/coset consistency
7. GW frequency range cross-check
8. RG flow matching

### Phase 4: Per-Paper DOCX + Lean Dual Audit
For each paper, compare:
- Abstract claims vs grep-verified Lean counts
- Main text derivations vs Lean axiom/theorem declarations
- Appendix claims vs actual Lean proof bodies
- Numeric constants in text vs Lean definitions

Use the appendix-audit-methodology.md 6-step procedure for appendices.

### Phase 5: Cross-Paper Parameter Matrix
Build a table: Parameter | V17 | V63 | V14 | Alignment.
Flag any mismatch >0.1% as P0. Flag consistent values with different derivation
paths as MV (mutual validation) strengths.

### Phase 6: Cross-Paper Theorem Classification
Apply the MV/BR/CA/CO taxonomy from cross-paper-theorem-classification.md.
Classify every identified theorem pair. Document the verification criteria met.

### Phase 7: Priority-Ranked Modification List
Classify every issue as P0-FATAL (mathematically false), P1-MAJOR (overstated
claims, missing honesty), P2-MINOR (notation, metadata), P3-COSMETIC.

Sort: P0 first, then P1, then P2. Each entry needs: file path, specific section
reference, exact issue description, proposed action, and severity rationale.

### Phase 8: Lean File Fixes (Automated)
Apply the simplest fixes via `patch` to Lean files:
- Update header comments with grep-verified counts
- Rename conflicting parameter names (e.g., kappa → kappa_inst/kappa_geo)
- Add audit-date stamps and honesty notes

### Phase 9: DOCX Abstract Updates (Scripted)
Use python-docx (via terminal script) to update:
- Theorem/axiom counts in abstracts
- Add phenomenological/honesty notes where derived claims are overstated
- Always create `.bak` copies before editing

## Key Pitfalls Discovered During V17×V63×V14 Audit

1. **Grep `^\s*(?:theorem|lemma)\s+\w+` fails on Lean files.**
   Lean comments and docstrings contain the word "theorem" in prose, confusing
   regex counts. Use plain `grep -c 'theorem '` (with trailing space) from the
   terminal — it correctly matches only declarations.

2. **Abstract counts are ALWAYS stale.**
   In all three papers, the DOCX abstract claimed theorem/axiom counts that
   differed from the grep-verified Lean counts by 30-60%. Never trust the
   abstract — always grep-verify independently.

3. **Parameter naming collisions hide in comments.**
   The `kappa` collision in V63 was easy to spot at definition sites but
   also appeared in 15+ comment-only references. Always grep for the bare
   parameter name and review every occurrence.

4. **RG flow sections accumulate contradictory versions.**
   When a paper undergoes multiple revisions, old RG calculations (using
   corrected parameters) sometimes remain alongside new ones. The V17 DOCX
   had two overlapping §III.D subsections with contradictory b0 and N_f values.
   Always check for duplicate section headings with conflicting content.

5. **GW peak frequency assignments drift between paper versions.**
   V17 and V14 assign different physical processes to overlapping frequency
   bands. Always build a cross-paper frequency-to-process mapping table
   before claiming convergence.

## Output Template

The modification checklist should follow this structure:
```
# TITLE
## Executive Summary
## I. Unified Axiom System — Base Parameters (VERIFIED)
## II-IV. Per-Paper Issues (P0-P3)
## V. Cross-Paper Harmonization Items
## VI. Lean Formal Proof Cross-Audit
## VII. Priority-Action Summary
## VIII. What Is Correct (No Action Needed)
## IX. Verification Methodology
## Appendix: File Paths
```

## Tool Stack
- `grep` for Lean file counts
- `read_file` for DOCX extraction
- `execute_code` (Python + math + SymPy) for numeric validation
- `patch` for Lean file edits
- `terminal` + python-docx script for DOCX abstract updates
- DeepSeek V4 Pro (t=0, max_tokens=16000) for reasoning
