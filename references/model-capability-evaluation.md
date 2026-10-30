# 本地模型数学证明能力评估 + 生成器/校核器分工

2026-08-17 会话沉淀：评估 DeepSeek-V4-Flash-Q4_K_XL vs Qwen3.8:27B-Q8_0 的 Lean 4 数学证明能力。

## 一、评估方法论（可复用）

用 4 个递进的 Lean 4 证明任务测两个模型，编译验证：

| 任务 | 难度 | 内容 |
|---|---|---|
| T1 | 易 | `theorem two_plus_two : (2:ℕ)+2=4 := by norm_num` |
| T2 | 中 | 二次型标量乘法 `normSq (2•B) x = 2 * normSq B x`（BilinForm/QuadraticForm）|
| T3 | 较难 | 链式法则 `deriv (exp(-s/τ)) t = exp(-t/τ)·(-1/τ)`（deriv_exp）|
| T4 | 难 | ODE 解析解 `I(t)=Ieq+(I0-Ieq)·e^(-t/τ)` 满足主方程 |

要点：
- prompt 要求 "Output only valid Lean code, no sorry"，温度 0.0。
- **陷阱**：模型生成的代码常缺 `import Mathlib`（只输出 theorem 行），compile=false 需先补 import 再判证明本身。
- 编译验证用 `lake env lean`（单文件 ~90s，import Mathlib 全量加载 13GB olean）。

## 二、评估结论

**DeepSeek-V4-Flash 的数学证明能力明显强于 Qwen3.8:27B**，核心依据：

1. **参数规模差一个量级**：284B MoE（Q4_K_XL=144GB）>> 27B 稠密（Q8=27GB）。MoE 激活参数少但总知识储备远超稠密 27B。
2. **证明深度**：历史实证——SL(6,C) 四论文 + 复分析 209 定理中，**所有真正证明（0 sorry）都由 DeepSeek 完成**（P0-6 deriv 链式法则 30 迭代、T2 ODE 解析解 22 方案、去 sorry 68 成功/100% 修复率）；qwen3.8 只生成 type-correct 陈述 + sorry 占位（40% 一次通过，需 DeepSeek 校核）。
3. **证明结构**：DeepSeek 简洁模块化（先引理后定理，T4 仅 1463 字符）；qwen3.8 冗长（T4 达 6273 字符 431 秒）。

## 三、最优分工（已验证，而非竞争）

- **qwen3.8 做批量"生成器"**：本地 4 GPU 全 offload 6.3 t/s，快速出陈述占位（复分析 209 定理）。
- **DeepSeek 做"校核器"**：修复证明到 0 sorry（修复率 100%）。
- 混合流程：llama 生成（40% 一次通过）→ deepseek 校核 → 最终 100% 可编译。

## 四、本地运行现实约束

- **Q4_K_XL 144GB 在 4×20GB 显存（80GB）上无法有效本地运行**：需 CPU offload（内存需 >144GB，本机 536GB 够），但 MoE 284B CPU 推理极慢（ollama 测试 300s 无响应）。GPU 被 qwen3.8 占用时更慢。
- **Qwen3.8 27GB 4 GPU 全 offload**，是唯一能本地流畅跑的数学模型。
- 若测 DeepSeek 本地能力，用 API 版（同架构）代替 Q4_K_XL。
- Q8 量化精度（8-bit）> Q4_K_XL（4-bit），数值稳定性更好——但数学证明能力由参数规模主导，量化精度是次要因素。
