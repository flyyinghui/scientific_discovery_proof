# GitHub Repository References

## Core Components

### Stage 0 — Math Agent Framework
- **Repository**: [nousresearch/math-agent-framework](https://github.com/nousresearch/math-agent-framework)
- **Copy on disk**: `D:\AI_for_Science\math-agent-framework\`
- **Description**: Bridge between LLM conceptual reasoning and deterministic symbolic computation. 5-level verification pipeline (symbolic → FOC/SOC → boundary → counterexample → chain consistency). Multi-agent adversarial verification (Proposer+Critic+Judge). MCP-ready with 60+ auto-registered tools.

### Stage 4 — AI-Scientist V2
- **Repository**: [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2)
- **Copy on disk**: `D:\AI_for_Science\AI-Scientist-v2\`
- **Description**: Workshop-level automated scientific discovery. BFTS (Best-First Tree Search) experimentation, automatic LaTeX paper writing, LLM peer review. First system with AI-generated papers accepted at ML workshops.

## Supporting Infrastructure

### Formal Verification
- **[leanprover/lean4](https://github.com/leanprover/lean4)** — Lean 4 theorem prover
- **[leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4)** — Mathlib4 mathematical library
- **MathCode V2** — Multi-tool Lean 4 verification (axiom_checker / proof_stats / sorry_analyzer)

### Neural Memory
- **Neural Memory Brain** — 170K+ neuron persistent concept association graph with LIF neuron model, semantic embeddings, and neurotransmitter-modulated connectivity.

### LLM Backend
- **[deepseek-ai/deepseek-v4](https://api.deepseek.com)** — Primary reasoning and code generation model
- **OpenAI Python SDK** — API client (`base_url=https://api.deepseek.com`)

## Pipeline Orchestration

### SimpleTES
- **ArXiv**: [2604.19341](https://arxiv.org/abs/2604.19341)
- **Description**: (C,L,K,Φ) evaluation-budget scaling with rpucg DAG-aware selector

### SciExplorer
- **ArXiv**: [2509.24978](https://arxiv.org/abs/2509.24978) (Nägele & Marquardt, PRX 2025)
- **Description**: LLM-driven autonomous physics model discovery through numerical experimentation

### Hermes Agent Skills
All components are registered as Hermes Agent skills at `~/.hermes/skills/`:
- `scientific-discovery-proof/` — This pipeline (orchestrator)
- `sciexplorer/` — Stage 1 numerical discovery
- `simpletes/` — Stage 2 candidate ranking
- `physics-proof-engine/` — Stage 3 formal proof
- `research/ai-scientist-v2/` — Stage 4 paper generation
- `neural-memory-brain/` — Brain bridge (shared infrastructure)

## Installation Map

| Component | Disk Path | GitHub |
|:---|---|:---|
| Math Agent Framework | `D:\AI_for_Science\math-agent-framework\` | `nousresearch/math-agent-framework` |
| AI-Scientist V2 | `D:\AI_for_Science\AI-Scientist-v2\` | `SakanaAI/AI-Scientist-v2` |
| PPE Core | `D:\ai_for_science\physics_proof_engine\` | — |
| Neural Memory Brain | `D:\ai_for_science\neural_memory_brain\` | — |
| Lean Formalizations | `D:\AI_for_Science\lean_formalizations\` | `leanprover-community/mathlib4` |
| MathCode V2 | `D:\ai_for_science\mathcode\` | — |
