# CGICE 爆炸原理消除 + 公理重构五步法 + ODE/拓扑荷真证明

2026-08-17 会话沉淀：CGICE V9.2 公理体系重构 + T2/T4 真证明。可复用于任何"公理自相矛盾"的形式化论文。

## 1. 爆炸原理（Ex Falso Quodlibet）检测与消除

症状：公理体系内存在 `X=Y`（由 A6+A10+A4 联合推出）与 `X≠Y`（A17 直接声明）冲突，Lean 可证 False，所有定理证明归零。这类缺陷比可见 sorry 更危险——它给人"0 sorry = 已验证"的虚假信心。

**检测**：Stage 3.5 审计门（`scripts/proof_consistency_audit.py`）检测类 1——提取 axiom 等式链，找 `X=Y` vs `X≠Y` 同名冲突。

**消除五步法**（不可妥协的顺序）：

1. **废除矛盾公理**（如 A17 `∀t, X≠Y`）。物理系统必须容许平衡解存在；非平凡演化由初始微扰 + 非线性动力学驱动，不能靠"追加一条否定平凡解的矛盾公理"。
2. **降级绑定公理为 def**（如 A6 `I_cycle = V_eff·常数`）。把"演化公理"降级为"渐近定义"（noncomputable def），释放动力学变量为自由泛函。
3. **确立主方程为唯一演化驱动器**（如 A16 `dI/dt = -(λ/2π)(I-I_eq)`）。微分方程是生成权的绝对来源，不是代数恒等式。
4. **非平凡初始条件**（如 A9 `I(0) ≠ I_eq`）。偏离平衡态的初值 + 主方程弛豫 = 自然非平凡动力学。
5. **谱几何修正**（非紧空间）：自由 Laplace-Beltrami 在非紧对称空间上谱绝对连续（Harish-Chandra，阈值 |ρ|²），离散谱 λ_k=k·λ 只能来自 Witten Laplacian 在四次拓扑势阱 `V_eff=(λ₁/2)‖χ‖²+(g_TC/4)‖χ‖⁴` 的束缚态——不是自由算子的离散谱。

## 2. 线性 ODE 解析解的 Lean 真证明（T2 模式）

主方程 `dI/dt = -(λ/2π)(I - I_eq)` 的解析解 `I(t) = I_eq + (I₀-I_eq)·e^(-t/τ)`，τ = 2π/λ。

**Mathlib deriv 引理链**（真证明，0 axiom 0 sorry）：
```
deriv_const_add       → 常数偏移导数为零
deriv_const_mul_field → 常数乘法导数
deriv_exp (hdiff)     → exp 复合链式法则（需 DifferentiableAt，用 fun_prop）
deriv_const_mul_id    → 线性项 c·x 导数 = c
ring                  → 代数收尾
```

**三个坑**：
- **rate reducible def 被 simp 展开**：`rate = lam1/(2π)` 是 reducible def，`simp [deriv_exp hdiff]` 会自动展开成 `lam1·π⁻¹·1/2`，导致链式法则参数 `hdiff` 不匹配。改用 `simp only`（排除默认 simp 集）阻止展开。
- **除法求导**：把 `-t/τ` 改写成 `-rate·t`（`neg_div_tau_eq` 引理），用 `deriv_const_mul_id` 处理，回避商法则/除法可微性。
- **三种等价策略**：calc 逐项（最直白）/ simp only 一次性 / HasDerivAt 组合子（`.exp`/`.const_mul`/`.const_add`/`.deriv`），选一种编译通过即可。

## 3. 拓扑荷守恒：对称-反对称耦合的前提条件（T4 诚实发现）

目标 `Σ_{μν} f^k_{μν} A^μ J^ν = 0`（结构常数 f 反对称）。

**关键数学洞察**：仅凭 `f_antisymm`（f^k_{μν} = -f^k_{νμ}）**无法证明**双重求和为零。S=-S 论证在交换指标后得到 `Σ f^k_{μν} A^ν J^μ`，但 `A^ν J^μ ≠ A^μ J^ν`（A 与 J 是独立对象）。反例：`f(0,1)=1, f(1,0)=-1, A(0)=J(1)=1, A(1)=J(0)=0 → Σ f A J = 1 ≠ 0`。

**正确路径**：额外需要 `A^μ J^ν` 在 μ↔ν 下对称（平行规范 A∥J 的 Abelian 条件），作为 `[honest-bridge-assumption]` 显式声明。这样 S=-S→S=0 才成立。用 `Finset.sum_comm` 交换求和指标 + `nlinarith`/`linarith` 证明 S=-S→S=0。

**一般定理**：对称张量 × 反对称张量缩并 = 0（对称-反对称耦合定理）；而 `f_self_contraction_zero`（`Σ f X X = 0`）仅用 f_antisymm 即可证（不需要额外假设）。

## 4. 公理重整化：终结"公理通货膨胀"

摘要称 25 条 / 正文称 14 条 / Lean 实测 61 条 = 三处矛盾。重整策略：
- **核心物理公设 5-6 条**（流形选择、Ricci 驱动、守恒、谱隙、主方程）保留为 axiom。
- **其余降级为 def**（I_eq 代数关系、自由参数 α=6π/35、初值设定等 → noncomputable def）。
- **跨尺度桥接标记**（KLS-Λ 对偶、Fisher 引力等）→ phenomenological bridge 显式标注。
- 公理计数统一为 `grep -c '^axiom '` 实测值（排除注释），全文单一口径。
