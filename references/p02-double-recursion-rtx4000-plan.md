# P0-② 双层递归耦合重构 — RTX4000 服务器跑通说明

> 目标：把 ScienceBuddy 的「recursive-in-recursive self-improvement」移植到
> scientific-discovery-proof 的 Stage 3.6/3.7，实现「harness 进化（内层）↔ 证明策略模型训练（外层）」
> 的双层递归耦合，在 RTX4000（96GB）服务器上跑通。
>
> 前置：本机已落地 P0-①（`scripts/pipeline_meta_evolution.py`，Stage 3.8，评估为结构分+历史分近似）。
> 本文档解决 P0-① 的诚实边界——**本机无法重跑完整 pipeline 求真实证明成功率**，
> 真实闭环需服务器重跑。

---

## 一、现状与缺口

scientific-discovery-proof 当前是**单层进化**：

| 模块 | 进化对象 | 评估器 |
|---|---|---|
| Stage 3.6 | 证明代码（Lean 文件） | 冻结评估器（MathCode 三工具 + 物理内容审计） |
| Stage 3.7 | 证明策略参数（变异权重/并行度/放弃阈值） | archive.jsonl 历史重放 |
| Stage 3.8（新） | pipeline harness（编排策略 JSON） | 结构分 + 历史分（**近似，本机局限**） |

三者**独立、不耦合**。ScienceBuddy 的核心是**双层递归耦合**：

```
内层（模型固定，改 harness）：提议 harness → Val 对比 → 选中 harness
外层（harness 固定，训模型）：fresh rollouts → verifier 评分 → GRPO 更新模型
         ↓ 交替，模型更新改变 harness 有效性，harness 改变改变模型经验
```

---

## 二、重构目标：双层递归耦合

### 2.1 两个组件

| 组件 | scientific-discovery-proof 映射 | RTX4000 实现 |
|---|---|---|
| **任务模型** M_k | 证明策略模型（生成 Lean 证明骨架 + tactic 体） | Qwen2.5-7B 或 Qwen3.5-4B（bf16，全参 GRPO） |
| **harness** H_{k,j} | pipeline 编排程序（Stage 顺序 + 参数 + gate + 证明提示词模板） | 可替换 Python 程序（继承本机 PipelineHarness，但升级为完整可执行） |
| 辅助模型 | harness 改进提议者 | DeepSeek v4-pro（API）或本地 Qwen2.5-7B |

### 2.2 交替公式（对齐 ScienceBuddy）

$$H_{k,j+1} = \mathrm{Select}(H_{k,j},\mathcal{C}_{k,j};M_k,D_{\mathrm{val}}),\qquad M_{k+1}=\mathrm{GRPO}(M_k;H_{k,J},D_{\mathrm{train}}),\qquad H_{k+1,0}=H_{k,J}$$

- **内层**（固定 M_k，改进 harness）：提议 harness 候选 → 在 Val 证明任务集上真实跑 → 严格更高成功率才替换。
- **外层**（固定 H，训 M_k）：用选中 harness 生成 fresh 证明尝试 → verifier（Lean 编译 + MathCode）评分 → GRPO 更新证明策略模型。
- 交替 3 个 cycle（对齐 ScienceBuddy 的默认 schedule）。

---

## 三、RTX4000 硬件适配

| 资源 | 规格 | 用途 |
|---|---|---|
| GPU | RTX4000 96GB | 证明策略模型全参训练（7B bf16 ≈ 14GB，余量充足） |
| 模型 | Qwen2.5-7B-Instruct | 证明策略模型（生成 Lean 骨架 + tactic） |
| 训练框架 | TRL（GRPO）或 SkyRL | 相对优势 GRPO，8 实例 × 8 尝试 |
| verifier | Lean 4 + MathCode 三工具 | 冻结评估器（评分 0/1：0 sorry 且物理内容非平凡） |
| 数据 | 冻结证明任务集 | Train/Val/Test 三划分（对齐 ScienceBuddy 715/90/90） |

**关键：verifier 是冻结的**（对齐 ScienceBuddy execution contract）——评分代码在独立环境运行，模型/harness 候选不能改写评分规则。scientific-discovery-proof 已有这套冻结评估器（Stage 3.5 审计 + physical_content_audit），直接复用。

### 证明任务集（Train/Val/Test）

从已有通过验证的猜想构建冻结任务集（每任务 = conjecture.json + 期望 Lean 证明）：

- **Train**（~60 任务）：harness 交互 + RL 尝试
- **Val**（~15 任务）：harness 选择（候选 vs 父对比）
- **Test**（~15 任务）：阶段边界测量（不参与学习）

任务来源：SL(6,C) 系列已通过的证明（CGICE/三峰引力波/右手中微子/光速分界面等）作为 ground truth，反推为"给定猜想 → 生成证明"的任务。

---

## 四、重构方案（分阶段实施）

### Phase 1：证明策略模型 + verifier 环境

1. 在 RTX4000 上装 TRL（`pip install trl`）+ torch（cu121/cu124）+ vLLM（verifier 的 Lean 编译用独立环境）。
2. 定义证明任务 schema：`{conjecture: {...}, target_theorem: "...", ground_truth_lean: "..."}`。
3. verifier = 现有 `physical_content_audit.py` + MathCode 三工具，封装为 `verify(lean_code) -> {0,1}`（0 sorry + 无重言式 + 无悬空引用 = 1）。

### Phase 2：harness 可执行化（升级本机 PipelineHarness）

1. 把本机 `pipeline_meta_evolution.py` 的 PipelineHarness 从"编排策略 JSON"升级为**完整可执行 Python 程序** `run(conjecture, api) -> lean_code`，其中 `api` 提供：
   - `api.generate(messages)` → 调证明策略模型
   - `api.execute(code)` → 在隔离容器跑 Lean 编译
   - `api.submit(answer)` → 提交 Lean 代码给 verifier
2. 继承本机的 gate 规则（Stage 1 BLOCKED → stop，Stage 3.5 BLOCK → block Stage 4）。

### Phase 3：内层递归（固定模型，改进 harness）

对齐 ScienceBuddy 内层：
1. 收集 Train 交互（当前 harness 跑 16 个 Train 任务）。
2. 提取公共证据（prompt/模型输出/tool 观察/verifier 结果，**排除私密 ground truth**）。
3. 辅助模型（DeepSeek v4-pro）提议 3 个候选 harness（完整 Python 程序）。
4. 结构验证（同步 `run(conjecture, api)` 接口 + 不调用禁用指令）。
5. 在 90 Val 任务上对比候选 vs 父（temperature 0，首个答案，完整 task-ID 覆盖）。
6. 严格更高成功率 + 无运行时错误才替换；平手保留父。

### Phase 4：外层递归（固定 harness，训模型）

对齐 ScienceBuddy 外层：
1. 选中 harness 冻结，SkyRL/TRL 采样 8 实例 × 8 尝试 = 64 episodes。
2. `R_i = Verify(lean_code_i) ∈ {0,1}`（首个提交答案，无 follow-up 修正）。
3. GRPO group-relative advantage：`A_i = (R_i - μ_x)/(std + δ)`。
4. clipped policy objective：`min(ρA, clip(ρ, 1-ε_low, 1+ε_high)A)`。
5. 30 个 optimizer 更新 / 阶段，只优化 model-generated completion tokens。
6. 导出模型 → 独立进程加载验证 Test 覆盖 + 非空生成 → 接受。

### Phase 5：交替循环 + 状态携带

```
model, harness = M0, H0
for cycle in 1..3:
    # 内层（模型固定）
    preflight harness; measure baseline Test
    for step in 1..3:
        collect 16 Train interactions
        propose 3 harness candidates
        evaluate parent + candidates on 90 Val tasks
        adopt earliest strictly-better error-free candidate (or keep parent)
    measure selected harness on Test
    # 外层（harness 固定）
    for update in 1..30:
        collect fresh grouped Train attempts
        compute verifier rewards + GRPO advantages
        update model from generated tokens
    export model; validate on Test
    inherit harness + model for next cycle
```

---

## 五、验证方案

| 指标 | 定义 | 目标 |
|---|---|---|
| 证明成功率（Test） | 首个答案 verifier=1 的比例 | 每 cycle 单调不降 |
| harness 采纳率 | 内层每个 harness step 是否产生严格改进 | 记录采纳历史 |
| 模型增益 | GRPO 前后 Test 成功率差 | 外层每 cycle 提升 |
| 耦合效应 | harness 改进 × 模型训练的联合增益 vs 各自独立 | 验证双层 > 单层 |

关键诚实指标：**双层耦合是否真的优于单层**（harness 进化 + 模型训练分别跑，对比联合跑）。这是 ScienceBuddy 论文的核心主张（recursive-in-recursive > 单层 RSI），需在服务器上验证。

---

## 六、诚实边界

1. **本机 P0-① 的评估是近似**：结构分 + 历史分，无法区分两个"都有效"的 harness 优劣。本文档 Phase 3 用真实 Val 任务成功率替代，这是 P0-② 的核心价值——**把近似评估升级为真实评估**。

2. **证明策略模型 ≠ DeepSeek**：scientific-discovery-proof 目前用 DeepSeek API 生成证明。P0-② 训练的是一个小的本地证明策略模型（7B），它可能不如 DeepSeek v4-pro 强。**双层递归的价值是"验证范式"，不是"替代 DeepSeek"**。若 7B 模型证明能力不足，可退化为"用 DeepSeek API 做模型层，但保留 harness 进化 + verifier 评分的双层结构"。

3. **verifier 信号稀疏**：证明任务的成功率可能很低（0 sorry 证明很难），导致 GRPO 奖励几乎全 0、梯度无方差。缓解：用 process reward（PRM 风格，ScienceBuddy 的 PRM 解释请求）或部分 credit（如"接近 0 sorry"给分），而非纯二进制。

4. **任务集构建成本**：冻结 Train/Val/Test 任务集需要从已有证明反推，需人工整理。任务太少则 GRPO 不稳，太多则服务器跑不动（单任务 Lean 编译可能几十秒）。

5. **ScienceBuddy 用的是 Qwen3.5-4B（小模型）**：证明策略模型不需要大，因为 verifier 信号（0/1）才是关键。7B 已是上限，4B 可能更合适。

---

## 七、建议执行顺序

1. **先跑 Phase 1+2**（环境 + harness 可执行化）：复用本机 PipelineHarness 的 schema，升级为可执行程序。
2. **跑 Phase 3 单层验证**（只 harness 进化，模型用 DeepSeek API）：验证"harness 进化 + 真实 Val 评估"闭环。
3. **跑 Phase 4 单层验证**（只模型训练，harness 固定）：验证"GRPO + verifier"闭环。
4. **跑 Phase 5 双层耦合**：验证"双层 > 单层"。

若第 4 步验证双层耦合无增益，则 ScienceBuddy 的范式对 scientific-discovery-proof 不适用，诚实报告负结果（这也是有价值的发现）。
