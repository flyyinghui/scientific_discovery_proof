# Cross-Paper Theorem Relation Classification (4-Dimension Taxonomy)

Taxonomy for classifying theorem-level relationships across papers sharing a common
mathematical framework. Developed and validated on the V17×V63×V14 SL(6,C) trilogy
(18 relations identified: 5 MV, 6 BR, 4 CA, 3 CO).

## Four Relation Types

### MV — Mutual Validation
Two theorems from different papers derive the SAME quantitative result through
INDEPENDENT mathematical paths.

**Strength classification:**
- **Extreme**: Identical value, fully independent paths, no shared parameters
  Example: V17 T2_KLS (Witten Laplacian λ=35/3) vs V63 T_D1 (V-D action g_TC²=8π²/λ_KLS)
- **Strong**: <1% difference, different methods, minimal shared assumptions
  Example: V17 N_e=161 (phase space dim formula) vs V14 N_e=160 (slow-roll integral)
- **Moderate**: Same order of magnitude, related mechanisms, some shared axioms

**Verification criteria:**
1. Both theorems produce a measurable numeric prediction
2. The prediction equations are structurally different (not trivially equivalent)
3. No shared free parameters between the two derivation paths
4. Numeric values agree to within stated precision

### BR — Bridging
A theorem from one paper provides the MATHEMATICAL MECHANISM connecting two
concepts that appear separately in another paper.

**Verification criteria:**
1. The bridge can be expressed as a mathematical identity (not just "similar idea")
2. The bridge connects specific named theorems or axioms, not vague "concepts"
3. The direction is asymmetric: PaperA.TheoremX → PaperB.ConceptY↔ConceptZ

**Examples:**
- Atiyah-Singer index analysis (V17) → V-D geometric effective action (V63): both yield g_TC²=8π²/λ_KLS
- CGICE 4-equation SDE (V17) → CGWB Cartan bridge (V63): compact→non-compact transition mechanism
- Witten Laplacian spectrum (V17) → KLS emergent phase (V14): shared λ_KLS through different mechanisms

### CA — Causal
The PHYSICAL PROCESS described by one theorem TEMPORALLY PRECEDES and enables
the process described by another theorem.

**Verification criteria:**
1. Both processes share a common energy scale or temperature
2. The earlier process creates the initial conditions for the later process
3. The timeline is physically coherent (no reversed causality)
4. Energy/temperature ordering is consistent with known physics

**Examples:**
- V17 Phase I (quantum foam, T~10¹⁶ GeV) → V63 CW condensation (φ₀~10¹⁴ GeV)
- V17 Phase II (CDM crystallization, T~10¹³ GeV) → V63 Seesaw (M_R~8×10¹³ GeV)
- V17 timeline → V14 GW peaks (three phases → three frequency bands)

### CO — Complementary
Two theorems address the SAME PHYSICAL PHENOMENON at DIFFERENT SCALES or through
DIFFERENT MATHEMATICAL FORMALISMS, with neither subsuming the other.

**Verification criteria:**
1. Both address the same physical phenomenon (e.g., dark matter density, time emergence)
2. The formalisms are genuinely different (not just notation)
3. Neither derivation is a special case of the other
4. The two descriptions are not contradictory at any shared scale

**Examples:**
- CW effective potential (V63, microscopic) ↔ Three-phase cosmology (V17, macroscopic)
- Seesaw mass (V63, particle physics) ↔ CDM crystallization (V17, cosmology)
- Stern-Brocot hierarchy (V63, algebraic) ↔ KLS spectral gap (V17, geometric)

## 5-Step Classification Procedure

1. **Extract all theorems**: Parse each paper's Lean file (or DOCX) for theorem/lemma declarations.
2. **Build cross-reference matrix**: For every theorem pair (PaperA.ThmX, PaperB.ThmY), check physical domain overlap.
3. **Classify by shared parameter**: If both produce the same numeric prediction → check MV criteria. If one provides mechanism connecting two concepts in the other → check BR criteria.
4. **Trace energy scales**: If both share a temperature/energy regime → check CA criteria. If different scales → check CO criteria.
5. **Assign confidence**: Each classification gets a confidence level (High/Medium/Low) based on how many of the verification criteria are met. Low-confidence classifications need explicit caveats.

## Pitfalls

1. **Don't force MV where independence fails.** If two theorems share a critical free parameter, they are NOT independent validations. Flag as "correlated" not MV.
2. **Don't conflate BR with CO.** BR is asymmetric and mathematical; CO is symmetric and phenomenological.
3. **Same name, different meaning.** b₀ in SPSGAN is a Betti number (topology), b₀ in V17/V63 is a gauge beta function coefficient. Always trace definition chains.
4. **"Derived" claims need audit.** Papers often claim derivation when parameters are actually fitted or calibrated. Use SciExplorer P0 + MAF symbolic audit to verify.
5. **Geometric independence IS a strength, not a gap.** When a geometric path (V14) converges with a phenomenological path (V63) without sharing their critical parameters, the convergence validates BOTH.
