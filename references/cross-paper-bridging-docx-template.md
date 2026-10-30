# Cross-Paper Bridging DOCX Generation Template

Use when deriving a physical mechanism from one paper within the unified framework
and bridging it to another paper's arguments, producing a standalone DOCX with
concrete edit instructions.

## 7-Section DOCX Structure

### I. Unified Axiom System Recap
- Parameter matrix table (11+ shared parameters: gauge group, lambda_KLS, dim, g_TC, b0, C2(adj), CGICE, FRG, Monge time)
- P0-P3 axiom hierarchy
- Cross-paper P0 validation status (SciExplorer 8 checks)

### II. Mechanism Derivation (e.g., Neutrino Condensation)
- CW effective potential with correct field content
- Dimensional transmutation: phi0 formula and numerical value
- Phase transition/crystallization analogy: order parameter, nucleation, supercooling
- Downstream consequences (seesaw masses, flavor hierarchy)

### III. Duality Theorem (e.g., Time-Charge)
- Monge OT derivation of emergent quantity (time, charge, etc.)
- Conjugate momentum identification
- Duality relation and physical implications

### IV. Bridging to Target Paper
- Causal chain table: Epoch | Temperature | Target Phase | Source Mechanism | Observable
- Key bridging theorems (3 bridges minimum, each with independent derivation paths)
- Convergence points: quantity | target value | source value | validation strength

### V. Modification Instructions
- **P0 Immediate Fixes**: fatal errors (wrong constants, stale counts) — grep commands + replacements
- **P1 Short-Term Additions**: new subsections to insert, cross-references to add — with exact DOCX insertion points
- **P2 Long-Term Goals**: joint analyses, unified figures, merger candidates
- Specific edit locations table: DOCX section | insertion anchor | content summary | priority

### VI. Verification Checklist
- SciExplorer P0 re-run
- grep for residual stale values (must return zero)
- Theorem/axiom count audit against Lean files
- Cross-reference resolution check
- addprevious() insertion order verification
- GW frequency mapping consistency
- Figure style compliance (SciencePlots + Microsoft YaHei + no-latex)

### VII. Key Equations Summary
- Condensation/bridge equations
- Duality equations
- Unified framework parameters
- Mechanism-specific bridge equations

## python-docx Patterns

```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
style = doc.styles['Normal']
style.font.name = 'Microsoft YaHei'
style.font.size = Pt(11)

# Heading
doc.add_heading('Title', level=0)

# Centered colored subtitle
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = sub.add_run('Subtitle text')
run.font.color.rgb = RGBColor(46, 134, 171)  # Cold blue

# Table with style
table = doc.add_table(rows=1, cols=N)
table.style = 'Light Shading Accent 1'

# Save
doc.save(output_path)
```

## Pitfalls

1. **python-docx not in Hermes venv.** Install: `.venv/Scripts/python -m ensurepip` then `pip install python-docx`. The global Python may have it but execute_code's sandbox sees only the venv.
2. **V17 DOCX filename**: `6D_Spacetime_Phase_Differentiation_Expanded_V17.docx` — not `V17_Paper_Manuscript.md` (doesn't exist).
3. **GW frequency band disambiguation**: V17 ET peak (~10^2 Hz) = CDM crystallization; V63 LISA peak (10^-2–10 Hz) = neutrino condensation supercooling. Different physical processes, same frequency neighborhood — must explicitly map in the unified table.
4. **Theorem/axiom count drift**: Always grep the actual Lean file before stating counts in the bridging DOCX. Abstract claims are routinely stale.
5. **Keep derivations self-contained**: The bridging DOCX must re-derive key equations rather than just citing — the reader may not have the source paper open.
