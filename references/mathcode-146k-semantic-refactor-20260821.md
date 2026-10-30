# formalverse 146K .lean 语义重构 + 批量编译（2026-08-21）

续 `mathcode-146k-batch-compilation.md`（评估）和 `mathcode-mechfix-screen-20260820.md`（机械修复）。本文件记录**语义重构阶段**的实测结论——从 51 个 .olean 深挖到第一批文件编译通过。

## 1. 关键发现：.olean 是陈旧产物，必须重编译验证

`mechfix` 给所有文件加了 `import Mathlib` 后，之前（2026-08-16）编译出的 .olean 已经失效。**不要信 .olean 计数**——深挖时发现 51 个 .olean 里至少 6 个"裸 class 重定义"文件现在重编译报 `Group has already been declared`。

诊断法：对每个声称"已编译"的文件，直接 `lake env lean <file>.lean` 重编译，grep `error:`。oleans 只能证明"历史上某个时刻编译过"，不证明"当前源码可编译"。

## 2. 根因：自包含 class 定义与 mathlib 全局类型类冲突

formalverse 原始风格是**每文件自包含**（自己 `class Group`/`Field`/`Ideal`/`Ring`）。`mechfix` 加了 `import Mathlib` 后，`import Mathlib` + `class Group` = **`Group has already been declared`**。

这不是 API 映射问题，是**语义冲突**：不能在同一命名空间里重新定义 mathlib 已有的类型类。

## 3. 可复用模式（一个文件能编译 ⟺ 不重定义 mathlib 类型类）

- ✅ 直接引用 mathlib 类型类写定理：`[Group G]`、`[CommRing R]`、`[Field K]`，证明用 mathlib 定理（`exists_nat_gt`/`field_simp`/`nlinarith`/`calc`/`rw`）。
- ✅ 定义**全新名字**的结构：`structure LienardSystem`/`LimitCycle`（不与 mathlib 冲突）。
- ❌ `import Mathlib` 下重定义 `class Group`/`Field`/`Ideal`/`Ring`/`Semigroup` → `has already been declared`。

## 4. 语义重构配方（对"class X 重定义"文件）

文件分两类，处理方式不同：

1. **裸 class 定义（无 theorem）**：`class Field`/`Semigroup`/`Group` 后面没有定理 → **确定性删除**整个 class，替换为注释 `-- mathlib already has \`X\` (Mathlib.Algebra.X.Defs); self-contained redefinition removed`。文件退化为 `import Mathlib` + 注释，编译通过。

2. **class + theorem/instance**：定理或实例用了自包含 class → 需**语义重构**（LLM）：
   - 删 class 定义。
   - 定理签名改用 mathlib 类型类 `[Group G]`。
   - **关键语义判断：ℕ 是加法结构，用 `AddSemigroup ℕ` 不是 `Semigroup ℕ`**（`Semigroup` 是乘法，ℕ 的加法是 `AddSemigroup`）。这是"乘法 vs 加法"语义区别，机械替换会错。
   - 删除与 mathlib 同名的冗余引理（`mul_inv_self`/`inv_mul_self` 已在 mathlib）。

## 5. LLM 生成重构的陷阱：孤儿 doc 注释 `/--` → `/-`

Qwen3.5 生成语义重构时，常留下**孤儿 doc 注释** `/-- ... -/` 后面跟 `--` 普通注释而非声明。Lean 要求 `/--` doc 注释**必须紧跟声明**（def/theorem/lemma），否则报 `unexpected token '/--'; expected 'lemma'`。

修复：把重构文件里所有 `/--` 替换为 `/-`（doc 注释 → 普通块注释）。这些注释都是信息性的，不需要 doc 状态。**一次性对全部 LLM 重构产物做 `txt.replace('/--', '/-')`**，再编译。

## 6. mechfix 附带损害：lakefile.lean 被破坏

`mechfix` 的 `fix_import` 会把 `import Lake` 错改成 `import Mathlib`，导致 `lake build`/`lake env lean` 完全无法运行（`unknown namespace Lake`）。修复：lakefile.lean 第一行改回 `import Lake`。

**通用教训**：批量 `fix_import`（给所有文件加 `import Mathlib`）会误伤 Lake 配置文件、脚本等非数学文件。跑完机械修复后，先 grep `lakefile.lean` 的 import 是否正确。

## 7. 批量编译工作流 + 双模型分工

工作流：
1. `grep -rlE '^class (Group|Field|Ideal|Ring|...)' --include='*.lean' .` 找候选（终端无 rg，用 grep；search_files 的 ripgrep 对大目录可能返回 0）。
2. 按大小排序取最小 N 个（小文件优先）。
3. 分类：裸 class（无 theorem）→ 确定性删除；class+theorem → LLM 语义重构。
4. LLM 重构 → 修孤儿 doc 注释 → `lake env lean` 逐个编译验证。
5. 失败文件用第二个模型（Qwen3.8）批量补证/修，循环。

双模型分工（用户指示）：
- **内网 Qwen3.5**（快，262K 上下文）：深挖 + 语义重构（识别 class 冗余、映射 mathlib 类型类、ℕ→AddSemigroup 等语义判断）。
- **本机 Qwen3.8:27b-Q8_0**：批量处理陈述（签名骨架 + mathlib 类型类 + 补证明）。

## 8. 编译验证要点

- `lake env lean <file>.lean` 单文件编译 ~60-90s（mathlib import 慢），批量用 `lake build` 共享 import。
- 编译通过判定：`grep -iE 'error:'` 无输出。`warning:`（如 unused variable）不影响通过。
- 批量编译脚本应**逐个即时落盘结果**（避免 300s 超时丢全部），后台跑 + notify_on_complete。
