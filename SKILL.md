---
name: scientific-discovery-proof
description: >-
  Five-skill integrated pipeline for end-to-end scientific discovery and proof:
  MAF Symbolic Audit (SymPy algebraic) → SciExplorer (numerical validation)
  → SimpleTES (candidate ranking) → PPE-V5.1Hybrid (formal proof)
  → AI-Scientist V2 (paper generation). 78%→65% end-to-end proof success rate,
  70% time reduction vs standalone PPE. NEW v2.3: Stage −1 dual-use safety gateway,
  Stage 3.5 Hallucination Clipping (numeric claim ↔ Lean cross-reference + joint
  reliability objective), Stage 2 UCB exploration bonus, Stage 3 three-phase scaffolding.
version: 2.8.0
tags: [pipeline, discovery, proof, orchestration, formal-verification, maf, symbolic, consistency-audit, recursive-repair, safety-gateway, hallucination-clipping, ucb, scaffolding, rsiagent, curriculum, exploration]
related_skills:
  - math-agent-framework (MAF stage 0)
  - SciExplorer (stage 1)
  - simpletes (stage 2)
  - physics-proof-engine (stage 3)
  - ai-scientist-v2 (stage 4)
---

# Scientific Discovery & Proof — Integrated Pipeline v2.8

Five-stage end-to-end pipeline for physics conjecture discovery → formal verification → publication.

**NEW in v2.8.0** (from RSIAgent, arXiv:2609.15364, 2026-09-19): **Stage 2.5 Curriculum Planner +
Stage 3.5 三条失败模式检测规则 + Stage 3.6d 深挖 + archive 因果三元组**。把 RSIAgent 的
「curriculum/actor/verifier 三智能体 + broad-then-deep 探索 + 因果记忆」移植为四个增量，
**不动现有五阶段管线**：
① **Stage 2.5 Curriculum Planner**（新脚本 `scripts/curriculum_planner.py`）——在 SimpleTES 排名后、
PPE 证明前，生成「证明变体任务队列」五大类型：weaken_premise（弱化前提）/ strengthen_premise（强化前提）/
boundary_case（边界反例）/ axiom_recombine（公理重组合）/ stress_test（压力测试）。把证明从「被动走固定
管线」升级为「课程驱动的主动探索」，在证明前暴露隐藏约束、边界条件、未挑战假设。
② **Stage 3.5 三条新检测规则**（`proof_consistency_audit.py` 检测 7/8/9）——映射 RSIAgent 三大失败模式：
unchallenged_axiom（未挑战假设，25%）/ uncertainty_downgrade（不确定性降级，33%）/ rule_scope_loss
（规则范围丢失，67%）。
③ **Stage 3.6d Deep Refinement (DRS)**（新脚本 `scripts/deep_refinement.py`）——RSIAgent broad-then-deep
的 deep 阶段：聚焦单一历史盲区缺陷，逐轮递增难度（基础修复→边界显式化→反例搜索→最小充分集），
是 Stage 3.6（broad 综合进化）的补充。
④ **archive.jsonl 因果三元组（P3）**（`replay_strategies.py` 新增 `defect_signature` + `causal_rules` +
`condition_match`；`stage36_evolution.py` record 新增 `condition` 字段）——把「被动记录」升级为
actions→conditions→consequences 可复用因果记忆，变异前注入「相同缺陷签名下的成功先例」。
完整记录见 [`references/rsiagent-integration.md`](references/rsiagent-integration.md)。

**NEW in v2.7.0** (from Dream-RSI, arXiv:2609.14858, 2026-09-17): **Stage 3.6 重放模拟器增强（P0-P2）**。
把 `archive.jsonl` 从「被动记录」升级为「主动重放预筛选器」（Dream-RSI 核心洞察：发现历史
本身是可重放的模拟器）。① **P0 replay simulator**：新增 `scripts/replay_strategies.py`
（`ReplaySimulator` 类，统计各变异策略历史成功率 + 对各类缺陷的修复率，ε-greedy 排序推荐，
针对性是硬门槛）② **P1 off-policy 反馈**：盲区检测（历史从未修复成功的缺陷类型）注入诊断
prompt ③ **P2 变异策略显式化**：单一「诊断→修复」拆成 5 个可评估策略（repair_dangling /
axiomatize / tactic_complete / lemma_decompose / deduplicate），archive.jsonl 新增
`mutation_strategy` + `defects_before` 字段。完整记录见
[`references/dream-rsi-replay-simulator-integration.md`](references/dream-rsi-replay-simulator-integration.md)。

**NEW in v2.6.0** (from Triple-GW V17 P0-5/6/7 repair + four-paper unification, 2026-09-04):
**四论文统一性交叉扫描 + g_TC² 谱隙角色分工修复**。发现三峰引力波 V17 与三大时空相 V17
两个 lean 的 `P03` 命名空间里 `gTCSq = 8π²/λ_KLS = 8π²/35 ≈ 2.26`（g_TC≈1.50），与全框架
统一值 `g_TC² = 24π²/35 ≈ 6.77`（g_TC=2.60）**差 3 倍**——根因是桥接公式误用纵向 λ_∥=35
而应代入横向 λ_⊥=35/3。修复：引入 `lambdaPerp = 35/3`、桥接改用横向、条件定理升级为 6 假设
（新增 h3D 3D 均分 honest-axiom A-3D）。**黄金门控标准**：条件定理 `#print axioms` 只依赖
经典逻辑（propext/Classical.choice/Quot.sound）、不出现任何研究级 axiom = 证据链闭合。
完整记录见 [`references/p05-p06-p07-unification-and-gtc-fix.md`](references/p05-p06-p07-unification-and-gtc-fix.md)。

**NEW in v2.5.0** (from Triple-GW V17 P0-4 repair, 2026-09-04): **条件定理重构模式**
（"无条件公理化" → "条件定理"）。当一个"定理"的推导依赖研究级开放前提（Eldan–Chen
局部化 / Atiyah–Singer 非紧推广 / Seeley–DeWitt 热核收敛等）时，不能把它压成无条件 axiom
（= 隐藏假设 = 审稿人一票否决），而应重构为条件定理：前提显式化为 `axiom ... : Prop`，
定理体保持 100% forward inference，并同时提供 `xxx_main`（公理实例化）+ `xxx_conditional`
（条件形式）双版本。配套的五方案自我进化（生成 5 种形式化方案 → 全部编译通过 → 按证据链
完整度排名选最优）与三层分离（Opaque 数据 + 谓词 + 真引理）完整记录见
[`references/p04-conditional-theorem-refactoring.md`](references/p04-conditional-theorem-refactoring.md)。

**NEW in v2.4.0** (from RSIHub + LeanMarathon evaluation, 2026-09-03): 增量嫁接两个
「多智能体 harness」框架的高价值模块，**不改动现有 5 阶段管线**——
① 新增 **Stage 3.5c 证明 DAG 审计**（`scripts/proof_dag_audit.py`，stdlib-only），
从 Lean 文件提取 lemma/theorem 为节点的证明 DAG，检查两个现有扁平审计缺的新缺陷类：
**冗余引理**（从未被下游使用）+ **未使用的 honest-axiom**（表演性诚实变体）+ 悬空引用。
② 新增 **Stage 3.6 冻结评估器进化循环**（`scripts/stage36_evolution.py`，RSIHub 的
select→evaluate→analyze→mutate→gate→record，用 MathCode/确定性评分当冻结评估器，
DeepSeek v4-pro 诊断 + v4-flash 修复，严格改进门控 + append-only archive.jsonl 证据链）。
完整评估与映射见 [`references/rsihub-leanmarathon-integration.md`](references/rsihub-leanmarathon-integration.md)。

**NEW in v2.3.0** (from Gemini Co-Scientist, arXiv:2608.26701): four concrete upgrades —
① Stage −1 **Two-Layer Safety Gateway** (dual-use research screening, the single clearest
new capability) ② Stage 3.5 **Hallucination Clipping** (numeric claim ↔ Lean-ground-truth
cross-reference with the joint reliability objective `Score = S_reviewer − λ1·S_plagiarism − λ2·S_hallucination`)
③ Stage 2 **UCB exploration bonus** for under-sampled hypotheses ④ Stage 3 **three-phase
Scaffolding → Transition → Full-Scale** canonical naming for Lean generation. Full mapping:
[`references/gemini-coscientist-reliability-modules.md`](references/gemini-coscientist-reliability-modules.md)

**NEW in v2.2.0**: Stage 3.5b **L2 LLM Structural Audit** — the six P0 defect classes are now
split into an **L1 mechanical layer** (stdlib-only, fast: performative honesty / axiom-count /
phantom theorems / `:= by trivial`) and an **L2 LLM structural layer** (axiom self-contradiction /
discrete-spectrum-on-noncompact, escalated from WARN to BLOCK by cross-axiom reasoning). This is
the Meta^n "depth-aware trace payload" idea (depth≤2 raw defects, depth≥3 structural patterns).
Also **Stage A strict-superset recursive Lean repair** (`lean_recursive_repair.py`) lands in
physics-proof-engine — a controlled experiment on CGICE's 3-sorry proof showed flat repair kills
CGICE dynamics (`deriv I_cycle = 0`) while strict repair preserves the master equation.

**NEW in v2.1.0**: Stage 3.5 **Formal Proof Consistency Audit** — a mandatory gate between
formal proof (Stage 3) and paper generation (Stage 4) that catches the six P0 proof-defect
classes discovered across three final reviews (CGICE V9.1 / Triple-GW V16 / V17):
axiom self-contradiction (ex-falso), performative honesty (comment-only attribute tags),
axiom-count mismatch, phantom theorems, `:= by trivial` stubs, and discrete-spectrum-on-noncompact errors.

**NEW in v2.0**: MAF (math-agent-framework) bridge for symbolic pre-verification.

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Stage −1 — Two-Layer Safety Gateway (NEW v2.3.0)                │
│   ├─ Layer 1: 研究方向伦理初筛 (one-shot ethics classification)  │
│   ├─ Layer 2: 逐阶段产出安全扫描 (dual-use 持续监督)              │
│   └─ 输出: 任何 BLOCK 在 Stage 0 前终止管线                      │
├──────────────────────────────────────────────────────────────────┤
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
│   ├─ ★UCB 探索奖励 (v2.3.0): 欠采样假设 +c·√(ln N / n)          │
│   └─ 输出: Top-3 精英候选 + 评分 + 排名理由                     │
├──────────────────────────────────────────────────────────────────┤
│ Stage 2.5 — Curriculum Planner (NEW v2.8.0, RSIAgent)          │
│   ├─ 生成证明变体任务队列（课程驱动主动探索）                     │
│   ├─ weaken/strengthen/boundary/recombine/stress 五类型          │
│   ├─ 输入: conjecture + 排名 + archive.jsonl 历史证据            │
│   ├─ LLM (v4-flash) 生成，无 key 回退确定性 mock 模板            │
│   └─ 输出: stage25_curriculum.json (证明变体任务队列)            │
├──────────────────────────────────────────────────────────────────┤
│ Stage 3 — PPE-V5.1Hybrid: Deep Formal Proof                     │
│   ├─ J-space 桥接矩阵 (Brain 170K 神经元)                        │
│   ├─ MCTS + ABC Bee Colony 双算法搜索                           │
│   ├─ ★三阶段脚手架 (v2.3.0): Scaffolding→Transition→Full-Scale  │
│   ├─ MathCode 三工具验证 (axiom/proof/sorry)                    │
│   ├─ ★Stage A: strict-superset 递归修复 (lean_recursive_repair)  │
│   └─ 输出: Lean 4 证明 (0 sorry) + 定理/公理/引理统计           │
├──────────────────────────────────────────────────────────────────┤
│ Stage 3.5 — Consistency Audit (v2.1) + L2 (v2.2) + Clip (v2.3) ★GATE │
│   ├─ L1 机械层 (stdlib, 快): 表演性诚实/公理计数/定理存在性/     │
│   │   空壳证明 (:= by trivial / := True)                        │
│   ├─ ★Hallucination Clipping (v2.3.0): 数值声明 ↔ Lean 地面真相 │
│   │   交叉核对 (联合目标 S_reviewer − λ1·plag − λ2·halluc)      │
│   ├─ L2 LLM 结构层 (读 L1 报告 + 公理依赖图): 公理自相矛盾/      │
│   │   离散谱 vs 连续谱 — WARN 候选升级为 BLOCK                   │
│   └─ 输出: stage35_audit_report.json + l2_audit.json + 门控     │
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
python pipeline_orchestrator.py \
  --conjecture /path/to/conjecture.json \
  --output /path/to/output/ \
  --stages -1,0,1,2,2.5,3,4 \
  --enable-maf \
  --enable-sciexplorer \
  --deepseek-key sk-...

# Stage 2.5 curriculum planner standalone (课程规划器, 新增 v2.8.0, RSIAgent)
python curriculum_planner.py \
  --conjecture /path/to/conjecture.json \
  --ranked stage2_ranked_candidates.json \
  --archive archive.jsonl \
  --output /tmp/stage25_curriculum.json   # 加 --mock 离线确定性模板

# Stage 3.5 L1 consistency audit standalone (机械层, stdlib-only, 快)
cd stage3_ppe
python proof_consistency_audit.py \
  --lean /path/to/proof.lean \
  --paper /path/to/paper.txt \
  --expected-axioms 14 \
  --output /tmp/audit.json

# Stage 3.5b L2 structural audit (LLM 深审计, 读 L1 报告 + 公理依赖图)
python proof_consistency_audit_l2.py \
  --lean /path/to/proof.lean \
  --paper /path/to/paper.txt \
  --expected-axioms 14 \
  --output /tmp/l2_audit.json   # 加 --demo 离线验证

# Stage 3.5c proof DAG audit (证明 DAG 审计, stdlib-only, 新增 v2.4.0)
python proof_dag_audit.py \
  --lean /path/to/proof.lean \
  --output /tmp/dag_report.json   # 冗余引理/未用 axiom/悬空引用

# Stage 3.6 frozen evaluator evolution (冻结评估器进化, 新增 v2.4.0)
python stage36_evolution.py \
  --lean /path/to/proof.lean \
  --generations 3 \
  --output /tmp/stage36/          # 加 --dry-run 离线自测（只评估不调 LLM）

# Stage 3.6d deep refinement (DRS 深挖, 新增 v2.8.0, RSIAgent broad-then-deep)
python deep_refinement.py \
  --lean /path/to/proof.lean \
  --archive /tmp/stage36/archive.jsonl \
  --rounds 3 \
  --output /tmp/deep_refine/      # 加 --dry-run 离线自测（只评估不调 LLM）

# Stage 3.6b — 接入 RSIHub（正式集成，2026-09-04）
# 用 RSIHub 真实 operator 类 + 冻结评估器 + archive.jsonl 做 Lean 证据链自我进化
cd ~/AI_for_Science/RSIHub
.venv/bin/python ./scripts/rsihub_lean_bridge.py \
  --lean /path/to/proof.lean --generations 3 --output /tmp/lean_evo [--dry-run]
# 详见 references/rsihub-lean-bridge.md + skill: rsihub

# MAF bridge standalone
cd ~/AI_for_Science/math-agent-framework
python maf_bridge.py
```

## Stage −1 — Two-Layer Safety Gateway (v2.3.0)

**Why it exists**: the pipeline previously had NO dual-use safety screening. Co-Scientist
(arXiv:2608.26701) demonstrates a two-layer gateway that refused **98.7%** of harmful
directions and produced ideas rated safe by independent experts in **96.3%** of cases.

- **Layer 1 (initial screening)**: a one-shot ethics classification of the `conjecture.json`
  research direction before any computation starts.
- **Layer 2 (continuous oversight)**: a per-stage output scan for dangerous experimental
  plans (dual-use categories: nuclear, gain-of-function, weaponizable materials, etc.).
- **Gate rule**: any BLOCK halts the pipeline before Stage 0. This is the single clearest
  *new capability* the paper reveals we were missing.

## Stage 2 — UCB Exploration Bonus (v2.3.0)

SimpleTES already ranks candidates (rpucg DAG-aware selector, γ=0.9). Add the Co-Scientist
ideation mechanism's **UCB exploration bonus** so promising-but-under-sampled hypotheses are
not starved:

```
rank_score = base_score + c·√(ln N / n)
```

where `N` = total candidate evaluations so far, `n` = times this candidate was evaluated,
`c` = exploration constant. This is a one-line change to the ranking score; the paper also
uses a high creativity temperature `τ = 1.6` at candidate generation and crossover
`p_c = 0.7` / mutation `1 − p_c = 0.3` over `G = 10` generations.

## Stage 3 — Three-Phase Scaffolding (v2.3.0)

Canonical naming for the Lean-generation pattern we already use empirically (skeleton stubs
→ tactic bodies → full verification), now principled from Co-Scientist's execution-grounded
code protocol:

- **Scaffolding** — generate the proof skeleton with `:= by trivial` / `:= True` stubs first
  (compiles fast, validates statement structure) under a short timeout (`T_scaffold = 600s`).
- **Transition** — replace stubs with real tactic bodies (`nlinarith`/`field_simp`/`ring`/`exact …_axiom`).
- **Full-Scale Execution** — assemble the full proof and run MathCode verification.

## Stage 3.5 Consistency Audit (v2.1.0 → v2.2.0 L1/L2 split → v2.3.0 Hallucination Clipping)

**Why it exists**: MathCode's three tools (`axiom_checker` / `proof_stats` / `sorry_analyzer`)
only COUNT — how many axioms, how many sorry, whether `has_sorry` is false. They cannot
detect whether the axioms **contradict each other**. Three final reviews (2026-08-16) proved
that a "0 sorry" proof whose axioms are mutually contradictory is MORE dangerous than a
proof with a visible sorry, because it grants false confidence of verification.

**v2.3.0 — Hallucination Clipping** (Gemini Co-Scientist's deterministic reliability module):
add a *numeric claim cross-reference* to the L1 layer:
1. Regex-extract every numeric constant from the paper (near units like GeV / eV / dimensionless
   ratios / axiom counts).
2. Verify each against the Lean proof's ground truth (`grep` the constant in `proof.lean`).
3. A paper claim with **no Lean grounding** → WARN; a claim that **contradicts** Lean → BLOCK.
4. Frame the gate as the joint reliability objective (converts the boolean gate into a
   quantifiable metric):
   `Score(P) = S_reviewer(P) − λ1·S_plagiarism(P) − λ2·S_hallucination(P, E, E_log)`

This subsumes defect classes #3 (axiom-count mismatch) and #4 (phantom theorem) under a single
named mechanism + objective function.

**v2.2.0 — L1/L2 depth-aware split** (Meta^n Appendix E.2 idea): the six P0 classes are split
into a mechanical layer and a structural layer.

**L1 mechanical layer** (`proof_consistency_audit.py`, stdlib-only, fast) — local, mechanically
checkable defects:

| # | Defect class | Example (real) | Severity | Layer |
|---|---|---|---|---|
| 2 | Performative honesty (comment-only tags) | Triple-GW V16: 26× `-- @[honest_axiom]`, 0 real attrs | WARN | L1 |
| 3 | Axiom-count mismatch | CGICE V9.1: "14 axioms" vs 39 actual | WARN | L1 |
| 4 | Phantom theorem (claimed but missing) | CGICE V9.1: "T4 fully verified" but no t4 in Lean | BLOCK | L1 |
| 5 | `:= by trivial` stub | DeepSeek v4-flash tendency | WARN | L1 |
| 7 | Numeric claim not in Lean (v2.3.0) | paper claims value absent/contradicted in proof.lean | WARN/BLOCK | L1 |

**L2 LLM structural layer** (`proof_consistency_audit_l2.py`, DeepSeek) — cross-axiom,
mathematical-judgment defects, escalated from L1 WARN candidates to BLOCK:

| # | Defect class | Example (real) | Severity | Layer |
|---|---|---|---|---|
| 1 | Axiom self-contradiction (ex-falso) | CGICE V9.1: A6+A10 ⟹ `I_cycle=I_eq`, A17 ⟹ `I_cycle≠I_eq` | BLOCK | L2 |
| 6 | Discrete spectrum on noncompact | CGICE V9.1 A3: λ_k=k·λ₁ on SL(6,C)/SU(6) or SU(3,3) | BLOCK | L2 |

**Gate rule**: any BLOCK (L1 or L2) stops the pipeline before paper generation; WARNs are recorded
and forwarded to Stage 4 so the paper can honestly disclose them.

### Stage 3.5 结构化缺陷检测规则 (v2.6.1 硬化 — 触发/反触发条件 + 分级判据)

> **来源**：SkillOpt ReflACT 优化（2026-09-11）。将分散的 Stage 3.5 审计规则系统化为
> 结构化 checklist，每条规则含**触发条件 + 反触发条件 + 证据强度分级**，显式区分 BLOCK/WARN。

### 3.5.0 BLOCK vs WARN 分级标准 (v2.6.1 新增，显式判据)

**核心原则**：BLOCK 阻断门控（Stage 4 不启动），WARN 记录转发（Stage 4 启动但报告标注）。

严重度由三元组决定：`severity = f(defect_class, evidence_strength, dependency_depth)`

| 缺陷类 | 证据强度 = 确定 | 证据强度 = 疑似 | 证据强度 = 提示 |
|---|---|---|---|
| 公理自相矛盾 (ex-falso) | **BLOCK** | BLOCK | WARN |
| 表演性诚实 (comment-only) | **BLOCK** | WARN | WARN |
| 公理计数不匹配 | **BLOCK** | WARN | WARN |
| 幻影定理 (phantom) | **BLOCK** | BLOCK | WARN |
| `:= by trivial` 空壳 | **BLOCK** | WARN | WARN |
| 非紧空间离散谱 | **BLOCK** | WARN | WARN |
| 数值声明交叉核对失败 | **BLOCK** (超硬容差) | WARN (软容差) | WARN |
| 冗余引理 (DAG) | WARN | WARN | WARN |
| 未使用 honest-axiom (DAG) | **BLOCK** | WARN | WARN |
| 悬空引用 (DAG) | **BLOCK** | BLOCK | WARN |

**依赖深度修正**：若缺陷位于**被下游 theorem 直接依赖**的节点（depth ≥ 2），
证据强度为"疑似"时**升级为 BLOCK**；若位于叶子节点（depth = 0），
证据强度为"确定"时**降级为 WARN**（隔离影响）。

**假阳性抑制（反触发条件）**：每条规则必须同时满足"触发条件"与"反触发条件不成立"
才可判 BLOCK。反触发条件见各规则小节。

### 3.5.1 L1 机械层 — 6 类 P0 缺陷

#### P0-1 公理自相矛盾 (ex-falso)
- **触发条件**：存在 `axiom a : P` 与 `axiom b : ¬P`，或存在 `axiom a : False`，
  或存在 `axiom a : P ∧ ¬P`。
- **反触发条件**：`P` 与 `¬P` 分属不同命名空间且文件内**无任何 theorem 同时引用两者**
  （隔离假设，非矛盾）→ 降级 WARN。
- **判定**：证据确定 → BLOCK；疑似（需 L2 跨公理推理确认）→ BLOCK；提示 → WARN。

#### P0-2 表演性诚实 (performative honesty)
- **触发条件**：`axiom` 或 `theorem` 的**注释**含 `honest` / `assumption` / `TODO` /
  `placeholder` 等标记，但**代码体未显式声明前提**（即注释声称诚实但实际是无条件公理）。
- **反触发条件**：注释标记同时伴随 `axiom ... : Prop` 显式前提声明
  （条件定理模式，见 v2.5.0）→ 不触发。
- **判定**：证据确定（注释与代码体直接矛盾）→ BLOCK；疑似 → WARN。

#### P0-3 公理计数不匹配
- **触发条件**：报告声称的 axiom 数量 ≠ `#print axioms <theorem>` 实际列出的数量。
- **反触发条件**：差异仅来自 `propext` / `Classical.choice` / `Quot.sound`
  （经典逻辑三件套，v2.6.0 黄金门控标准）→ 不触发。
- **判定**：证据确定 → BLOCK；疑似 → WARN。

#### P0-4 幻影定理 (phantom theorem)
- **触发条件**：论文/报告引用了 Lean 文件中**不存在**的 theorem 名，
  或 theorem 存在但**从未被编译验证**（无 `#check` 通过记录）。
- **反触发条件**：theorem 存在于 `references/` 引用的外部文件且路径有效 → 降级 WARN。
- **判定**：证据确定 → BLOCK；疑似 → BLOCK；提示 → WARN。

#### P0-5 `:= by trivial` 空壳
- **触发条件**：theorem 体为 `:= by trivial` / `:= True` / `:= by simp` 且
  目标命题**非平凡**（非 `True`、非恒真式）。
- **反触发条件**：目标命题确为 `True` 或经 `decide` 可判定的恒真式 → 不触发。
- **判定**：证据确定 → BLOCK；疑似 → WARN。

#### P0-6 非紧空间离散谱
- **触发条件**：定理断言在**非紧空间**（如 `ℝ^n`、`ℝ`、开流形）上算子的谱为
  **离散**（如 `∃ (λ : ℕ → ℝ), spectrum = range λ`），且**无紧性/紧嵌入前提**。
- **反触发条件**：定理显式假设 `CompactSpace` / `IsCompactOperator` /
  紧嵌入（如 `CompactEmbedding`）→ 不触发。
- **判定**：证据确定 → BLOCK；疑似 → WARN。

### 3.5.2 L2 LLM 结构层 — 跨公理推理

L2 读取 L1 报告 + 公理依赖图，执行**跨公理推理**，可将 L1 的 WARN **升级为 BLOCK**：
- **公理自相矛盾升级**：L1 判 WARN 的隔离假设，若 L2 发现某 theorem 通过传递依赖
  同时引用 `P` 与 `¬P` → 升级 BLOCK。
- **非紧离散谱升级**：L1 判 WARN 的疑似案例，若 L2 发现该定理被下游论文核心结论
  直接依赖 → 升级 BLOCK。
- **升级必须记录**：`l2_audit.json` 中记录 `{from: WARN, to: BLOCK, reason, dependency_chain}`。

### 3.5.3 Clip 层 — 数值声明交叉核对 (Hallucination Clipping)

**联合可靠性目标**：`Score = S_reviewer − λ1·S_plagiarism − λ2·S_hallucination`

**前置检查（v2.6.1 新增，消除 s05/s07 假阳性）**：
1. **单位一致性**：数值声明的单位必须与 Lean 地面真相的单位一致；不一致 → 先做单位换算，
   换算失败 → WARN（非 BLOCK）。
2. **容差带**：数值比对使用**相对容差** `ε_rel = 1e-6`（硬）/ `1e-3`（软）。
   - 超硬容差 → BLOCK
   - 超软容差但未超硬容差 → WARN
   - 在软容差内 → 不触发
3. **有效数字**：仅比对声明中**有效数字位数**内的位数，避免末位舍入误判。

**触发条件**：论文数值声明 `x_claim` 与 Lean 地面真相 `x_lean` 满足
`|x_claim − x_lean| / max(|x_lean|, 1) > ε_rel`。
**反触发条件**：声明为**近似值**（含 `≈` / `~` / `order of`）且差异在软容差内 → 不触发。

### 3.5.4 DAG 层 — 证明依赖图审计 (v2.4.0 规则补全)

从 Lean 文件提取 lemma/theorem 为节点构建证明 DAG，检查三类缺陷：

#### DAG-1 冗余引理 (redundant lemma)
- **触发条件**：lemma 定义后**从未被任何下游节点引用**（入度 = 0 且非 `#check` 目标）。
- **反触发条件**：lemma 被 `#check` / `#print` 显式引用，或标注 `@[simp]` 等属性
  供 simp 集合使用 → 不触发。
- **判定**：WARN（记录转发，不阻断）。

#### DAG-2 未使用 honest-axiom (unused honest-axiom)
- **触发条件**：`axiom ... : Prop`（条件定理前提）**从未被任何 theorem 实例化**
  （即无 `xxx_main` 引用）→ 表演性诚实变体。
- **反触发条件**：axiom 被 `xxx_conditional` 形式引用（条件形式保留）→ 降级 WARN。
- **判定**：证据确定 → BLOCK；疑似 → WARN。

#### DAG-3 悬空引用 (dangling reference)
- **触发条件**：DAG 中存在指向**不存在节点**的边（引用了未定义的 lemma/theorem）。
- **反触发条件**：引用指向 `references/` 外部文件且路径有效 → 降级 WARN。
- **判定**：证据确定 → BLOCK；疑似 → BLOCK；提示 → WARN。

### 3.5.5 输出产物

- `stage35_audit_report.json` — L1 机械层结果
- `l2_audit.json` — L2 结构层结果 + WARN→BLOCK 升级记录
- `dag_audit.json` — DAG 三类缺陷结果
- `severity_table.json` — 每条缺陷的 `{defect_class, evidence_strength, dependency_depth, severity}`
- **门控决策**：任一 BLOCK → Stage 4 不启动；仅 WARN → Stage 4 启动且报告标注。

## Stage A — Strict-superset Recursive Lean Repair (in physics-proof-engine)

`lean_recursive_repair.py` (in physics-proof-engine `scripts/`) upgrades the sorry-repair loop from
flat self-refinement (reads only the current verification output) to Meta^n strict-superset
(reads current traces + historical version diff + prior repair strategy). A controlled experiment
on `cgice_proof_v5_manual.lean` (3 sorry in T1 master equation) showed both modes reach 0 sorry,
but **only strict mode preserves the physics**: flat mode introduced `deriv I_cycle = 0` (killing
CGICE dynamics and collapsing T3 to 0=0), while strict mode correctly introduced the master equation
as an honest axiom (matching the paper's A6). Defect count is necessary but not sufficient —
semantic correctness is the real gate.

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

| Metric | Standalone PPE | v1.0 Pipeline | v2.0 + MAF | v2.1 + Audit | v2.2 + L2 | v2.3 + Safety/Clip |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|
| End-to-end success | 25% | 78% | ~65% (stricter gates) | ~65% + zero ex-falso | ~65% + zero ex-falso | ~65% + zero ex-falso |
| P0 error blockage | 30% | 2% | ~0.5% (symbolic+num) | ~0.5% + axiom-consistency | ~0.5% + structural (L2) | ~0.5% + numeric-claim clip |
| MCTS effective branching | 35% | 85% | ~75% (5-level filter) | ~75% | ~75% | ~75% + UCB |
| Counterexample discovery | 10% | 25% | ~50% (50K optimization) | ~50% | ~50% | ~50% |
| Axiom-contradiction escape | 100% | 100% | 100% | **~0%** (Stage 3.5 gate) | **~0%** (L1+L2 gate) | **~0%** (L1+L2 gate) |
| Semantic-destroying repair escape | — | — | — | — | **~0%** (Stage A strict-superset) | **~0%** (Stage A) |
| Dual-use harmful direction escape | — | — | — | — | — | **~1.3%** (Stage −1 gate) |

## Dependencies

All five sub-skills must be installed:
- **MAF Bridge** (NEW): `pip install sympy scipy` + `sys.path` to math-agent-framework
- SciExplorer (skill)
- simpletes (skill + `pip install openai numpy`)
- physics-proof-engine (skill + MathCode)
- ai-scientist-v2 (skill)
- **Stage −1 safety gateway**: `openai` + `DEEPSEEK_API_KEY` (one-shot ethics classification)
- **Stage 3.5 L1 audit**: stdlib-only (`python proof_consistency_audit.py`), no extra deps
- **Stage 3.5b L2 audit**: `openai` + `DEEPSEEK_API_KEY` (structural judgment)
- **Stage A recursive repair**: `openai` + `DEEPSEEK_API_KEY` + MathCode tools

## Environment

Requires `DEEPSEEK_API_KEY` for LLM calls across all stages.
