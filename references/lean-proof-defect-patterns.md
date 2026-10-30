# Lean 4 证明缺陷模式与修复（2026-08-17 三轮终审固化）

本轮（CGICE V9.1 / 三峰 V16 完善方案）暴露并修复的三类 Lean 4 形式化证明缺陷。均可用 Stage 3.5 审计门（`scripts/proof_consistency_audit.py`）自动检测。

## 1. @[honest_axiom] 真实 attribute 注册（跨文件，非注释）

**问题**：`-- @[honest_axiom]` 注释标签是"表演性诚实"——编译语义为零，无法机器审计。论文声称"declared as @[honest_axiom]"是失实。

**根因**：Lean 4 的 `registerTagAttribute` 在 `initialize` 块延迟执行，**同文件** `@[attr]` 在语法解析阶段就报 "Unknown attribute"（initialize 还没跑）。

**正确实现（跨文件三步）**：
1. 独立文件 `HonestAttr.lean`：
```lean
import Mathlib
public meta section
open Lean Elab Command Parser.Term Meta
initialize honestAxiomAttr : TagAttribute ←
  registerTagAttribute `honest_axiom "honest research-level axiom marker"
initialize phenomAxiomAttr : TagAttribute ←
  registerTagAttribute `phenomenological "phenomenological calibration input"
end
```
2. `lakefile.lean` 的 roots 加入：`roots := #[`HonestAttr, `main_proof]`
3. 主文件 `import HonestAttr` + 用 `@[honest_axiom]` 标注

**关键签名**：`registerTagAttribute (name : Name) (descr : String) ... : IO TagAttribute`，必须用 `initialize x : TagAttribute ←` 接收（不是三个参数）。`TagAttribute.hasTag attr env decl` 可机器审计。

**迁移**：把 `-- @[honest_axiom]` 批量 `replace("-- @[honest_axiom]", "@[honest_axiom]")`，但注意孤儿 attribute（原注释标记的 def 已在别处定义）要删除。

## 2. 爆炸原理消除（ex-falso elimination）

**问题**：`A6 ⟹ X=Y` 与 `A17 ⟹ X≠Y` 并存 → `A=B ∧ A≠B` → Ex Falso Quodlibet，整个证明系统逻辑归零。比可见 sorry 更危险（虚假的"已验证"信心）。

**修复模式（三原则）**：
1. **废除矛盾公理**：删除全局不等式 `∀t, X(t)≠Y(t)`（A17 类）。非平凡动力学应由初始微扰 + 主方程非线性弛豫驱动，而非矛盾公理强行注入。
2. **绑定公理降级为 def**：`I_cycle = V_eff·常数`（A6 类）全时间域绑定 → 释放为自由动力学泛函；`I_eq = 代数组合`（A10 类）改为 `noncomputable def`。
3. **主方程唯一驱动**：`dX/dt = -rate·(X-Y)`（A16 类）作为唯一演化驱动器，配合非平凡初始条件 `X(0)≠Y(0)`。

**检测**：Stage 3.5 检测 1（提取 axiom 等式链，检测 X=Y 与 X≠Y 同名冲突）。

## 3. 反对称双重求和 S=-S 需额外对称假设

**问题**：声称 `Σ_{μν} f^k_{μν} A^μ J^ν = 0` 仅凭结构常数反对称 `f^k_{μν}=-f^k_{νμ}` 可证（S=-S→S=0）。

**真相**：S=-S 论证交换指标后得到 `Σ f^k_{μν} A^ν J^μ`，但 `A^ν J^μ ≠ A^μ J^ν`（A 与 J 独立对象）。**仅凭 f_antisymm 不可证**。反例：f(0,1)=1, f(1,0)=-1, A(0)=J(1)=1, A(1)=J(0)=0 → Σ f A J = 1 ≠ 0。

**修复**：额外需要 `A^μ J^ν` 在 μ↔ν 下对称（平行规范 A∥J），声明为 `[honest-bridge-assumption]`，诚实文档化为何必需。这是让 T4 拓扑荷守恒严格成立的最小诚实输入。

**通用结论**：对称-反对称耦合为零的论证，必须核对**被耦合的两个对象是否共享同一对称性**。结构常数反对称只抵消"同一张量自缩并"（Σ f X X = 0 可纯 S=-S 证），不能抵消两个独立张量的缩并。

## 相关

- 检测脚本：`scripts/proof_consistency_audit.py`（六类 P0，含以上三类）
- 审计清单：`references/formal-proof-consistency-audit.md`
- 完整实现：`<PAPER_DIR>/三峰引力波证明_20260606/HonestAttr.lean`
