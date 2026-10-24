# IdeaScientist 对 scientific-discovery-proof 技能的提升价值评估

> 论文：IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation（arXiv:2610.04074，Liu et al. 2026）
> 代码：github.com/jiarui-liu/IdeaScientist（CC BY-NC 4.0）
> 评估日期：2026-10-13
> 评估者：灰因斯坦（Grey Turing），基于论文摘要 + README + roles.py/reward.py/novelty.py 深读

---

## 一、IdeaScientist 是什么

**把"科学创意生成（ideation）"从下游实现中分离为独立任务**，并用 RL 训练三个角色各自擅长的一环：

| 角色 | 职责 | 产出 |
|---|---|---|
| **gap finder** | 识别密切相关工作中的**方法学局限**（非 benchmark/数据缺口） | `gaps.md` |
| **innovator** | 在**另一个问题设置**中寻找其逻辑可迁移到该空白的机制 | `candidates.md` |
| **report writer** | 把存活的直觉发展成完整提案 | `report.json` |

核心直觉：**一个领域的挑战，常能被另一个领域解决类似挑战的机制解决**（跨域机制迁移）。

**关键机制**：
1. **Svalbard Idea Vault**（2.77M 分解创意）：每篇论文缩减为**结果掩码记录**（问题/方法/设计，删除所有测量结果），agent 只能读"人类团队打算做什么"而不知道"是否成功"。
2. **RL 奖励**：`r = 0.85·g·(r_free + r_ref + r_cit)/3 + 0.15·r_proc`，`g` 是有效性门 {0,1}。
3. **引用可验证门**：citation gates 在**代码中对照 rollout 自身文件状态计算**（非 LLM 判断），伪造 near-miss id 是最常见的 reward farming，故做成可验证。
4. **时序控制评估**：限制访问 cutoff 日期前文献，衡量提案与人类后来探索方向的对齐度（15K 论文）。

**结果**：Qwen3.6-27B 上超最强开源 autoresearch 基线 14.0%（novelty 驱动），超 Claude-4.8-Opus / GPT-5.4 达 5.9%。

---

## 二、定位关系：相邻但不同的阶段

| | scientific-discovery-proof | IdeaScientist |
|---|---|---|
| 任务 | **证明生成**（猜想 → 形式化验证 → 论文） | **创意生成**（空白 → 提案） |
| 入口 | 给定猜想 | 给定问题领域 |
| 核心 | PPE-V5.1Hybrid + Lean 0-sorry + 冻结评估器进化 | 三角色 RL + 跨域机制迁移 |
| 出口 | 证明包 + 论文 | 研究提案 |

**结论：IdeaScientist 补的是 scientific-discovery-proof 的"上游"**——把入口从"给定猜想"前移到"生成猜想"。这是当前 scientific-discovery-proof 最缺的一环（猜想起源目前依赖人工或大脑召回，无系统化的生成机制）。

---

## 三、可移植增量（按 P0-P4 性价比排序）

### P0-① 跨域机制迁移（innovator 角色）→ Stage 0 前的「猜想生成器」 ★★★★★

**缺口**：scientific-discovery-proof 从"给定猜想"开始，猜想起源无系统机制。

**移植**：新增 Stage 0.5 之前的「跨域猜想生成器」——给定一个研究问题，故意**离开问题所属子域**，检索相邻领域（如从博弈树搜索借 MCTS、从统计物理借重整化群）中可迁移的机制，生成候选猜想。这正是 innovator 的核心。

**落地**：brain.recall() 跨域检索（现有）+ 一个 innovator 风格的 prompt 模板。无需新语料库，大脑 181K 神经元的跨域桥接（已有 cross-domain bridge）是现成的检索后端。

**收益**：把管线从"证明器"升级为"发现器 + 证明器"。

### P0-② 引用可验证门（代码计算，非 LLM 判断）→ 强化 Stage 3.5 ★★★★

**缺口**：scientific-discovery-proof 的 reference_verification.py（Stage 3.5 P0-1）是**事后审计**，IdeaScientist 把它做成**训练/评分级 gate**。

**移植**：把"引用 id 可解析 + 确实读过（有 digest 文件）"做成**代码计算的确定性 gate**，在 Stage 3.6 进化循环的评分前运行，失败则 veto（而非靠 LLM 判断）。这是"可验证而非可评判"的原则——对已有 reference_verification 的强化。

**收益**：把引用核查从"审计项"提升为"评分信号"，防 reward farming。

### P1-③ 结果掩码（results-masked）→ 喂投大脑 / 证明策略学习 ★★★☆

**缺口**：scientific-discovery-proof 喂投大脑时，概念带"结果"（如"X 方法有效"），导致 agent 学结果导向而非方向。

**移植**：喂投大脑时，对"证明策略"类概念做**结果掩码**——只保留"方法/方向/机制"，删除"是否成功"的结果。与 Stage 3.6 的 learn_on_pass（只记"不退化"先例）方向一致。

**收益**：中。scientific-discovery-proof 主要非训练数据驱动，价值低于 IdeaScientist 原生场景。

### P1-④ 时序控制评估（temporal cutoff）→ 猜想质量预测 ★★★☆

**缺口**：scientific-discovery-proof 无"未来信息泄漏"概念（证明任务无未来）。

**移植**：若做「猜想质量评估」（预测哪些猜想会被未来研究证实），引入 cutoff 日期约束——评估时限制访问 cutoff 前的文献，衡量猜想与人类后来方向的对齐度。

**收益**：中。仅当增加"猜想质量预测"模块时有用。

### P2-⑤ 盲区 orchestrator + 阶段工件唯一接口 ★★★

**缺口**：scientific-discovery-proof 的 Stage 之间有 JSON 接口，但 orchestrator 无"盲区"约束。

**移植**：借鉴"orchestrator 不能直接检索/读原文，只通过子代理写的工件了解状态"——这使每个阶段的工件成为**唯一可检查的接口**，也让每阶段可独立评估/训练。scientific-discovery-proof 的 pipeline_orchestrator 可引入此约束。

**收益**：中。提升分解可检查性，但需要重构 orchestrator。

### P2-⑥ Mechanism non-obviousness 两步调用（先冻结候选，再评分）★★★

**缺口**：scientific-discovery-proof 的 Stage 3.5 审计评估"证明是否平凡/重言式"时，单次 LLM 调用可能逆向工程出"应判平凡"的答案。

**移植**：借鉴两步调用——第一步**看不到待评估对象**，独立推导候选"平凡化模式/证明策略"；第二步拿冻结列表评分待评估对象。防逆向工程。

**收益**：中。强化 physical_content_audit.py 的反重言式检测。

### P3-⑦ judge 解析失败 → DROP rollout（而非伪造分数）★★☆

**缺口**：scientific-discovery-proof 的 Stage 3.6 进化循环，评分 LLM 解析失败时可能伪造分数。

**移植**：借鉴"judge 无法解析就丢弃 rollout（loss_multiplier=0），而非用伪造值评分"——对应 Stage 3.6 的 sealed evaluator 原则，但更硬（丢弃而非降级）。

**收益**：中低。已有 sealed evaluator 部分覆盖。

### P3-⑧ paper reader 隔离 + digest 累积 ★★☆

**缺口**：scientific-discovery-proof 的子代理 context 管理。

**移植**：借鉴"全文只进独立 single-turn context 的 paper_reader，其他角色拿 goal-by-goal digest（累积式）"。

**收益**：中低。context 管理优化，非核心。

---

## 四、优先级总表

| 优先级 | 增量 | 来源模块 | 填充缺口 | 预期收益 |
|---|---|---|---|---|
| **P0-①** | 跨域机制迁移 → 猜想生成器 | innovator 角色 | 猜想起源 | 最高（发现器+证明器） |
| **P0-②** | 引用可验证门（代码计算） | reward.py gates | Stage 3.5 引用核查 | 高 |
| P1-③ | 结果掩码 | Svalbard Vault | 大脑喂投 | 中高 |
| P1-④ | 时序控制评估 | temporal cutoff | 猜想质量预测 | 中高 |
| P2-⑤ | 盲区 orchestrator | orchestrator | 分解可检查性 | 中 |
| P2-⑥ | 两步调用防逆向 | novelty_aspects | 反重言式审计 | 中 |
| P3-⑦ | 解析失败丢弃 | reward.py drop | 进化循环评分 | 中低 |
| P3-⑧ | paper reader 隔离 | read_paper | context 管理 | 中低 |

---

## 五、诚实边界

1. **阶段不同**：IdeaScientist 是"创意生成"，scientific-discovery-proof 是"证明生成"。移植是**机制移植**（prompt 模板 / gate 设计 / 评估设计），**非代码转录**——两者的输入输出完全不同。

2. **RL 训练不可复现**：IdeaScientist 的三角色 RL 训练需要 NeMo-RL + Qwen3.6-27B（tensor parallel 8）+ Svalbard Idea Vault 2.77M。本机 WSL P620 4GB 无法跑。**移植的只是"设计模式"，不移植训练管线。**

3. **跨域迁移依赖全学科语料库**：innovator 的跨域检索依赖 Svalbard Idea Vault（全 arXiv 学科）。scientific-discovery-proof 的大脑（181K 神经元）是物理/数学领域，跨域检索范围受限。P0-① 的落地需接受"大脑领域偏物理/数学"的约束。

4. **核心增量只有 P0-① 和 P0-② 是真正的新能力**：P1-P3 是对已有机制的强化或优化，非革命性新增。scientific-discovery-proof 已集成 10 个外部框架，IdeaScientist 的第 11 个贡献是**「上游猜想生成」这个维度**（此前无框架覆盖）。

5. **评估口径差异**：IdeaScientist 的 14.0% 提升是"提案对齐人类方向"（novelty），不是"证明成功率"。移植到 scientific-discovery-proof 后，收益衡量应改为"猜想质量/可证明性"，两者不可直接类比。

---

## 六、建议

**唯一值得立即落地的：P0-①（跨域猜想生成器）+ P0-②（引用可验证门）**。

- P0-① 是最稀缺的增量（补"发现"维度，此前 10 框架都在"证明"维度）。
- P0-② 是对已有 reference_verification 的"从审计到评分"升级，成本低、方向明确。

其余 P1-P3 作为"设计模式参考"归档，不主动落地（除非后续做"猜想质量预测"或"orchestrator 重构"时再提取）。

完整评估归档至 `scientific-discovery-proof/references/ideascientist-integration-assessment.md`。
