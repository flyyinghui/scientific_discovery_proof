# CGICE V9.1 Lean 闭环增补 + Lean 4 attribute 注册陷阱（2026-09-03）

本文档记录两件事：① CGICE V9.1 论文的 Lean 证明（`cgice_proof_v9.lean`）数学推导闭环增补全过程；② 过程中暴露的 Lean 4 自定义 attribute 注册陷阱（可复用于任何诚实标注项目）。

## 一、CGICE V9.1 Lean 闭环增补

### 定位的「未闭环/不完备」环节（Stage 3.5 L1 审计 + 手工审查）

| # | 缺陷 | 位置 | 修复 |
|---|---|---|---|
| 1 | `: True` 空壳公理 ×3（CW 势） | `cw_one_loop_integral` / `mass_matrix_root` / `cw_minimization` | → 有内容的 def/axiom |
| 2 | 零内容 `: Prop` ×2（谱理论） | `spec_gap_bound` / `a_t3_harish_chandra_lower_bound` | → 有内容命题 / 删除 |
| 3 | `lam1 ≡ lambda_perp` 从未形式化 | 文件头注释声称等价但无定理 | → 5 个闭环定理 |
| 4 | honest-axiom 仅为注释标签（表演性诚实） | 全文 `-- [honest-axiom]` | → 31 个 `@[honest_axiom]` + 10 个 `@[phenomenological]` |

### 空壳公理修复细节

**CW 势 3 个 `: True` → 有内容：**

```lean
-- 单圈 CW 积分核 (维度正规化): ∫d⁴k_E ln(k²+m²) → (m⁴/64π²)(ln(m²/μ²)−3/2)
noncomputable def cw_one_loop_kernel (m2 mu : ℝ) : ℝ :=
  (m2^2 / (64 * Real.pi^2)) * (Real.log (m2 / mu^2) - 3/2)

-- 质量矩阵 M_α² = |α(v)|² = (α·v)²
noncomputable def mass_matrix_sq (alpha v : ℝ) : ℝ := (alpha * v)^2

-- 非平凡存在性前提（非零真空凝聚）
axiom cw_vev_exists : ∃ v_c : ℝ, v_c ≠ 0
```

**零内容 Prop 修复：**

```lean
-- spec_gap_bound: 从 `: Prop`（裸命题）→ 有内容的命题定义（V_eff 有下界）
def spec_gap_bound : Prop := ∃ m : ℝ, ∀ t : ℝ, m ≤ V_eff t
-- a_t4 保持 `: spec_gap_bound`（现在是 spec_gap_bound 命题的证明）
axiom a_t4_semiclassical_discrete_spectrum : spec_gap_bound
```

**关键教训**：`axiom X : T` 中 T 必须是 Sort（类型）。旧 `axiom spec_gap_bound : Prop` 声明 spec_gap_bound 是 Prop 类型的**项**（命题），所以 `axiom a_t4 : spec_gap_bound` 合法（a_t4 是 spec_gap_bound 的证明）。但改成 `axiom spec_gap_bound : ∃ m, ...` 后，spec_gap_bound 变成 `∃ m, ...` 类型的**项**（证明），不再是类型，`axiom a_t4 : spec_gap_bound` 报 "type expected, got (...)"。正确做法：`def spec_gap_bound : Prop := ∃ m, ...`（命题定义）+ `axiom a_t4 : spec_gap_bound`（证明）。

**`a_t3_harish_chandra_lower_bound` 删除理由**：数值 |ρ|²_B=35 已由 `rho_sq_doubled_value` 定理严格证明；"自由谱下界=Weyl 范数平方"的 Harish-Chandra Plancherel 定理需 Mathlib 对称空间谱理论库（当前不存在），已由条件定理 `s1_lambda_perp_eq_35_over_3` 的假设 h_double 承载（论文 §5.5 自述）。删除零内容 axiom 避免表演性诚实。

### lam1 ↔ lambda_perp 闭环

```lean
theorem lam1_eq_lambda_perp : lam1 = lambda_perp := by
  unfold lam1 lambda_perp
  rfl

theorem lambda_par_value : lambda_par = 35 := by unfold lambda_par; rfl
theorem lambda_perp_value : lambda_perp = 35/3 := by unfold lambda_perp; rfl
theorem lam1_value_closed : lam1 = 35/3 := by unfold lam1; rfl
theorem lambda_perp_eq_par_div_3 : lambda_perp = lambda_par / 3 := by
  unfold lambda_perp lambda_par; norm_num
```

**教训**：`unfold` 后目标若变成字面相等的表达式（如 `35/3 = 35/3`），必须补 `rfl` 收尾——`unfold` 只做定义展开，不自动 closed。

### 最终状态

- 编译通过（exit 0），**0 sorry / 0 admit / 0 `:= True` / 0 `:= by trivial`**
- 74 axiom / 57 theorem / 12 lemma（净变化：+`cw_vev_exists` −`a_t3`）
- 31 个 `@[honest_axiom]` + 10 个 `@[phenomenological]` machine-auditable 标签

## 二、Lean 4 自定义 attribute 注册陷阱（通用）

### 陷阱 1：`initialize` 块不能内联注册同文件使用的 attribute

```lean
-- ❌ 错误：内联注册，同文件后续 @[honest_axiom] 报 "Unknown attribute"
import Lean
initialize honestAxiomAttr : Lean.TagAttribute ←
  Lean.registerTagAttribute `honest_axiom "..."
axiom foo : True    -- 上面 @[honest_axiom] 无法解析

-- ✅ 正确：独立文件 HonestAttr.lean 注册 + 主文件 import
-- HonestAttr.lean:
import Lean
initialize honestAxiomAttr : Lean.TagAttribute ←
  Lean.registerTagAttribute `honest_axiom "..."

-- 主文件:
import HonestAttr   -- 先于使用 @[honest_axiom]
@[honest_axiom]
axiom foo : True
```

**根因**：`initialize` 块在模块 elaboration **之后**才执行（运行时）。同一文件里，`@[honest_axiom]` 的使用在 `initialize` 块执行前就被 elaborator 解析，故报 "Unknown attribute"。独立文件被 `import` 时，其 `initialize` 块在**主文件 elaboration 之前**执行，attribute 已注册。

### 陷阱 2：`import` 需要 .olean，而 `lean` 默认不生成到源目录

`import HonestAttr` 搜索的是 `HonestAttr.olean`（编译产物），不是 `HonestAttr.lean` 源文件。且 `lean HonestAttr.lean` 默认**不**把 .olean 生成到源目录（可能到 LEAN_PATH 或默认位置）。

```bash
# 必须显式 -o 生成到源目录
lean -o HonestAttr.olean HonestAttr.lean
```

### CGICE 编译命令（复用已编译 mathlib，避免 4-6h 重编译）

```bash
export PATH=/root/.elan/bin:$PATH            # lake 不在默认 PATH
cd /mnt/d/AI_for_Science/Mathlib_setup/mathlib4-master
# 先编译 HonestAttr.olean
lean -o "/mnt/c/.../cgice/HonestAttr.olean" "/mnt/c/.../cgice/HonestAttr.lean"
# 再编译主文件（LEAN_PATH 指向 cgice 目录以找到 HonestAttr.olean）
lake env sh -c 'LEAN_PATH="/mnt/c/.../cgice:$LEAN_PATH" lean "/mnt/c/.../cgice/cgice_proof_v9.lean"'
```

### DAG 审计 attribute 假阳性修复

`proof_dag_audit.py` 的悬空引用检测用 `DEP_SUFFIX_RE = \b(..._axiom|_lemma|_theorem)\b`，会把 `@[honest_axiom]` 的 attribute 名误报为"悬空引用"。修复：检测前先剥离 attribute 标签 `re.sub(r"@\[[^\]]*\]", "", text)`。**通用模式**：任何解析 Lean 标识符引用的正则，必须先排除 `@[...]` attribute 标签。

## 三、相关文件

- Lean：`C:\Users\Think\Desktop\AI论文\cgice\cgice_proof_v9.lean`（1010→1040 行）
- HonestAttr：`C:\Users\Think\Desktop\AI论文\cgice\HonestAttr.lean`（新建）
- 论文：`cgice_paper_v9_fop.md`（§5.5 待办已落地，可同步）
- DAG 审计：`scripts/proof_dag_audit.py`（已修复 attribute 假阳性）
