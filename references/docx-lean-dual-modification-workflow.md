# DOCX + Lean Dual Modification Workflow

## When to Use

When modifying a scientific paper that has BOTH a .docx manuscript AND a .lean formal proof file,
and the modifications span parameter fixes, new sections, cross-references, and figure additions.

Validated on V17 DOCX (6D_Spacetime_Phase_Differentiation_Expanded_V17.docx) + V17 Lean
(6D_Spacetime_Formal_Proof_V17.lean), 2026-08-05/06.

## Pre-Modification Phase

### 1. Read the DOCX structure first
```python
from docx import Document
doc = Document(docx_path)
for i, p in enumerate(doc.paragraphs):
    if p.text.strip():
        print(f"[{i}] {p.text[:100]}")
```
Identify all section boundaries (III.C, IV.A, IV.B, etc.) and their paragraph indices.

### 2. Verify Lean counts before touching the DOCX
```bash
grep -c "^theorem " *.lean
grep -c "^lemma " *.lean
grep -c "^(axiom|honest_axiom) " *.lean
wc -l *.lean
```
The DOCX abstract and FIG.9 counts drift from Lean over revisions — always verify
independently and update both.

### 3. Scan for stale parameter values in DOCX
```python
import re
full = '\n'.join([p.text for p in doc.paragraphs])
# Check for known stale values
for pat, label in [
    (r"b[_0]*\s*=\s*39", "b0=39"),
    (r"dim\s*=\s*20(?!\d)", "dim=20"),
    (r"95 theorems|156 theorem|454 axioms", "stale counts"),
]:
    print(f"{label}: {len(re.findall(pat, full, re.IGNORECASE))}")
```

## Modification Phase

### P0 (Immediate Fixes)
1. Fix parameter residues with `for run in p.runs: run.text = run.text.replace(old, new)`
2. Remove duplicate/obsolete sections by deleting their XML elements:
   ```python
   for idx in range(end_idx - 1, start_idx - 1, -1):
       paras[idx]._element.getparent().remove(paras[idx]._element)
   ```
3. Update theorem/axiom counts in both DOCX abstract AND Lean header comment

### P1 (Section Insertions)
**CRITICAL: FORWARD iteration for paragraph insertion.**

When inserting multiple paragraphs before a reference paragraph R:
```python
contents = [para_A_text, para_B_text, para_C_text]  # desired order
for content in contents:  # FORWARD — do NOT use reversed()
    new_p = ref_para.insert_paragraph_before(content)
```
This produces A, B, C in correct order before R. Using `reversed()` silently
reverses the content.

For mixed content (headings + body paragraphs), insert them all in one FORWARD
pass against the same reference paragraph:
```python
items = [
    ("heading", "Section Title"),
    ("body", "First paragraph..."),
    ("body", "Second paragraph..."),
]
for item in items:
    if item[0] == "heading":
        h = ref.insert_paragraph_before(item[1])
        h.style = doc.styles['Heading 3']
    else:
        ref.insert_paragraph_before(item[1])
```

### P1 (Cross-References)
Add at minimum:
- Abstract: mention companion paper's mechanism
- Main body: cite specific sections/theorems
- Conclusion/validation: add a dedicated "Unified Framework Validation" paragraph
  before the Theorem Summary

### Figure Generation
Use matplotlib with:
- `matplotlib.use('Agg')` for headless
- Cold colors: #2E86AB (blue), #A23B72 (purple)
- SciencePlots + no-latex if available
- Avoid Unicode math symbols in labels (use ASCII: lambda, tau, ->, etc.)
- Save at 200 DPI to desktop

## Post-Modification Verification

### 1. Section order scan
Re-run the paragraph index scan and verify all sections appear in logical order
with increasing indices.

### 2. Residue sweep
Re-run the stale parameter scan — should return zero for all meaningful errors.
Accept only deliberate historical notes (e.g., "claims were based on b0=39; hereby retracted").

### 3. Cross-reference count
```python
v63_count = full.count('[V63]')
print(f"[V63] references: {v63_count}")
```
Aim for >= 4 total references with at least 3 section-level citations.

### 4. Lean header sync
The Lean header comment should match the DOCX abstract:
- Line count
- Theorem + lemma count
- Axiom count
- Cross-paper reference block

### 5. File list confirmation
```
DOCX: 6D_Spacetime_Phase_Differentiation_Expanded_V17.docx
Lean: 6D_Spacetime_Formal_Proof_V17.lean
Figures: FIG10_*.png, FIG11_*.png, FIG12_*.png
```

## Pitfalls

1. **Reversed paragraph order.** Using `reversed()` with `insert_paragraph_before()`
   silently reverses content. Always FORWARD.

2. **XML element removal invalidates indices.** When deleting multiple paragraphs,
   iterate from highest index to lowest to avoid shifting.

3. **LaTeX in DOCX runs.** Parameters like `\\(b_0=39\\)` are split across runs.
   Search in `p.text` (full paragraph text) but fix in individual `run.text`.

4. **Historical notes contain stale values.** Retraction statements like
   "claims were based on b0=39; hereby retracted" deliberately mention old values.
   Do NOT remove these — they are documenting the correction.

5. **Figure captions inserted in wrong section.** Always verify the reference
   paragraph is in the Figures section (before APPENDIX), not accidentally
   before a theorem or conclusion.

6. **Lean header has its own stale counts.** The Lean file header comment is
   hand-maintained and diverges from actual `grep` counts. Always verify with
   grep before updating.

7. **python-docx may not be in the agent's venv.** Install with:
   ```bash
   .venv/Scripts/python -m ensurepip
   .venv/Scripts/python -m pip install python-docx
   ```
