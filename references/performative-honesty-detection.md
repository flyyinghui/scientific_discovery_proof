# 表演性诚实检测 (Performative Honesty Detection)

CGICE V9.1 交叉校核 (2026-08-21, `CGICE_V9_交叉校核报告_20260821.md`) 暴露的缺陷类。比 Stage 3.5 的六类 P0 更细——这些是"声明存在但零数学内容"的公理，比可见 `sorry` 更危险（虚假的"已验证"信心）。

## 1. 重言式公理 (tautology axioms)

```lean
axiom a_t3_harish_chandra_lower_bound : (35 : ℝ) ≤ 35   -- 恒真, 零内容
axiom a_t4_semiclassical_discrete_spectrum : (0 : ℝ) ≤ 1 -- 恒真
axiom a_t5_eyring_kramers_first_excitation : (1 : ℝ) = 1 -- 恒真
```

- 检测: `grep -E "axiom[^:]*:\s*\([0-9]+ : ℝ\)\s*[≤=]\s*[0-9]+"` 找"数字≤数字/数字=数字"的平凡断言
- 修复: 编码实质内容，绑定实际量。如 `a_t3 → (35 : ℝ) = rho_sq_doubled`（自由谱下界=加倍 Weyl 范数=35），`a_t4 → spec_gap_bound`（束缚条件成立），`a_t5 → lam1 = (35:ℝ)/3`

## 2. 假全称公理 (false universal)

```lean
axiom spec_gap_bound : ∀ (grad_sq lapV : ℝ), 0 ≤ grad_sq - lapV  -- 取 grad_sq=0,lapV=1 即假
```

- 检测: 对 `∀` 全称断言找反例（一个反例即假）
- 修复: 改为研究级前提 Prop——`axiom spec_gap_bound : Prop`（半经典束缚条件成立，具体形式待 Mathlib 流形库）

## 3. 零内容 def (zero-content def)

```lean
def a1_geometric_manifold : ℝ → ℝ := fun x => x   -- 恒等函数, 零内容
```

- 检测: `grep ":= fun.*=>"` 或 `:= True` / `:= by trivial`
- 修复: 编码实质（如 `def a1_geometric_manifold : ℕ := 35` 流形维数）

## 4. 装饰性死公理 (unused decorative axioms)

a_t3/a_t4/a_t5 声明了但 `s1_*` 定理根本不引用它们（只用 h_double 和 hT6_ratio 两个前提）→ 装饰性。

- 检测: 对每个 axiom，grep 它在 theorem/lemma 证明体中的引用次数；0 引用 = 装饰性
- 修复: 要么让定理真正引用它们，要么删除 + 论文诚实标注"前提已陈述但未形式化"

## 5. 注释标签陈旧 (comment label staleness)

标识符正确但注释 A 编号系统性偏移（历史编号迁移只改了标识符、没改注释）:

```
-- [honest-axiom] A7: Information Cycle Closure   ← 错, 应为 A6
axiom a6_cycle_closure ...
-- [honest-axiom] A16: Master Equation            ← 错, 应为 A7
axiom a7_master_equation ...
```

- 检测: 对每个 `aN_*` 声明，取上方最近注释的 `AN:` 标签，核对 N 是否一致
- 案例 (CGICE): A6 起偏移 +1，A7 起偏移 +9，A15 起偏移 +3，共 15 处

## 6. Header-only fix (表头已改正文未改)

表头/摘要已修正数值，但正文/附录仍留旧值。V17 案例: 表头已写 "N_e=80.6 (NOT 161)"，但正文 4 处仍 "N_e=161.18"（§III.A/§IV.A/§V/Appendix）。

- 检测: 修完数值后 `grep` 旧值，**不只看表头/摘要**（正文/附录最易漏）
- 与 Pitfall #18（stale value pollution in appendices）同族，但这是"表头改了正文没改"的特例

## 7. 注释式 honest-axiom vs 真实 attribute (跨论文机器可审计性, 2026-08-28)

跨论文审计发现：同一 SL(6,C) 系列论文中，honest-axiom 标记的"机器可审计性"不一致。

- **真实 attribute**（机器可审计）：`@[honest_axiom]` 行首 attribute，需独立 `HonestAttr.lean` 文件注册（`initialize` 阶段 `registerTagAttribute`，同文件 `@[attr]` 会报 Unknown attribute）。检测：`grep -cE '^\s*@\['` 行首 attr 数 > 0。
- **注释式标签**（表演性诚实，机器不可审计）：`-- @[honest_axiom]` 注释标签。检测：`grep -c 'honest.axiom'` 总数 vs `grep -cE '^\s*@\['` 行首 attr 数，两者差距 = 注释式标签数。

实例（四论文 2026-08-28）：V17 324 标记/0 真实 attr、CGICE 22/0、V63 103/0（全注释），V16 67/33（唯一有真实 attr，经 HonestAttr.lean）。

**md 层披露 vs Lean 层修复的分工**：根因在 Lean 源码（注释 vs attribute），md 手稿只能在"形式化验证"段落补充"诚实标准声明"披露现状 + 计划升级（仿 V16 建 HonestAttr.lean）；真正的机器可审计修复必须改 Lean 文件，不能只在 md 里声明。

## 双模型交叉审查的误判案例 (false positive)

v4-pro 曾把 `s1_lambda_perp_eq_35_over_3` 判 ✗（声称 `mul_right_inj'` 方向错），但实际编译 exit 0 证明正确。根因: v4-pro 记错了 `mul_right_inj'` 的签名（真实: `mul_right_inj' (ha : a ≠ 0) : a * b = a * c ↔ b = c` 是**左乘**可注入）。用 `mathlib_api_lookup.py` 检索源码 + Qwen3.8 交叉 + 实际编译三方一致才判真。教训: **检索当前源码比模型记忆可靠**，单模型独有结论须人工核实。
