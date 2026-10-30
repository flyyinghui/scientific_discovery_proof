# Lake + Mathlib 编译环境搭建（github.com 443 blocked 时）

验证于 V63/V17 Lean 编译（2026-08-15）。当 github.com 直连 443 blocked（git clone 失败）
但 codeload.github.com CDN 可达时，用以下完整方案让依赖 Mathlib 的项目可编译。

## 1. 下载 mathlib 依赖包（8 个）

mathlib 的 `lake-manifest.json` 记录 7 个直接依赖 + 1 个传递依赖（lean4-cli），每个有精确
`rev`。从 codeload 按 rev 下载 zip：

```
https://codeload.github.com/<org>/<repo>/zip/<commit-sha>
```

7 直接依赖（**Lake 包名 ≠ GitHub 仓库名**，直接抄 Lake 名当仓库名会 404）：

| Lake 包名 | 实际 GitHub 仓库 | 分支 |
|-----------|-----------------|------|
| batteries | batteries | main |
| Qq | **quote4** | master |
| aesop | aesop | master |
| proofwidgets | **ProofWidgets4** | main |
| importGraph | **import-graph** | main |
| LeanSearchClient | LeanSearchClient | main |
| plausible | plausible | main |

+ 第 8 个传递依赖：`Cli` → `leanprover/lean4-cli`（注意 org 是 `leanprover` 不是
`leanprover-community`，分支是版本 tag 如 `v4.34.0-rc1`）。

解压后把 `<repo>-<commit>` 目录重命名为 Lake 包名（用 Python zipfile 读取 namelist 确认顶层
目录名，比 unzip -l 可靠）。

## 2. 放置依赖包

把 8 个包目录放到项目的 `.lake/packages/<Lake包名>/`。

## 3. 根包 lakefile.lean 用本地路径 require（覆盖 git 声明）

```lean
require batteries from ".lake/packages/batteries"
require Qq from ".lake/packages/Qq"
require aesop from ".lake/packages/aesop"
require proofwidgets from ".lake/packages/proofwidgets"
require importGraph from ".lake/packages/importGraph"
require LeanSearchClient from ".lake/packages/LeanSearchClient"
require plausible from ".lake/packages/plausible"
require Cli from ".lake/packages/Cli"
require mathlib from "../CGICE/.lake/packages/mathlib"   -- mathlib zip 解压位置
```

根包的本地路径 require 覆盖 mathlib lakefile 里的 `require "org"/"repo" @ git` 声明，
避免 Lake 尝试 git clone（会因 "not a git repository" / 443 失败）。

## 4. 跳过 cache 下载

```bash
MATHLIB_NO_CACHE_ON_UPDATE=1 lake build
```

mathlib 的 post_update 钩子会运行 `lake exe cache get` 下载预编译 olean；网络 blocked 时
报 "mathlib: failed to fetch cache"。该环境变量跳过。

## 5. lean_lib 配置两要点

- 加 `@[default_target]` 注解，否则 `lake build` 报 "Nothing to build"。
- 加 `roots := #[`模块名]` 指定根模块（默认按 lib 名找 `Spacetime.lean`）。

## 6. 数字开头文件名的坑（关键！）

Lean 4 **不支持数字开头的模块名**。文件 `6D_Spacetime_Formal_Proof_V17.lean` 四种写法全失败：

| 写法 | 错误 |
|------|------|
| `roots := #[`6D_...]`（反引号） | `'`'; expected '`('`（语法错误） |
| `roots := #[«6D_...»]`（法语引号） | `Unknown identifier` |
| `roots := #[Name.mkSimple "6D_..."]` | `Unknown identifier Name.mkSimple` |
| `import «6D_...»`（wrapper 导入） | `unknown module prefix '6D_...'` |

唯一可靠方案：**重命名文件**为字母开头的合法模块名（如 `Spacetime_Formal_Proof_V17.lean`），
头部注释保留原文件名，lakefile 用 `roots := #[`Spacetime_Formal_Proof_V17]`。

## 7. 编译时间与验证

mathlib 全量源码编译 **8725 模块约 7 小时**（~2.75s/模块并行，非 2-3h）。后台
`lake build` 时务必 `notify_on_complete=true`。验证 job computation 通过：输出出现
`Building <模块名> (Ns)` 而非立即报错。

## 8. 每项目独立编译 mathlib

每个项目的 `.lake/build` 独立，mathlib 的 olean 不跨项目共享。V63 和 V17 各需重新编译
一遍 mathlib（并行会竞争 CPU，但总时间优于串行）。
