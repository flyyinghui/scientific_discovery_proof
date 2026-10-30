# formalverse benchmark 语义重构模式（class 重定义冲突）

formalverse（MathCode formal-proof-lib，146K .lean）的批量编译，真正的根因不是 API 映射，而是**每文件自包含定义 `class Group`/`Field`/`Ideal`/`Semigroup` 等，`import Mathlib` 后与 mathlib 全局类型类冲突 → `has already been declared`**。

## 诊断

- `.lake/build/lib/lean/*.olean` 的数量是**陈旧产物**（mechfix 加 `import Mathlib` 之前编译的）。必须**重新编译验证**才知真实可编译集。
- 一个文件能编译 ⟺ **不重新定义 mathlib 已有的类型类/结构**。
- 重定义 `class Group` 报错：`Group has already been declared`（不是 API 错）。

## 两类重构配方

### A. 裸 class 定义（无定理）——确定性删除
文件只有 `class X ... where <字段>` 无 theorem/lemma/def。mathlib 已有 X，定义冗余。
```python
# 删除 class 块(含缩进字段)，在 import Mathlib 后插注释
comment = f"-- [refactor] mathlib already has `{cls}` (Mathlib...); redefinition removed."
```
类名→mathlib 路径映射：Group/Semigroup/Abelian_group→`Mathlib.Algebra.Group.Defs`，Field→`Mathlib.Algebra.Field.Defs`，Ring→`Mathlib.Algebra.Ring.Defs`，Module/VectorSpace→`Mathlib.Algebra.Module.Defs`，OrderedField→`Mathlib.Algebra.Order.Field.Defs`。

### B. class + theorem——LLM 语义重构
文件定义 class 且有用它的定理/实例。需删 class + 定理改用 mathlib 类型类：
- `[Group G]`、`[CommRing R]`、`[Field K]`
- **ℕ 是加法** → 实例用 `AddSemigroup ℕ` 非 `Semigroup ℕ`
- 删除与 mathlib 同名的冗余引理（`mul_inv_self` 等已在 mathlib）
- 保留不冲突的新定义（`def BinaryOperation`）

## 双模型分工（已验证）

- **内网 Qwen3.5-122B-A10B**：语义重构（删 class + 映射 mathlib 类型类 + AddSemigroup 语义判断），每批 ~17 文件，127-147s/批。63/63 编译通过。
- **本机 Qwen3.8:27b**：批量陈述/补证明（陈述占位→补证明场景）。
- 编译：`lake env lean <file>.lean` 逐文件（~60-90s/文件，mathlib import 慢）。

## 关键坑

1. **Qwen3.5 留孤儿 doc 注释**：重构输出里 `/-- ... -/` 后跟 `--` 普通注释（非声明），Lean 报 `unexpected token '/--'; expected 'lemma'`。修复：重构后统一 `txt.replace('/--', '/-')`（doc 注释→普通块注释，信息性注释无需 doc 状态）。
2. **mechfix 破坏 lakefile**：`fix_import` 把 `lakefile.lean` 的 `import Lake` 错改成 `import Mathlib`，导致 `lake build` 报 `unknown namespace Lake`。修复：改回 `import Lake`。
3. **编译超时不等于失败**：个别文件 `lake env lean` 超 180s（TIMEOUT），重试 300s 即通过——先重试再判失败。
4. **排除 .lake 内文件**：候选搜索会匹配 `.lake/packages/Qq/...`（mathlib 依赖），须过滤 `.lake` 路径。

## 已验证结果（2026-08-21）

248 文件重构+编译通过：185 裸 class（确定性删）+ 63 class+theorem（Qwen3.5 语义重构）。CGICE 证明文件是 `cgice_proof_v9.lean`（73 axiom/36 thm/13 lem），`formalverse_mapped.lean` 是 benchmark 非 CGICE 证明。
