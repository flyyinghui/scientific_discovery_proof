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
version: 2.25.0
tags: [pipeline, discovery, proof, orchestration, formal-verification, maf, symbolic, consistency-audit, recursive-repair, safety-gateway, hallucination-clipping, ucb, scaffolding, rsiagent, curriculum, exploration, planted-truth, constant-certification, bootloops, faithfulness, disproof, target-strength, anti-trivialization, total-function-default, vacuous-hypothesis, scout, world-model, janus, three-criteria, jspace, brain-bridge]
related_skills:
  - math-agent-framework (MAF stage 0)
  - SciExplorer (stage 1)
  - simpletes (stage 2)
  - physics-proof-engine (stage 3)
  - ai-scientist-v2 (stage 4)
---

# Scientific Discovery & Proof — Integrated Pipeline v2.22

Five-stage end-to-end pipeline for physics conjecture discovery → formal verification → publication.

**NEW in v2.22.0** (J-space 桥接矩阵动态化，2026-10-12): **幽灵子系统修复 + 大脑支持度闭环**。
把「文档化但零实现」的 J-space 桥接矩阵从宣传变成可执行信号：
① **新 `scripts/jspace_bridge.py`** —— 用 `brain.recall()` 真实语义检索**动态重算** J-score
（替代 references/jspace-bridge-matrix.md 的硬编码 12×12 快照），三成分 J = 0.4·sim + 0.3·MI
+ 0.3·co_activation（sim=概念代表向量余弦相似度 / MI=召回 neuron Jaccard 共现 /
co_activation=共同召回比例），附 `calibrate()` 阈值重标定提示。
② **接入 pipeline** —— 新增 `run_jspace_grounding`（一次性子进程加载大脑算全部概念 J-score），
Stage 1 的 `j_score_hint` 占位符 → 真实 `path_j_score`，新增 `--skip-brain` 开关。
③ **喂给世界模型** —— `WorldModel.predict()` 新增 J-space 先验（j_score ≥ 0.5 保护候选不被
历史剪枝），`three_criteria_score()` 报告 `brain_support` 字段，形成「大脑知识 → 证明策略
预筛选」闭环。
完整评估见 `references/jspace-bridge-dynamic-landing.md`。

诚实边界：动态 J-score 值域 ≠ 硬编码矩阵值域（阈值需按当前脑重标定）；J-score 是「先验支持度」
非硬门控（硬门控仍由 Stage 3.5 审计负责）；大脑加载昂贵（181K 神经元 ~35-170s），设计为
一次性子进程绝不内联进进化循环。

**NEW in v2.21.0** (from JANUS, 中科院计算所 AI 安全国重《Predict-Verify-Evolve》arXiv:2610.13194, 2026-10-12): **世界模型（预执行预测）+ 三标准评分**。
把 JANUS 的两项 P0 增量落地到 Stage 3.6 进化循环，**不动主线五阶段**：
① **P0-① 世界模型（预执行预测）**（新 `scripts/world_model_prescreen.py` 的 `WorldModel`）——
在昂贵的 LLM 变异 + Lean 编译之前，用 archive.jsonl 历史预测一次 (strategy × condition)
变异的期望增益 + 达成 0 sorry 的概率。有足够历史 + 预测无增益 + 0-sorry 概率低 → PRUNE
（跳过本次变异省成本）。已接入 `stage36_evolution.py` 每代变异前。
② **P0-② 三标准评分（价值 + 信息增益 + 探索效用）**（同脚本 `three_criteria_score`）——
把 JANUS 三标准落到候选评估，补当前 Stage 3.6 只有「单一缺陷扣分」的缺口：信息增益
（盲区缺陷占比 + 新 condition 奖励）+ 探索效用（UCB 欠采样策略加分）。每个 archive
record 新增 `three_criteria` 字段。
完整评估见 `references/janus-world-model-integration.md`。

诚实边界：① 世界模型是**预筛选器**（省成本），**不替代** RSIHub 冻结评估器——
PRUNE 只跳过变异，幸存者仍走冻结评估器 + 隐藏物理内容审计定最终分数；② 三标准是
**排序 + 归档**信号，不改变接受判定（防「探索效用」给低质证明放行的 reward-hack）；
③ 世界模型纯历史统计、无 LLM、确定性，候选者无法改写，满足「评估器冻结」原则。

**NEW in v2.20.0** (from AIDE²/RSI, Weco AI《Recursive Self-Improvement of AI Research Agents》2026-09-22, 2026-10-12): **RSI 等级评估 + 点火测试 + 隐藏评分机制**。
把 AIDE² 的三项独特增量落地到 Stage 3.6 进化循环，**不动主线五阶段**：
① **P0-① RSI 等级评估（Level 0–3）**（`stage36_evolution.py` 新增 `assess_rsi_level`）——
进化循环总结时输出 `rsi_level_assessment` 字段，诚实标注处于哪个 AIDE² 阶梯：
Level 0 委托（无净正增益）/ Level 1 净正（比人类手调高效改进）/ Level 2 点火
（需 ignition_test 诊断）/ Level 3 拐点（永不声称）。同时量化接受率（P3-⑤）。
② **P0-② 点火测试**（新 `scripts/ignition_test.py`）——读 archive.jsonl，按 generation 分前/后
两半比较接受率 + 平均 gain，后期显著高于早期 → 点火弱信号（Level 2 候选）。这是
「改进自身改进能力」的唯一可操作诊断。
③ **P1-③ 隐藏评分机制**（`stage36_evolution.py` gate 阶段）——把评分拆「可见分数
（编译 0 sorry）+ 隐藏分数（physical_content_audit 的 BLOCK 数）」双通道，只在可见分数
提高时才跑隐藏审计，物理内容零重言式才通过。AIDE² 借此把 reward-hacking 率从 63%→34%。
完整评估见 `references/aide2-rsi-integration.md`。

诚实边界：①是诚实标注（区分 Level 0/1，不声称 Level 2/3）；②是趋势诊断（非「改进
自身改进能力」的严格证明）；③是事前预防（物理内容非平凡门槛，非形式化保证）。

**NEW in v2.19.0** (from prove2me 二次评估，2026-10-08): **形式化忠实性前置规范 + 反证分支 + 退化输入检测**。
深读 prove2me_workspace 全库（SKILL.md + 13 reference + 2 Lean 脚本），在 v2.18.0 已落地的 5 项
（read-back / faithfulness 5 约束 / typeDeps·valueDeps / reduction 复用 / milestone）之外，落地 4 项新增量，
**不动主线五阶段**：
① **P0 Target 强度分层 + 平凡化排除前置声明**（新 `scripts/conjecture_spec_check.py` + `_generate_proof_skeleton`
注入）——把 V64 教训从「事后检测」前移到「猜想定义时的前置声明」：目标应为最弱稳定陈述（真相形状）而非
硬编码常数，且一句话排除 vacuous hypothesis / trivial-true definition / hard-coded special case。
② **P1 Faithfulness 退化输入检测**（`physical_content_audit.py` 新增 2 检测）——原则 3「total function 坏输入
默认值」（log/sInf/iSup 无保护假设）+ 原则 5「vacuous/不可满足假设」（False / P∧¬P / x<x）。均为 WARN（启发式）。
③ **P1 Disproof 反证分支**（新 `scripts/disproof_probe.py`，Stage 2.6 旁路）——prove2me 三种移动之一，
Stage 2 后主动尝试证明猜想否定，disproved/possibly_false → WARN 提示猜想可能为假。
④ **P2 Scout 失败路径侦察**（`stage36_evolution.py` 的 failed_approach 加 rejected_by/reject_reason）——
权威拒绝方 + 理由，比「自己失败」更硬的信号。
完整评估见 `references/prove2me-second-assessment.md`。

诚实边界：①②是「前置声明」规范（不产生形式化保证，实质平凡化仍由 physical_content_audit 兜底）；
③反证是 LLM 启发式（不是形式化保证，真正阻断靠 Stage 3.5 审计）；④是流程增强（不产生新 BLOCK 门控）。

**NEW in v2.15.0** (from V64 定义重言式教训，2026-10-05): **物理内容审计门控**。
新增 `scripts/physical_content_audit.py`（stdlib-only），把「0 sorry / 0 axiom 编译通过」与「物理内容非平凡」区分开。
V64 教训：把物理对象直接定义为 S ≡ 谱底·‖φ‖²+V_top，则 bound 变成重言式（35x+b ≥ 35x+b），是替换非推导——
4/5 代理一致 P0。三类检测：① **字面恒等重言式**（conclusion 形如 X=X / X≥X / X≤X）→ BLOCK；② **定义重言式**
（rw/unfold 展开 conclusion 里的定义 + 无实质 tactic）→ BLOCK；③ **浅层证明**（证明体无 calc/have/ring/exact
等实质 tactic）→ WARN。实质 tactic = calc/have/ring/ring_nf/field_simp/by_contra/induction/cases/exact<非rfl>/
linarith[假设]/apply/refine。用法见 Quick Start。**已接进 `pipeline_orchestrator.py` 的 Stage 3.5b 主流程**
（`_run_stage35b_physical_content_audit`，在自洽性审计之后、DAG 审计之前自动运行），且 Stage 3.5/3.5b/3.5c
任一 BLOCK 时**阻止 Stage 4 论文生成**。

**NEW in v2.14.0** (from RSIAgent 复审，arXiv:2609.15364 代码深读，2026-10-05): **Stage 3.6 进化循环五项增量落地**。
把 RSIAgent 剩余未落地的「元层」增量落地到 Stage 3.6 进化循环 + L2 审计，**不动主线五阶段**：
① **P0-① 三大改进极限元诊断**（`stage36_evolution.py` 新增 `_diagnose_stall`）——连续停滞时判断根因
（Insufficiently Targeted Exploration / Incomplete Verification / Unreliable Memory Consolidation），注入下轮诊断。
② **P0-② 密封评估器 + 防 reward hack**（新增 `_detect_reward_hack`）——检测缺陷等价替换
（sorry→admit / 空壳→sorry / 未完成总量增加），等价替换即拒绝（即使分数虚高）。
③ **P0-③ learn_on_pass**（record 新增 `learn_on_pass` 字段 + `replay_strategies.py` 成功判断扩展）——
分数不退化（≥）也记录为「成功经验」，供 replay 学习「不退化」先例。
④ **P5 证明模式模板库**（新 `scripts/proof_templates.json` + `scripts/proof_template_library.py`）——
把已验证证明模式（条件定理重构/诚实公理化/黄金门控/0 公理重构等 8 个）冻结为 few-shot 模板，
新证明按缺陷类型检索注入 mutate prompt（记忆冻结复用）。
⑤ **P4 屏蔽自我描述**（`proof_consistency_audit_l2.py` 的 `_extract_paper_claims` 降级修辞）——
把论文「we prove/establish」降级为「the paper claims」，标注 [UNVERIFIED]，防 LLM 被修辞带偏。
完整记录见 [`references/rsiagent-integration.md`](references/rsiagent-integration.md) 复审补充节。

**NEW in v2.13.0** (from BootLoops 1.0, M. D. Schwartz / Anthropic, 2026-10-01): **Stage 1.5 数值层健全性双门**。
把 BootLoops 的两个核心协议落成两个脚本，插在数值验证 (Stage 1) 与形式化证明 (Stage 3) 之间，
**不动主线五阶段**，补上管线数值层最薄弱的两个缺口（假猜想/数值错/循环认证）：
① **Stage 1.5a 植物真值门**（新 `scripts/planted_truth_gate.py`，BootLoops `planted-truth`）——
形式化前先验证数值引擎能 (a) 恢复一个已知植入答案（正对照）且 (b) 抓住一个故意污染的错误输入
（负对照）。内置 SL(6,C) 四论文框架的 5 正 + 1 负对照（含 v2.6.0 的 g_TC²=8π²/35 历史 bug 作为
canonical 负对照）。任一对照失败 → BLOCK（在 Stage 3 前终止）。
② **Stage 1.5b 闭环常数认证**（新 `scripts/constant_certify.py`，BootLoops `constant-recognition`）——
用 PSLQ 整数关系把高精度数值认证为「声明常数环」上的闭环形式，纪律是「先声明环+高度+精度预算，
找不到就拒绝发明」。内置 SL(6,C) 的 g_*²=12π²/35、g_inst²=24π²/35、λ_KLS=35/3、|ρ_res|²=35 四个认证目标。
完整评估见 [`references/bootloops-integration.md`](references/bootloops-integration.md)。

**NEW in v2.12.0** (from Dream-RSI full mechanism, arXiv:2609.14858): **Stage 3.7 证明策略元优化器**。
补上 v2.7.0 只落地「重放模拟器」表层而缺失的核心层——**优化探索策略本身**（而非单个候选解）。
新增 `scripts/proof_policy_optimizer.py`，落地 Dream-RSI 的 P0/P2/P3 三项机制，**不动主线五阶段**：
① **P0 探索策略元优化**：把「证明策略」（5 个变异策略的偏好权重 / 并行度 W / 放弃阈值 / 探索率 ε）
编码为可执行 `ProofPolicy` 对象，用 archive.jsonl 历史重放反馈迭代改进策略参数本身
（`ProofPolicy.mutate_params` 参数扰动 + 可选 `_llm_develop_policy` v4-flash 策略开发）。
② **P2 replay objective 三项**：`V = 质量 − β1·成本 + β2·平均并行度`（`PolicyReplayEvaluator`），
量化「并行证明 vs 串行证明 vs 放弃」的收益，β1/β2 控制成本/并行权衡。
③ **P3 单调性保证**：候选策略集始终包含当前策略 π_t，选 max 保证不退化。
关键设计分离：**「选择」由策略权重决定（×针对性软约束），「结果」由历史真实结果决定**
（历史成功率 × 平均 gain）——与 Stage 3.6（优化证明代码）正交，是它的元层。
完整评估见 [`references/dream-rsi-full-assessment.md`](references/dream-rsi-full-assessment.md)。

**NEW in v2.11.0** (from Stellar Colosseum, arXiv:2609.15983): **三个前向阶段增量落地**。
把 Colosseum 的「探索策略→readiness gate→前向分解→失败路径」移植为三个增量，**不动主线五阶段**：
① **P1-1 Strategy Explorer**（新 `scripts/strategy_explorer.py`，Stage 0.5 前置）——证明前生成
3-5 条候选证明路线（各含 mechanism/required_lemmas/expected_bottleneck/falsifiable_test），
readiness gate 打分选路（Colosseum 三条件：中心约化稳定 / 未决声明可指派 / 无未决桥接改架构）。
② **P0-2 Pre-Proof Decomposer**（新 `scripts/preproof_decomposer.py`，Stage 2.7 前置）——证明前
把猜想分解为「编号 section 骨架 + 依赖 DAG」，拓扑排序产出可并行批次，指导 Stage 3 按依赖并行
生成 Lean 片段 + 失败 section 局部重试。
③ **P1-2 失败路径**（`stage36_evolution.py` record 新增 `failed_approach` 字段）——被拒变异记录
「精确失败点 + 变体可行条件」，archive 升级为可复用失败知识目录。
完整评估见 [`references/colosseum-integration.md`](references/colosseum-integration.md)。

**NEW in v2.10.0** (from Stellar Colosseum, arXiv:2609.15983, 2026-09-15): **Stage 3.5 两个增量落地**。
把 Colosseum 的定向证伪 + 缺陷定位移植为两个增量，**不动主线五阶段**：
① **P0-1 Targeted Falsification 缺陷分类学**（`proof_consistency_audit_l2.py` 新增三检测）——映射
Colosseum 定向证伪的 3 个新缺陷类：`strengthened_hypothesis`（静默强化假设）/
`proved_vs_target_mismatch`（证明命题≠目标命题）/ `missing_downstream_assumption`（下游缺失假设）。
三个 LLM 结构检查，结果并入 L2 报告 `targeted_falsification` 字段 + 最终 gate。
② **P0-3 缺陷定位**（`proof_consistency_audit.py` 新增 `_localize_findings`）——每个 finding 附加
`defect_location: {section, line}`，把缺陷绑定到具体 section/claim（支持 §N / Section N / STEP N /
Lemma L / [honest-axiom An] / A 编号注释头定位），使审阅可操作。
完整评估见 [`references/colosseum-integration.md`](references/colosseum-integration.md)。

**NEW in v2.9.0** (from ScientistTwo, arXiv:2609.19644, 2026-09-17): **Stage 3.5 三个 P0 正确率检测**。
把 ScientistTwo 的 CoE 完整性审计（0/1814 引用幻觉、方法-代码逐行对齐）和 Ablation Critic
（组件必要性消融）移植为三个新检测，**直插 Stage 3.5 门控**，不动主线五阶段：
① **P0-1 Reference Verification**（`scripts/reference_verification.py`）——正文 `[n]` 引用 ↔
参考文献表逐条核对，悬空引用 → BLOCK，未引用 → WARN。
② **P0-2 Method-Code Alignment**（`scripts/method_code_alignment.py`）——论文 ↔ Lean 双向对齐，
phantom（论文声称 Lean 缺失）→ BLOCK，undeclared（Lean 有论文没提）→ WARN，输出映射表。
③ **P0-3 Axiom Ablation**（`scripts/axiom_ablation.py`）——反事实消融：注释公理→重编译→仍通过=冗余。
静态模式（WARN 快筛）+ 编译级模式（BLOCK 定论，需 `--lean-bin`）。
三个检测已并入 `proof_consistency_audit.py`（检测 10/11/12），完整评估见
[`references/scientisttwo-integration.md`](references/scientisttwo-integration.md)。

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

# Stage 0.5 strategy explorer (证明策略探索, 新增 v2.11.0, Colosseum)
python strategy_explorer.py \
  --conjecture /path/to/conjecture.json \
  --paper /path/to/paper.txt \
  --output /tmp/stage05_strategies.json    # 加 --mock 离线确定性模板

# Stage 2.7 pre-proof decomposer (前向证明分解, 新增 v2.11.0, Colosseum)
python preproof_decomposer.py \
  --conjecture /path/to/conjecture.json \
  --strategy /tmp/stage05_strategies.json \
  --output /tmp/stage27_decomposition.json  # 加 --mock 离线确定性模板

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

# Stage 3.6+ ignition test (点火测试, 新增 v2.20.0, AIDE²/RSI Level 2 诊断)
python ignition_test.py \
  --archive /tmp/stage36/archive.jsonl \
  --output /tmp/ignition.json      # 后期接受率/gain 显著高于早期 → 点火弱信号

# Stage 3.6+ world model pre-screen (世界模型+三标准评分, 新增 v2.21.0, JANUS)
# 已自动接入 stage36_evolution.py（变异前预筛选 + record 记 three_criteria 字段），无需额外参数。
# 独立自测：
python world_model_prescreen.py --self-test   # 验证三标准评分 + 世界模型 predict/PRUNE

# J-space 桥接（动态 J-score, 新增 v2.22.0，替代硬编码矩阵 + j_score_hint 占位符）
# 已自动接入 pipeline_orchestrator.py（spec_check 后运行，--skip-brain 可跳过）。
# 独立运行 / 自测：
python jspace_bridge.py --conjecture /path/conjecture.json --output /tmp/jspace.json
python jspace_bridge.py --self-test            # mock brain 离线自测（不加载 181K 神经元）

# 大脑数据挂接（neural_memory_data, 2026-10-13 重新挂接并实测通过）:
#   数据 <WORK_DIR>\neural_memory_data\ (181,488 神经元) + 代码 neural_memory_brain.py
#   路径解析内建(env NEURAL_MEMORY_DIR / 候选探测), 见 references/neural-memory-brain-hookup.md
#   需 numpy 环境(本机: <LEAN_PROJECT>\.conda\python.exe), 真实加载 ~23s
python brain_hookup_check.py                   # 挂接健康自检（真实 181K 大脑 recall + J-score 冒烟）

# 外部论文方程获取（无 web 工具时的可用链路：arXiv API 检索 → HTML(MathML) 下载 → 公式提取）
# 见 references/arxiv-paper-tex-extraction.md（含 alttext 正则、/tmp 路径坑、查询引号坑）

# Stage 3.7 proof policy meta-optimizer (证明策略元优化, 新增 v2.12.0, Dream-RSI P0/P2/P3)
python proof_policy_optimizer.py \
  --archive /path/to/stage36/archive.jsonl \
  --rounds 3 --candidates 8 \
  --beta1 0.1 --beta2 0.5 \
  --output /tmp/policy_opt/       # 加 --dry-run 只用参数扰动；--self-test 离线全流程自测

# Stage 3.6d deep refinement (DRS 深挖, 新增 v2.8.0, RSIAgent broad-then-deep)
python deep_refinement.py \
  --lean /path/to/proof.lean \
  --archive /tmp/stage36/archive.jsonl \
  --rounds 3 \
  --output /tmp/deep_refine/      # 加 --dry-run 离线自测（只评估不调 LLM）

# Stage 3.5 P0-1 Reference Verification (参考文献零幻觉, 新增 v2.9.0, ScientistTwo)
python reference_verification.py \
  --paper /path/to/paper.txt --output /tmp/ref_check.json

# Stage 3.5 P0-2 Method-Code Alignment (论文↔Lean 双向对齐, 新增 v2.9.0, ScientistTwo)
python method_code_alignment.py \
  --lean /path/to/proof.lean --paper /path/to/paper.txt --output /tmp/align.json

# Stage 3.5 P0-3 Axiom Ablation (公理必要性消融, 新增 v2.9.0, ScientistTwo)
python axiom_ablation.py \
  --lean /path/to/proof.lean --output /tmp/ablation.json          # 静态（WARN 快筛）
python axiom_ablation.py \
  --lean /path/to/proof.lean --lean-bin /root/.elan/bin/lean       # 编译级（BLOCK 定论）

# 三个检测已并入 proof_consistency_audit.py（检测 10/11/12），跑一次全量审计即自动触发


# Stage 3.5 物理内容审计门控（定义重言式检测, 新增 v2.15.0, V64 教训）
# 把「0 sorry/0 axiom 编译通过」与「物理内容非平凡」区分开：检测字面恒等重言式 +
# 定义重言式（rw/unfold 展开结论定义 + 无实质 tactic）+ 浅层证明。
python physical_content_audit.py \
  --lean /path/to/proof.lean --output /tmp/content_audit.json      # BLOCK 则 paper 不生成
python physical_content_audit.py --self-test                       # 离线自测


# Stage 1.5a planted-truth gate (植物真值门, 新增 v2.13.0, BootLoops planted-truth)
# 形式化前验证数值引擎能恢复已知植入答案(正对照) + 抓住故意污染输入(负对照)。
python planted_truth_gate.py --self-test                        # 内置 SL6C 5正+1负对照
python planted_truth_gate.py --controls /path/controls.json --output /tmp/stage15.json

# Stage 1.5b constant certification (闭环常数认证, 新增 v2.13.0, BootLoops constant-recognition)
# PSLQ 认证「声明环上的闭环形式」，先声明环+高度+精度预算，找不到就拒绝发明。
python constant_certify.py --self-test                           # 内置 SL6C 四个闭环常数
python constant_certify.py --target NAME --value X --ring "pi**2" "1" --height 1e8 --digits 50


# Stage 3.6b — 接入 RSIHub（正式集成，2026-09-04）
# 用 RSIHub 真实 operator 类 + 冻结评估器 + archive.jsonl 做 Lean 证据链自我进化
cd ~/projects/ai_for_science/RSIHub
.venv/bin/python ~/.hermes/skills/scientific-discovery-proof/scripts/rsihub_lean_bridge.py \
  --lean /path/to/proof.lean --generations 3 --output /tmp/lean_evo [--dry-run]
# 详见 references/rsihub-lean-bridge.md + skill: rsihub

# MAF bridge standalone
cd ~/projects/ai_for_science/math-agent-framework
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

---

## prove2me 形式化忠实性嫁接 (v2.18.0, 2026-10-08)

**NEW in v2.18.0**: 从 prove2me_workspace 嫁接「形式化忠实性（faithfulness）审计」框架，五项增量全部增量嫁接（主线五阶段不动），完整评估见 `references/prove2me-integration-assessment.md`。

- **P0-① Stage 3.5a Read-back 盲读回**：新增 `scripts/faithfulness_readback.py`，两阶段（盲读只给 Lean 代码 → 对比 read-back vs 猜想意图），检测 formalization 忠实性 gap。直接针对 V64 教训：把物理对象定义为重言式恒等式（S := 谱底·‖φ‖²+V）是 faithfulness gap，不是可编译性缺陷。已接入 `pipeline_orchestrator.py` 的 `_run_stage35a_faithfulness_readback`（Stage 3.5 之前，gate=BLOCK 时阻断）。
- **P0-② Faithfulness 5 约束注入 PPE prompt**：`physics_proof_engine/reasoner.py` 的 `_build_proof_prompt` 注入 5 条（假设/结论双向匹配、禁止假设结论、退化输入、边缘输入、定义 vs 推导区分）。
- **P1-③ typeDeps/valueDeps 区分**：`proof_dag_audit.py` 新增 `node_type_and_value` 拆分语句依赖 vs 证明依赖，新增 `unverified_definition_deps` 检测（定义层被陈述引用但从未被证明使用，WARN）。
- **P1-④ Reduction 可复用激励**：`preproof_decomposer.py` 新增 `reusability` 字段 + REDUCTION REUSE RULE（分解为可复用核心引理，避免 trivial 转移）。
- **P2-⑤ Milestone 里程碑**：新增 `scripts/milestone_curation.py`（显式 milestones 验证 / 从 required_lemmas 自动提名权威里程碑）。

诚实边界：read-back 是 LLM 启发式审计（非形式化保证）；`unverified_definition_deps` 是语法层检测（可能有 typeclass 隐式使用的假阳性）——均 WARN 而非 BLOCK。

---

## MVP-0 — Harness² RSI 多智能体回环（v2.23.0，2026-10-29 落地）

**NEW in v2.23.0**（对齐 Google Research Harness² Propose–Probe–Compose + 本技能 Lean 硬验证）：
把「单线程 RSI」升级为「N 路并行 + 轨迹差异归因」。**不动主线五阶段**，只新增一个策略层进化环。

### 为什么需要它

现有 Stage 3.6 的 archive.jsonl 只存 `{gain, defects_before, defects_after, mutation_strategy}`
这类**标量摘要**。Stage A strict-superset 实验里最关键的一条信息——
「第 N 步 `deriv I_cycle = 0` 把 CGICE 动力学杀掉」——是靠**人工比对**才发现的，
因为标量把「哪一步开始分叉」丢掉了。MVP-0 把这一步自动化。

### 新增四个脚本 + 一个闭环

| 脚本 | 职责 |
|---|---|
| `scripts/proof_harness.py` | `ProofHarness` 对象（prompt_style / memory_policy / scaffold_phase / tool_whitelist / parallelism）+ `propose_edits()` 单维变异 |
| `scripts/agent_fleet.py` | L2 micro-agent 注册表（MVP 10 个）+ `run_fleet()` N 路并行 + **`arbitrate()` 唯一判定入口** |
| `scripts/trajectory_diff.py` | 多轨迹对齐（LCS + `step_order` 逻辑序）+ 三类分歧（outcome / output / structural_gap） |
| `scripts/jev_arbiter_bridge.py` | Jev-Omni 排序桥，**choice 型专用 + 代码级红线守卫** |
| `scripts/mvp0_smoke.py` | 端到端闭环：Propose → Probe(4 路) → Arbiter → Diff → Rank → Compose |

```bash
cd scripts
python mvp0_smoke.py --self-test                    # 离线自测（无需 Lean/API/GPU）
python mvp0_smoke.py --rounds 3 --output /tmp/mvp0  # 三代进化闭环
```

### 三条硬设计（违反任一条整个方案就退化成普通并行搜索）

1. **判定与排序分离**：只有 `agent_fleet.arbitrate()` 能写 `{lean_ok, sorry_count,
   axiom_count, audit_verdict}`。Composer / Proposer / Jev 全部只读。
   Jev 的概率**禁止**进 gate —— `jev_arbiter_bridge._assert_not_gate()` 会在
   调用参数含 gate/verdict/block/verifier 时直接抛 `JevMisuseError`。
2. **单维编辑**：`propose_edits()` 每个变体只改一个维度 → 分歧步能归因到具体维度。
   多维亚变会让「首个分歧步」无法解释，等于放弃 harness2 的核心价值。
3. **单调性优先**：Compose 第一步检查「基线是否已 `lean_ok=True`」，是则**直接保持不动**。
   实测踩过：无此检查时第 2 代基线已全过，Compose 却退化成去选最差变体
   （`prompt_style_concise`），完全违反「不退化」原则。

### 实测闭环（3 代，离线 mock，4.1 秒）

```
ROUND 1  4 个 harness 全 BLOCK（P03 硬编码常数 / T01 缺脚手架 / T07 无法编译）
         Compose 抽出 2 个单维编辑：
           prompt_style: concise → detailed   （依据：P03 在 detailed 下通过）
           memory_policy: none  → archive_prior（依据：T07 在 archive_prior 下通过）
         → composed_r1 = detailed + archive_prior
ROUND 2  composed_r1  PASS  10/10 步 · lean_ok=True · 0 sorry · 0 axiom · 链闭合
         同代父本 prompt_style_concise / memory_policy_none 仍 BLOCK
         Compose 检测基线已过 → 保持（单调性）
ROUND 3  仍 PASS，稳定不退化
```

**关键洞察**：`H02 条件定理重构`需要 `detailed(0.55) + archive_prior(0.35) = 0.90 ≥ 0.85`
才过——任何**单维**变异都到不了（0.35+0.35=0.70、0.55+0=0.55）。这正是 harness2
「从差异互补而非取平均」的价值点，单靠标量 gain 永远发现不了。

### 诚实边界

- **MVP agent 是确定性 mock**：接口真实、行为可复现，不依赖 Lean/LLM/API key。
  替换真实现只需改 `agent_fleet._EXEC` 表里的 10 个函数体，调度/对比/判定逻辑全不动。
- **Jev-Omni 未起服时降级**：`rank_runs()` 返回 `mode="degraded"`，Compose 退回「按分歧归因选」，
  不阻塞闭环。本机 choice 型实测 80%，score 型 12.8%（禁用）。
- **不承诺「更多 agent = 更高正确率」**：105 个 L2 agent 里真正可并行的约 30 个（其余有依赖链），
  实际加速远低于 30×；收益主要来自**归因质量**（知道改哪一维），不是并行度。

## MVP-1 — 10 个 agent 的真实现 + V64/CGICE 回归（v2.24.0，2026-10-29）

**NEW in v2.24.0**：把 `agent_fleet.py` 的 10 个 mock 换成真实现（`agent_fleet_real.py`），
在两个已知 P0 缺陷的真实证明文件上回归。**调度/对比/判定骨架一行未改**，只换 `_EXEC` 表。

### 真实现分工（因本机无 Lean 编译器，4 个显式降级）

| agent | 真实现 | 需要编译？ |
|---|---|---|
| P01 StatementTranslator | 从 `.lean` 提取全部 theorem/lemma 声明 | 否 |
| P03 TargetStrengthAuditor | 正则扫结论里的硬编码观测常数（`0.\d{6,}` 等） | 否 |
| **T01 SkeletonGenerator** | 检查每个定理是否有真实证明体（非空、非纯 sorry） | 降级 |
| **T06 ProofStateDebugger** | 静态定位缺陷行（pca findings + sorry 行号） | 降级 |
| **T07 SorryEliminator** | 统计 sorry 数与行号，不尝试修复 | 降级 |
| H02 ConditionalRefactorer | 检测 `axiom X : Prop` 条件模式占比 | 否 |
| H05 PerformativeHonestyDetector | **真调** `physical_content_audit.audit()` | 否 |
| **E01 AxiomDependencyPrinter** | 静态替代 `#print axioms`：axiom 声明 + 本文件引用计数 | 降级 |
| E02 GoldenGateChecker | 非经典公理筛查（propext / Classical.choice / Quot.sound 之外） | 否 |
| E06 ChainClosureAuditor | 综合判定 | 否 |

**本机实测：`~/.elan` 不存在，`where lean` 无结果**。4 个编译类 agent 走静态投影，
detail 一律带 `[degraded: no lean]` 标记，**不假装编译成功**。

### 回归结果（4 路并行 × 两个真实文件）

| 对象 | 规模 | 最佳 verdict | 卡在哪 |
|---|---|---|---|
| **V64** `A30_Formal_Verification.lean` | 310 行 / 5 定理 / 4 公理 / 0 sorry | **BLOCK** | H02（0/4 条件形式）、E02（4 个非经典公理） |
| **CGICE V9.1** `cgice_proof.lean` | 2400 行 / 47 定理 / 88 公理(去重 25) / 10 sorry | **BLOCK** | T01（主方程 sorry-only）→ T06/T07 传导、H02（0/25）、E02（25 个非经典） |

两个真实发现（不是 mock 演出来的）：
1. **CGICE `target1_cgice_master_equation` 的证明体是 sorry-only** —— 它正是 CGICE 的核心定理，
   一编译就会暴露。这解释了 Stage A 实验里为什么 flat repair 会把它"修"成 `deriv I_cycle = 0`。
2. **V64 的 4 个公理在本文件内引用数为 0** —— 静态看是孤立公理（需跨文件确认，
   detail 里明确写 `file-local` 以免误判）。
3. 两个文件的 `physical_content_audit` gate 都是 **WARN**（V64 有 5 个 `shallow_proof`、
   CGICE 有 4 个），即「没有定义重言式，但有一批浅层证明」—— 与人工评审结论一致。

### 诚实边界（真实现暴露的新事实）

- **harness 敏感度显著低于 mock**：mock 里 `scaffold_off` 直接让 T01 崩；真实现里
  **审计结果是文件事实**，harness 只能影响生成类 agent（P01/T07）。
  4 个 harness 在 CGICE 上都是 4 ok / 10 步 —— 轨迹差异仅存在于 P01/P03 的产物指纹。
  **结论：真实现阶段，harness 精炼的价值要等 P01/T07 真接 LLM 后才显现**，
  不能拿 mock 的"三代进化"曲线当真实预期。
- **T01 失败不再硬阻断**：早期版本 P01/T01 都 break，导致一个 sorry-only 定理就让
  H02/H05/E01/E02 全部拿不到结果。现在只有 P01 失败才 break。
- **E01 的孤儿判定是 file-local**：跨文件引用需要 `--lean-deps`（未实现），
  所以「4 个孤立公理」只能当提示，不能当 BLOCK 依据。

```bash
cd scripts
python agent_fleet_real.py --self-test                                    # V64 + CGICE 双回归
python agent_fleet_real.py --lean "path\to\proof.lean" --output r.json     # 单文件审计
```

## MVP-2 — P01/T07 接真 LLM，harness 精炼终于有作用对象（v2.25.0，2026-10-29）

**NEW in v2.25.0**：MVP-1 回归暴露的核心问题——4 个 harness 在真实文件上结果完全一样，
因为审计类 agent 判的是**文件事实**，harness 改不动。只有生成类 agent（P01 出命题 /
T07 补证明）才受 harness 影响。本版把这两个接上真 LLM。

### 新增两个脚本

| 脚本 | 职责 |
|---|---|
| `scripts/proof_llm.py` | stdlib LLM 后端：`llm()` / `extract_lean()` / `has_decl/sorry/substantive_tactic`，磁盘缓存 + 三级降级 |
| `scripts/agent_llm.py` | `run_proof_llm()` / `run_fleet_llm()`：P01/T07 走 LLM，其余 8 个复用 `agent_fleet_real` |

```bash
python proof_llm.py                       # 在线/降级自测
python agent_llm.py --self-test           # P01 真生成 + memory 对比
```

### 🔴 关键坑：reasoning 模型的 thinking 会吃光 max_tokens

实测 `deepseek-v4-pro`（temperature=0）在 `max_tokens=16` 时返回 **content=""**：

```
max_tokens=16    content=''      finish=length  reasoning_tokens=16   ← 全给思考
max_tokens=256   content='PONG'  finish=stop    reasoning_tokens=21
max_tokens=8192  content='```lean...'           reasoning_tokens=918
```

**复杂物理猜想的 thinking 长度不可控**：同一个 8192 预算，有时够（78s 出 154 字符），
有时不够（95s 返回 None）。`proof_llm.llm()` 的处理：

```python
if finish_reason == "length" and reasoning_tokens >= max_tokens * 0.9:
    max_tokens = min(max_tokens * 4, 65536)   # 自动扩预算重试
```

P01/T07 直接用 **32768**。**不要用 2048/4096 跑形式化任务**——会静默返回空串。

### 真 LLM 下的 4 路并行结果（同一猜想，4 个 harness 变体）

```
baseline_concise_none    5 个声明  g_TC, lambda_perp, lambda_perp_value
concise_archive          3 个声明  standardFramework, conjecture, lambda_perp_value
detailed_none           10 个声明  lambdaPerpValue, predictedGTCSq, SL6CFramework
detailed_archive         7 个声明  lambdaPerpStandardValue, tripleGaugeBound, conditional_triple_g…

唯一产物指纹 4 / 4  →  harness 变体产生真实差异 ✅
轨迹首个分歧步：P01 [output_diverge]
```

**这是 harness 精炼能成立的直接证据**：
- `concise` → 精简定义（3–5 个声明）
- `detailed` → 显式框架与边界（7–10 个声明）
- `archive_prior` → 引导出 **`conditional_triple_g…`**（条件定理模式），
  即记忆块里的历史成功先例真的改变了生成结构

### 成本与缓存（必须知道）

- **60–100 秒 / 次**调用（v4-pro，复杂猜想）；4 路并行一轮约 5–8 分钟
- **磁盘缓存**：key = sha256(model + prompt + params)，落 `%TEMP%\proof_llm_cache\`
  同一 harness 变体重复跑不再收费（实测 4 路里 3 路命中缓存，wall=0.0s）
- 想换 temperature / max_tokens 就一定重新计费（缓存 key 含这两个参数）

### 诚实边界

- **T07 只尝试 1 次改写**：模型一次没消掉 sorry 就算失败，不做多轮自修复
  （多轮留给 Stage A strict-superset repair，避免这里重复造轮子）
- **无 Lean 编译器**：T07 生成后**无法编译验证**，判据只能是「无 sorry + 有实质 tactic」，
  `has_substantive_tactic` 是正则启发式，不是形式化保证
- **P01 判据不要求 0 sorry**：P01 只负责出命题（`:= by sorry` 是合法的中间态），
  证明由 T07 负责
- **降级链是三级不是两级**：LLM 不可用 → 回落静态实现 → 静态也不可用（无文件）→ FAIL

## EmbeddingGemma-2 集成 (v2.17.0, 2026-10-08)

**NEW in v2.17.0**: **Stage 4.5 论文引用语义核查**。集成 EmbeddingGemma-2（litert-community/embeddinggemma-2-740m-litert-lm，768 维，int4 QAT，8K ctx）做幻影引用检测。

- 新增 `scripts/semantic_reference_check.py`：在 reference_verification.py 的编号层核对之上，加 embedding 语义匹配层（引用上下文 vs 文献条目余弦相似度），用相对离群（Tukey 下界 Q1−1.5×IQR）而非绝对阈值检测疑似幻影引用。
- 已接入 `pipeline_orchestrator.py` 的 `run_stage4_paper`（论文生成后自动运行 Stage 4.5，gate=WARN 不阻塞 Stage 4；EmbeddingGemma-2 不可用时优雅降级 PASS+note）。
- 依赖 `litert-lm-api` + `ai-edge-litert`（LiteRT-LM 格式 `.litertlm`，**非** transformers/sentence-transformers）；封装模块 `embeddinggemma.py`（embed/cosine/semantic_match）软链到 Hermes venv site-packages，全局 `import embeddinggemma`。
- **精度限制（务必知晓）**：int4 量化 edge 模型对学术文本区分度有限——真实引用相似度全挤在 0.68-0.80 窄带，适合语义检索/排序，**不适合**绝对阈值判断幻影引用。本阶段定位为「检索辅助 + 相对离群启发式」，只提示疑似幻影引用供人工复核，不承诺精确判定。若需高精度引用验证，用 text-embedding-3-large / bge-large 级别模型。

---

## SkillOpt 优化增量 (v2.16.0, 2026-10-07)

**NEW in v2.16.0** (from SkillOpt checklist-based ReflACT, 2026-10-07): **Stage 3.5b 物理内容审计补充 8 类缺陷检测**。补齐物理内容审计的 8 个盲区：参数化伪装 / 状态升级 / 循环定义 / 假实数等式 / 孤立公理 / 换名复发 / import ghost 属性 / 嵌套注释 sorry 假阳性。每条规则含触发条件 + 反触发条件 + P0-P3 分级判据。

---

### c04 参数化伪装检测（Parameterized Disguise）

**触发条件**（满足任一即触发）：
- 定理/引理的结论中出现自由参数 `p`，且该参数在证明体内被赋值为某个具体观测常量（如 `p := 0.007297...`、`p := 137.036`），随后结论被当作"从第一性原理导出"。
- `axiom`/`theorem` 签名含未约束自由变量，其取值仅由外部数值反推得到，且该变量未出现在任何前置假设或定义域约束中。
- 证明中出现形如 `have h : f p = observed := by rfl` 或 `native_decide` 直接闭合数值的模式，而 `p` 无独立来源。

**反触发条件**（不触发）：
- 自由参数在签名中被显式量化并有物理来源注释（如 `(α : ℝ) (hα : α = fine_structure_constant)`）。
- 参数为定理的显式输入（`theorem foo (p : ℝ) : ...`），且调用方负责提供，非证明体内反推。
- 参数出现在 `variable` 块且被 `omit`/`include` 显式管理。

**分级判据**：
- P0（BLOCK）：结论声称"导出"但参数实为观测值反推，且无来源标注。
- P1（WARN）：参数有来源但未在签名中约束。
- P2（PASS）：参数显式量化且有来源注释。

---

### c05 状态升级检测（Status Escalation）

**触发条件**（满足任一即触发）：
- 声明关键字为 `theorem`/`lemma`，但证明体以 `sorry`、`admit`、`by assumption` 或未实例化的 `axiom` 收尾，且该声明在后续被当作已证事实引用。
- 注释或文档字符串将 `axiom`/`hypothesis`/`Ansatz` 描述为 "theorem"、"proven"、"derived"。
- 同一命题先以 `axiom` 声明，后以 `theorem` 重声明且证明体引用前者（循环升级）。

**反触发条件**（不触发）：
- 显式使用 `axiom` 关键字且文档一致标注为公理/假设。
- `theorem` 证明体完整闭合（无 `sorry`/`admit`），即使依赖公理也属正常。
- 临时 `sorry` 位于 `example` 或 `-- TODO` 标记的草稿块内。

**分级判据**：
- P0（BLOCK）：`theorem` 含 `sorry` 且被下游引用为已证。
- P1（WARN）：文档措辞与关键字不一致但无下游依赖。
- P2（PASS）：关键字与文档一致。

---

### c06 循环定义检测（Circular Definition）

**触发条件**（满足任一即触发）：
- 定义链 `A := f(B)` 且 `B := g(A)`，二者互引且无外部基例。
- `def`/`abbrev`/`axiom` 的展开图存在有向环（可用 `#print axioms` 或依赖图工具检测）。
- 定理 A 的证明引用定理 B，B 的证明引用 A，且无归纳/递归结构支撑。

**反触发条件**（不触发）：
- 递归定义有明确 `termination_by`/`decreasing_by` 且基例独立。
- 互递归 `mutual` 块有结构递减证据。
- 环中至少一个节点由外部公理或观测独立锚定。

**分级判据**：
- P0（BLOCK）：无基例的纯循环定义。
- P1（WARN）：有基例但环未显式标注。
- P2（PASS）：递归有终止证据。

---

### c07 假实数等式检测（False Real Equality）

**触发条件**（满足任一即触发）：
- `axiom`/`theorem` 断言两个实数精确相等，但右侧为十进制近似（如 `π = 3.14159`、`α = 0.00729735256`）。
- 使用 `norm_num`/`decide` 闭合的等式实际依赖浮点截断。
- 等式两侧差值小于 `1e-6` 但被声明为 `=` 而非 `≈` 或区间包含。

**反触发条件**（不触发）：
- 显式使用 `≈`、`|x - y| < ε` 或 `Set.Icc` 区间形式。
- 等式为定义（`def π := Real.pi`）而非断言。
- 近似值有 `-- approximation, exact value in ref` 注释且不参与下游精确推理。

**分级判据**：
- P0（BLOCK）：精确 `=` 断言十进制近似且被下游当精确值用。
- P1（WARN）：近似等式无注释。
- P2（PASS）：使用 `≈` 或区间形式。

---

### c08 孤立公理检测（Orphan Axiom）

**触发条件**（满足任一即触发）：
- `axiom` 声明后在整个项目中被引用次数为 0（可用 `#print axioms` 反向扫描或 grep 引用）。
- 公理仅在自身声明文件出现，无 `import` 方使用。
- 公理被 `@[simp]` 等属性标记但无重写目标。

**反触发条件**（不触发）：
- 公理位于 `Scratch`/`Draft`/`_archive` 目录且显式标注为未使用。
- 公理为对外 API 的一部分（`public` 且文档标注为接口）。
- 公理被 `export` 或列入 `@[expose]`。

**分级判据**：
- P1（WARN）：孤立公理无标注。
- P2（PASS）：孤立但有归档标注或对外接口说明。
- P0（BLOCK）：孤立公理被下游间接引用为已证事实（结合 c05）。

---

### c09 换名复发检测（Renamed Recurrence）

**触发条件**（满足任一即触发）：
- 本轮新增 `axiom` 的签名（类型表达式规范化后）与上一轮已删除缺陷公理的签名同构，仅标识符名不同。
- 公理体/注释与历史删除记录语义等价（可用规范化哈希或 AST diff 比对）。
- 同一物理断言以 `axiom foo_v2`、`axiom foo'`、`axiom foo_alt` 等形式重现。

**反触发条件**（不触发）：
- 新公理有独立来源引用且签名实质不同（参数、量词结构变化）。
- 历史删除记录标注为 "superseded by" 且新公理为显式替代。
- 名称相似但类型不同构。

**分级判据**：
- P0（BLOCK）：签名同构且无新来源。
- P1（WARN）：签名相似但来源存疑。
- P2（PASS）：有独立来源且签名实质不同。

---

### c11 import ghost 属性检测（Import Ghost Attribute）

**触发条件**（满足任一即触发）：
- 代码使用 `@[honest_axiom]`、`@[verified]`、`@[proven]` 等自定义属性装饰声明，但注册该属性的文件（含 `register_attribute`/`initialize` 的模块）不存在或未被 `import`。
- 属性名在 `import` 图中无定义，Lean 静默忽略（不报错）。
- 属性被用于绕过审计（如标记 `axiom` 为"已验证"）。

**反触发条件**（不触发）：
- 属性注册文件存在且被显式 `import`。
- 属性为 Lean 核心/标准库内置（如 `@[simp]`、`@[reducible]`）。
- 属性在 `lakefile` 的依赖中可解析。

**分级判据**：
- P0（BLOCK）：ghost 属性用于标记公理为已证。
- P1（WARN）：ghost 属性存在但未影响审计结论。
- P2（PASS）：属性注册文件存在且被 import。

---

### c12 嵌套注释 sorry 假阳性（Nested Comment Sorry False Positive）

**触发条件**（用于抑制误报）：
- 检测工具在 `/- ... -/` 块注释内匹配到 `sorry`/`admit` 关键字并报告。
- `sorry` 位于 `--` 行注释内。
- `sorry` 位于字符串字面量内（如 `"sorry"`）。

**反触发条件**（即真正触发 sorry 检测的条件）：
- `sorry` 位于块注释外的实际代码位置。
- `sorry` 位于 `/- ... -/` 嵌套块的外层之后（Lean 4 支持嵌套注释，需正确配对）。
- `sorry` 位于 `docComment`（`/-- ... -/`）内但该 docComment 被 `#check` 等实际求值。

**分级判据**：
- P3（PASS）：`sorry` 在注释/字符串内，确认为假阳性，不报告。
- P0（BLOCK）：`sorry` 在活跃代码中（由 c05 处理）。
- P1（WARN）：嵌套注释配对存疑，需人工复核。

**实现提示**：解析时需维护注释嵌套深度计数器，仅在深度为 0 时匹配 `sorry`。
