# Lean 4 编译环境搭建 (Lake 本地路径 + 数字开头模块名)

验证于 2026-08-15 (V63 中微子凝聚 + V17 六维流形时空, Lean 4.34.0-rc1, Lake 5.0)。

## 背景

github.com 443 blocked 时无法 `git clone` mathlib 及其依赖。mathlib 源码
(mathlib4-master.zip) 已解压到 `CGICE/.lake/packages/mathlib/`, 但其 8 个
依赖包需按 lake-manifest.json 的精确 rev 从 codeload CDN 下载。

## 完整流程

### 1. 下载 mathlib 的 8 个依赖包

mathlib 的 `lake-manifest.json` 记录每个依赖的 `url` + `rev` + `name`。
按 rev 从 codeload 下载 zip (github.com 直连 blocked, codeload.github.com 可达):

```
https://codeload.github.com/<org>/<repo>/zip/<rev>
```

8 个包 (Lake 名 → 实际仓库名, 注意 3 个名称不一致):

| Lake 包名 | 实际 GitHub 仓库 | 分支 |
|-----------|-----------------|------|
| batteries | batteries | main |
| Qq | **quote4** | master |
| aesop | aesop | master |
| proofwidgets | **ProofWidgets4** | main |
| importGraph | **import-graph** | main |
| LeanSearchClient | LeanSearchClient | main |
| plausible | plausible | main |
| Cli | leanprover/lean4-cli (传递依赖, inherited) | v4.34.0-rc1 |

解压后重命名为 Lake 包名 (zip 内顶层目录是 `<repo>-<rev>`):

```python
import zipfile, os, shutil
for lake_name, repo, commit in [...]:
    with zipfile.ZipFile(f"{lake_name}.zip") as zf:
        top = zf.namelist()[0].split('/')[0]
        zf.extractall(base)
    os.rename(os.path.join(base, top), os.path.join(base, lake_name))
```

放置位置: 根包的 `.lake/packages/<Lake包名>/` (Lake 用根包的 packagesDir)。

### 2. 根包 lakefile.lean 模板

```lean
import Lake
open Lake DSL

package «project» where
  -- 项目说明

@[default_target]
lean_lib «Project» where
  roots := #[`RootModule]  -- 字母开头的根模块名

-- 本地路径 require 覆盖 mathlib 的 git 声明 (github blocked 时必需)
require batteries from ".lake/packages/batteries"
require Qq from ".lake/packages/Qq"
require aesop from ".lake/packages/aesop"
require proofwidgets from ".lake/packages/proofwidgets"
require importGraph from ".lake/packages/importGraph"
require LeanSearchClient from ".lake/packages/LeanSearchClient"
require plausible from ".lake/packages/plausible"
require Cli from ".lake/packages/Cli"
require mathlib from "../CGICE/.lake/packages/mathlib"  -- 本地路径指向 mathlib
```

还需 `lean-toolchain` 文件 (内容 `leanprover/lean4:v4.34.0-rc1`)。

### 3. 编译命令

```bash
MATHLIB_NO_CACHE_ON_UPDATE=1 lake build
```

`MATHLIB_NO_CACHE_ON_UPDATE=1` 跳过 mathlib 的 post-update cache 下载
(否则报 "mathlib: failed to fetch cache", 因 cache server 不可达)。

mathlib 全量编译 ~8725 模块, 约 2-3 小时 (取决于 CPU)。多个项目各自有
独立的 `.lake/build`, **不共享 olean** — 每个项目都要重新编译 mathlib。

## 关键坑

### 数字开头模块名 (6D_...)

Lean 4 模块名必须以字母/下划线开头。文件 `6D_Spacetime_Formal_Proof_V17.lean`
无法用以下任何方式引用:
- 反引号 `` `6D_... `` → "'`'; expected '`('"
- 法语引号 `«6D_...»` → "Unknown identifier"
- `Name.mkSimple "6D_..."` → "Unknown identifier"

**唯一可靠方案**: 重命名文件为字母开头 (如 `Spacetime_Formal_Proof_V17.lean`),
头部注释保留原文件名。`roots := #[`Spacetime_Formal_Proof_V17]` 正常。

### 多文件合并残留 (V17 不可编译根因)

"3 proof files merged → 1 unified Lean file" 的产物有两个历史 bug:
1. 文件头 `/-! ... -/` 注释缺关闭 `-/` → "unterminated comment" (把 import 吞进注释)
2. 每个 section 残留 `import Mathlib` (V17 有 37 个) → "invalid 'import' command"

修复: 补文件头 `-/`; 删除第一个 import 之后的所有 `import Mathlib`
(保留 `import Mathlib; open Real; ...` 的 open 部分)。

诊断 import 数量: `search_files pattern='^import '` 统计。

## 常见错误速查

| 错误 | 原因 | 修复 |
|------|------|------|
| "URL has changed / not a git repository" | 包不是 git repo, Lake 尝试 clone | 本地路径 require 覆盖 |
| "failed to fetch cache" | mathlib post-update 下载预编译 olean | MATHLIB_NO_CACHE_ON_UPDATE=1 |
| "no default targets / Nothing to build" | lean_lib 缺 @[default_target] | 加注解 |
| "no such file ... <LibName>.lean" | lean_lib 默认找 Lib名.lean | roots 指定实际文件 |
| "unterminated comment" | 文件头 /- 注释缺 -/ | 补关闭符 |
| "invalid 'import' command" | 文件中间有 import | 删除重复 import |
