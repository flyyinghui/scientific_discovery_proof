# Gemini Co-Scientist (arXiv:2608.26701) → Scientific-Discovery-Proof Skill Mapping

**Source paper**: "Accelerating Scientific Research with Gemini in the Real-World"
(Schmidgall et al., 2026, arXiv:2608.26701, cs.AI). An execution-grounded extension of
Google's Co-Scientist multi-agent system (original in *Nature* 2026), validated across
materials science (MXene/TMD CVD synthesis), biology (E. coli swarming prediction), and
computer science (Agent_H medical AI architecture discovery).

**Fed into brain**: 2026-08-29, +40 neurons (14 concept / 13 finding / 13 evidence), source `arXiv:2608.26701`.
**Code generated**: `/mnt/d/ai_for_science/paper_code/2608.26701/code.py` (34.8K chars, 7 algorithms, runs clean).

---

## Why this paper matters for this skill

Co-Scientist is the closest industrial counterpart to our five-stage pipeline
(MAF → SciExplorer → SimpleTES → PPE-V5.1Hybrid → AI-Scientist V2). It independently
converged on the same core insight we encoded in **Stage 3.5 (Formal Proof Consistency
Audit)**: *a "0 sorry" proof / "valid" paper whose claims are not grounded in the actual
execution logs is MORE dangerous than one with visible errors.* The paper's "Hallucination
Clipping" module is literally Stage 3.5, renamed. Its quantitative result (severe
methodological errors reduced 100% → 24%) independently validates the audit-gate design.

## Paper → Skill mapping (concrete, actionable)

### 1. Hallucination Clipping → strengthens Stage 3.5

**Paper mechanism** (deterministic reliability module):
- Cross-reference **every quantitative claim** in the drafted paper against the raw
  experimental log `E_log`.
- If a paper claims a value that is NOT in the logs → **targeted rewrite** of that claim.
- Joint objective (manuscript optimization):
  `Score(P) = S_reviewer(P) − λ1·S_plagiarism(P) − λ2·S_hallucination(P, E, E_log)`

**Skill translation** — add a *numeric claim cross-reference* as an L1 (mechanical,
stdlib-only) check in Stage 3.5:
1. Regex-extract every numeric constant from the paper (e.g. `\d+\.?\d*` near units like
   GeV / eV / dimensionless ratios / axiom counts).
2. Verify each against the Lean proof's ground truth (`grep` the constant in `proof.lean`).
3. A paper claim with **no Lean grounding** → WARN; a claim that **contradicts** Lean → BLOCK.
4. Frame the gate as the joint objective above: `final_score = reviewer_score − λ1·plag − λ2·halluc`.
   This converts Stage 3.5 from a boolean gate into a **quantifiable quality metric**.

This subsumes the existing defect classes #3 (axiom-count mismatch) and #4 (phantom
theorem) — the paper gives them a single named mechanism + objective function.

### 2. Three-Phase Code Development Protocol → improves Stage 3 (Lean generation)

**Paper mechanism** (execution-grounded code development):
- **Scaffolding**: write logic on a *minimal subset* under a short timeout
  (`T_scaffold = 600s`) to confirm the environment is correct.
- **Transition**: replace mock data / temporary stubs with real variables.
- **Full-Scale Execution**: run the finalized program on the full dataset/hardware.

**Skill translation** — this is exactly the "skeleton stubs" Lean-generation pattern we
already discovered empirically (see `physics-proof-engine/references/deepseek-trivial-proof-pitfall.md`),
now with a principled three-phase name:
- **Scaffolding** = generate the proof skeleton with `:= by trivial` / `:= True` stubs first
  (compiles fast, validates the statement structure).
- **Transition** = replace stubs with real tactic bodies (nlinarith/field_simp/ring/exact …_axiom).
- **Full-Scale** = assemble the full proof and run MathCode verification.

Recommend making this the *canonical phrasing* in Stage 3 documentation.

### 3. Evolutionary selection with TrueSkill + UCB → improves Stage 2 (SimpleTES)

**Paper mechanism** (ideation):
- Initial candidates at high sampling temperature `τ = 1.6` (creativity).
- Ranked by a **Reflection Agent** + **TrueSkill Bayesian skill rating** + **UCB exploration**
  (`score + c·√(ln N / n)` bonus for under-sampled candidates).
- Crossover `p_c = 0.7`, mutation `1 − p_c = 0.3`, `G = 10` generations.

**Skill translation** — SimpleTES already does candidate ranking (rpucg DAG-aware selector,
γ=0.9). Add the **UCB exploration bonus** for under-sampled hypotheses: a candidate seen
few times gets a `+c·√(ln N / n)` exploration bonus so promising-but-unexplored hypotheses
aren't starved. This is a one-line change to the ranking score.

### 4. Two-Layer Safety Gateway → NEW pre-stage (genuine gap)

**Paper mechanism**:
- **Layer 1 (initial screening)**: high-level ethics module evaluates research direction.
- **Layer 2 (continuous oversight)**: LLM evaluator monitors ideas/plans in real-time.
- Result: 98.7% of harmful directions refused; 96.3% of resulting ideas rated safe.

**Skill translation** — the pipeline currently has NO dual-use safety screening. For
physics/discovery work with dual-use potential (e.g. nuclear, gain-of-function, weaponizable
materials), add a lightweight **Stage −1 safety gate**:
- Layer 1: a one-shot ethics classification of the conjecture.json direction.
- Layer 2: per-stage output scan for dangerous experimental plans.
- Gate rule: any BLOCK halts the pipeline before Stage 0.

This is the single clearest *new capability* the paper reveals we are missing.

---

## Quantified takeaways (memorize these numbers)

| Paper metric | Value | Relevance to skill |
|---|---|---|
| Severe methodological errors (baseline → with reliability modules) | 100% → 24% | Validates Stage 3.5 audit-gate ROI |
| Hallucination penalty weight | λ2 (tunable) | Map to audit gate's WARN/BLOCK severity |
| Plagiarism penalty weight | λ1 (tunable) | Map to cross-ref originality check |
| Ideation creativity temperature | τ = 1.6 | SimpleTES candidate generation |
| Crossover probability | p_c = 0.7 | SimpleTES candidate recombination |
| Evolution generations | G = 10 | SimpleTES iteration budget |
| Scaffolding timeout | T_scaffold = 600s | Stage 3 Lean scaffold timeout |
| Rejection-sampling candidates | n = 16 | Any VLM-based figure/layout selection |
| Safety: harmful-direction refusal | 98.7% | Stage −1 gate target |
| Safety: resulting ideas rated safe | 96.3% | Stage −1 gate target |
| Agent_H clinical-harm reduction | p = 0.0486 | Statistical significance bar for eval |
