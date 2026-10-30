# Formal Proof Consistency Audit — 形式化证明自洽性审计清单

**版本**: 1.0 | **固化来源**: CGICE V9.1 / 三峰 V16 / V17 三轮终审 (2026-08-16)
**用途**: Stage 3.5 审计门 — 在 PPE 形式化证明完成后、AI-Scientist 论文生成前，对 Lean 4 证明做**自洽性 + 诚实性 + 数学正确性**三重审计。

---

## 为什么需要这个审计门

MathCode 三工具验证（`axiom_checker` / `proof_stats` / `sorry_analyzer`）只能回答：
- 有多少 axiom？（数量）
- 有多少 sorry？（占位符）
- proof_stats 的 has_sorry 是 true/false？

**它无法回答**（三轮终审反复暴露的致命问题）：
1. 这些 axiom 之间是否**互相矛盾**？
2. `@[honest_axiom]` 标签是真实 Lean attribute 还是**注释掉的文本**？
3. 论文声称的"14 公理"与 Lean 实际"39 axiom"是否一致？
4. 论文声称"fully verified"的定理，Lean 里是否**真的存在**？
5. 定理体 `:= by trivial` 是"证明"还是**空壳**？
6. 声称的"离散谱"在非紧空间上是否**数学上成立**？

---

## 六类 P0 检测模式

### 1. 公理自洽性（爆炸原理检测）— 最致命

**症状**：两条公理联立推出矛盾（如 `X = Y` 和 `X ≠ Y`），体系可证 False。

**案例（CGICE V9.1）**：
- A6: `I_cycle = V_eff·(2π/λ₁)` = `V_eff·6π/35`
- A10: `V_eff·(6π/35) = (35/3)(V_eff/Λ_CC)` = `I_eq`
- 联立 → `I_cycle = I_eq`
- A17: `I_cycle ≠ I_eq`（作者注释"防止平凡解"）
- **直接矛盾 → 爆炸原理下可证任何命题**

**更简单的独立矛盾（A9 vs A17）**：
- A9: `I_cycle 0 = I_eq`（初始条件）
- A17 取 t=0: `I_cycle 0 ≠ I_eq`
- **连 A6/A10 都不需要就矛盾了**

**检测方法**：
1. 提取所有 axiom 的**精确语句**（非注释）
2. 识别"同名量的等式链"：`X = expr1`、`expr1 = expr2`、... → 传递闭合
3. 检查是否存在 `X = Y` 与 `X ≠ Y` 同时出现
4. **关键**：`def` 定义的常量（如 `λ₁ := 35/3`）与 axiom 声明的等式（如 `λ₁ = 35/3`）会产生"定义相等"的隐藏链，必须展开 def 再判断

**修复原则**：让非平凡结论成为**推导结果**（作为某条动力学公理的解），而非追加矛盾公理硬撑。追加 `X ≠ Y` 来"防止平凡解"是最常见的错误——它直接把体系变成不自洽的。

---

### 2. 表演性诚实（注释标签 vs 真实 attribute）

**症状**：`@[honest_axiom]` / `@[phenomenological]` 标签全是 `-- @[...]` 注释掉的文本，真实 Lean attribute 行数为 0。论文却声称"declared as @[honest_axiom]"。

**案例（三峰 V16）**：26 处 `-- @[honest_axiom]` + 8 处 `-- @[phenomenological]`，全部是注释。编译语义上等于零，无法机器审计。

**检测方法**：
```python
# 真实 attribute（非注释）应匹配：行首就是 @[honest_axiom]
real_attrs = [l for l in lines if l.strip().startswith('@[honest_axiom')]
comment_attrs = [l for l in lines if '-- @[honest_axiom' in l]
# 若 real_attrs == 0 且 comment_attrs > 0 → 表演性诚实
```

**修复原则**：要么实现真实 Lean attribute（`@[honest_axiom]` + `#print axioms` 机器审计），要么论文明确写"在源码注释中文档化"，不声称"declared as attribute"。

---

### 3. 公理计数不一致（多口径互斥）

**症状**：摘要说 14、正文说 25、Lean 实际 39，三处互斥。

**检测方法**：`grep -c '^axiom ' file.lean`（排除注释行）得到真实计数，与论文所有声称数字逐一对比。

**案例**：CGICE V9.1 声称 "fourteen axioms"（§1）vs "twenty-five axioms"（摘要/结论）vs 实测 39。

**修复原则**：选定唯一口径 = Lean 实测数。区分"核心物理公理"（研究级前提）与"技术正则化公理"（可微性/非零性）时，用**两个显式计数**，不混用。

---

### 4. 定理存在性（声称 vs 实际）

**症状**：论文声称 "theorem t4 ... fully verified"，但 Lean 文件中**无此定理**（只有注释 "UNDER DEVELOPMENT"）。

**检测方法**：从论文提取所有 "theorem XXX" 声称，逐一 `grep -c "^theorem XXX" file.lean` 验证存在性。

**案例**：CGICE V9.1 的 T4 拓扑荷守恒——论文 §5.4/§A.4/§9 三处声称已形式化，Lean 只有注释。

**修复原则**：这是**学术不端级**问题（比 sorry 严重）。要么补证明，要么删除声称。

---

### 5. `:= by trivial` 空壳（假证明）

**症状**：定理体 `:= by trivial` / `:= by rfl`，或 `:= True` 占位，编译通过但零数学内容。

**案例**：DeepSeek v4-flash 生成 Lean 时，倾向给所有定理写 `:= by trivial`（对含数学内容的命题无法通过编译，但对 `True`/恒等式能通过）。

**检测方法**：
```python
grep -c ':=' by trivial' file.lean   # 空壳证明
grep -c ':=' True' file.lean          # 空壳命题
```

**区分**：`norm_num` 证明 `35 = 35` 是"算术恒等式"（合法但零内容）；`:= by trivial` 证明 `True` 是空壳。两者都应标注，但后者更严重。

---

### 6. 离散谱 vs 连续谱（数学错误）

**症状**：声称非紧对称空间上的 Laplace/Witten-Laplacian 有**离散谱** `λ_k = k·λ₁`。

**案例（CGICE V9.1 A3）**：SL(6,C)/SU(3,3) 是非紧空间（同胚于 ℝ³⁵），谱是**连续谱**（Plancherel 测度绝对连续），不存在离散本征值。即使取紧对偶，谱也由 Freudenthal 公式 ⟨μ+2ρ,μ⟩ 给出，非 k·λ₁。

**修复原则**：非紧对称空间的谱理论必须用 Plancherel 测度（连续），离散谱只对紧空间成立。混淆两者是**类别错误**。

---

## 审计门执行流程（Stage 3.5）

```python
# scripts/proof_consistency_audit.py
from proof_consistency_audit import audit

result = audit(lean_path, paper_path=None):
# 1. 提取 active axiom/theorem/lemma（排除注释）
# 2. 公理计数 vs 论文声称（若提供 paper）
# 3. 检测 := by trivial / := True 空壳
# 4. 检测表演性诚实（真实 attribute vs 注释）
# 5. 定理存在性（论文声称 vs Lean 实际）
# 6. 公理自洽性（等式链传递闭合 → 矛盾检测）
# 7. 输出 audit_report.json + 通过/阻断判定
```

**门控规则**：
- 公理矛盾（类型 1）→ **BLOCK**（可证 False 是阻断级）
- 定理虚假声称（类型 4）→ **BLOCK**
- 表演性诚实（类型 2）→ **WARN**（需论文措辞修正）
- 公理计数不一致（类型 3）→ **WARN**（需统一口径）
- `:= by trivial` 空壳（类型 5）→ **WARN**（需补充真实证明体）
- 离散谱错误（类型 6）→ **BLOCK**（数学类别错误）

---

## 一句话

**MathCode 三工具验证是"数数"，这个审计门是"查矛盾"——前者保证形式完整，后者保证逻辑自洽。** 三轮终审证明：一个 0 sorry 但公理互相矛盾的证明，比一个有 sorry 但自洽的证明更危险，因为前者会给人"已验证"的虚假信心。
