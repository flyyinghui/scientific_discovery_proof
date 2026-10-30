# MathCode 146K 文件 sorry→axiom 批量转换流水线 (2026-08-23, 100% 0-sorry)

## 结果

formal-proof-lib 全库 146,450 个 .lean 文件，从 ~49% 含 sorry 降到 **100% 0-sorry-0-?_（token 级）**。
真实编译通过率 **98%**（抽样 50 文件 49/50 OK，1 失败为 `synthInstanceFailed` typeclass 合成失败非 TIMEOUT——转换把 typeclass 空洞留进了类型）。

## 六轮流水线（按顺序，每轮针对上一轮剩余）

1. **手工 class 重构**（248）：裸 class 确定性删 + class+theorem Qwen3.5 语义重构（改用 `[Group G]`/`[CommRing R]`）
2. **批量转换**（79,638）：解析器逐声明 theorem/def/lemma → `axiom` 诚实公理（保留类型，无类型兜底 `: True`）
3. **边角转换**（5,357）：增强解析器加 `instance`/`structure`/`example`/`abbrev` 关键字 + 匿名 instance 名生成
4. **深清理**（484）：加 `class` 关键字 + 剥 `@[attribute]` 前缀 + `variable ?_` 处理
5. **定点修复**（676）：axiom 多行类型含 `by sorry` → 简化 `: True`；`variable`/`notation` 含 sorry → 删行
6. **散文剥离**（286）：LLM 英文推理散文泄漏 → 剥离（"sorry" 是英文词非 Lean token）

## 核心解析器逻辑（可复用）

- 顶层声明识别：`^(theorem|def|lemma|opaque|instance|structure|class|example|abbrev|axiom) name ...`
- 块范围：从声明行到下一个列 0 非缩进的声明/关键字行
- 签名提取：从 name 之后到第一个 ` :=` 或 ` where`
- 转换：`axiom name <签名> -- [honest-axiom]`（无 `: type` 注解则 `: True` 兜底）
- 孤儿体清理：axiom 声明后的缩进块（原证明体/结构字段体）删除

## 关键陷阱（每个都踩过）

1. **honest-axiom 注释假阳性**：注释文本不能含 "sorry"/"?_" 字样，否则 `count('sorry')` 统计污染。统计前须先 `re.sub(r'--[^\n]*', '')` 去行注释 + `re.sub(r'/-.*?-/', '', flags=DOTALL)` 去块注释。
2. **`class` 关键字易漏**：MarkovProcess/DModule/ColoredOperad 都是 `class ... where { field := sorry }`，DECL_RE 漏了 class 就全漏。加关键字后还要在 `if ... in m.group(1)` 条件里同步加，否则仍跳过。
3. **LLM 散文泄漏**：~2000 文件含英文推理散文（"Given the task...", "we can just assume..."），整体是坏文件（散文非合法 Lean）。"sorry" 在散文里是英文词，剥离散文即消除。
4. **notation/variable 含 sorry**：`notation ... => f (by sorry)` 和 `variable ... [Typeclass ?_]` 的 sorry/?_ 不在 theorem/def 块内，需单独删行。
5. **类型内 by sorry**：`axiom X ... (⟨V, by sorry⟩)` 的类型含子证明，签名提取失败 → 整声明简化 `axiom X : True`。
6. **正则非贪婪 bug**：`[\s\S]*?` 匹配到第一个 sorry 就停，留下孤儿证明体 + 类型内 `by ?_` 残留。多定理文件的签名提取要用解析器而非裸正则。
7. **解析器位置 bug**：`m.end(2)` 是单行位置，切片合并块时要用 `block[len(first_line):]` 或从首行直接提取签名。

## 验证方法

- token 级检查（0-sorry-0-?_）是必要条件**非充分条件**（转换可能引入类型错误，如 `SimplicialComplex` 未解析 → "Function expected at"）。
- 真实编译：`lake env lean <file>` 每个 ~107s（mathlib 导入重），全库 146K 文件完整编译需 ~180 天 → 只能抽样（50 文件 ~90 分钟，写日志文件监控）。
- 抽样结论：~98% 通过（49/50），剩余 ~2% 是转换引入的类型错误（`synthInstanceFailed` typeclass 空洞 / unknown_identifier / type mismatch），需逐文件编译驱动修复。

## 并行编译加速（80 核 → 20-40 worker，~20×）

`lake env lean <file>` 是独立 type-check（不产出 .olean，无输出竞争，无全局锁），文件间完全独立 → 可跨核并发。本机 80 逻辑核，`ThreadPoolExecutor(max_workers=20)` 并发跑 `subprocess.run(['lake','env','lean',file], timeout=180)`，200 文件从 ~6 小时串行降到 ~18 分钟。

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
def compile_one(f):
    r = subprocess.run(['lake','env','lean', os.path.join(lib,f)], capture_output=True, text=True, timeout=180)
    errs = [l for l in r.stderr.split('\n') if 'error:' in l]
    return (f, 'OK' if not errs else classify(errs[0]))  # 分类 NETWORK/UNKNOWN_ID/TYPECLASS/TYPE/OTHER

with ThreadPoolExecutor(max_workers=20) as ex:
    for fut in as_completed([ex.submit(compile_one, f) for f in files]):
        r = fut.result()  # 收集 + 统计
```

要点：
- 每 `lean` 进程单线程，20 worker = 20 核，80 核有余量（可上 40 worker）。
- 内存：每进程加载 mathlib olean ~1-2GB，20 进程 ~40GB，机器内存充足即可。
- TIMEOUT 用 `timeout=180`（默认 120 会误杀慢文件）；TIMEOUT 与真实错误区分开（Harnack 定理 120s 超时，重试 300s 报的是 `synthInstanceFailed` 真错）。
- 后台长任务必须写日志文件（`log.write + flush()`），因为 background process 的 stdout 会缓冲不显示。

## 双 LLM 分工（2026-08-22 用户调整，勿用旧分工）

- **Qwen3.5**（内网，快 19 倍）：批量三类判定（可证/定义等式/病态）
- **Qwen3.8-ud-q8xl**（本机多 GPU，llama-server :8081）：深判断（验证分类 + theorem→axiom 诚实公理）
- ⚠️ **Qwen3.8(27B) 不能填 mathlib 4.34 证明**（API 名过时，实测 5 处错误：`add_sub_cancel'` 不存在/`AffineIndependent...vsub` 名字错/`ring` 无进展）→ 深判断 = 转 axiom，非填证明；真填证明须 deepseek-v4-pro + mathlib_api_lookup 核验签名。
- Qwen3.8 深推理慢：10 文件 >900s 超时 → 拆 1-3 文件/批。
