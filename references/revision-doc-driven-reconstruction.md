# 修改意见文件驱动的论文重构工作流（Revision-Doc-Driven Reconstruction）

用户反复采用的工作模式（CGICE V9.1 三轮验证：双阶段 RG 流 / 宇宙学常数几何破译 / Witten Laplacian 谱隙严格化）：给出一个「修改意见 .md」→ 重构论文对应章节 + 同步 Lean → 编译 0 sorry。

## 六步工作流（每轮 ~15 分钟）

1. **读修改意见文件**（用户给出路径，如 `CGICE论文修改_双阶段重整化群流.md`），提取核心推导链 + 关键公式。
2. **独立数学校核**（`execute_code` Python 重算）：修改意见文件**本身可能有错**。实例：双阶段 RG 流意见文件的单圈解分母写 8π²，但分离变量 ∫g⁻³dg=−g⁻²/2 引入因子 2，正确是 **4π²**——必须独立重算后再落地。校核项：公式代数自洽、数值回代、量纲（Einstein 常数 [M]² vs 能量密度 [M]⁴）。
3. **重构 MD 对应章节**：把"开放问题/自由参数/现象学动机"叙事升级为"第一性原理推导"。用 `[2026-08-18 RESTRUCTURE ...]` 标记。**修正修改意见文件的错误**（如 8π²→4π²），不照抄。
4. **同步 Lean 证据链**：在文件末尾 `end` 前插入（见下方三模式）。
5. **编译验证**：`MATHLIB_NO_CACHE_ON_UPDATE=1 timeout 500 lake build`，目标 0 sorry。
6. **全文呼应**（用户明确要求，不可省略）：修改正文后，**摘要/引言/结论/讨论/附录都要同步呼应**核心推导。用户原话："除了增加补充 7.3-7.5 节以外，摘要和其它章节需要呼应的也一并补充简要说明。" 每次重构后 grep 检查旧叙事残留（如 "OPEN PROBLEM"、"assumed, not derived"、"discrete spectrum"）必须为 0。

## Lean 证据链构造三模式（0 sorry 真证明）

1. **数值恒等式** → `norm_num` / `rfl` 真证明（纯有理数，无 π，不会触发 norm_num+π 假阳性）：
   - `rho_sq_std_value : (25+9+1+1+9+25)/4 = 35/2`（A₅ 根系 |ρ|²）
   - `rho_sq_fdv_A5 : 6*(6^2-1)/12 = 35/2`（Freudenthal–de Vries）
   - `factor2_bridge_rho : (2:ℝ)*(35/2) = 35`（标准→doubled 归一化桥接）
2. **研究级前提** → `axiom` + `[honest-axiom]` 注释（μ_c、η_k、J、ΔR 数值、异常维度）。诚实边界：前提声明为 axiom，定理体用真推理链。
3. **真推理链** → `calc` + `field_simp` + `ring`（代数验证）。关键模式 `fixed_point_zero`：
   ```lean
   theorem fixed_point_zero (b0 eta g : ℝ) (hb0 : b0 ≠ 0)
       (hg2 : g^2 = -(4 * Real.pi^2 * eta / b0)) :
       beta_NP b0 eta g = 0 := by
     unfold beta_NP
     have hg3 : g^3 = g * (-(4 * Real.pi^2 * eta / b0)) := by
       calc
         g^3 = g^2 * g := by ring
         _ = (-(4 * Real.pi^2 * eta / b0)) * g := by rw [hg2]
         _ = g * (-(4 * Real.pi^2 * eta / b0)) := by ring
     rw [hg3]
     field_simp [hb0]
     ring
   ```
   （假设固定点条件 g²=−4π²η/b₀，真代数证明 β_NP(g)=0。）

## Lean 编译陷阱（本轮踩过）

1. **`10^(-122)` 类型错误**：`10` 默认是 Nat，`-122` 是 Int，`Nat ^ Int` 无实例。报 `failed to synthesize instance of type class`。修复：`(10 : ℝ) ^ (-(122 : ℤ))`（zpow 整数幂，负指数合法）。
2. **重复声明**：插入前先 grep 文件已有的符号。CGICE Lean 头部已有 `noncomputable def lambda_par := 35`、`lambda_perp := 35/3`、`M_Pl := 2.435e18`——新插入的 `def lambda_par` / `axiom M_Pl` 会报 `has already been declared`。修复：删除新声明，复用头部已有定义。
3. **删除重复声明时**：用精确多行匹配删除（含紧跟的 theorem），保留文件头部的 `noncomputable def`（grep 残留时区分 `def X` 匹配到 `noncomputable def X` 是正常的）。

## 诚实标注规范

- 研究级开放前提（μ_c 值、|η_k| 数值、ΔR、J）→ `[honest-axiom]` 注释 + `axiom` 声明，绝不伪证。
- 真定理（|ρ|² 恒等式、固定点代数）→ norm_num/calc/ring，0 sorry。
- 修改意见文件的错误修正（8π²→4π²）→ 显式标注 `[4π² denominator — corrected 2026-08-18]`。
- 旧叙事残留（"open problem"/"assumed not derived"/"discrete spectrum λ_k=kλ₁"）→ grep 强制归零。
