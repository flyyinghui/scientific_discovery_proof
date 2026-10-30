# MathCode 146K 批量编译评估 (2026-08-16)

## 库规模
- 路径: `<WORK_DIR>\mathcode_v2\mathcode_v2_pack\formal-proof-lib\`
- 146,029 个 .lean 文件, 338 MB, 平均 2320 字节/文件
- 63% 文件含 sorry (抽样 1000 文件, 630 有 sorry)
- 文件名格式: `<hash>_<编号>_<名称>.lean`, hash 是数字开头 (如 `0c7bb95e11c1_...`)

## 编译障碍 (mathlib 4.34.0-rc1 下)
1. **数字开头文件名** → 非法 Lean 模块名 (无法 import/注册), 需重命名为 `M_` 前缀
2. **56% import 模块名过时** (抽样 200 文件: 158 个 import, 89 缺失) — `Mathlib.Topology.Instances.Real.Basic`、`Mathlib.MeasureTheory.MeasureSpace` 等已改名 → 用 `import Mathlib` 单入口绕过
3. **内容 API 过时** — mathlib 4 的 Is 前缀重构: `OrderedRing`→`IsOrderedRing`、`TopologicalGroup`→`IsTopologicalGroup`、`Archimedean`→`MulArchimedean`; `Field` 结构字段变化 (intCast_ofNat 等默认值合成失败)
4. **63% sorry** — 编译通过但非完整证明

## 关键数据 (500 模块测试批次, 2026-08-16)
- **成功 50 (10%), 失败 450 (90%)**
- 失败根因: Field 结构字段变化 + typeclass 合成失败 (`invalid binder annotation`, `could not synthesize default value for field ...`)

## 完整错误三分类 (182 报错模块深入分析, 2026-08-16)
对 500 模块测试的完整 log (3491 行, 182 报错模块) 深入分析后，**修正之前的结论**——主要障碍不是 Field 结构字段变化 (仅 3 处)，而是：

| 错误类型 | 数量 | 本质 | 可批量化 |
|---------|------|------|---------|
| **type mismatch** | **103 (57%)** | 定理/引理参数类型签名变化 (degree_mul_eq 隐式参数等) | ❌ 逐个理解新签名 |
| Unknown identifier | 56 | mathlib 4 定理改名 (eq_top_iff_one_mem/gcdMonoidGCD/add_eq_bot_iff) | ⚠️ 需映射表 |
| unsolved goals | 42 | 证明策略失效 | ❌ 修复策略 |
| no goals | 17 | 策略多余 (目标已闭合) | ✅ 删除多余策略 |
| invalid binder | 9 | typeclass binder 问题 | ⚠️ |
| Field 字段默认值 | **仅 3** | 结构字段变化 (intCast_ofNat 等) | ⚠️ 少数 |

**重复声明 (~783 处, 教学示例自包含的根本冲突)**: MathCode 每个文件是"教学示例"，自包含定义 `class Group`(174) / `class Semigroup`(116) / `class Field`(87) / `structure Ideal`(87) / `class Ring`(87) / `abbrev Seq`(87) / `def IsCoprime`(87) 等简化版基础结构。`import Mathlib` 后与 mathlib 完整类型类冲突 ("has already been declared")。这是**根本设计差异**（教学示例从零定义 vs mathlib 类型类复用），删除声明会失去文件意义，完整编译不现实。
- 成功模块 = 简单定理 (Archimedean_property, Completeness_axiom_LUB, Continuity_at_a_point)
- 失败模块 = 复杂模块 (Fundamental_Theorem_of_Calculus, Lebesgue_integral, Metric_space_topology)

## Lake roots 递归深度限制
- lakefile `roots := #[...]` 列 **5000 个模块** → `error: maximum recursion depth has been reached`
- 降到 **500 模块** 可正常编译
- 结论: 大批量模块编译必须分批 (每批 ≤500 模块), 不能一次性 roots 全部

## 编译策略 (实测)
- **单文件 `lake env lean <file>` = 111 秒** (瓶颈是 `import Mathlib` 全量加载 13GB olean 索引, 不是文件内容)
- **批量 `lake build` = 共享加载**, 快得多 (mathlib olean 进程内复用)
- 完整流程: (1) 重命名数字开头→M_ 前缀 (Python os.rename), (2) 生成 lakefile roots 列表 (Python 脚本), (3) `MATHLIB_NO_CACHE_ON_UPDATE=1 lake build`
- 预处理脚本模式: import 单入口替换 (第一个 import → `import Mathlib`, 删除后续 import 行) + API 映射替换 (word-boundary 正则 `\bOrderedRing\b` → `IsOrderedRing`)

## 结论
MathCode 146K 文件在 mathlib 4.34 下的**可编译率约 10%**, 90% 需系统性 API 修复 (几十个映射 + 批量替换 + 反复编译), 且 63% 是 sorry 未完成证明。完整编译是远超单次会话的工程。已交付价值: 可复用编译环境 + import/API/重命名三阶段预处理 + 10% 可编译率基准数据。
