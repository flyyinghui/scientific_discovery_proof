# flash 生成 Lean 证明 → 5 轮编译迭代收敛模式

> 来源：2026-09-13 三大时空相论文五个开放问题（§5.5/§5.9/§8.4/§5.6/§7）的形式化证明实战。
> 管线：v4-pro 生成 ≥10 策略 → 选定最优 → deepseek-flash 生成 Lean → 编译迭代 → 0 sorry → 回填论文。

## 触发条件

用户要求对论文开放问题「逐项开展形式化证明补充完整证据链，每个 ≥10 种论证策略，
选择证据链最完善且与论文物理诠释关系最密切的完善并编译成功 0 sorry，再逐条补充到论文」。

## 完整工作流（7 步）

1. **激活大脑 + 确认 API**：brain.recall() 召回关键概念；`deepseek-flash`（用户口语称 v4.1-flash）
   与 `deepseek-v4-pro` 是当前 DeepSeek API 仅有的两个有效模型名。
   - v4-pro 默认 thinking 模式：推理在 `reasoning_content`，结论在 `content`；
     用 `getattr(msg, 'reasoning_content', None)` 或 `msg.model_extra.get('reasoning_content')` 提取。
   - flash 生成 Lean 必须 `extra_body={"thinking":{"type":"disabled"}}`，否则 content 为空。
2. **策略生成（v4-pro thinking）**：每问题一个 prompt，要求 ≥10 种策略，
   每种含「数学路径/可形式化程度/honest-axiom 数量/证据链完整度/物理契合度/关键风险」+ 排序前 3。
   实测：p1 完整 12 策略、p2/p4 被 max_tokens 截断、p3 content 空（全进 reasoning）——
   但 reasoning 里已有排序表，可从 reasoning 提取或接受。
3. **选定方案**：按「证据链完整度 × 物理契合度」乘积，通常 72-90 分者入选。
4. **flash 生成 Lean（每问题一个 namespace）**：prompt 明确要求 0 sorry、honest-axiom 显式声明、
   定理体真实推理（ring/nlinarith/field_simp/norm_num）、禁止 `:= by trivial`/`:= True`。
5. **合并 + 一次编译**：把 N 个 namespace 合并成一个文件（去掉各自 import），
   一次 `lake env lean` 编译全部——省去 N 次 mathlib 加载（每次 6-10 分钟）。
6. **迭代修复（典型 5 轮，13→4→3→3→0）**：见下方陷阱清单。
7. **合并进主 Lean + 回填论文 + 交叉审计**：审计 = grep 论文引用的定理名在 Lean 中存在 +
   数值一致性（关键常数出现次数对齐）。

## 编译环境

```bash
cd ~/Desktop/papers/cgice   # 借用 CGICE 的 mathlib（12GB olean 已编译）
export PATH=/root/.elan/bin:$PATH
export HOME=/root   # 关键：后台进程 HOME 未设置会报 `/.local/bin/env: No such file or directory`
lake env lean /path/to/proof.lean
```
- Lean 4.34.0-rc1 + mathlib。每次编译 6-10 分钟（mathlib olean 加载是固定成本，与文件大小无关）。
- 后台进程必须 `export HOME=/root`，否则 lake env 的 shim 找不到 `~/.local/bin/env`。

## flash 生成 Lean 的 13 个高频陷阱（本次实战全部踩过）

### 数学正确性 bug
1. **矩阵列和不守恒**：flash 生成的转移矩阵 A 第三列和 = −Γ_b2DM ≠ 0，总质量不守恒。
   守恒要求「每列的流入 = 流出」，即列和 = 0。修复：重写 A 使每列和为零，
   然后 `act_total_zero` 的 ring 才闭合。
2. **结构体默认值字段陷阱**（最隐蔽）：`structure S where g : ℝ := default`，
   对任意 `s : S`，`s.g` **不必然**等于 default——默认值只对「未显式给 g」的构造成立。
   任何依赖 `s.g = default` 的证明对任意 s 都是错的。修复：去掉默认值字段，
   g 用独立函数 `f s := ...` 计算，定理直接用函数值。

### 结构性问题（表演性诚实 / 空壳，Stage 3.5 要拦截的 P0-2）
3. **flash 自定义宏与 HonestAttr 冲突**：flash 会自己定义 `class HonestAxiom (P : Prop)` +
   `honest_axiom` syntax/macro，与 HonestAttr.lean 的 TagAttribute 冲突。
   必须删除自定义宏，统一用 `@[honest_axiom] axiom ...`。
4. **`:= 0` 空壳定义**：PiTT/hTT/Sh 全被定义成恒等于 0，使"各向同性零定理"沦为 trivial。
   修复：改 `opaque` + `@[honest_axiom] axiom` 声明性质（如 `PiTT_isotropic_zero`）。
5. **`honest_axiom ... : True` 占位**：用 True 填充的 axiom 是表演性诚实。
   必须声明有实际数学内容的前提（如 `callias_index_absolute_value : calliasIndexAbs = 1`）。
6. **`@[honest_axiom]` 标记 def**：标记应给 axiom，不是 def。函数用 `opaque` 或普通 `def`。

### 语法/顺序/类型问题
7. **引用顺序**：`axiom lambda_pos` 引用了后面才定义的 `lambdaFn`。先定义被引用者。
8. **恒真空壳字段**：`xpos : ∀ x, 0 < x → True` 恒真，删除。
9. **sq_lt_sq.mpr 用法**：输入是 `|a| < |b|`（非 Or），且 a,b 需非负才能去绝对值。
   正确：`apply sq_lt_sq.mpr; rw [abs_of_pos hpos1, abs_of_pos hpos2]; exact h`.
10. **`right` 对非 Or 目标失败**：`right` 只对 Or 目标有效，误用于 sq_lt_sq 会报
    "target is not an inductive datatype"。

### 策略失败（field_simp / norm_num / positivity / ring）
11. **`by positivity` 在 `lam/4` 上失败**：改用 `div_nonneg (le_of_lt lam_pos) (by norm_num)`。
12. **norm_num / field_simp 报 "failed to prove positivity"**：对 ℝ 除法 `(-3/2)` 或 `-mu2/lam`
    处理失败。两种解法：①先证「具体值中间引理」（如 `phiStar_sq_value : phiStar^2 = 3`，
    把 sqrt 消掉），再 `norm_num [mu2, lam]`；②直接 `ring_nf`（field_simp + ring 的规范化）。
13. **ring 多余（No goals to be solved）**：`norm_num + field_simp` 后目标已闭合，
    再 `ring` 报 No goals。删 ring 或改 `ring_nf`（ring_nf 对已闭合目标也报 No goals，慎用）。

## 编译迭代收敛（本次实测）

| 轮次 | 错误数 | 主要修复 |
|---|---|---|
| 1 | 13 | 矩阵守恒 bug、宏冲突、空壳定义、引用顺序、sq_lt_sq、field_simp |
| 2 | 4 | field_simp、sq_lt_sq 类型、EC.ind 重写 |
| 3 | 3 | norm_num positivity、change 失败 |
| 4 | 3 | positivity、ring 多余、结构体默认值 |
| 5 | **0** | 最后 3 处细节 |

关键经验：**flash 一次生成的代码平均 13 个错误，5 轮收敛到 0**。每轮只修「本轮暴露的错误」，
不要预防性大改（会引入新错误）。0 sorry 贯穿始终（flash 用 thinking disabled 不会写 sorry，
但会写 `:= 0`/`:= True` 空壳和自定义宏，这才是真正要拦截的）。

## 验证清单（编译通过后）

1. `grep -c "error"` = 0 且 `grep -c "sorry\|admit"` = 0（排除注释后）
2. 论文引用的每个定理名 `grep -c "^theorem X\|^lemma X\|^axiom X"` 在 Lean 中 = 1
3. 数值一致性：关键常数（g_TC²=24π²/35、f=47/547 等）在 Lean 与论文出现次数对齐
4. honest-axiom 计数 = 研究级前提数，无 True/:=0 占位
5. Stage 3.5 L1 审计：无公理自相矛盾、无幻影定理、无空壳证明

## 关键命名约定

- 每个开放问题一个独立 namespace（`VEV123CW`/`SourceQ`/`FredholmThree`/`DMAbundance`/`GWTT`）
- 研究级前提：`@[honest_axiom] axiom <name> : <有内容的 Prop>`
- 真证明：`theorem <name> : ... := by <forward tactic>`（ring/nlinarith/field_simp/norm_num/calc）
- 论文回填用 `**[Formal proof — YYYY-MM-DD]**` 段，列出关键定理名 + honest-axiom 边界
