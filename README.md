---
name: scientific-discovery-proof
description: >-
  Five-skill integrated pipeline for end-to-end scientific discovery and proof:
  MAF Symbolic Audit (SymPy algebraic) → SciExplorer (numerical validation)
  → SimpleTES (candidate ranking) → PPE-V5.1Hybrid (formal proof)
  → AI-Scientist V2 (paper generation). 78%→65% end-to-end proof success rate,
  70% time reduction vs standalone PPE. NEW: MAF bridge for symbolic pre-verification.
version: 2.1.0
tags: [pipeline, discovery, proof, orchestration, formal-verification, maf, symbolic, consistency-audit]
related_skills:
  - math-agent-framework (MAF stage 0)
  - SciExplorer (stage 1)
  - simpletes (stage 2)
  - physics-proof-engine (stage 3)
  - ai-scientist-v2 (stage 4)
---

# Scientific Discovery & Proof — Integrated Pipeline v2.1

Five-stage end-to-end pipeline for physics conjecture discovery → formal verification → publication.

**NEW in v2.1.0**: Stage 3.5 **Formal Proof Consistency Audit** — a mandatory gate between
formal proof (Stage 3) and paper generation (Stage 4) that catches the six P0 proof-defect
classes discovered across three final reviews (CGICE V9.1 / Triple-GW V16 / V17):
axiom self-contradiction (ex-falso), performative honesty (comment-only attribute tags),
axiom-count mismatch, phantom theorems, `:= by trivial` stubs, and discrete-spectrum-on-noncompact errors.

**NEW in v2.0**: MAF (math-agent-framework) bridge for symbolic pre-verification.

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Stage 0 — MAF Symbolic Audit (NEW v2.0)                          │
│   ├─ SymPy 符号恒等式检验 (simplify(LHS-RHS)==0)                 │
│   ├─ 5-Level 验证 (符号/FOC/边界/反例/链)                        │
│   ├─ Multi-Agent 对抗验证 (Proposer+Critic+Judge)                │
│   ├─ 与 SciExplorer 并行/串行共调用                               │
│   └─ 输出: maf_audit.json + 符号错误标记                         │
├──────────────────────────────────────────────────────────────────┤
│ Stage 1 — SciExplorer + MAF 共调用: Numerical Discovery          │
│   ├─ SciExplorer P0 致命错误检测 (κ, V_eff, β 函数)              │
│   ├─ MAF P1 5层验证 + 50K反例搜索                                │
│   ├─ 工程控制论稳定性预审                                        │
│   └─ 输出: 5-8 个通过双重验证的候选假设                          │
├──────────────────────────────────────────────────────────────────┤
│ Stage 2 — SimpleTES: Candidate Ranking & Selection              │
│   ├─ C=4 并行链同时评估                                          │
│   ├─ rpucg DAG 感知选择器 (γ=0.9)                               │
│   └─ 输出: Top-3 精英候选 + 评分 + 排名理由                     │
├──────────────────────────────────────────────────────────────────┤
│ Stage 3 — PPE-V5.1Hybrid: Deep Formal Proof                     │
│   ├─ J-space 桥接矩阵 (Brain 170K 神经元)                        │
│   ├─ MCTS + ABC Bee Colony 双算法搜索                           │
│   ├─ MathCode 三工具验证 (axiom/proof/sorry)                    │
│   └─ 输出: Lean 4 证明 (0 sorry) + 定理/公理/引理统计           │
├──────────────────────────────────────────────────────────────────┤
│ Stage 3.5 — Formal Proof Consistency Audit (NEW v2.1.0) ★GATE   │
│   ├─ 公理自洽性 (爆炸原理检测: X=Y vs X≠Y 矛盾)                  │
│   ├─ 表演性诚实 (注释标签 vs 真实 Lean attribute)                │
│   ├─ 公理/定理计数一致性 (论文声称 vs Lean 实测)                 │
│   ├─ 定理存在性 (论文声称 "fully verified" vs Lean 实际缺失)     │
│   ├─ 空壳证明检测 (:= by trivial / := True)                     │
│   ├─ 离散谱 vs 连续谱 (非紧空间类别错误)                         │
│   └─ 输出: stage35_audit_report.json + PASS/WARN/BLOCK 门控     │
├──────────────────────────────────────────────────────────────────┤
│ Stage 4 — AI-Scientist V2: Paper Generation                     │
│   ├─ IMRAD 结构化论文                                            │
│   ├─ Nature 期刊图表                                             │
│   └─ 输出: DOCX + LaTeX + MD + 图表包                            │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Full pipeline with MAF
python scripts/pipeline_orchestrator.py \
  --conjecture /path/to/conjecture.json \
  --output /path/to/output/ \
  --stages 0,1,2,3,4 \
  --enable-maf \
  --enable-sciexplorer \
  --deepseek-key sk-...

# Stage 3.5 consistency audit standalone
cd scripts
python proof_consistency_audit.py \
  --lean /path/to/proof.lean \
  --paper /path/to/paper.txt \
  --expected-axioms 14 \
  --output /tmp/audit.json

# MAF bridge standalone
cd /mnt/d/AI_for_Science/math-agent-framework
python maf_bridge.py
```

## Stage 3.5 Consistency Audit (v2.1.0)

**Why it exists**: MathCode's three tools (`axiom_checker` / `proof_stats` / `sorry_analyzer`)
only COUNT — how many axioms, how many sorry, whether `has_sorry` is false. They cannot
detect whether the axioms **contradict each other**. Three final reviews (2026-08-16) proved
that a "0 sorry" proof whose axioms are mutually contradictory is MORE dangerous than a
proof with a visible sorry, because it grants false confidence of verification.

**Six P0 defect classes detected** (see `references/formal-proof-consistency-audit.md`):

| # | Defect class | Example (real) | Severity |
|---|---|---|---|
| 1 | Axiom self-contradiction (ex-falso) | CGICE V9.1: A6+A10 ⟹ `I_cycle=I_eq`, A17 ⟹ `I_cycle≠I_eq` | BLOCK |
| 2 | Performative honesty (comment-only tags) | Triple-GW V16: 26× `-- @[honest_axiom]`, 0 real attrs | WARN |
| 3 | Axiom-count mismatch | CGICE V9.1: "14 axioms" vs 39 actual | WARN |
| 4 | Phantom theorem (claimed but missing) | CGICE V9.1: "T4 fully verified" but no t4 in Lean | BLOCK |
| 5 | `:= by trivial` stub | DeepSeek v4-flash tendency | WARN |
| 6 | Discrete spectrum on noncompact | CGICE V9.1 A3: λ_k=k·λ₁ on SL(6,C)/SU(3,3) | BLOCK |

**Gate rule**: any BLOCK stops the pipeline before paper generation; WARNs are recorded
and forwarded to Stage 4 so the paper can honestly disclose them.

## MAF Bridge Integration

MAF provides symbolic verification that SciExplorer's LLM-driven experiments cannot:
- **SymPy identity checking**: `simplify(LHS - RHS) == 0` catches algebraic errors
- **5-Level verification**: symbolic → FOC/SOC → boundary → counterexample → chain
- **Multi-Agent adversarial**: Proposer+Critic+Judge pattern

MAF and SciExplorer **co-call** in three modes:
1. **Parallel (P0)**: MAF.symbolic_audit || SciExplorer.p0_validate → combined verdict
2. **Serial (P1)**: SciExplorer.p1_filter → MAF.verify_5level → expand/trim MCTS
3. **MAF-only**: Multi-agent adversarial verification on proof claims

See `references/MAF_SDP_Integration.md` for full documentation.

## Performance

| Metric | Standalone PPE | v1.0 Pipeline | v2.0 + MAF | v2.1 + Audit |
|:--|:--:|:--:|:--:|:--:|
| End-to-end success | 25% | 78% | ~65% (stricter gates) | ~65% + zero ex-falso |
| P0 error blockage | 30% | 2% | ~0.5% (symbolic+num) | ~0.5% + axiom-consistency |
| MCTS effective branching | 35% | 85% | ~75% (5-level filter) | ~75% |
| Counterexample discovery | 10% | 25% | ~50% (50K optimization) | ~50% |
| Axiom-contradiction escape | 100% | 100% | 100% | **~0%** (Stage 3.5 gate) |

## Dependencies

All five sub-skills must be installed:
- **MAF Bridge** (NEW): `pip install sympy scipy` + `sys.path` to math-agent-framework
- SciExplorer (skill)
- simpletes (skill + `pip install openai numpy`)
- physics-proof-engine (skill + MathCode)
- ai-scientist-v2 (skill)
- **Stage 3.5 audit**: stdlib-only (`python proof_consistency_audit.py`), no extra deps

## Environment

Requires `DEEPSEEK_API_KEY` for LLM calls across all stages.
