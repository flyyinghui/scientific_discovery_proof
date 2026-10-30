# 重言式公理修复配方 + 死公理检测 (2026-08-23 CGICE V9.1 终审修复)

外部审查 P0-M2（"实质编码"修复本身是重言式，三类全中）逐条修复 + 编译 + 计数统一的完整配方。

## 1. 死公理检测 (grep usage count)

```bash
for name in a_t3_harish_chandra_lower_bound a_t4_semiclassical_discrete_spectrum \
            a_t5_eyring_kramers_first_excitation a4_kls_spectral_gap a5_conservation; do
  echo "$name: $(grep -c "$name" file.lean) 次"
done
```

**判定**: 计数 = 1 意味着仅自声明一次、无任何定理引用 → 死公理（幽灵公理）。
CGICE 实测: a_t3/a_t4/a_t5/a5 全部计数=1（死），a4 计数=2（声明 + 1 引用）。s1_*/s2_* 条件定理把研究级前提作为 HYPOTHESES 传入，不引用 a_t* 死公理。

## 2. 重言式公理三类修复

| 类型 | 症状 | 修复 |
|------|------|------|
| 可归约恒等式 | `axiom X : 35 = rho_sq_doubled`，`rho_sq_doubled def := 2*(35/2)` 经 norm_num 归约 = 35 | → `axiom X : Prop`（研究级前提，comment 描述真实内容 σ_ess⊂[|ρ|²,∞)）|
| 重复公理 | `axiom X : lam1 = 35/3` 与 a4 逐字重复 | → 直接删除（连同注释行）|
| 自由 Prop | `axiom X : spec_gap_bound`，`spec_gap_bound : Prop` 未约束 | → 保留（已是诚实形式，勿再"实质编码"成可归约恒等式）|

## 3. 物理错误谱分解修复（四次势等距谱）

`λ_k = k·λ₁` 等距谱只对纯二次势成立；四次势 V_eff=(λ₁/2)‖χ‖²+(g/4)‖χ‖⁴ 非谐，四次项移动所有 k≥2 能级。

- Lean: `axiom a3_spectrum_decomposition (k : ℕ) : a3_witten_spectrum_val k = (k:ℝ)*lam1`
  → `axiom a3_spectrum_decomposition : a3_witten_spectrum_val 1 = lam1`
- 同步改引用处: `lemma l1 (k : ℕ) : ... = (k:ℝ)*lam1 := by exact a3_spectrum_decomposition k`
  → `lemma l1 : a3_witten_spectrum_val 1 = lam1 := by exact a3_spectrum_decomposition`

**陷阱**: 改声明签名（删 `(k : ℕ)` 参数）后必须同步改所有 `exact <name> k` 调用点，否则编译报 `error: Function expected at`。

## 4. 真证据链识别

条件定理把研究级前提作为 HYPOTHESES（`h_double : rho_double = rho_sq_doubled`），定理体是真推理链（`mul_right_inj'` + `norm_num`、`Real.exp_pos` + `exp_lt_one_iff`）。死公理 a_t* 是装饰——真证据链在 s* 定理里，不在 a_t* 公理里。

## 5. 删除后计数统一（MD ↔ Lean）

删除 a_t5 → axiom 73→72。论文计数出现在 3 处（摘要 §1、公理节 §3 开头、结论/附录），须全部同步。**陷阱**: grep 残留时先区分"真残留（旧值）"vs"正确值"——本轮 `36 theorems` grep 命中但 36 是正确值（定理未删），不是残留。
