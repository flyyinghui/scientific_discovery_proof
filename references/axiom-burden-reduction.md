# Axiom Burden Reduction — Multi-Paper Formal Proof Systems

5-phase procedure for reducing axiom count in Lean 4 formal proof systems
while preserving logical completeness. Validated on the V17 SL(6,C) trilogy
(296 axioms → 32, 89% reduction).

## Phase 1: Extract

```bash
# Count all declaration types
grep -c "^axiom " paper.lean
grep -c "^theorem " paper.lean
grep -c "^lemma " paper.lean
grep -c "sorry" paper.lean
```

Extract all axiom names with line numbers, section context, and severity tags:
```python
import re
axioms = []
for i, line in enumerate(lines):
    m = re.match(r'^\s*axiom\s+(\w+)', line)
    if m:
        severity = 'P?'
        for s in ['P0', 'P1', 'P2', 'P3']:
            if f'[{s}' in context: severity = s; break
        axioms.append((i+1, m.group(1), severity))
```

## Phase 2: Classify

Categorize every axiom into one of 15+ domain buckets:
`GEOMETRY_GROUP`, `SPECTRAL`, `CGICE_DYNAMICS`, `MONGE_TIME`,
`BAKRY_EMERY`, `BOURGAIN`, `ATIYAH_SINGER`, `RENORMALIZATION`,
`STOCHASTIC`, `COSMOLOGY`, `GW`, `OBSERVATIONAL`, `GAUGE_FIXING`,
`PHASES`, `TOPOLOGY`, `TIME_CRYSTAL`, `DIMENSIONALITY`, `OTHER`.

## Phase 3: Map to Core

For each domain bucket, identify the MINIMAL set of irreducible axioms that
cannot be derived from others within the same domain. The 10 unified core
axioms from the cross-paper framework serve as the anchor:

| # | Core Axiom | Domains Covered |
|---|-----------|----------------|
| A1 | Cartan decomposition | GEOMETRY_GROUP, DIMENSIONALITY |
| A2 | Witten Laplacian | SPECTRAL |
| A3 | KLS spectral gap | SPECTRAL, COSMOLOGY |
| A4 | CGICE 4-SDE | CGICE_DYNAMICS, STOCHASTIC |
| A5 | Monge OT | MONGE_TIME |
| A6 | Bakry-Émery CD | BAKRY_EMERY |
| A7 | Bourgain slicing | BOURGAIN |
| A8 | M_Pl | OBSERVATIONAL (PARAM) |
| A9 | FRG/Wetterich | RENORMALIZATION |
| A10 | H₀ | COSMOLOGY (PARAM) |

## Phase 4: Re-classify

Each original axiom gets one of five tags:

| Tag | Meaning | Action |
|-----|---------|--------|
| `CORE` | Irreducible, maps to unified axiom | Retain as axiom |
| `DERIVE` | Provable from core axioms | Promote to `lemma` or `theorem` |
| `MERGE` | Duplicate of another axiom | Consolidate into single axiom |
| `PARAM` | Numerical input (P3) | Move to `§PARAMETERS` section |
| `TOOL` | Computational utility | Move to `def` or `notation` (not physical axiom) |

**Checklist before re-tagging:**
- [ ] Every P0 (speculative) axiom → `CORE` or `CONJECTURE`
- [ ] Every P3 (numerical) axiom → `PARAM`
- [ ] BRST/ghost axioms → `TOOL`
- [ ] P2 (standard physics) — check if derivable from core
- [ ] P1 (deep math) — check if reducible to fewer assumptions

## Phase 5: Update Dual Artifacts

### Lean File Updates
1. Update header comment block with new axiom/theorem/lemma counts
2. Add `§AXIOM_ARCHITECTURE` section describing the hierarchy
3. Add `[CORE]`, `[DERIVE]`, `[MERGE]`, `[PARAM]`, `[TOOL]` comment tags on each declaration
4. Update `:= True` stubs with `[sorry-NEEDS-MATHLIB]` markers

### DOCX Updates
1. Update Abstract axiom count
2. Add Axiom Architecture section before REFERENCES
3. Update Conclusions with reduction summary
4. Verify paragraph insertion order is FORWARD (not `reversed()`)

## Pitfalls

1. **grep overcounts** — `grep -c "axiom "` matches comments, audit notes, and string literals. Always follow up with Python regex extraction that matches only actual declarations.
2. **Section context is fragile** — the Lean file header `/-! ## §NAME` comments may not match the actual axiom location. Use `grep -n` line numbers as ground truth.
3. **Don't delete, re-tag** — never remove an axiom from the Lean file. If it's MERGE'd or promoted to lemma, add a comment `[was: axiom, now: lemma from A3]` so the lineage is traceable.
4. **DOCX insertion order** — when inserting paragraphs before a reference element, iterate FORWARD. `reversed()` silently reverses order.
5. **Counts in DOCX and Lean must agree** — always independently verify with grep after editing both files. Stale counts in abstracts are the #1 audit finding.
