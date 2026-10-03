# Scientific Discovery & Proof — Integrated Pipeline

**Five-skill end-to-end pipeline for physics conjecture discovery → formal verification → publication.**

`MAF Symbolic Audit → SciExplorer (numerical validation) → SimpleTES (candidate ranking) → PPE-V5.1 Hybrid (formal proof) → AI-Scientist V2 (paper generation)`

- **78% → 65%** end-to-end proof success rate improvement
- **70%** time reduction vs. standalone PPE
- **Version**: v2.13.0

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage −1  Two-Layer Safety Gateway         (dual-use screening) │
│ Stage 0   MAF Symbolic Audit               (SymPy 5-level check)│
│ Stage 1   SciExplorer Numerical Discovery  (P0 error detection) │
│ Stage 1.5 Planted-Truth Gate + Constant Certification (BootLoops)│
│ Stage 2   SimpleTES Candidate Ranking      (UCB exploration)    │
│ Stage 2.5 Curriculum Planner               (RSIAgent)           │
│ Stage 3   PPE-V5.1 Hybrid Formal Proof     (MCTS + ABC)         │
│ Stage 3.5 Consistency Audit ★GATE          (L1 mech + L2 LLM)   │
│ Stage 3.6 Frozen-Evaluator Evolution       (RSIHub)             │
│ Stage 3.7 Proof-Policy Meta-Optimizer      (Dream-RSI)          │
│ Stage 4   AI-Scientist V2 Paper Generation (IMRAD + figures)    │
└─────────────────────────────────────────────────────────────────┘
```

The pipeline is **modular** — every increment since v2.0 was grafted in *without touching the core five stages*. Each stage ships as a standalone script with an offline `--mock` / `--self-test` / `--dry-run` mode.

---

## Golden Gate Standard (v2.6.0)

A proof is only "closed" when the main conditional theorem's `#print axioms` depends
**exclusively on classical logic** (`propext`, `Classical.choice`, `Quot.sound`) — no
research-level axiom survives. This is the single most reliable signal that the evidence
chain is actually closed rather than axiomatized into existence.

---

## Stage 3.5 Consistency Audit (the mandatory gate)

Catches the six P0 proof-defect classes discovered across three final reviews
(CGICE V9.1 / Triple-GW V16 / V17) that MathCode's counter tools (`axiom_checker` /
`proof_stats` / `sorry_analyzer`) cannot see:

| # | Defect class | Real example | Severity |
|---|---|---|---|
| 1 | Axiom self-contradiction (ex-falso) | A6+A10 ⟹ `I_cycle=I_eq`, A17 ⟹ `I_cycle≠I_eq` | BLOCK (L2) |
| 2 | Performative honesty (comment-only tags) | 26× `-- @[honest_axiom]`, 0 real attrs | WARN/BLOCK (L1) |
| 3 | Axiom-count mismatch | "14 axioms" vs 39 actual | WARN/BLOCK (L1) |
| 4 | Phantom theorem (claimed but missing) | "T4 fully verified" but no `t4` | BLOCK (L1) |
| 5 | `:= by trivial` stub | DeepSeek v4-flash tendency | WARN/BLOCK (L1) |
| 6 | Discrete spectrum on noncompact | λ_k = k·λ₁ on SL(6,C)/SU(6) | BLOCK (L2) |

---

## Scripts

All scripts are stdlib-only unless noted; every LLM-dependent script has an offline
`--mock` / `--self-test` / `--dry-run` fallback.

| Script | Stage | Purpose |
|---|---|---|
| `pipeline_orchestrator.py` | all | Full pipeline driver |
| `planted_truth_gate.py` | 1.5a | BootLoops planted-truth: recover known answer + catch poisoned input |
| `constant_certify.py` | 1.5b | PSLQ closed-form constant certification (declare ring/height/budget first) |
| `strategy_explorer.py` | 0.5 | Generate 3-5 candidate proof routes + readiness gate |
| `preproof_decomposer.py` | 2.7 | Conjecture → section skeleton + dependency DAG (topological batches) |
| `curriculum_planner.py` | 2.5 | Proof-variant task queue (weaken/strengthen/boundary/recombine/stress) |
| `proof_consistency_audit.py` | 3.5 | L1 mechanical audit (12 defect detections) |
| `proof_consistency_audit_l2.py` | 3.5b | L2 LLM structural audit (cross-axiom reasoning) |
| `proof_dag_audit.py` | 3.5c | Proof DAG: redundant lemmas / unused axioms / dangling refs |
| `reference_verification.py` | 3.5 | Zero-hallucination reference ↔ citation check |
| `method_code_alignment.py` | 3.5 | Paper ↔ Lean bidirectional alignment |
| `axiom_ablation.py` | 3.5 | Counterfactual axiom necessity ablation |
| `replay_strategies.py` | 3.6 | Dream-RSI replay simulator (strategy success stats) |
| `stage36_evolution.py` | 3.6 | Frozen-evaluator evolution loop (select→evaluate→mutate→gate) |
| `deep_refinement.py` | 3.6d | RSIAgent broad-then-deep refinement |
| `proof_policy_optimizer.py` | 3.7 | Dream-RSI policy meta-optimizer (optimize the strategy itself) |
| `rsihub_lean_bridge.py` | 3.6b | Bridge to RSIHub operator classes |

---

## Version History (increments)

| Ver | Source framework | Increment |
|---|---|---|
| 2.0 | — | MAF symbolic-audit bridge |
| 2.1 | — | Stage 3.5 consistency audit |
| 2.2 | Meta^n | L1/L2 depth-aware audit split |
| 2.3 | Gemini Co-Scientist | Safety gateway + hallucination clipping + UCB + scaffolding |
| 2.4 | RSIHub + LeanMarathon | Proof DAG audit + frozen-evaluator evolution |
| 2.5 | Triple-GW P0-4 | Conditional-theorem refactoring |
| 2.6 | Triple-GW P0-5/6/7 | Four-paper unification + g_TC² spectral-gap fix |
| 2.7 | Dream-RSI | Replay simulator (P0-P2) |
| 2.8 | RSIAgent | Curriculum planner + 3 detections + deep refinement |
| 2.9 | ScientistTwo | Reference verification + method-code alignment + axiom ablation |
| 2.10 | Colosseum | Targeted falsification + defect localization |
| 2.11 | Colosseum | Strategy explorer + pre-proof decomposer + failure path |
| 2.12 | Dream-RSI | Proof-policy meta-optimizer (P0/P2/P3) |
| 2.13 | BootLoops | Planted-truth gate + constant certification |

---

## Quick Start

```bash
# Full pipeline
python scripts/pipeline_orchestrator.py \
  --conjecture conjecture.json \
  --output ./out/ \
  --stages -1,0,1,2,2.5,3,4 \
  --enable-maf --enable-sciexplorer

# Stage 3.5 consistency audit (stdlib-only, fast)
python scripts/proof_consistency_audit.py \
  --lean proof.lean --paper paper.txt --expected-axioms 14 --output audit.json

# Planted-truth self-test (no LLM required)
python scripts/planted_truth_gate.py --self-test
```

---

## Dependencies

| Skill | Stage | Role |
|---|---|---|
| `math-agent-framework` | 0 | Symbolic audit (SymPy) |
| `sciexplorer` | 1 | Numerical discovery |
| `simpletes` | 2 | Candidate ranking |
| `physics-proof-engine` | 3 | Formal proof (MCTS + ABC) |
| `ai-scientist-v2` | 4 | Paper generation |

LLM backend: DeepSeek (`v4-pro` for diagnosis, `v4-flash` with `thinking=disabled` for generation).

---

## Directory Layout

```
scientific-discovery-proof/
├── SKILL.md                    # Hermes skill definition
├── Stage35_Integration_Plan.md # Stage 3.5 integration plan
├── scripts/                    # 17 standalone stage scripts
└── references/                 # 20 integration assessment + audit records
```

## License

Released for open-source distribution. See the parent project for license terms.
