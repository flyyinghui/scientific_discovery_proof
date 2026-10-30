# Mathlib 4.34 — Finset 乘积引理与依赖消除陷阱（2026-08-21 实测）

编译 Littlewood-Offord 形式化（`littlewood_offord_inverse.lean`）时踩到的 6 类 API 坑。全部是"模型不知道正确 mathlib 4.34 API 名"这一类——换更强模型也救不了，必须检索源码/查真实签名。

## 1. `Finset.prod_le_prod` 是"非负性"，不是"单调性"

- `Finset.prod_le_prod` 在 mathlib 4.34 的签名是 `(∀ i ∈ s, 0 ≤ f i) → 0 ≤ ∏ i in s, f i`（证明**乘积非负**）。
- 单调性（`∏ f ≤ ∏ g`）是 **`Finset.prod_le_prod'`**，签名 `(∀ i ∈ s, f i ≤ g i) → ∏ f ≤ ∏ g`。
- **症状**：把 `hfactor i`（类型 `f i ≤ g i`）传给 `prod_le_prod` 报 `Type mismatch: hfactor i has type ... ≤ ... but expected 0 ≤ ?m`。
- **修复**：比较两个乘积的大小 → 用 `prod_le_prod'`。

## 2. `Finset.prod_ge_one` 不存在 → `Finset.one_le_prod`

- 证 `1 ≤ ∏ f`（每个因子 ≥ 1）用 `Finset.one_le_prod (by intro i _; omega)`。
- `Finset.prod_ge_one` 是 LLM 常猜的错名，报 `Unknown constant 'Finset.prod_ge_one'`。

## 3. `pow_eq_prod_const` 不存在 → `Finset.prod_const`

- 证 `∏ i, c = c^card` 用 `Finset.prod_const`（`simp [Finset.prod_const]`）。
- 配合 `rw [Finset.prod_mul_distrib]`（正向，把 `∏(f*g)` 拆成 `(∏f)*(∏g)`）。`← prod_mul_distrib` 是反向，会报 "Did not find occurrence of the pattern"。

## 4. 投影等式上做依赖消除 → 用 `IsEmpty` 空集法

`subst`/`cases` 在**投影等式**（如 `h : Q.rank = 0`，LHS 是结构投影）上都会失败：

- `subst h` → `invalid equality proof, it is not of the form (x = t) or (t = x)`
- `cases h` → `Dependent elimination failed: Failed to solve equation`
- `cases Q with | mk rank steps dims => subst rank` → `did not find equation for eliminating 'rank'`（`rcases` 不重写假设里的投影）

**可行修复**（绕开依赖消除，直接用 `h` 证明 `Fin Q.rank` 为空）：
```lean
theorem volume_rank_zero (Q : SymmetricGAP G) (h : Q.rank = 0) : Q.volume = 1 := by
  rw [SymmetricGAP.volume]
  have hempty : IsEmpty (Fin Q.rank) := by
    rw [h]          -- 目标是 Prop，rw 能重写类型参数 Q.rank → 0
    infer_instance  -- Fin 0 有 IsEmpty 实例
  exact Finset.prod_eq_one (fun i _ => False.elim (hempty.elim i))
```

## 5. `-(2*l+1)` 对 ℕ 取负号 → 转 ℤ

- `(n : ℝ) ^ (-(2 * l + 1))` 其中 `l : ℕ`，报 `failed to synthesize Neg ℕ`。
- 修复：指数必须是 ℤ，`(n : ℝ) ^ (-(2 * (l : ℤ) + 1))`。

## 6. `v ~ w`（List.Perm 中缀）→ `List.Perm v w`

- `h : v ~ w` 报 `unexpected token '~'`。
- 修复：`h : List.Perm v w`（或文件头 `open scoped List`）。

## 7. `opaque` 返回结构体需要 `Inhabited`

- `opaque gapSumset : SymmetricGAP G → SymmetricGAP G → SymmetricGAP G` 报 `failed to synthesize Inhabited ... for SymmetricGAP G`。
- 修复：抽象操作（无定义体、无可构造值）直接用 `axiom`，不要 `opaque`（`opaque` 需要 Inhabited 提供隐藏定义体）。

## 关键教训

这些坑全是"预训练模型 mathlib 知识早于 4.34 重构"导致——Qwen3.8 给出的证明也用错名（`subst h`、`prod_le_prod`）。**检索（grep 源码/`#check`）比模型记忆可靠**。修此类错误按 `mathlib_api_lookup.py` 的 `retrieve_for_error` 路径：从 error 文本提取 unknown identifier → 解析正确名 → 注入 prompt。
