# Harness² 集成评估（google-research/harness2, arXiv:2610.14224）

**评估日期**：2026-10-19
**结论**：正确率提升空间 **~0-3%**（P3 级，不推荐嫁接主线）。核心机制已被
ScienceBuddy/Dream-RSI/RSIHub/AIDE²/AI-Scientist 等框架的增量覆盖；harness2 的
独有卖点「无需 ground-truth verifier」在形式化证明场景是**降级**。

---

## 1. Harness² 是什么

Google 开源的「递归 agent harnessing」框架。核心命题：**模型权重固定，只优化
harness**（模型周围的系统）。两层递归：

- **Task-level**：对比式 **Propose–Probe–Compose**（提议编辑 → 探测效果 → 从行为
  对比组合精炼 harness）
- **Harnessing-level**：experience reflector 把采纳的 harness + 证据支持的教训
  更新到持久 improvement harness

8 个可编辑组件（c1..c8）：system prompt / guardrails / memory / tool guidance /
subagents / skills / scripts / plugins。

**关键设计**：`RunView` 从不携带 score（源码 `spec.py` 注释 "Never carries a
score"），方法层只看到 `delivered` / `ok` / `trajectory` 行为信号，且
`_accept_tree` 强制 `assert_tree_has_no_grader_verdicts`（禁止 grader 泄露）。
改进信号完全来自**行为轨迹对比**，而非 ground-truth 分数。

报告结果：GLM-5 / Gemini 3.5 Flash 在 JobBench（+4.5）、LAB（+11.8pp partial）、
WorkBuddy（+11.5）上超越 base harness。

## 2. 逐项对比：harness2 机制 vs SDP 现有能力

| harness2 机制 | SDP 对应 | 状态 |
|---|---|---|
| 两层递归（task + harnessing） | v2.24 Stage 3.8 pipeline_meta_evolution | **已覆盖** |
| Propose（提议 harness 编辑） | v2.24 辅助模型提议 PipelineHarness 改进 | **已覆盖** |
| Probe（多候选执行对比） | Stage 3.6 冻结评估器进化 + BFTS 多草稿 | **部分覆盖** |
| **Compose（行为轨迹对比组合）** | Stage 3.8 是「确定性评估严格更优替换」单候选 | **唯一差异** |
| experience reflector（经验反思） | v2.7 replay + v2.8 archive 因果三元组 | **已覆盖** |
| library + ledger（库 + 账本） | archive.jsonl + harness_archive.jsonl | **已覆盖** |
| 8 组件结构化 harness | PipelineHarness（编排策略 JSON，未细分） | 部分覆盖 |
| **无需 verifier 行为对比** | Lean 编译 + 黄金门控（强 verifier） | **降级** |

## 3. 为什么提升空间小

### 3.1 核心机制已被覆盖

SDP 在 v2.4–v2.25 期间已密集嫁接了 10+ 个 RSI/元进化框架（RSIHub、Dream-RSI、
RSIAgent、AIDE²/RSI、JANUS、ScienceBuddy、AI-Scientist、BootLoops、Colosseum、
prove2me…）。harness2 的「递归 harness 自我改进」不是新概念：

- v2.24 `pipeline_meta_evolution.py`（ScienceBuddy）= harness2 的 harnessing-level
  recursion（辅助模型提议 harness → 确定性评估 → 严格更优才替换 → append-only 归档）
- v2.12 `proof_policy_optimizer.py`（Dream-RSI）= 策略元优化
- v2.7 `replay_strategies.py`（Dream-RSI）= 历史重放反馈
- v2.25 `proof_manager_agent.py`（AI-Scientist）= 跨阶段元协调

### 3.2 「无需 verifier」在形式化证明是降级

这是 harness2 最核心的卖点，但**恰好在 SDP 场景不适用**。形式化证明有最强的
verifier：

- Lean 编译 EXIT=0
- 0 sorry / 0 admit / 0 axiom
- `#print axioms` 黄金门控（只依赖 propext/Classical.choice/Quot.sound）
- 物理内容审计（定义重言式 / 字面恒等 / 浅层证明）

harness2 用「行为对比」（delivered/ok/trajectory）替代 verifier 信号，是因为
JobBench/LAB/WorkBuddy **没有**确定性的 ground-truth。形式化证明**有**（编译结果
就是最精确的「行为信号」），用弱信号替代强信号是降级，既丢失精确性又增加多候选
并行执行的成本。

### 3.3 任务域不匹配

harness2 的 3 个基准（JobBench 办公 / LAB 法律 / WorkBuddy 代码）都是「开放任务，
靠『是否交付 artifact』判断」。形式化证明靠「编译 + 0 sorry」判断，前者的行为
信号在后者场景**冗余**——编译通过/失败本身就是最精确、最便宜的行为对比。

### 3.4 验证瓶颈未解决

SDP v2.24 诚实边界已明确：本机 P620 无法重跑完整 pipeline 求真实证明成功率，
真实优劣区分需 RTX4000 服务器。harness2 即使嫁接，也无法在本机验证收益——同
一瓶颈。这进一步压低「值得移植」的性价比。

## 4. P0-P4 嫁接方案

| 级别 | 内容 | 建议 |
|---|---|---|
| **P0** | — | 无（无高性价比增量） |
| **P1** | — | 无 |
| **P2** | — | 无 |
| **P3** | Compose 行为对比组合：把 Stage 3.8 的「单候选严格更优替换」升级为「多候选 PipelineHarness 并行执行 + 行为轨迹对比组合」 | 不推荐。形式化证明有 verifier，直接看编译结果即可归因，多候选并行只增成本，收益 ~0-3% 且无法本机验证 |

## 5. 诚实边界

- 本评估是**静态机制对比**（深读 harness2 全库 spec/proposer/recursion/prompts +
  SDP v2.25 全量 SKILL.md + 30 reference），非实测。真实收益需在 RTX4000 服务器
  上跑「SDP Stage 3.8 单候选替换 vs harness2 多候选组合」的 A/B 对比才能定论。
- 「~0-3%」是基于机制重叠度 + verifier 冗余度 + 任务域错配的**估计**，非测量值。
- harness2 作为**方法论参考**（Propose–Probe–Compose 的对比式 harness 精炼设计、
  8 组件结构化、无 verifier 的行为对比纪律）仍有价值，只是不值得移植到 SDP 主线。

## 6. 附：harness2 关键源码位置

| 文件 | 核心内容 |
|---|---|
| `harness2/core/spec.py` | RunView（"Never carries a score"）+ BenchmarkAdapter 接缝 |
| `harness2/core/proposer.py` | Proposer：隔离 workspace agentic 编辑 harness + audit trail + cache |
| `harness2/core/recursion.py` | `_run_stage`（build evidence → mission → prop.call → _accept_tree）+ `_accept_tree`（autotrigger/diff/validate/no-grader-verdicts） |
| `harness2/core/prompts.py` | propose/aggregate/compose_round/select/experience prompt 模板 |
| `harness2/core/context.py` | 证据构建（轨迹/交付物/行为对比 → mission） |
