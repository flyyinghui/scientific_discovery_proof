# MathCode 146K 文件批量编译：障碍诊断 + 修复方案

Validated 2026-08-16 on `<WORK_DIR>\mathcode_v2\mathcode_v2_pack\formal-proof-lib\`
(146,029 `.lean` files, 338 MB, avg 2320 B/file, 63% contain `sorry`).

## 障碍清单（按优先级）

1. **56% import 模块名过时** — MathCode 基于旧版 mathlib 编写，`import` 的子模块名
   （`Mathlib.Topology.Instances.Real.Basic`, `Mathlib.MeasureTheory.MeasureSpace`,
   `Mathlib.Data.Rat.Order` 等）在 mathlib 4.34-rc1 里已改名/重组。
   抽样 200 文件：158 个不同 import 模块，69 存在 / 89 缺失。
   **修复：`import Mathlib.xxx` 全部替换为 `import Mathlib` 单入口**（第一个 import 保留，
   后续 import 删除）。全量 olean 已存在，单入口零模块匹配成本。

2. **内容 API "Is 前缀重构"过时** — mathlib 4 把一批类型类加了 `Is` 前缀。已确认映射：
   - `OrderedRing` → `IsOrderedRing`
   - `TopologicalGroup` → `IsTopologicalGroup`
   - `TopologicalRing` → `IsTopologicalRing`
   - `Archimedean` → `MulArchimedean`
   **未改名（还在，勿动）**：`NormedAddCommGroup`, `MetricSpace`, `NormedSpace`,
   `NormedRing`, `NormedField` — 抽样统计里它们出现频率最高（全量约 6.3 万次）但**不是**过时。
   批量替换用 `\bOrderedRing\b` word-boundary 正则，避免误伤 `IsOrderedRing`（`\b` 不会
   匹配 `IsOrderedRing` 里的 `OrderedRing`，因为前面是字母 `s`）。

3. **数字开头文件名（非法模块名）** — `0c7bb95e11c1_000_...lean` 数字开头，
   Lean 4 无法作为模块名（Pitfall #39）。`lake env lean <file>` 直接编译单文件
   **不需要**模块名，但 `lake build` 批量（注册 roots）需要。
   **修复：批量重命名 `M_` 前缀**（`0c7bb95e11c1_...` → `M_0c7bb95e11c1_...`）。
   文件只 import Mathlib（不互相 import），重命名不影响内部引用。

4. **63% sorry** — 编译通过（sorry 是 warning）但非完整证明。诚实标注，不试图补全。

## 关键性能 pitfall：单文件编译 111 秒 vs lake build 批量

`lake env lean <单个文件>` 的瓶颈是 `import Mathlib` 全量加载 13GB olean 索引
（实测 111 秒/文件），**不是**文件内容。146K 文件串行 = 187 天，8 核并行 = 23 天。

正确路径：**重命名 + 注册 roots + `lake build` 批量**，mathlib 只加载一次（进程内共享），
单文件降到秒级。但即便批量，146K × (1-5s) 仍是 40-200 小时，且大量 API 过时文件会失败。

## 环境搭建（github.com 443 blocked）

1. `lean-toolchain` = `leanprover/lean4:v4.34.0-rc1`（与 mathlib olean 匹配；elan 默认
   4.33.0 会报 "incompatible header"）。
2. `lakefile.lean` 用本地路径 `require` 覆盖 8 个依赖 + mathlib（复用 CGICE 的 olean）：
   ```lean
   @[default_target]
   lean_lib «Mathcode» where
     roots := #[`Mathcode]
   require batteries from ".lake/packages/batteries"   -- ×8 (Qq/aesop/...)
   require mathlib from "<LEAN_PROJECT>/.lake/packages/mathlib"
   ```
3. 依赖包从已编译成功的项目（V16/V63）复制 `.lake/build`（olean），
   **不要**用 `ignore_patterns('.git', '.lake')` 只复制源码——会触发依赖包重新编译
   （batteries 1506 模块超时）。
4. **陷阱**：批量替换 `import` 的脚本会误改 `lakefile.lean` 的 `import Lake` →
   `import Mathlib`，导致 "unknown namespace Lake"。脚本必须排除 `lakefile.lean` 和
   根模块（如 `Mathcode.lean`）。

## 批量脚本模式

三个独立后台脚本（`terminal background=true + notify_on_complete`）：
1. `_fix_imports.py` — import 单入口替换（130K+ 文件，~2 分钟）
2. `_fix_api.py` — word-boundary API 映射替换
3. `_rename.py` — 数字开头 → `M_` 前缀 + 生成 `_module_names.txt` 供 roots

编译统计脚本的 `print(..., flush=True)` 输出仍会被缓冲——结果直接写文件
（`_compile_results.txt`）而非依赖 stdout。
