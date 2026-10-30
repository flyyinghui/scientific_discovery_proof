# Lean 4 Tactic / API Pitfalls (mathlib 4.34, 2026-08-21 编译实录)

从 `littlewood_offord_inverse.lean` 编译修复中沉淀的**通用** tactic/API 陷阱（非项目特有，任何 mathlib 4.34 编译都会踩）。LLM 生成 Lean 代码后最常见的失败根因不是"不会证明"，而是"不知道正确 API 名 / 用错 tactic 变体"——检索源码核实比模型记忆可靠。

## 1. `Finset.prod_le_prod` vs `Finset.prod_le_prod'`（名字只差一个撇，LLM 常猜错）

- `Finset.prod_le_prod : (∀ i ∈ s, 0 ≤ f i) → 0 ≤ ∏ i in s, f i` —— **证明"乘积非负"**
- `Finset.prod_le_prod' : (∀ i ∈ s, f i ≤ g i) → ∏ i in s, f i ≤ ∏ i in s, g i` —— **证明"乘积单调"**

报错特征：`hfactor i has type A ≤ B but is expected to have type 0 ≤ ?m` → 说明你用成了"非负"版，应换 `prod_le_prod'`。

## 2. 投影等式的 `cases` / `subst` 依赖消除失败

`h : Q.rank = 0`（LHS 是**投影** `Q.rank`，不是变量）时：

- `subst h` → `Tactic 'subst' failed: invalid equality proof, it is not of the form (x = t) or (t = x)`
- `cases h` → `Dependent elimination failed: Failed to solve equation`

根因：依赖消除要求等式的 LHS 是自由变量，投影 `Q.rank` 不是。两种修复：

```lean
-- 方案 A: 先解构 Q 把 rank 变成变量，再 subst
theorem volume_rank_zero (Q : SymmetricGAP G) (h : Q.rank = 0) : Q.volume = 1 := by
  cases Q with
  | mk rank steps dims =>
    subst rank
    simp [SymmetricGAP.volume]

-- 方案 B: IsEmpty 空集法（更稳，绕开依赖消除）
theorem volume_rank_zero (Q : SymmetricGAP G) (h : Q.rank = 0) : Q.volume = 1 := by
  rw [SymmetricGAP.volume]
  have hempty : IsEmpty (Fin Q.rank) := by
    rw [h]
    infer_instance
  exact Finset.prod_eq_one (fun i _ => False.elim (hempty.elim i))
```

## 3. 不存在的引理名（LLM 幻觉）

- `pow_eq_prod_const` **不存在** → 用 `Finset.prod_const`（`∏ i ∈ s, a = a ^ s.card`）
- `Finset.prod_ge_one` **不存在** → 用 `Finset.one_le_prod`（`(∀ i ∈ s, 1 ≤ f i) → 1 ≤ ∏ f`）

## 4. `List.Perm` 记号

- `h : v ~ w`（infix `~`）报 `unexpected token '~'` → 改用 `List.Perm v w`（或文件头 `open scoped List`）。

## 5. ℕ 取负号

- `-(2*l+1)`（l : ℕ）报 `failed to synthesize instance of type class Neg ℕ` → 转 ℤ：`-(2 * (l : ℤ) + 1)`。

## 6. 块注释 `/-` 未闭合

- `/- ---------- 标题 ----------`（无 `-/`）会把后续代码吞进注释 → 报 `unterminated comment`。
- 节标题分隔线若用 `/-` 必须配 `-/`，否则用 `--` 行注释。
