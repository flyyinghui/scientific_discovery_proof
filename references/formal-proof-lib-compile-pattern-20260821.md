# Formalverse 146K 文件语义重构模式 (2026-08-21 实测)

## 核心结论
formalverse benchmark（`<WORK_DIR>\mathcode_v2\mathcode_v2_pack\formal-proof-lib`，146,449 个 .lean）的真实编译率仅 **0.035%**（51 个 .olean，且是 mechfix 加 `import Mathlib` **之前**编译的陈旧产物）。重新编译验证后，6 个"裸 class 重定义"文件已失败（`error: Group has already been declared`）。

## 根因（非 API 映射，是语义重构）
每文件自包含定义 `class Group/Ideal/Field/Semigroup` 等 → mechfix 给所有文件加 `import Mathlib` 后与 mathlib 4.34 全局定义冲突 → `already been declared`。

## 51 个陈旧 .olean 的真实分类（重编译验证）
| 类别 | 可编译 | 特征 |
|------|:---:|------|
| mathlib 原生定理 | ✅ | `[Group G]`/`[CommRing R]` + mathlib 定理（`exists_nat_gt`/`field_simp`/`nlinarith`/`calc`/`rw`）|
| 新名 structure | ✅ | `structure LienardSystem`/`LimitCycle`（不冲突）|
| mathlib 类型类引用 | ✅ | `class X extends IsDomain R, IsPrincipalIdealRing R`（引用已有）|
| **裸 class 重定义** | ❌ | `class Group`/`Field`/`Semigroup` → "already declared" |

## 可复用重构模式（实测 14/14 通过）
1. **裸 class 定义文件**（无 theorem，~185 个）：确定性删除 `class X`，加注释 `-- mathlib already has X (Mathlib.Algebra.Group.Defs)`。**不需 LLM**，Python 正则即可。
2. **class + theorem 文件**（~66 个，需 Qwen3.5 语义重构）：
   - 删 `class X`，定理签名改用 mathlib 类型类 `[Group G]`/`[CommRing R]`
   - 定理体用 mathlib 定理名
   - **语义陷阱**：ℕ 是加法，用 `AddSemigroup ℕ` 非 `Semigroup ℕ`；冗余引理（`mul_inv_self`/`inv_mul_self`）已在 mathlib，删除
3. **全新名字 structure**：保留（不冲突）。

## 双模型分工
- **Qwen3.5（内网 :1122）深重构**：识别 class 冗余 + 映射 mathlib 类型类 + ℕ→AddSemigroup 语义判断。53s/14 文件，14/14 通过。
- **Qwen3.8（本机 :8081）批量陈述**：签名骨架 + mathlib 类型类，做"陈述占位→补证明"。

## 坑（实测，下次直接避开）
1. **Qwen3.5 孤儿 doc 注释**：重构输出留下 `/-- ... -/` 后跟 `--` 普通注释（非声明）→ Lean 报 `unexpected token '/--'; expected 'lemma'`。修复：全部 `/--` → `/-`（转普通块注释）。
2. **mechfix 破坏 lakefile.lean**：`fix_import` 把 `import Lake` 错改成 `import Mathlib` → `lake build` 报 `unknown namespace Lake`。修复：改回 `import Lake`。**这是 lake build 无法运行的隐藏阻塞，先查 lakefile 再查文件。**
3. **.olean 陈旧性**：不要信 .olean 数量判断编译率——mechfix 改动 import 后旧 .olean 全失效，必须实际重编译抽样验证。

## 批量编译策略
1. 按文件**大小区间**过滤候选（小文件优先，裸 class 优先确定性删）。
2. `lake build` 分批 ≤500（避开 Lake maxRecDepth）。
3. grep error 分流：`already been declared` → 删 class；`unknown identifier` → `mathlib_api_lookup` 检索正确 API 名。

## 关键文件定位
- CGICE 形式化证明 = `cgice_proof_v9.lean`（73 axiom / 36 theorem / 13 lemma / 0 sorry）
- `formalverse_mapped.lean` 是 formalverse benchmark（401 个 `fv_*` 通用数学题），**不是 CGICE 证明**——接到文件名先 grep 内容核实归属，别信文件名。
