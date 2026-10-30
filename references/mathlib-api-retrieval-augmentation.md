# mathlib 4.34 API 检索增强 — 测试记录与接入方法

日期: 2026-08-21
状态: ✅ 已验证（端到端闭环通过）

## 背景与动机

形式化证明补全的瓶颈排序（本 session 多次实测确认）：

1. **定理陈述本身为假**（如 CGICE 的 Λ_CC 两值矛盾、H0 反向工程）——无模型可救，只能靠 Stage 3.5 `proof_consistency_audit` 拦截。
2. **编译验证太慢**（`lake env lean` 111-249s/文件）——靠 `lake build` 批量化。
3. **LLM 不知道正确的 mathlib 4.34 API 名**——这是唯一能靠"检索"改善的点。

第 3 点的根因：所有预训练模型的 mathlib 知识都早于 4.34 的 Is-prefix 重构
（`OrderedRing`→`IsOrderedRing` 等）。换更强的模型（Llemma 7B / DeepSeek-Prover）也救不了，
因为它们的训练数据同样是旧 mathlib。**检索当前源码比模型记忆可靠。**

## 模块位置与依赖

- 模块: `scripts/mathlib_api_lookup.py`（纯 stdlib，无第三方依赖）
- 依赖: mathlib 源码在 `<LEAN_PROJECT>/.lake/packages/mathlib/Mathlib`（32 子目录）
- 检索方式: Python `re` 扫描 .lean 源码（`rg` 本机不可用，已用纯 Python 回退）

## 核心函数签名

```python
from mathlib_api_lookup import (
    retrieve_from_code,   # 编译前: 从源码 [X ...] binder 提取旧 typeclass 名 → 输出"✗ X → 应改为 Y"
    retrieve_for_error,   # 编译后: 从 error 文本提取 unknown identifier/constant → 解析
    find_theorems,        # 按模式找引理: find_theorems("exp_lt") → exp_lt_one_iff
    resolve_typeclass,    # 单个旧名解析: OrderedRing → IsOrderedRing
    build_prompt_injection,# 检索结果 → prompt 注入文本
    check_binders,        # 提取源码所有 [X ...] binder 并核对
    verify_decl,          # 检查声明名在 mathlib 4.34 是否存在(含 (?!\.) 防命名空间误匹配)
)
```

## 两条调用路径（均实测通过）

### 路径 A：编译前预防（推荐，省一次编译）

```python
draft = """import Mathlib
variable {R : Type*} [Ring R] [PartialOrder R] [OrderedRing R]
theorem t {a b : R} (ha : 0 ≤ a) (hb : 0 ≤ b) : 0 ≤ a * b := by
  sorry
"""
inj = retrieve_from_code(draft)
# inj = "【mathlib 4.34 typeclass 检查】\n  ✗ OrderedRing → 应改为 IsOrderedRing"
prompt = f"补全下面定理...\n{inj}\n\n{draft}"
# → Qwen3.5 输出 exact mul_nonneg ha hb → 编译通过
```

### 路径 B：编译后修复

```python
err = "error: unknown identifier 'OrderedRing'"
ret = retrieve_for_error(err)   # → OrderedRing → IsOrderedRing
inj = build_prompt_injection(ret)
```

## 实测数据（2026-08-21）

| 测试 | 结果 |
|------|------|
| `resolve_typeclass('OrderedRing')` | ✓ → IsOrderedRing (Defs.lean:69) |
| `resolve_typeclass('TopologicalGroup')` | ✓ → IsTopologicalGroup (Defs.lean:110) |
| `resolve_typeclass('Archimedean')` | ✓ 仍存在（技能旧清单"改名 MulArchimedean"是错的）|
| `resolve_typeclass('LinearOrderedField')` | ✗ 已移除，无 Is 后继 |
| `find_theorems('exp_lt_one')` | ✓ → `exp_lt_one_iff {x : ℝ} : exp x < 1 ↔ x < 0` |
| 端到端闭环（旧 API → 检索 → 注入 → 补证明 → 编译）| ✓ 编译通过 + 0 sorry，~122s |

## 关键事实（源码 grep 得出，比静态清单更准）

- `OrderedRing` → `IsOrderedRing`；`TopologicalGroup` → `IsTopologicalGroup`
- `Archimedean` **仍存在**（`class Archimedean (R) [AddCommMonoid R] [PartialOrder R]`，与 MulArchimedean 并存）
- `LinearOrderedField` **已移除**，现代分解：`LinearOrderedAddCommGroup` / `LinearOrderedCommGroupWithZero` / `LinearOrderedAddCommMonoidWithTop`（按用例选）
- `Real.exp_lt_one_of_neg` 不存在（LLM 常猜的错名），正确 `exp_lt_one_iff`

## 陷阱

1. **"invalid binder annotation, type is not a class instance" 不报名字**——这是用旧 typeclass 作 binder 的新式错误，`retrieve_for_error` 提取不到名字。必须用 `retrieve_from_code`（编译前主动查 binder）而非等编译失败。
2. **`rg` 在本机不可用**——模块已回退到纯 Python `re` 扫描，勿再尝试 `rg`。
3. **命名空间误匹配**——`structure TopologicalGroup.IsSES` 会被 `verify_decl('TopologicalGroup')` 误判为"存在"。已用 `(?!\.)` 负向前瞻修复。
4. **检索不能证明假定理**——它只解决"名字不知道"，不解决"陈述为假"。假陈述仍要靠 Stage 3.5 拦截。

5. **`mul_right_inj'` 签名陷阱 + 双模型假阳性靠源码检索裁决（2026-08-21 实测）**：mathlib 4.34 中 `mul_right_inj' (ha : a ≠ 0) : a * b = a * c ↔ b = c` 是**左乘可注入**（"right" 指右消去，非右乘）。DeepSeek v4-pro 在论证 `s1_lambda_perp_eq_35_over_3` 时误记为"右乘 a*c=b*c"，据此判该定理 ✗（假阳性）；Qwen3.8 校核判 ✓。用 `get_signature('mul_right_inj\'')` 检索源码确认真实签名是 `a*b = a*c`（左乘），与定理证明 `apply (mul_right_inj' h3).1; rw [hT6_ratio]`（hT6_ratio : 3*lambda_perp = rho_double）完全匹配，且 `lake env lean` 编译 exit 0 佐证。教训：**模型对 mathlib API 签名的记忆常错，单模型独有结论必须用 `mathlib_api_lookup.get_signature()` 检索源码 + 实际编译双重裁决**，不能盲信主审模型的 ✗。
