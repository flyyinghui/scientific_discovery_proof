# Scientific Discovery & Proof

**A five-stage, formally-verified pipeline for physics conjecture discovery → symbolic audit → formal proof → consistency gate → publication.**

This skill orchestrates five specialist sub-skills into one end-to-end workflow, with a hardened proof-quality gate that distinguishes *logical consistency* (0 sorry) from *physical content* (non-tautological derivation). It is the formal-verification backbone behind the SL(6,C) program (CGICE, spacetime phase evolution, right-handed-neutrino condensation, gravitational-wave signatures, and the light-speed interface).

---

## Pipeline Architecture

```
Stage −1   Two-Layer Safety Gateway          (dual-use screening)
Stage 0    MAF Symbolic Audit                (SymPy identity / counterexample)
Stage 1    SciExplorer Numerical Validation  (P0 fatal-error detection)
Stage 1.5  Planted-Truth + Constant Gate     (numerical sanity doors)
Stage 2    SimpleTES Candidate Ranking       (rpucg DAG-aware + UCB bonus)
Stage 2.5  Curriculum Planner                (proof-variant task queue)
Stage 3    PPE-V5.1Hybrid Formal Proof       (MCTS + ABC Bee Colony, Lean 4)
Stage 3.5  Consistency Audit                 (axiom self-consistency, L1/L2)
Stage 3.5b Physical Content Audit            (definitional-tautology gate)
Stage 3.5c Proof DAG Audit                   (redundant lemmas / dangling refs)
Stage 3.6  Frozen-Evaluator Evolution        (RSI-style recursive self-improvement)
Stage 3.7  Proof Policy Meta-Optimizer       (strategy-level optimization)
Stage 4    AI-Scientist V2 Paper Generation  (IMRAD + Nature figures)
```

**Gate rule:** any BLOCK in Stages 3.5 / 3.5b / 3.5c halts paper generation.

---

## Key Capabilities

- **Honest axiomatization + golden gate.** Conditional theorems whose `#print axioms` depends only on classical logic (`propext`, `Classical.choice`, `Quot.sound`) — zero research-level axioms.
- **Definitional-tautology gate** (`physical_content_audit.py`). Detects proofs that compile with 0 sorry but carry no physical content (`unfold def + linarith`), catching the "honest but thin" failure mode.
- **Formal verification discipline.** Lean 4 + Mathlib, MathCode three-tool verification (axiom_checker / proof_stats / sorry_analyzer).
- **Multi-agent review.** Five-agent hybrid review for final audits; L1 (mechanical) and L2 (LLM structural) audit layers.
- **Recursive self-improvement.** Replay simulator, ε-greedy mutation strategies, causal-memory triples, and a frozen proof-template library (few-shot memory reuse).

---

## Quick Start

```bash
# Full pipeline
python scripts/pipeline_orchestrator.py \
  --conjecture /path/to/conjecture.json \
  --output /path/to/output/ \
  --stages 1,2,3,4

# Standalone gates
python scripts/proof_consistency_audit.py --lean proof.lean --output /tmp/audit.json
python scripts/physical_content_audit.py  --lean proof.lean --output /tmp/content.json
python scripts/proof_dag_audit.py         --lean proof.lean --output /tmp/dag.json

# Recursive self-improvement
python scripts/stage36_evolution.py --lean proof.lean --generations 3 --output /tmp/evo/
python scripts/proof_policy_optimizer.py --archive /tmp/evo/archive.jsonl --rounds 3
```

Set `DEEPSEEK_API_KEY` (or a compatible OpenAI-style endpoint) in the environment. Most audit gates are stdlib-only and run offline.

---

## Scripts

| Script | Role |
|---|---|
| `pipeline_orchestrator.py` | End-to-end orchestration with gates |
| `proof_consistency_audit.py` | Stage 3.5 L1 mechanical audit |
| `proof_consistency_audit_l2.py` | Stage 3.5 L2 LLM structural audit |
| `physical_content_audit.py` | Stage 3.5b definitional-tautology gate |
| `proof_dag_audit.py` | Stage 3.5c proof-dependency DAG audit |
| `stage36_evolution.py` | Frozen-evaluator evolution loop |
| `deep_refinement.py` | Deep refinement (broad-then-deep) |
| `proof_policy_optimizer.py` | Proof-strategy meta-optimization |
| `replay_strategies.py` | Replay simulator + mutation strategies |
| `proof_template_library.py` | Frozen proof-pattern template library |
| `curriculum_planner.py` | Stage 2.5 curriculum generation |
| `strategy_explorer.py` / `preproof_decomposer.py` | Pre-proof strategy / decomposition |
| `axiom_ablation.py` | Axiom-necessity ablation |
| `reference_verification.py` | Zero-hallucination citation check |
| `method_code_alignment.py` | Paper ↔ Lean bidirectional alignment |
| `planted_truth_gate.py` | Numerical planted-truth control |
| `constant_certify.py` | PSLQ closed-form constant certification |
| `rsihub_lean_bridge.py` | RSIHub Lean evolution bridge |

---

## Integrated Frameworks

The pipeline incrementally grafts unique mechanisms from recent recursive-self-improvement and verification research, without rewriting the five-stage core:

- **Gemini Co-Scientist** — safety gateway, hallucination clipping, UCB exploration
- **RSIHub** — frozen-evaluator evolution
- **Dream-RSI** — replay simulator, off-policy feedback, strategy meta-optimization
- **RSIAgent** — curriculum planner, three-failure-mode diagnosis, causal-memory triples, proof-template reuse
- **ScientistTwo** — reference verification, method-code alignment, axiom ablation
- **Colosseum** — targeted falsification, defect localization
- **BootLoops** — planted-truth gate, constant certification

See `references/` for per-framework integration notes and pitfalls.

---

## Dependencies

- Python 3.11+ (audit gates are stdlib-only; LLM stages need `openai`)
- Lean 4 + Mathlib (for formal proof and kernel checks)
- `sympy`, `scipy` (symbolic audit)
- A DeepSeek-compatible LLM endpoint (or any OpenAI-style API)

---

## Version

**v2.15.0** — physical-content audit gate (definitional-tautology detection) integrated into Stage 3.5b.

## License

Apache-2.0
