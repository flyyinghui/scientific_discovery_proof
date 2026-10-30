# LLM 证明修复的局限与 Finset.sum 证明模式

**来源**: 2026-08-17 DeepSeek API 校核 Linear Algebra 8 定理（0/8 修复）对比复分析 209 定理（100% 修复）。

## DeepSeek API 校核的"重新生成 vs 精确定位"陷阱

校核修复率**强烈依赖任务类型**，不能一概而论：

| 任务类型 | 修复率 | 案例 |
|---------|--------|------|
| 陈述占位 → 补证明体 | ~100% | 复分析 209 定理，DeepSeek 补上 sorry 的证明 |
| 已有证明 → 修 subtle API 细节 | ~0% | Linear Algebra 8 定理，0/8 修复成功 |

**根因**: DeepSeek 每次迭代"重新生成完整代码"而非"针对编译错误精确定位修复"。可观察特征：3 次迭代输出几乎相同字符数（如 1175/1175/1175、426/425/445、2179/2050/2050），卡在相同的 `unsolved goals` / `unusedSimpArgs`。

### 校核能修 vs 不能修

- **能修**: 简单 tactic 用法错误（如 `rw` vs `apply` 一字之差），DeepSeek 能给出正确方向。
- **不能修**（需人工精确干预）:
  - `Finset.sum` 内代数（`sum_add_distrib`/`mul_sum`/`sum_mul` 的 rewrite 顺序）
  - typeclass 实例缺失（`synthInstanceFailed`）
  - 环境问题（object file 路径指向错误的 lake 目录，**任何模型都无法修复**——这是 lakefile require 配置问题，不是代码问题）

### 校核策略

1. **先分类任务**: 是"补证明体"还是"修 API 细节"？前者用 DeepSeek API 校核，后者需人工。
2. **检测"重新生成而非修复"**: 若连续迭代输出相同字符数，说明模型在重生成而非定位修复，立即转人工，不要浪费时间迭代。
3. **环境错误先排除**: 编译错误含 `object file '.../.lake/packages/...'` 时，先修 lakefile 的 mathlib require 路径，再谈模型校核。

## Finset.sum 求和的正确证明模式

### 对称性（sum 内交换乘法）

```lean
theorem dot_symm {n : ℕ} (v w : Fin n → ℝ) : dot v w = dot w v := by
  unfold dot
  apply Finset.sum_congr rfl   -- NOT rw [Finset.sum_congr ...]
  intro i hi
  rw [mul_comm]
```

### 两个陷阱

1. `rw [Finset.sum_congr rfl (fun i _ => ...)]` 失败 `"Did not find an occurrence of the pattern"` —— `sum_congr` 是**定理要 apply，不是 rewrite**。
2. `simp [dot, mul_comm]` **不会**在 `Finset.sum` 内部应用 `mul_comm`（`mul_comm` 是逐点非 sum 级），报 `unsolved goals`。

### 求和线性（分配律，dot_bilinear 类）

`∑ i, (a·v i + b·w i) · u i = a·(∑ i, v i·u i) + b·(∑ i, w i·u i)` 这类目标，`simp [...]` 触发 `unusedSimpArgs` + `unsolved goals`（simp 认为某些参数多余但仍不闭合）。正确路径是**逐项处理**：`apply Finset.sum_congr rfl; intro i hi; simp [Pi.smul_apply, Pi.add_apply, mul_add]; ring`——把求和内的代数交给 `ring` 逐点解决，而非试图用 sum 级 rewrite 一步到位。
