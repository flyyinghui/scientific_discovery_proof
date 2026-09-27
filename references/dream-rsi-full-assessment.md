# Dream-RSI 完整评估：对 scientific-discovery-proof 猜想证明策略与证明通过率的实质帮助

**论文**：Dream-RSI: Recursive Self-Improvement through Evolving Worlds（arXiv:2609.14858，Google + DeepMind + UMD + UVA，17 作者）
**代码**：github.com/zhengkid/Dream-RSI
**评估日期**：2026-09-27

---

## 一、Dream-RSI 核心机制（一句话）

**积累的发现历史（discovery trees）本身就是一个可重放的模拟器**——用它做「做梦」（dreaming），在不跑真实在线探索的情况下，快速评估并迭代改进「探索策略」本身。

三阶段循环：
1. **Online Explore**：当前探索策略 π_t 引导 coding agent 扩展发现树，记录轨迹
2. **Construct Replay Simulator**：发现树转成可重放的模拟器池
3. **Dreaming-based Policy Improvement**：生成大量候选策略 → 在重放模拟器里模拟执行 → 选最优 → 重新部署在线

**关键点**：优化的对象是**探索策略本身（可执行代码）**，不是单个候选解。这是「元层」优化。

---

## 二、与已集成 v2.7.0 的差距

v2.7.0（2026-09-17）已经落地了 Dream-RSI 的**表层**：

| Dream-RSI 概念 | v2.7.0 已落地 | 深度 |
|---|---|---|
| replay simulator | `ReplaySimulator` 类（变异策略成功率 + 缺陷修复率统计） | 浅（只统计变异策略） |
| off-policy 反馈 | 盲区检测注入诊断 prompt | 浅 |
| 变异策略显式化 | 5 个 MUTATION_STRATEGIES + ε-greedy | 中 |
| **探索策略元优化**（policy improvement loop） | **未落地** | **核心缺失** |
| **发现树重放**（tree replay） | 未落地（archive.jsonl 是扁平列表） | **核心缺失** |
| **replay objective 三项**（质量-成本+并行） | 未落地（只有「针对性硬门槛」） | **缺失** |
| **策略选择单调性保证** | 未落地 | **缺失** |

**结论**：v2.7.0 只借了「历史可重放」这个**思想**，借错了层——它把「变异策略」当成了重放对象，而 Dream-RSI 真正要优化的是**探索策略本身**。

---

## 三、对「猜想证明策略」的实质帮助（按性价比 P0-P4 排序）

### P0 —— 探索策略元优化层（核心增量，未落地）

**Dream-RSI 的核心**：探索策略 π 是**可执行代码**，通过「策略开发 agent 检查重放轨迹 → 识别成功决策/反复失败 → 改写策略代码 → 重放再评估」迭代改进。

**对应证明场景**：scientific-discovery-proof 目前所有阶段都是**固定策略**（Stage 3 的 MCTS + ABC 参数、引理顺序、公理攻击顺序、并行度、放弃阈值都是写死的）。Dream-RSI 揭示我们缺的正是「**把证明策略本身当成可优化的元层**」。

**落地**：新增 `scripts/proof_policy_optimizer.py`（Stage 3.7 前置），把证明策略编码为可执行代码（选哪个引理先证 / 先攻哪个公理 / 并行几路 / 何时放弃一条路线），用 archive.jsonl 的历史证明尝试做重放评估，迭代改进策略代码。这是对「提高通过率」最直接的一层——**让管线学会「怎么证明」，而不只是「修复失败」**。

### P1 —— 证明树重放模拟器（深化已有）

archive.jsonl 目前是**扁平列表**（每条记录独立），而 Dream-RSI 的发现树是**树结构**（节点有 parent-child，记录「从哪个证明状态出发 → 得到什么结果」）。

**落地**：把 archive.jsonl 重建为「证明树」——每条证明尝试记录其 parent 证明状态（哪个公理/引理未解决），重放时**确定性返回记录的 children**，快速评估「不同的证明分支顺序」哪个更快收敛到 0 sorry，不实际跑 LLM。

### P2 —— Replay objective 三项（质量 - 成本 + 并行）

Dream-RSI 的 replay score：`V = max(质量) - β1·(生成次数) + β2·(平均并行度)`。

**对应证明场景**：量化「并行证明 vs 串行证明 vs 放弃」的收益。让管线学习「哪些子证明值得并行（成本低、收益高）、哪些应该串行（有依赖）、哪些应该直接放弃（历史证明是死路）」。

### P3 —— 策略选择单调性保证

Dream-RSI 保证 π_{t+1} 不差于 π_t（候选集含当前策略）。

**对应证明场景**：策略改进时保留「当前最优策略」作为候选，避免「策略改进反而退步」——这是 Stage 3.6 进化循环（RSIHub 冻结评估器）已经隐含的「严格改进门控」的元层版本。

---

## 四、对「提高证明通过率」的量化评估（诚实分析）

### 关键限制：Dream-RSI 的实验不是「证明通过率」

Dream-RSI §4.2「Mathematics Optimization」的 3 个任务是**连续优化**：
- Sum-Difference Problem（离散组合）
- Circle Packing（几何）
- Autocorrelation Inequalities（函数）

这些任务的 score 是**连续可比的**（1.145427 vs 1.144047），而**形式化证明的通过率是离散的**（编译通过 / 0 sorry / 公理数）。Dream-RSI 论文**没有**在 Lean 形式化证明上做实验。

### 两个不可直接迁移的假设

1. **确定性重放假设**：Dream-RSI 的 offline replay 假设「从相同节点确定性返回记录的 children」。但 Lean 证明场景「从相同证明状态重新生成 Lean 代码」是**随机**的（LLM 方差），replay 的「确定性返回」不成立。
2. **连续 score 假设**：replay objective 的 quality term（max s_v）依赖 score 连续可比。证明的 score 是离散的（0/1 式），quality term 会退化。

### 能迁移的：探索策略元优化的「框架思想」

**真正能迁移、且有实质帮助的，不是 Dream-RSI 的重放机制细节，而是它揭示的一个结构性能力缺口**：

> scientific-discovery-proof 目前是「**固定策略 + 修复循环**」——所有阶段用写死的策略跑，失败后进入修复循环。但「**怎么证明**」（策略）本身从未被优化过。

Dream-RSI 的贡献是证明：**在长时程发现中，优化「探索策略本身」比优化「单个候选解」收益更大**（2.43× 成本降低、2.09× 质量提升）。这对证明管线的启示是：

- **预期收益**：把「证明计算分配」从固定策略升级为可学习策略，减少「在无效证明路线上反复尝试」的浪费 → 预期**证明时间下降、通过率提升**（对应 Dream-RSI 的成本降低结论，但**幅度需在 Lean 场景实测，不能直接套用 2.43×**）。
- **诚实边界**：这是**机制迁移**，不是**结果迁移**。Dream-RSI 的 2.43× 是 KernelBench 连续优化场景的数字，不能声称 Lean 证明也能 2.43×。

---

## 五、结论与嫁接建议

### 实质帮助总结

Dream-RSI 对「提高证明通过率」的实质帮助**不在于重放机制细节**（那针对连续优化），而在于它揭示的**元层优化能力**：

| 帮助层级 | 内容 | 状态 |
|---|---|---|
| **P0 探索策略元优化** | 把「怎么证明」（引理顺序/公理顺序/并行度/放弃时机）当可优化代码 | **核心增量，未落地** |
| **P1 证明树重放** | archive.jsonl 重建为树，确定性重放评估证明路线 | 深化已有 |
| **P2 replay objective** | 质量-成本+并行，量化并行/放弃决策 | 未落地 |
| **P3 单调性保证** | 策略改进不退化 | 未落地 |

### 建议（增量嫁接，不动主线五阶段）

1. **先做 P0**：新增 Stage 3.7「证明策略元优化」脚本，把 Stage 3 的证明策略编码为可执行代码，用 archive.jsonl 历史重放反馈迭代改进。这是唯一「新能力」级别的增量。
2. **再做 P1**：archive.jsonl 加 `parent_state` 字段，重建为证明树，支持树重放。
3. **P2/P3 顺带**：replay objective 三项 + 单调性保证，是 P0 的配套。

### 与其他已集成框架的关系

- 与 **RSIHub**（Stage 3.6 冻结评估器进化）：RSIHub 优化的是「**证明**（Lean 代码）」的修复，Dream-RSI 优化的是「**证明策略**（怎么证明）」的元层——两者**正交互补**，不冲突。
- 与 **RSIAgent**（Stage 2.5 课程规划 + 3.6d 深挖）：RSIAgent 的 curriculum 是「**预定义的**证明变体任务」，Dream-RSI 的元优化是「**学习**如何生成/选择这些任务」——Dream-RSI 是 RSIAgent 的元层。
- 与 **Colosseum**（Strategy Explorer，v2.11.0）：Colosseum 的 strategy explorer 是「证明前生成 3-5 条候选路线」，Dream-RSI 的元优化是「**用历史反馈迭代改进**路线生成策略本身」——Colosseum 是静态生成，Dream-RSI 是动态学习。

**一句话结论**：Dream-RSI 的独特价值是让 scientific-discovery-proof 从「**固定策略 + 修复循环**」升级为「**可学习策略 + 修复循环**」——补上「证明策略元优化」这缺失的一层，这是当前已集成的 6 个框架（Co-Scientist / RSIHub / RSIAgent / ScientistTwo / Colosseum / Dream-RSI 表层）都**没有**覆盖的能力。
