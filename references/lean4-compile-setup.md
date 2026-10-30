# Lean4 编译环境离线配置（mathlib 本地 require）+ 编译阻塞诊断

四篇 SL(6,C) 论文（V63/V17/V16/CGICE）的 Lean 形式化证明需编译验证，但 mathlib 依赖 8 个
GitHub 包，而 github.com 在本机 443 blocked。以下为离线配置 + 编译阻塞根因（2026-08-15 验证）。

## 一、完整配置步骤

1. **下载 mathlib 的 8 个依赖包**（按 `lake-manifest.json` 的精确 rev，从 codeload）：
   - codeload.github.com 可达（github.com 443 blocked，git clone 直接失败）
   - URL：`https://codeload.github.com/<org>/<repo>/zip/<commit-sha>`
   - 解压后**重命名为 Lake 包名**（zip 内顶层目录是 `<repo>-<commit>`）。3 个名称差异：
     `Qq→quote4`、`proofwidgets→ProofWidgets4`、`importGraph→import-graph`
   - 第 8 个 `Cli`（lean4-cli）是 `inherited` 传递依赖，org 是 `leanprover`（非 leanprover-community）

2. **放置依赖包**：复制到项目 `.lake/packages/<Lake包名>/`（Lake 包名作目录名）

3. **lakefile.lean**（本地 require 覆盖 mathlib 的 git 声明）：
   ```lean
   import Lake
   open Lake DSL
   package «neutrino» where
   @[default_target]
   lean_lib «Neutrino» where
     roots := #[`Neutrino_Condensation_proof_63]   -- 根模块名 = 文件名去掉 .lean
   require batteries from ".lake/packages/batteries"
   require Qq from ".lake/packages/Qq"
   -- ... 其余 6 个包
   require mathlib from "../CGICE/.lake/packages/mathlib"
   ```

4. **lean-toolchain**：`leanprover/lean4:v4.34.0-rc1`

5. **MATHLIB_NO_CACHE_ON_UPDATE=1**：跳过 mathlib 的 post-update 钩子 `lake exe cache get`
   （否则编译到最后报 "mathlib: failed to fetch cache"，因为 cache server 不可达）

6. **编译时间**：mathlib 全量 **8725 模块，约 8 小时**（单项目串行）。**不要并行编译多个
   项目** —— 每个项目都从 scratch 编译 mathlib（olean 写在各自 `.lake/build`），并行不仅
   竞争 CPU，实测会导致 build 产物丢失（`.lake/build` 被清理，磁盘充足非原因）。

## 二、编译阻塞根因（V17 三个历史 bug，逐层修复）

诊断顺序：修复一个错误重新编译会暴露下一个。三个历史阻塞：

1. **数字开头文件名无法作为模块名**（V17：`6D_Spacetime_Formal_Proof_V17.lean`）
   - 模块名 `6D_...` 以数字开头，Lean 4 报 `unknown module prefix '6D_...'`
   - 三种写法都失败：`roots := #[`6D_...]`（反引号）→ 语法错误 `'`'; expected '`('`；
     `roots := #[«6D_...»]`（法语引号）→ `Unknown identifier`；`Name.mkSimple` → 不在 Lake DSL 作用域
   - **唯一可靠方案：重命名文件为字母开头的合法模块名**（如 `Spacetime_Formal_Proof_V17.lean`），
     头部注释保留原文件名。用户指定数字开头文件名时需说明这是 Lean 4 限制。

2. **`/-!` 文档注释导致 "invalid import"**（Lean 4.34.0-rc1）
   - 文件头 `/-! ... -/`（文档注释）后跟 import 报
     `invalid 'import' command, it must be used in the beginning of the file`
   - 实测：`/-!`+import 报错，`/-`（普通块注释）+import 正常
   - **修复：文件头 `/-!` 改成 `/-`**

3. **文件头注释 `-/` 缺失** → `unterminated comment`
   - `/-!` 块注释缺少配对 `-/`（如分隔行写成 `# =====` 而非 `# ===== -/`），
     导致后续 `import Mathlib` 被注释吞掉

4. **重复 import**（多文件合并残留）
   - 多个 Lean 文件合并成一个时，每个 section 残留 `import Mathlib`（V17 有 37 个）
   - Lean 4 只允许 import 在文件开头 → `invalid import`
   - **修复：删除第一个 import 之后的所有重复 import**（`import Mathlib; open Real` 形式
     只删 `import Mathlib; ` 前缀，保留 `open Real`）

5. **孤儿 import**（文件末尾 `end` 之后还有 `import Mathlib`，GAP 说明块残留）→ 同样非法

## 三、验证脚本（词法检查，快速定位未关闭注释）

编译报 `unterminated comment` 时，用嵌套块注释扫描定位（正确处理 `/-`/`-/` 嵌套、
忽略字符串 `"..."` 和单行注释 `--`）。注意：简单 grep `/-` 与 `-/` 数量差会误报
（字符串/注释里的符号不是真块注释）。扫描逻辑：
- 块注释优先（`/-` 进入，嵌套 `/-` 加深，`-/` 减浅），块注释内忽略一切
- 字符串 `"..."` 内忽略 `/-`、`--`、`-/`
- 单行注释 `--` 跳到行尾
