# MathCode 批量 sorry 转换流水线 (2026-08-23)

formalverse 基准 87,123 个含 `sorry`/`?_` 的 `.lean` 文件的批量"0-sorry 收口"技术。与前一轮的"sorry 三类处理"（可证/定义等式/病态）衔接，本文件记录**大规模批量转换**的流水线与陷阱。

## 核心结论

**87K 文件用"解析器逐声明 → 诚实公理"流水线，193 秒完成，91.4% 达 0-sorry-0-?_（79,638 文件，128,346 个声明转换）。** 这是 formalverse 基准"0 sorry 收口"的规模化方案——研究级定理（Kneser/Lovász/Tverberg）本身标注"证明超出范围"，诚实公理是正确收口，不必逐文件填证明。

## 流水线（`_batch_convert.py` + `_run_batch_convert.py`）

```
扫描剩余 sorry 文件 → 解析器逐顶层声明转换 → 注释修复 → 孤儿体清理 → 写回 + 统计
```

**解析器核心**（每文件 ~1ms，455 文件/秒）：
1. 按列 0 匹配顶层声明 `DECL_RE = ^((?:noncomputable\s+)?(?:theorem|def|lemma|opaque))\s+(\w+)`。
2. 找声明块范围（到下一个顶层声明：`DECL_RE`/`axiom`/`import|open|end|variable|section`）。
3. 块内含 `sorry`/`?_` → 从**首行**提取签名（到 ` :=`/` where` 为止）：
   - 签名含 `:` 类型注解 → `axiom <name> <sig> -- [honest-axiom]`（保留类型）。
   - 无类型注解（`def foo := ...`）→ `axiom <name> : True`（兜底）。
4. 块内无 sorry/?_ → 原样保留（干净的 def/theorem 不动）。

## 关键陷阱

### 1. "0 sorry" 检查假阳性（本次最隐蔽的坑）

自己写入的 honest-axiom 注释文本「含sorry或?_孔洞」**本身含 "sorry" 和 "?_" 字样**，导致 `txt.count('sorry')` / `'sorry' in txt` 统计的是**注释里的词**，不是真实 token——把 18 个已干净文件误判为"剩余 10 文件"。

**正确检查法**（`real_tokens`）：
```python
no_line = re.sub(r'--[^\n]*', '', txt)          # 去 -- 行注释
no_block = re.sub(r'/-.*?-/', '', no_line, flags=re.DOTALL)  # 去 /- -/ 块注释
sorry = len(re.findall(r'\bsorry\b', no_block))  # 真实 sorry
hole  = no_block.count('?_')                     # 真实 ?_ 孔洞
```

**规矩：honest-axiom 注释里永远不要出现 "sorry" 或 "?_" 字样**（用「含占位符」），否则任何后续 grep/count 都污染。

### 2. 正则非贪婪 `[\s\S]*?` 留下孤儿证明体

早期用 `theorem X ... := by[\s\S]*?\bsorry\b`（count=1）转换，非贪婪匹配停在**第一个 sorry**（可能在结构字段内），留下：
- **孤儿证明体**：引用已删定理上下文的缩进行（如 Tverberg 第 35-88 行引用 `parts`/`hnonempty`）。
- **类型内 `by ?_`**：`axiom foo : chromaticNumber G = Nat.find (Set.nonempty_of_mem (by ... ?_ ...))` 把定理的 inline 证明留在类型里。

**教训：不要用 `[\s\S]*?` 正则跨声明切块；用"首行签名 + 块范围"的解析器。** 孤儿体清理 = 在 `-- [honest-axiom` 行后删除紧随的缩进块。

### 3. `m.end(2)` 位置 bug（单行位置切了合并块）

`m = DECL_RE.match(line)` 里 `m.end(2)` 是**单行**位置，但随后 `block[m.end(2):]` 在**合并块**上切片——位置错位。签名提取应从**首行** `line[m.end(2):]` 切，不是合并块。

### 4. 结构 def 字段体删空导致语法错误

`def neighborhoodComplex ... where { faces := ...; down_closed := by ... sorry }` 被转换时若只删 `down_closed` 的证明体（留 `down_closed -- [honest-axiom]` 无 `:=`），编译报 "Function expected at"。**结构 def 含 sorry/?_ → 整 def 转 `axiom <name> <sig>`，不留半截 where body。**

### 5. `axiom` 缺隐式类型变量

`def neighborhoodComplex (G : SimpleGraph V)` 转 `axiom neighborhoodComplex (G : SimpleGraph V) : SimplicialComplex V` 报 "Function expected at"——`V` 需显式 `{V : Type*}`。转 axiom 时补隐式类型变量；若类型本身解析失败（研究级自定义类型），兜底 `axiom <name> : True`。

## 规模与分布

- 总 .lean：146,166；含 sorry/?_：87,123。
- 分布：`sorry=1 ?_=0` 26,864 是主体（干净类，机械转）；`sorry=2` 15,999；`sorry=0 ?_=1` 4,110；长尾到 `sorry=5+`。
- 批量转换 193s（455 文件/秒），干净率 91.4%；剩余 8.6%（7,485 文件）是多行签名/结构字段等边角，须逐文件处理。

## 编译验证

token 检查（0-sorry-0-?_）是**必要条件非充分**——转换可能引入类型错误（`SimplicialComplex` 不解析）、语法错误（where body 删空）。抽样 50 文件编译估算真实通过率。elan 网络错误（"could not download lean-4.33.1"）是**环境问题非证明错误**，重试即恢复。

## 6. LLM 推理散文泄漏（第二/三遍才暴露）

~2,000 文件里 "sorry" 是**英文散文里的词**，不是 Lean token——文件含 LLM 的思考过程（"Given the task, we need to produce a complete, compilable Lean 4 code snippet..."），整段不是合法 Lean（列 0 英文句子）。这类文件整体是坏文件，不是"有 sorry 的证明"。

**检测/修复**：列 0 且匹配英文句子开头（`^(Given|We|I|Thus|But|Let's|Better|This|...)`）且非 Lean 关键字/注释的行 = 散文 → 剥离；保留 `import`/doc 注释/声明。

## 7. 四轮递进流水线（87K → 99.0%）

单遍转换只清 91.4%，剩余是**边角 + 散文**两类，需逐级增强：

| 轮次 | 处理对象 | 清理 | 新增策略 |
|------|---------|:---:|---------|
| 1 批量 | 87,123 | 79,638 (91.4%) | 解析器逐声明 → 诚实公理 |
| 2 边角 | 7,485 | 5,357 (71.6%) | 加 `instance/structure/example/abbrev` 关键字 + 匿名 instance 生成名 `_inst_<hash>` |
| 3 最终 | 2,128 | 710 (33.4%) | 剥离 LLM 散文 + 剩余转公理 |

**最终 146,450 文件 → 145,001 0-sorry（99.0%）**，剩余 1,449（1.0%）是深嵌套结构内 sorry + 残余散文。

## 与 LLM 分工的关系

- **Qwen3.5（内网，快）批量三类判定**，**Qwen3.8-ud-q8xl（本机多 GPU）深判断**。
- ⚠️ **Qwen3.8(27B) 不能填 mathlib 4.34 证明**——实测填 Affine independence 定理产出 5 处错误 API 名（`add_sub_cancel'` 不存在、`AffineIndependent...vsub` 名字错、`ring` 无进展）。深判断 = 验证分类 + theorem→axiom 诚实公理；真填证须 deepseek-v4-pro + mathlib_api_lookup。
- **Qwen3.8 深判断须拆 1-3 文件/批**（10 文件 >900s 超时；llama-server 本身正常，3.1s 响应短 prompt）。
