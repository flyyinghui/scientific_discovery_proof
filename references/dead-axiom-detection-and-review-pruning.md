# Dead-Axiom Detection + Review Pruning + Same-Symbol Fix (2026-08-23 CGICE V9.1)

## 1. Dead-axiom detection via grep count == 1

一个 Lean `axiom` 声明后从未被任何 theorem/lemma 引用 = "幽灵/死公理"——虚增公理计数但对证明零贡献。检测：

```bash
for name in a_t3 a_t4 a_t5 a4 a5; do
  echo "$name: $(grep -c "$name" proof.lean) 次"  # ==1 表示仅自声明(死公理)
done
```

`grep -c` == 1 = 名字只出现在它自己的声明行 → 死公理。>= 2 = 有引用，需查引用点。

CGICE V9.1 实测: a_t3/a_t4/a_t5/a4/a5 全是 1 次(死公理)；s1_*/s2_* 条件定理才是真推理——它们把研究级前提以**假设**(`h_double : rho_double = rho_sq_doubled`)传入，而非引用这些死公理。**通用规律: 条件定理模式的"研究前提公理"几乎全是死公理，逐个 grep count 即可揪出。**

## 2. Review pruning (后置精简，用户固定工作流)

审查意见逐条落实后，用户会要求"把已修改的意见从审查 MD 删除，仅保留未修改的"。步骤：

1. 删除每个已修改意见的正文段（regex 从该标题匹配到下一个同级标题，DOTALL）。
2. 删除汇总表里对应的行。
3. 删除「修改建议」里对应的条目。
4. 重新编号「修改建议」剩余条目（regex `^\d+\.` → 顺序递增）。
5. 更新过时交叉引用（如"73 axioms" → 删除后实际计数；"a_t5 已删除"标注）。

判断"已修改"标准：意见的核心诉求已落实（数值改对/措辞改对/公理删除）。只加了注释标注（如 A5 只加"诚实标注"未删）不算已修改，保留。

## 3. "Reviewer missed the existing fix" 误读模式

审查称"论文 L116 声称 X 是类别错误"，但论文**同节 10 行后 L126** 已有诚实澄清。检测：接受任何"论文声称 X"类发现前，先 grep 同节确认是否已有诚实标注——大量"类别错误"实为"审查读了第 N 行、跳过了第 N+10 行"。

CGICE 实例: 外部审查 P0-1 "L116 upgrade λ₁=35/3 to first-principles 是类别错误" 是误读——L116 已写 "with a single stated equipartition postulate"，且 L126 已完整标注 "λ₁=|ρ|²/3 是 honest-axiom，非证明恒等式"。该条已从审查文件删除。

## 4. Same-symbol contradiction → dual-variable fix

两条公理给**同一符号**赋互斥表达式（A7: dI_cycle/dt = −(λ₁/2π)(I_cycle−I_eq) vs A19: dI_cycle/dt = +(λ₁/2π)(V_eff−I_eq)）时，修复**不是**强行统一，而是引入对偶变量：

```lean
axiom I_cycle_dual : ℝ → ℝ
axiom a19_legendre_duality_diff (t : ℝ) :
    (deriv (fun s => I_cycle_dual s) t = (lam1/(2*Real.pi)) * (V_eff t - I_eq ...)) ↔
    (deriv (fun s => V_eff s) t = -(2*Real.pi/lam1) * (I_cycle_dual t - V_eff t))
```

A19 的 Legendre-对偶左端是**共轭变量**，不是 A7 的动力学 dI_cycle/dt。改名分离，不调和。论文同步把 §3.4 公式左端 `dI_cycle` → `dI_cycle^dual`。
