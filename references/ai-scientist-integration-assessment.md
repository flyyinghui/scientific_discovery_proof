# AI-Scientist（The AI Scientist）集成评估与落地

> 框架：SakanaAI "The AI Scientist" — Nature 2026 *"Towards end-to-end automation of AI research"*
> （Chris Lu, Cong Lu, Robert Tjarko Lange, Yutaro Yamada, Shengran Hu, Jakob Foerster et al.）
> 代码仓库：`SakanaAI/AI-Scientist`（v1，模板驱动）＋ `SakanaAI/AI-Scientist-v2`（agentic tree search）
> 评估日期：2026-10-18　落地版本：scientific-discovery-proof v2.25.0

## 一、框架定位（先按管线维度定位，再评估增量）

AI-Scientist 是**「实验型」科学发现**框架——自动化 ML 实验（创意 → 代码 → 跑实验 →
画图 → 写论文 → 同行评审），metric 是 validation loss / accuracy 等实验指标。

scientific-discovery-proof 是**「证明型」科学发现**管线——形式化证明（审计 → 数值 → 排名 →
Lean 证明 → 一致性审计 → 论文），metric 是 sorry_count / axiom_count / 编译 EXIT。

两者**维度不同**，但**元层机制通用**（阶段化 / 树搜索 / LLM 综合评估 / 元协调）。嫁接只移植
元结构，不移植 ML 实验的 goal 文案。

**重要前提**：scientific-discovery-proof 的 **Stage 4 早已命名为「AI-Scientist V2: Paper
Generation」**——即已借用 AI-Scientist V2 的「论文生成」**表层**（IMRAD 结构化 + Nature 期刊图）。
因此本次评估的实质是**补齐从未评估过的元层增量**，而非从零评估（对齐 external-framework-grafting
教训 #1「先查集成记录」）。

## 二、核心机制（代码深读，v2 全库）

| 文件 | 机制 |
|---|---|
| `treesearch/agent_manager.py` | **实验管理器 agent**：四阶段管理（initial→baseline→creative→ablation）+ 三个 LLM eval（stage_config / stage_progress / stage_completion）+ 阶段继承（best_implementation 传递）|
| `treesearch/journal.py` | **BFTS 树**：Node（plan/code/metric/is_buggy）+ Journal（draft/buggy/good_nodes）+ `get_best_node`（LLM 综合选择，失败回退 metric）|
| `treesearch/parallel_agent.py` | **debug/improve 分流**（is_buggy→debug 修编译，非 buggy→improve 减指标）+ VLM 图表分析 + metric 解析 |
| `perform_ideation_temp_free.py` | **无模板创意生成**：Semantic Scholar 文献搜索 tool + 5 轮反思（至少一次文献搜索才 finalize）|
| `perform_llm_review.py`（v2）/ `perform_review.py`（v1）| **LLM 同行评审循环**：生成论文 → LLM 模拟审稿评分 → 按意见修改 → 迭代 |

## 三、独有增量（对比已集成的 14 个框架）

scientific-discovery-proof 已集成 RSIHub / Dream-RSI / Co-Scientist / RSIAgent / ScientistTwo /
Colosseum / BootLoops / AIDE² / JANUS / IdeaScientist / ScienceBuddy / prove2me / EmbeddingGemma-2 /
MAF。AI-Scientist 的**未落地独有增量**：

| 级别 | 增量 | 落地 |
|---|---|---|
| **P0** | **实验管理器 agent（跨阶段元协调）**：LLM 自动判断阶段是否完成/是否推进/重试/放弃。之前 Stage 固定顺序硬走，缺「这个策略卡死了吗」的元判断 | ✅ `scripts/proof_manager_agent.py`（Stage 3.9）|
| **P1** | **Best-First Tree Search**：multi-draft 并行 + metric 优先展开 + debug/improve 分流。补 Stage 3 现有 MCTS+ABC 缺的「多草稿 + 最优优先」| ✅ `scripts/bfts_search.py` |
| **P1** | **LLM 综合选择最佳**（node_selection_spec）：不只 sorry_count，综合结构完整性/证据链/命名空间覆盖/下游可引用性 | ✅ 并入 `bfts_search.py` 的 `_llm_select` |
| **P2** | **四阶段管理 + 阶段继承**：initial→baseline→creative→ablation，stage N+1 继承 stage N 最佳。对应「证明骨架→完整证明」增量深化 | ✅ 并入 `proof_manager_agent.py` 的 `PROOF_STAGES` + `stage_inheritance` |
| **P2** | **无模板创意生成（文献 grounding + 反思）**：Semantic Scholar + 5 轮反思。增强已集成的 IdeaScientist | ⏳ 未落地（IdeaScientist 已覆盖三角色 ideation，文献 grounding 边际增量低）|
| **P3** | **VLM 图表分析**：物理证明图信息量远低于 ML 实验图，收益弱 | ❌ 不落地 |
| **P4** | **LLM 同行评审循环**：用户已有 Hybrid-review-my-paper（5-agent 终审），边际低 | ❌ 不落地 |

## 四、落地映射（P0/P1/P2 细节）

### P0 — `proof_manager_agent.py`（Stage 3.9 证明管理器）

AI-Scientist AgentManager 的「实验型四阶段」映射为「证明型四阶段」：

| AI-Scientist | 证明型（本落地）|
|---|---|
| initial_implementation | skeleton_implementation（骨架，编译可失败）|
| baseline_tuning | compile_fix（修复编译，EXIT=0）|
| creative_research | sorry_reduction（减 sorry/admit，0）|
| ablation_studies | axiom_ablation（公理消融，0 axiom + 经典三元组）|

- **三个 LLM eval 合一**：`_llm_decision()` 一次调用输出 `ready_for_next_stage / action /
  reasoning / recommendations / suggested_focus`。
- **黄金门控是硬顶**：`golden_gate_verdict()`（编译 EXIT=0 + 0 sorry + 0 admit + 0 axiom +
  物理内容非平凡）决定最终通过，LLM 只建议「是否值得继续投入 + 该往哪走」。
- **放弃判断**：`infer_stage` + `iterations_in_stage >= max_iterations` → `abandon_or_rescope`
  （诚实降级：建议重标定猜想或换策略，而非硬走到底）。
- **阶段继承**：`stage_inheritance.next_stage_base` 标注 stage N+1 继承 stage N 最佳证明。

### P1 — `bfts_search.py`（Stage 3 BFTS + LLM 综合选择）

- **ProofNode**：code / sorry_count / axiom_count / exit_code / structure_score /
  namespace_coverage / evidence_chain（对应 journal.Node）。
- **best-first 展开**：`node_priority()` = (是否编译通过, sorry, axiom, −structure)，小堆优先展开
  最优未展开节点。
- **debug/improve 分流**：`is_buggy = exit_code != 0`；debug=修编译，improve=减 sorry（不同 prompt 口径）。
- **LLM 综合选择**：`_llm_select()` 明确「不要只靠 sorry_count」，综合结构完整性/证据链/
  命名空间覆盖/下游可引用性；失败回退 `_metric_select()`。

## 五、诚实边界（沿用技能一贯口径）

1. **P0 的 LLM 只建议**，最终通过由确定性黄金门控决定——「LLM 判断值得继续投入 vs
   证明成立」是两回事，后者仍由编译 + 0 sorry/axiom + 物理内容审计保证。
2. **P1 的 BFTS 是搜索策略**，不是评估器——best-first 贪心可能陷入局部最优（MCTS 的 UCB
   探索项正是为此而设，两者可共存：BFTS 提供多草稿 + 分流，MCTS 提供探索/利用权衡）。
3. **LLM 综合选择只做候选排序 + 归档建议**，最终接受/拒绝由确定性门控决定，防 LLM 偏好
   给低质证明放行。
4. 两个脚本均 stdlib-only（除可选 OpenAI SDK）+ `--mock` 确定性回退 + `--self-test` 离线自测，
   无 API key 也能跑通、可独立单测。

## 六、v1 仓库说明

`SakanaAI/AI-Scientist`（v1）核心差异是「模板驱动 + few-shot 示例 + LLM 同行评审循环」，
成功率高但依赖人类模板；v2 是无模板 + agentic tree search，开放式探索、成功率低。
本次评估以 v2 代码深读为主（本机已有 v2 克隆 `~/projects/AI-Scientist-v2`），
v1 的 LLM 同行评审循环判定为 P4（用户已有 Hybrid-review-my-paper）。v1 zip 下载因 codeload
极慢（约 20 分钟仅 99MB）最终未完整解压，但其机制已从 README + Nature 论文摘要 + v2 代码确认，
不影响 P0/P1/P2 落地结论。
