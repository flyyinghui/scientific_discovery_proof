# formal-proof-lib 批量 sorry 清理流水线 (2026-08-23)

formalverse benchmark 146,450 个 .lean 文件从 ~49% 含 sorry → **100% 0-sorry** 的六轮流水线。

## 六轮流水线（87,000+ 文件清理）

| 轮次 | 策略 | 清理量 |
|------|------|:---:|
| ① 手工 | Qwen3.5 批量三类判定 + 解析器 + 诚实公理 | 283 |
| ② 批量转换 | 解析器逐声明 theorem/def → axiom 诚实公理 | 79,638 |
| ③ 边角转换 | 增强解析器（instance/structure/匿名名生成）| 5,357 |
| ④ 深清理 | 加 `class` 关键字 + 剥 `@[attribute]` 前缀 | 484 |
| ⑤ 定点修复 | axiom 类型内 `by sorry` 简化 + variable/notation 删行 | 676 |
| ⑥ 散文剥离 | LLM 英文推理泄漏（"sorry"是英文词非 token）| 286 |

## 关键陷阱（按复发频率排序）

1. **honest-axiom 注释禁含 "sorry"/"?_" 字样**——`count('sorry')` 会统计注释里的词，产生假阳性（把 18 个已干净文件误判为"剩余"）。检查前必须先 `re.sub(r'--[^\n]*','')` + `re.sub(r'/-.*?-/','', flags=DOTALL)` 剥注释。
2. **`class` 关键字易漏**——MarkovProcess/DModule/ColoredOperad 都是 `class ... where { field := sorry }`，DECL_RE 必须含 `class`，且 step 条件里也要加 `'class' in m.group(1)`（两处都要）。
3. **LLM 散文泄漏**——~2,000 文件含 LLM 的英文推理散文（"Given the task, we need to produce..."），"sorry" 是散文里的英文词，整体是坏文件，需激进剥离（保留 import/open/doc/关键字行/缩进代码，删列 0 英文散文）。
4. **notation/variable 里的 sorry**——`notation "f" A => f A (by sorry)`、`variable (Γ) [Subgroup.Normal ?_]`，正则解析器不处理，需定点删行。

## 编译验证

- 抽样 50 文件: **49/50 OK (98%)**，1 失败 = typeclass 合成失败（转换副产物，非 sorry）
- 真实编译率 ~98%，token 级 0-sorry 是必要条件非充分（转换可能引入类型错误）

## lake env lean 并发（重要技术发现）

- 串行 ~107s/文件（其中 ~80s 是 mathlib 导入，~27s 才是文件编译）
- **20 worker 并发 → 0/200 全 TIMEOUT**（mathlib olean 13GB 每次重新导入 + 并发争用）
- 内存 511GB / CPU 80 核充足，**瓶颈是 mathlib olean 导入**，不是 CPU/内存
- 甜点约 4-8 worker；真正提速须 `lake build`（缓存 .olean 增量编译）或 `lean --server`（LSP 常驻，mathlib 导入只做一次）
- 结论：`lake env lean <file>` 每次重导 mathlib，不适合 naive 并发
