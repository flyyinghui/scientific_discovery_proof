# DeepSeek 校核的两种场景（陈述占位 vs API 细节）— 修复率天壤之别

本会话（数学物理教材 Linear Algebra 批量形式化）发现：之前"DeepSeek 校核 ~100% 修复率"的经验**只适用于场景 A**，不能泛化到场景 B。判别标准决定用 DeepSeek 校核还是人工修复。

## 场景 A：陈述占位 → 补证明（DeepSeek 高修复率）

- 案例：复分析（Gamelin）项目。qwen3.8 生成 type-correct 定理陈述 + `sorry` 占位，DeepSeek 补完整证明，修复率 ~100%（68/68）。
- 特征：定理**陈述已经正确**，缺的只是证明体。DeepSeek 只需在正确陈述下生成证明链，命中率高。

## 场景 B：已有证明 → 修 subtle API 细节（DeepSeek 低修复率）

- 案例：数学物理教材 Linear Algebra 核心概念（dot product、det、linear map、Cauchy-Schwarz）。qwen3.8 生成 **0 sorry 完整证明**，但 Mathlib API 细节错误。
- 实测：DeepSeek API（v4-pro）校核 **0/6 修复成功**。3 次迭代输出字符数几乎相同（1175/1175/1175、426/425/445），即**每次重新生成相同（仍错误）的代码**。
- 根因：DeepSeek 的修复策略是"重新生成完整代码"而非"针对编译错误精确定位"。对 `Finset.sum` 内的代数（`mul_comm` 不在 sum 内应用、`sum_add_distrib` 的 rewrite 顺序、`sum_congr` 的 rw-vs-apply），它的 `simp [...]` 修复反复触发 `unusedSimpArgs` + `unsolved goals`。

## 判别标准（先判断再选工具）

| 信号 | 场景 A（补证明）| 场景 B（修 API 细节）|
|---|---|---|
| sorry 数 | 有 sorry 占位 | 0 sorry |
| 错误类型 | 无证明体 | `rewrite failed` / `synthInstanceFailed` / `unsolved goals` |
| DeepSeek 校核 | ✅ 有效 | ❌ 无效（输出相同错误代码）|
| 正确做法 | DeepSeek 补证明 | 人工精确修复 |

场景 B 的人工修复范式（已验证可编译）：
- `sum_congr` 是 **apply** 不是 rewrite：`apply Finset.sum_congr rfl; intro i hi; rw [mul_comm]`
- `Finset.sum` 内逐项代数用 `apply Finset.sum_congr rfl; intro; ...; ring`，避免全局 `sum_add_distrib` 的 rewrite 顺序问题
- 纯微积分（deriv 库）比 Finset.sum 代数更"校核友好"——若批量验证，优先选 deriv/分析定理而非求和代数定理

## 相关：Stage 3.5 审计门的 sorry 检测修复

`proof_consistency_audit.py` 的 sorry 计数原用 `\bsorry\b`，会误报——匹配注释里的 "0 sorry" 文本（如 `-- 真证明 (0 sorry)`）。已修复为 `^\s*sorry\b`（仅行首 active sorry）。admit 同理改 `^\s*admit\b`。
