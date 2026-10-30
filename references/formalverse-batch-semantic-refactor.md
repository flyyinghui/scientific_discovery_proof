# formalverse benchmark 批量语义重构（Qwen3.5 + 孤儿 doc 注释修复）

formal-proof-lib 146K 文件的批量编译，比"机械修复 + API 映射"更进一步的**语义重构**模式。实测 2026-08-21：63 个 class+theorem 文件经 Qwen3.5 语义重构后 **63/63 编译通过**，185 个裸 class 文件确定性删除。

## 核心失败模式：class X 重定义 vs mathlib 全局定义

mechfix 给所有文件加了 `import Mathlib` 后，凡重新定义 mathlib 已有类型类的文件报 **`X has already been declared`**。

**可编译判据**：文件能编译 ⟺ **不重新定义 mathlib 已有的类型类/结构**。
- ✅ 直接引用 mathlib 类型类（`[Group G]`/`[CommRing R]`）+ mathlib 定理
- ✅ 定义全新名字的结构（`structure LienardSystem`）
- ❌ `import Mathlib` 下重定义 `class Group`/`Field`/`Ideal`/`Ring` → "already been declared"

## 三类文件 + 三种处理

| 类别 | 特征 | 处理 |
|------|------|------|
| 裸 class 定义（无 theorem）| 只有 `class Group ...` | **确定性删除** class → 注释指向 mathlib（`-- mathlib already has X (Mathlib.Algebra...)`）|
| class + theorem | `class X` + 定理/实例用它 | **Qwen3.5 语义重构**：删 class + 定理改 `[X]` 类型类 |
| 新名结构 | `structure LienardSystem` 不冲突 | 保留 |

## Qwen3.5 语义重构配方（实测 63/63 通过）

1. 分批发送（每批 ≤17 文件，避免截断），prompt 明确规则：
   - 删除重定义 `class X`；定理/实例改用 mathlib 类型类
   - **ℕ 是加法 → 用 `AddSemigroup` 不是 `Semigroup`**
   - 保留不冲突的新定义；删除与 mathlib 同名的冗余引理
   - 输出格式 `### 文件名\n```lean\n<内容>\n``````
2. **孤儿 doc 注释坑（必查）**：Qwen3.5 常留 `/-- ... -/` doc 注释后面跟 `--` 普通注释（非声明），Lean 报 `unexpected token '/--'; expected 'lemma'`。修复：应用后统一 `txt.replace('/--', '/-')` 转普通注释。
3. 编译验证：`lake env lean <file>.lean`（每文件 ~60-90s，mathlib import 慢），失败文件 grep error 分流。

## 关键陷阱

1. **陈旧 .olean ≠ 当前可编译**。mechfix 加 `import Mathlib` 之前 `lake build` 出的 .olean 是陈旧的——原来自包含的 `class Group` 文件在加 import 后反而编译失败（"already been declared"）。判断真实可编译集必须**实际重编译验证**，不能信旧 build 产物。
2. **mechfix 破坏 lakefile.lean**。fix_import 把 lakefile 的 `import Lake` 错改成 `import Mathlib`，导致 `lake build` 报 `unknown namespace Lake` 完全无法运行。修复：改回 `import Lake`。批量修复脚本要排除 `lakefile.lean` 与 `.lake/` 目录。
3. **grep 找候选**：终端无 rg 时用 `grep -rlE '^class (Group|Field|Ideal|Ring|Semigroup|Monoid|Module|VectorSpace|AbelianGroup|OrderedField)\b' --include='*.lean' .`（Windows/MSYS 用 conda python + 写文件到项目目录，别写 /tmp，native python 读不到 MSYS /tmp）。
4. **编译串行**：多个 `lake env lean` 并行会争抢同一 mathlib olean 卡死，必须串行（后台脚本逐个 subprocess.run）。

## 复用脚本骨架

```python
# 确定性删裸 class
def refactor_class(txt):
    lines = txt.split('\n'); out = []; skipping = False; cls_name = ''
    for l in lines:
        if not skipping:
            m = re.match(r'^(class|structure)\s+(\w+)\b', l)
            if m: skipping = True; cls_name = m.group(2); continue
            out.append(l)
        else:
            if l.strip() == '' or l[:1] in (' ','\t'): continue
            skipping = False; out.append(l)
    result = '\n'.join(out)
    comment = f"-- [refactor] mathlib already has `{cls_name}`; redefinition removed."
    return result.replace('import Mathlib', 'import Mathlib\n' + comment, 1), cls_name
```
