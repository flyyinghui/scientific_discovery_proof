# MathCode formal-proof-lib 机械修复 + 启发式语法筛查（2026-08-20 实测）

146,449 个 .lean 文件的批量机械修复与语法筛查结果。脚本在 `formal-proof-lib/mech_fix.py`（单文件修复）+ `batch_mechfix_screen.py`（全库批处理）。

## 格式分布（300 文件随机抽样）

| 特征 | 占比 |
|------|------|
| 无 Markdown 围栏（已干净）| 95.7% |
| 有 Markdown 围栏（```lean ... ```）| 4.3% |
| 含 theorem/lemma | 73% |
| 含 `sorry` | 51% |
| 纯定义（无 theorem）| 27% |
| import 不在文件开头 | 1% |
| 重定义 mathlib typeclass（class Group 等）| 0.3%（远低于早期估计）|

注意：围栏错误在早期 lake build 里看着像"全库"问题，但实际只占 4.3%——它**按前缀聚集**（如 `0000e0073ecb` 实分析卷几乎全带围栏），随机抽样会低估。

## mech_fix 修复类型与实测数量（全库 146,449 文件，391 秒）

| 修复 | 数量 | 是否实质 |
|------|------|---------|
| fix_import（import 重定位）| 133,368 | ⚠️ **多数是空行级微调**，非实质修复 |
| strip_fence（去围栏）| 4,509 | ✓ 实质 |
| add_import（补缺失 import Mathlib）| 3,928 | ✓ 实质 |
| unicode_sup_² | 10,395 | ✓ 实质 |
| unicode_sup_³ | 2,296 | ✓ |
| lambda_identifier_rename（λ→lam）| 2,468 | ✓ |
| unicode_sup_⁴ | 460 | ✓ |
| constant_to_axiom | 114 | ✓ |
| unicode_sup_⁶ | 36 | ✓ |
| structure_extends_syntax | 7 | ✓ |

**诚实坑**：`fix_import` 会重排每一个有 import 的文件（删掉全部 import 行，在 header 注释后重插 `import Mathlib`），即使原文件 import 位置本就正确——所以"137,296 个文件被修复"里 133K 是空行级微调，真正实质修复约 20K（围栏 4.5K + import 补缺 3.9K + 上标 13K + λ 2.5K）。

## 启发式语法筛查结果

- **98.4%（144,104）无已知阻塞模式**（围栏/非法 ∃-binder/旧 structure 语法/旧 typeclass）。
- 剩余 2,345 个已知阻塞：
  - `∃ M, [Nonempty M]` 非法实例 binder：1,822（机械不可修，需语义重写为 `∃ (M) (_ : Nonempty M)`）
  - 旧 typeclass 名：~522（OrderedSemiring 86、LinearOrderedField 238、LinearOrderedRing 69 等）

## 关键诚实结论：启发式筛查"通过" ≠ 能编译

启发式 screen 只查**已知模式**，过了 ≠ 能编译。实测原文件（含 sorry）编译率仍 ~0%，因为三类**非启发式可查**的致命问题：
1. **语法错误**（`∃ M, [Nonempty M]` 非法 binder 语法）
2. **幻影符号**（`Language`/`Theory`/`IsBrownianMotion`/`unitaryGroup` 等 mathlib 不存在的高级 API）
3. **定理陈述本身为假**（如 `order_mod_pow_prime` 的 b=0 反例；CGICE 的 Λ_CC 两值矛盾）

"证据链完善"（填 sorry）对这三类**无效**——它们不是证明链问题，是陈述/API/语法问题。机械修复能推进的是围栏/import/上标/λ 这 ~5% 的语法层，真正决定编译率的是幻影符号 + 假陈述，需 LLM 语义重写 + 假陈述拦截（Stage 3.5 proof_consistency_audit）。

## 复用要点

- 批量处理 146K 文件用**纯 stdlib Python + regex**（mech_fix），391 秒跑完，不要逐文件 `lake env lean`（111-249s/文件）。
- 选"理想候选文件"（有 sorry+theorem、无围栏、无自定义 structure）时，**按文件大小升序选会把空文件/gam_*_fixed 残留选进来**——须按 `500B ≤ size ≤ 8KB` 且含 `sorry`+`theorem` 过滤（实际 66,461 个候选）。
- 启发式 screen 的值是**快速定位"肯定有问题"的 2.3K 文件**，不是宣称"其余 98% 能编译"。
