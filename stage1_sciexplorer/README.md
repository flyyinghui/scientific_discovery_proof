# Stage 1 — SciExplorer: Numerical Discovery

**LLM-driven autonomous physics model discovery agent with numerical pre-validation.**

## Overview

Based on **"Agentic Exploration of Physics Models"** — Maximilian Nägele & Florian Marquardt, Physical Review X (2025), [arXiv:2509.24978](https://arxiv.org/abs/2509.24978).

SciExplorer implements an autonomous agent loop: **observe → reason → experiment → analyze → repeat**. It discovers equations of motion, Hamiltonians, and physical laws through LLM-guided numerical experimentation.

## Architecture

```
User Task → SciExplorerAgent
              ├── LLM (DeepSeek v4-flash thinking mode)
              ├── Tool Registry
              │   ├── run_experiment(params) → numerical simulation
              │   ├── run_code(python_code) → arbitrary analysis
              │   ├── plot(code) → visual inspection
              │   └── save_result(answer) → stop & finalize
              └── External Memory (arrays, metadata, exploration history)
```

## Agent Loop

1. **Observe** — Receive task and initial system description
2. **Reason** — LLM plans next experiment based on memory
3. **Experiment** — Execute numerical simulation with chosen parameters
4. **Analyze** — Run code analysis, generate plots, inspect results
5. **Repeat** — Up to N steps (default 100) until save_result called
6. **Summarize** — Produce human-readable summary of discoveries

## Usage

```python
from sciexplorer_agent import SciExplorerAgent, PhysicsScenario

agent = SciExplorerAgent(
    model="deepseek-v4-flash",
    api_key="...",
    max_steps=100
)

scenario = PhysicsScenario(
    name="Dynamical System Discovery",
    system_description="A nonlinear oscillator with unknown damping",
    experiment_fn=lambda params: run_simulation(params),
    ground_truth="d²x/dt² + γ dx/dt + ω²x = 0"
)

result = agent.explore(scenario)
print(result.summary)
```

## Co-Call with MAF

In the SDP pipeline, SciExplorer co-calls with MAF Bridge:

| Mode | SciExplorer Role | MAF Role |
|:---|:---|---|
| P0 (parallel) | LLM experiment generation | SymPy algebraic audit |
| P1 (serial) | Numerical feasibility filter | 5-level formal verification |

## Pitfalls

1. **v4-flash thinking mode**: For JSON extraction, disable thinking (`thinking: {type: disabled}`) — thinking mode dumps tokens into `reasoning_content`, leaving `content` empty.
2. **Large prompts**: 80K+ char prompts with thinking mode can exceed 300s timeout. Break into two phases.
3. **ExperimentRunner**: Must be extended with actual numerical simulation code — the skeleton provides the interface only.

## Reference

- **Paper**: Nägele, M. & Marquardt, F. (2025). "Agentic Exploration of Physics Models." *Physical Review X*. arXiv:2509.24978v6.
- **Build log**: `sciexplorer-build-log.md` — full session log from paper extraction to agent generation.
