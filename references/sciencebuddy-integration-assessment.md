# ScienceBuddy 对 scientific-discovery-proof 技能的提升价值评估

> 论文：ScienceBuddy: Recursive-in-Recursive Self-Improvement for Interactive Scientific Agents（arXiv:2609.17523，Xue et al. 2026，PhAI Labs）
> 代码：github.com/Gen-Verse/ScienceBuddy（Gen-Verse，简单实现 simple_scibuddy + SkyRL 子模块）
> 评估日期：2026-10-13
> 评估者：灰enstein（Grey Turing），基于论文摘要 + README + docs/algorithm.md 深读

---

## 一、ScienceBuddy 是什么

**交互式生物医学研究工作区**，把「研究者–智能体协作」转化为可复用任务、评估 rubric、harness 更新、模型训练数据。核心范式是 **recursive-in-recursive self-improvement（递归中的递归自改进）**。

### 核心：双层递归耦合

两个组件 + 一个固定辅助模型：

| 组件 | 作用 |
|---|---|
| **任务模型** M_k | 生成 agent 响应和工具使用决策 |
| **harness** H_{k,j} | 完整 Python 程序，组织 prompt、模型调用、工具执行、context、答案提交 |
| 辅助模型 | 提议 harness 变更，参数固定 |

**内层递归**（固定模型 M_k，改进 harness H）：
```
收集任务交互和反馈 → 提议 Python harness 程序 → 在固定 Val 任务上对比候选与父程序 → 选中 harness 传给模型学习
```

**外层递归**（固定 harness H，训练模型 M_k）：
```
生成 fresh on-policy 任务尝试 → verifier 评分 → SkyRL GRPO 更新模型 → 导出模型回传 harness 学习
```

$$
H_{k,j+1} = \mathrm{Select}(H_{k,j},\ \mathcal{C}_{k,j};\ M_k, D_{\mathrm{val}}),\qquad
M_{k+1} = \mathrm{GRPO}(M_k;\ H_{k,J}, D_{\mathrm{train}}),\qquad H_{k+1,0}=H_{k,J}
$$

harness 变化改变模型如何收集经验；模型更新改变哪些 harness 过程在下一阶段有效。

### 关键机制

1. **harness 是完整 Python 程序**（可替换 prompt/解析/控制流/记忆/工具编排），辅助模型提议整个程序的替换，候选在 90 Val 任务上严格更高分 + 无运行时错误才替换。
2. **execution contract**：host 强制 provenance/limits/grading/episode 终止，controller 和执行容器**无网络访问**，私密 reference 和凭据在 host。
3. **first-answer verifier reward**：`R_i = Verify(a_i^(1)) ∈ {0,1}`，只评首个提交答案，follow-up 修正不改变（防刷分）。
4. **GRPO group-relative advantage**：`A_i = (R_i - μ_x)/(std + δ)`，相对优势而非绝对分数。
5. **state carried between stages**：明确哪些状态流转、哪些清除。
6. **冻结任务 release**：715 Train / 90 Val / 90 Test，防数据泄漏。

---

## 二、定位关系：自我改进「范式」而非「任务」

| | scientific-discovery-proof | ScienceBuddy |
|---|---|---|
| 任务 | 形式化证明生成 | 交互式生物医学研究 |
| 进化对象 | **证明代码**（Lean 文件，Stage 3.6）+ **策略参数**（Stage 3.7） | **harness 程序**（内层）+ **任务模型**（外层） |
| 进化层级 | 单层（证明代码 / 策略参数各自进化） | **双层耦合**（harness ↔ 模型交替） |
| 评估器 | sealed evaluator（概念性） | execution contract（工程实现） |

**结论：ScienceBuddy 补的是「自我改进范式」维度——把 pipeline 本身（harness）作为可进化的一等对象，并与模型训练双层耦合。** 这是 scientific-discovery-proof 此前 10 个框架都没覆盖的维度：它们都进化「证明代码」或「策略参数」，没有一个进化「pipeline 编排逻辑本身」，也没有「harness 进化 ↔ 模型训练」的交替耦合。

---

## 三、可移植增量（按 P0-P4 性价比排序）

### P0-① harness 作为可进化对象 → Stage 3.8 pipeline 元进化 ★★★★★

**缺口**：scientific-discovery-proof 的 pipeline（orchestrator prompt、工具编排、评分 gate 顺序、Stage 衔接）是**固定代码**。Stage 3.6 只进化"证明代码"（Lean），Stage 3.7 只优化"策略参数"，都不动 pipeline 结构。

**移植**：把 pipeline 的编排逻辑（orchestrator 决策规则、Stage 调用顺序、评分 gate 组合）抽象为一个**可替换的 Python 程序**（`run(conjecture, api)`），用辅助模型（DeepSeek v4-pro）提议整个程序的改进，在 Val 证明任务集上对比候选与父程序，严格更高成功率才替换。

**收益**：把 scientific-discovery-proof 从"固定管线 + 进化证明"升级为"管线自身可进化"——这是真正的元层增量。

### P0-② 双层递归耦合（harness 进化 ↔ 模型训练交替） ★★★★★

**缺口**：scientific-discovery-proof 的 Stage 3.6（证明代码进化）和 Stage 3.7（策略优化）是**独立不耦合**的。

**移植**：借鉴 ScienceBuddy 的交替范式——内层（固定 DeepSeek 模型，改进 pipeline harness），外层（固定 harness，用证明结果训练/优化策略）。虽然 scientific-discovery-proof 不是训练自有模型，但可以把这个"交替耦合"范式应用到"pipeline 进化 ↔ 证明策略优化"的交替。

**收益**：这是"发现智能"的核心范式。但落地需要重新设计 Stage 3.6/3.7 的耦合关系，工作量最大。

### P1-③ execution contract 工程化（评估器冻结的工程实现） ★★★★

**缺口**：scientific-discovery-proof 的 sealed evaluator（RSIAgent P0-②）是**概念性**的（"评估器冻结"原则），缺乏工程实现。

**移植**：借鉴 execution contract——host 强制 provenance/limits/grading，评分/验证代码在独立隔离环境运行，无网络访问，私密 reference（如黄金标准证明）只在 host。这能把"评估器冻结"从原则变成代码。

**收益**：高。直接强化 Stage 3.6 的 sealed evaluator 和 Stage 3.5 的审计门控。

### P1-④ first-answer verifier reward（防刷分） ★★★

**缺口**：scientific-discovery-proof 的 Stage 3.6 进化循环，评分可能被"反复试错直到通过"刷高。

**移植**：借鉴 first-answer 原则——只评首个提交的证明结果，follow-up 修正不改变 reward。对应 Stage 3.6 的"严格改进门控"，但更硬（首个答案而非最终答案）。

**收益**：中高。强化防 reward hack。

### P2-⑤ state carried between stages（状态流转契约） ★★★

**缺口**：scientific-discovery-proof 的 Stage 之间状态流转无明确契约。

**移植**：借鉴 ScienceBuddy 的明确状态表（哪些状态在 harness 阶段/RL 阶段/下个 cycle 之间流转、哪些清除）。工程化 Stage 之间状态管理。

### P2-⑥ GRPO group-relative advantage ★★

**缺口**：scientific-discovery-proof 的 Stage 3.6 用"缺陷扣分"（绝对），非相对。

**移植**：借鉴 group-relative advantage（同任务的多个尝试比较相对优势）。但 Stage 3.6 是"证明代码变异"非"同一任务多尝试"，直接映射有限。

### P3-⑦ 冻结任务 release（715/90/90）★★

**缺口**：scientific-discovery-proof 无固定证明 benchmark。

**移植**：若要做"证明成功率"的标准化评估，借鉴冻结 split。但目前证明任务各异，价值有限。

---

## 四、优先级总表

| 优先级 | 增量 | 来源 | 填充缺口 | 预期收益 |
|---|---|---|---|---|
| **P0-①** | harness 可进化对象 | 内层递归 | pipeline 元进化 | 最高（元层增量） |
| **P0-②** | 双层递归耦合 | recursive-in-recursive | 进化范式 | 最高（范式级） |
| P1-③ | execution contract | host broker | 评估器冻结工程化 | 高 |
| P1-④ | first-answer reward | verifier | 防刷分 | 中高 |
| P2-⑤ | state carried | stage handoff | 状态流转契约 | 中 |
| P2-⑥ | GRPO group-relative | 外层递归 | 相对优势 | 中 |
| P3-⑦ | 冻结任务 release | frozen split | 标准化评估 | 中低 |

---

## 五、诚实边界

1. **场景不同**：ScienceBuddy 是"交互式生物医学 workspace"（224 工具/22 模块），核心是 harness 进化 + 模型训练；scientific-discovery-proof 是"形式化证明管线"。移植的是**「harness 进化 + 模型 RL 耦合」的设计模式**，非代码转录。

2. **训练不可复现**：双层递归需要 SkyRL + Qwen3.5-4B + 冻结 715/90/90 任务 release。本机 WSL P620 无法跑。scientific-discovery-proof 也不训练自有模型（用 DeepSeek API），所以 P0-② 的"模型训练"部分需替换为"证明策略优化"。

3. **P0-① 是唯一真正的新维度**：scientific-discovery-proof 已进化"证明代码"（Stage 3.6）和"策略参数"（Stage 3.7），ScienceBuddy 的增量是**「pipeline 编排逻辑本身」的进化**——这个维度此前 10 框架都没覆盖。

4. **与 IdeaScientist 互补而非重叠**：IdeaScientist 补「上游猜想生成」（发现维度），ScienceBuddy 补「pipeline 元进化 + 双层耦合」（自我改进范式维度），两者正交，都指向"发现智能"。

5. **P0-② 落地代价最大**：双层递归耦合需要重构 Stage 3.6/3.7 的耦合关系，工作量远超 P0-①。建议先落地 P0-①（pipeline 元进化），P0-② 作为长期方向。

---

## 六、建议

**与 IdeaScientist 并列的第三个关键框架**：
- IdeaScientist → 补「猜想生成」（上游）
- ScienceBuddy → 补「pipeline 元进化 + 双层耦合」（自我改进范式）
- 两者 + 已有 10 框架 → 共同指向"发现智能"（discovery intelligence）

**建议立即落地**：P0-①（harness 可进化对象 → Stage 3.8 pipeline 元进化）+ P1-③（execution contract 工程化评估器冻结）。

**长期方向**：P0-②（双层递归耦合）—— 需要先重构 Stage 3.6/3.7，工作量最大但范式价值最高。

完整评估归档至 `scientific-discovery-proof/references/sciencebuddy-integration-assessment.md`。
