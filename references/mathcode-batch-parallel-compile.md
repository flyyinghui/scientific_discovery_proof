# MathCode 批量编译: 并行化 + 边缘文件清理 (2026-08-23)

全库 146,450 文件 100% 0-sorry-0-?_ 之后的两个收尾技术。前置参考 `mathcode-batch-sorry-to-axiom-pipeline.md`（六轮流水线）。

## 1. 并行编译 `lake env lean`（串行 107s/文件 → 并行 ~20×）

`lake env lean <file>` 是**独立 type-check**（不产出 .olean、无输出竞争、无共享锁），文件间完全独立，可跨 CPU 核并发。

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
def compile_one(f):
    r = subprocess.run(['lake','env','lean', os.path.join(lib,f)], capture_output=True, text=True, timeout=180)
    errs = [l for l in r.stderr.split('\n') if 'error:' in l]
    if not errs: return (f, 'OK', '')
    e0 = errs[0] if errs else ''
    if 'could not download' in e0: return (f,'NETWORK',e0[:60])
    if 'unknown identifier' in e0 or 'unknown constant' in e0: return (f,'UNKNOWN_ID',e0[:60])
    if 'synthInstanceFailed' in e0 or 'typeclass' in e0: return (f,'TYPECLASS',e0[:60])
    return (f,'OTHER',e0[:60])

with ThreadPoolExecutor(max_workers=20) as ex:  # 80 逻辑核 → 20-40 worker
    for fut in as_completed({ex.submit(compile_one,f): f for f in files}):
        ...  # 结果分类
```

要点：
- 用 `ThreadPoolExecutor`（不是 ProcessPool）——实际 CPU 工作在被调起的 `lean` 子进程里，线程只做调度。
- worker 数 = min(核数/2, 内存GB/2)。每个 `lean` 进程 ~1-2GB（加载 mathlib olean）。
- **TIMEOUT 是编译慢，不是证明错误**——个别复杂文件（如 Harnack 型）超 120s，须单独用更长 timeout 重试才能区分。
- 实测：50 文件抽样 49/50 = 98% 真实编译通过（1 个 TYPECLASS 失败是转换副产物——axiom 类型里留了 `by ?_` 型 class 空洞）。
- 全库 146K × 107s 串行 ≈ 180 天；20 worker ≈ 9 天。抽样验证替代全量编译是唯一可行路径。

## 2. 边缘文件清理（六轮之后仍含 sorry/?_ 的 0.2%）

正则解析器把顶层声明转 axiom 后，剩余边缘文件按**关键字遗漏**顺序清理，每补一个关键字清一批：

| 边缘模式 | 示例 | 修复 |
|---------|------|------|
| **`class` 关键字遗漏**（最易漏） | `class MarkovProcess ... where { field := ... sorry }` | DECL_RE 加 `\|class`，且 step-3 的 `if '...' in m.group(1)` 条件**也要**加 `'class'`（两处都要改，漏一处=0 命中）|
| **LLM 推理散文泄漏** | 文件含 "Given the task, we need to produce..." 英文推理，"sorry" 是英文词非 Lean token | 激进散文剥离：列0 + 英文特征词(the/we/can/since/because...) + 非 Lean 关键字 → 删行；保留 import/open/doc/声明 |
| **`@[attribute]` 前缀** | `@[simp] axiom ι_mul ... := by sorry` | 剥 `@[...]` 前缀再匹配声明 |
| **axiom 类型内 `by sorry`** | `axiom f (⟨V, by sorry⟩) ...` | 整个 axiom 简化 `axiom name : True` |
| **`notation`/`variable` 声明** | `notation "f" A => functionalCalculus f A (by sorry)` | 删含 sorry 的 notation 行 / variable 行 |

**`class` 关键字是最易漏的**——MarkovProcess/DModule/ColoredOperad 等 typeclass 都是 `class ... where`，不在 `theorem|def|lemma|instance|structure` 列表里。加 `class` 后一个文件就清 395/1360。

## 3. "0-sorry" 假阳性检查铁律（统计前必做）

honest-axiom 注释文本若含 "sorry"/"?_" 字样，`txt.count('sorry')` 会把注释词当 token 统计，把已干净文件误判为"剩余"。**检查前必须剥注释**：

```python
no_line = re.sub(r'--[^\n]*', '', txt)
no_block = re.sub(r'/-.*?-/', '', no_line, flags=re.DOTALL)
sorry = len(re.findall(r'\bsorry\b', no_block))
hole = no_block.count('?_')
```

或直接把 honest-axiom 注释写成不含 "sorry"/"?_" 字样（如「含占位符」）。
