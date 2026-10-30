# 公理自相矛盾（Ex Falso 爆炸原理）检测与修复

2026-08-17 CGICE V9.1 修复沉淀：三轮终审反复暴露"0 sorry 但公理互相矛盾"比可见 sorry 更危险（虚假的"已验证"信心）。

## 1. 爆炸原理（Ex Falso Quodlibet）的代数根源

当一组公理联合推导出 `X = Y` 与 `X ≠ Y` 同名冲突时，Lean 可证 False，所有后续定理证明逻辑归零。典型：

```
CON-1: A6 (I_cycle = V_eff·2π/λ₁) + A10 (V_eff·2π/λ₁ = I_eq) + A4 (λ₁=35/3)
       ⟹ I_cycle = I_eq
       A17 (∀t, I_cycle ≠ I_eq) ⟹ I_cycle ≠ I_eq
       → A=B ∧ A≠B 矛盾
CON-2: A9 (I_cycle(0) = I_eq) + A17 (∀t, I_cycle ≠ I_eq) → t=0 处矛盾
```

深层病理：作者意识到 A6/A10/A4 会把系统约束为静态平凡解（dI_cycle/dt=0），于是追加一条否定平凡解的矛盾公理（A17）强行注入动力学——这是最错误的形式化手段。

## 2. 修复模式（CGICE V9.1 验证）

| 步骤 | 操作 | 理由 |
|---|---|---|
| 1 | **废除矛盾公理**（A17 全局不等式）| 自洽系统必须容许平衡解存在 |
| 2 | **降级冗余公理为 def**（A10 → noncomputable def I_eq）| I_eq 是代数组合定义，非独立公理 |
| 3 | **释放被绑定的动力学泛函**（废除 A6，I_cycle 释放为自由泛函）| 非平凡动力学应由主方程驱动，非代数绑定 |
| 4 | **修正初始条件为非平凡**（A9: I_cycle(0)=I_eq → ≠I_eq）| 系统从偏离平衡态出发，由主方程弛豫到平衡 |
| 5 | **确立主方程为唯一动力学驱动器**（A16 保留）| dI_cycle/dt = -(λ₁/2π)(I_cycle-I_eq) |

结果：axiom 数 63 → 60（废除 A6/A10/A17），编译 0 sorry，不再可证 False。

## 3. 符号冲突的语境分离（A16 vs A22）

两个公理对同一量 `deriv I_cycle` 给出矛盾方向（A16 负号弛豫 vs A22 正号反弛豫），但 Lean 不爆炸（A22 是双向蕴含 ↔，Q 端无约束）。

解决：**语境分离声明**——A16 是唯一动力学驱动器（弛豫），A22 是 Legendre 对偶公设（共轭变量关系，其左端不是实际主方程），两者不联立。在 Lean 注释 + MD 正文明确声明。

## 4. 反对称×对称缩并为零的额外假设（T4 诚实发现）

试图证明 `Σ_{μν} f^k_{μν} A^μ J^ν = 0` 仅凭 f_antisymm（f^k_{μν}=-f^k_{νμ}）：

- S=-S 论证在交换指标后得到 `Σ f^k_{μν} A^ν J^μ`，而 `A^ν J^μ ≠ A^μ J^ν`（A 与 J 是独立场）。
- 反例：f(0,1)=1, f(1,0)=-1, A(0)=J(1)=1, A(1)=J(0)=0 → Σ=1≠0。

**结论**：S=-S→S=0 需额外 `A^μ J^ν = A^ν J^μ`（平行规范 A∥J，Abelian 条件）。必须把该桥接假设显式声明为 axiom 并文档化，而非隐藏结论。这是"反对称张量与独立张量缩并"与"反对称张量与对称张量缩并"的本质区别——后者 `Σ f X X` 才可仅凭 f_antisymm 证明为零（纯 S=-S）。

## 5. Stage 3.5 一致性审计门（六类 P0）

`scientific-discovery-proof` 技能 v2.9.0 已整合 `scripts/proof_consistency_audit.py`，检测：

1. 公理自相矛盾（爆炸原理）🔴 BLOCK — 提取等式链检测 X=Y 与 X≠Y
2. 表演性诚实（注释标签 vs 真实 attribute）🟡 WARN — `real_attrs`（行首 @[）vs `comment_attrs`（-- @[）
3. 公理/定理计数不一致 🟡 WARN — `grep -c '^axiom '`（排除注释）vs 论文声称
4. 定理虚假声称（幻影定理）🔴 BLOCK — 论文 "theorem X" vs Lean 存在性
5. 空壳证明（:= by trivial / := True / admit）🟡 WARN
6. 离散谱 vs 连续谱（非紧空间类别错误）🔴 BLOCK — 关键词 "λ_k=k·λ" + "非紧"

独立运行：`python scripts/proof_consistency_audit.py --lean proof.lean --paper paper.txt --expected-axioms 14`

## 6. 数值断言公理 = 循环论证

把答案写成公理（`H0_analytic_derivation : H0 = 67.42`）不是"first-principles 解析推导"，是循环论证。61 axiom 中 ~5 个是数值断言（H₀/N_e/Ω_DE），~30 个是占位符号（无定义自由函数），真实内容公理仅 ~26。诚实化：把 "analytic derivation" 改写为 "phenomenological calibration（数值断言公理）"。
