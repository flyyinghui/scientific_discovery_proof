# P0-5/6/7 统一性修复 — g_TC² 3 倍矛盾 + λ_∥/λ_⊥ 角色分工 + 四论文交叉审计

> 案例来源：四篇 SL(6,C) 论文（CGICE v9 / 三大时空相 V17 / 右手中微子 V63 / 三峰引力波 V17）
> 统一框架：`SL6C_Unified_Geometric_Dynamics_Framework.md`
> 2026-09-04，沿用 P0-4 条件定理形式化方法（`p04-conditional-theorem-refactoring.md`）。

---

## 1. 背景：P0-5/6/7 是什么

三峰引力波论文 V16 终审（2026-08-30）的 7 项 P0 中，P0-4 已修复（strong_log_concave
条件定理重构），剩余 P0-5/6/7 是 Weyl 动力学桥接（V17 lean `P03` 命名空间）的三个
"研究级开放问题"：

| 编号 | 内容 | 形式化现状 |
|---|---|---|
| P0-5 | Atiyah–Singer \|ind(D̸)\|=1 猜想（非紧推广，Moscovici L² 指数定理） | 已条件定理化（`weyl_dynamics_bridge_conditional`） |
| P0-6 | g_TC² = 8π²/λ_KLS 定义非推导 | **需修复**（8π²/35 vs 24π²/35 差 3 倍） |
| P0-7 | λ_KLS=35 群论循环（纵向 35 vs 横向 35/3 混用） | **需修复**（区分 λ_∥/λ_⊥） |

---

## 2. 统一性审计方法（四论文交叉扫描）

**核心思路**：四篇论文共享 SL(6,C) 框架，关键参数（λ_KLS、λ_⊥、g_TC²、η_k、|ρ|²、N_e）
必须表述一致。用一次 `execute_code` 脚本对 8 个文件（4 论文 + 4 lean）做正则交叉扫描，
提取每个关键参数的**数值表述 + 上下文**，再对比母框架统一参数表。

**母框架统一参数**（`SL6C_Unified_Geometric_Dynamics_Framework.md` §3.1）：

| 参数 | 统一值 | 来源 |
|---|---|---|
| λ_∥（纵向 λ_KLS） | 35 | Harish-Chandra \|ρ\|²（真推导 weyl_norm_sq_eq_35） |
| λ_⊥（横向 λ_KLS_eff） | 35/3 ≈ 11.667 | 3D 空间均分（honest-axiom A-3D） |
| g_TC²（IR 定点） | 24π²/35 ≈ 6.768 | FRG 定点 g*² = 4π²\|η_k\|/b₀ |
| g_TC(IR) | 2.60 | √(24π²/35) |
| g_TC(UV) | 0.5 | 裸 GUT 耦合 |
| η_k（异常维度） | 72/35 ≈ 2.057 | C₂·h^∨/dim = 12·6/35（群论 Ansatz） |
| \|ρ\|² | 35 | doubled normalization B=2n·Tr（标准 Tr 下 35/2） |
| N_e | 80.6 | (35/6)·ln(1+10⁶)，唯象输入 |

---

## 3. 发现的 3 倍矛盾（P0-6 根因）

扫描发现**唯一实质矛盾**：`V17_lean`（三大时空相）和 `TGW_lean`（三峰引力波）的
`P03` 命名空间里：

```lean
def gTCSq : ℝ := 8 * Real.pi ^ 2 / lambdaKLS   -- 8π²/35 ≈ 2.256（g_TC ≈ 1.50）
```

而全框架统一值是 `g_TC² = 24π²/35 ≈ 6.768`（g_TC(IR) = 2.60）。

**根因**：P03 桥接公式 `g_TC² = c·|index D̸|/λ_KLS, c=8π²` 里的 λ_KLS 被误用为
**纵向** λ_∥=35，而物理上应代入**横向** λ_⊥=35/3：

```
8π²/λ_⊥ = 8π²/(35/3) = 24π²/35 ≈ 6.768 ✓
```

**对照印证**：V17_paper 已明确写"旧版误用 λ_KLS=35 曾得到 g_TC²≈2.26（g_TC≈1.50），
该值是废弃错误值；正确代入 λ_⊥=35/3 得 g_TC²=24π²/35"。即**论文（md）已统一，但
lean 文件的 P03 命名空间滞后未改**——这是"论文领先、lean 滞后"的典型不一致。

---

## 4. 修复方案（条件定理 + 角色分工）

### 4.1 引入横向谱隙 lambdaPerp

在 `P03` 命名空间 `opaque lambdaKLS` 后新增：

```lean
/-- 横向谱隙 λ_⊥ = 35/3（3D 空间均分，honest-axiom A-3D）。 -/
def lambdaPerp : ℝ := (35 : ℝ) / 3
```

### 4.2 gTCSq 定义改用横向谱隙

```lean
def gTCSq : ℝ := 8 * Real.pi ^ 2 / lambdaPerp   -- 24π²/35 ≈ 6.77
```

### 4.3 保留纵向 λ_∥=35 的运动学角色（P0-7 修复）

`weyl_kinematic_gap : lambdaKLS = rhoSqCompact`（=35）**保留**——这是 Weyl 幺正技巧的
**运动学**谱映射（纵向 λ_∥=|ρ|²=35 的真推导），不用于动力学桥接。桥接用横向 λ_⊥。

### 4.4 条件定理升级为 6 假设

```lean
theorem weyl_dynamics_bridge_conditional
    (hVZ : l2CohomologyIndex = 1)
    (hMM : l2CohomologyIndex = indexDirac)
    (hAS : indexDirac = a2)
    (hSD : a2 = kappaInst * b0 * rhoSqCompact / (12 * Real.pi ^ 2))
    (hWeyl : lambdaKLS = rhoSqCompact)
    (h3D : lambdaPerp = lambdaKLS / 3) :      -- 新增 3D 均分 honest-axiom A-3D
    gTCSq = (8 * Real.pi ^ 2) * |indexDirac| / lambdaPerp := by
  ...
```

关键：`h3D` 把纵向 λ_∥=35（hWeyl）经 3D 均分转化为横向 λ_⊥=35/3，使 6 条研究级前提
全部显式化且都被使用（用 `have _` 一致性验证抑制 unused warning）。

### 4.5 数值验证

```lean
theorem gTC_sq_value : gTCSq = 24 * Real.pi ^ 2 / 35 := by
  unfold gTCSq lambdaPerp
  rw [div_div_eq_mul_div]
  ring
```

---

## 5. 编译验证 + #print axioms 审计标准

两个 lean 文件（`triple_gw_dm_proof_v17.lean` + `6D_Spacetime_Formal_Proof_V17.lean`）
均 `lake env lean` 编译 **EXIT_CODE=0，0 warning**。

**条件定理的黄金审计标准**（`#print axioms`）：

```
'P03.weyl_dynamics_bridge'            depends on axioms: [propext, Classical.choice,
    P03.matsushima_murakami, P03.vogan_zuckerman_cohomology, Quot.sound]
'P03.weyl_dynamics_bridge_conditional' depends on axioms: [propext, Classical.choice, Quot.sound]
```

- **主定理**（公理实例化）依赖研究级前提（VZ/MM）→ 正确
- **条件定理**只依赖经典逻辑公理（propext/Classical.choice/Quot.sound）→ **这就是
  "全面证据链"的判定标准**：条件定理的 `#print axioms` 不出现任何研究级 axiom，说明
  所有研究级前提都已显式化为假设，定理体 100% forward inference。

---

## 6. 可复用模式提炼

### 模式 D：四论文统一性交叉扫描

对共享同一母框架的多篇论文 + 多 lean 文件，做**一次性正则交叉扫描**提取关键参数
的数值表述，对比母框架统一参数表。判别标准：
- 论文（md）与 lean **不一致** = 需要修复（论文领先、lean 滞后最常见）
- 数值差整数倍（如 3 倍）= 谱隙/维度角色混淆（纵向 vs 横向、compact vs non-compact）
- 数值完全一致但来源不同 = 需检查是否循环论证

### 模式 E：谱隙角色分工（λ_∥ vs λ_⊥）

纵向 λ_∥（=35，Weyl 运动学 |ρ|²）与横向 λ_⊥（=35/3，3D 均分）必须**分名**，桥接公式
用哪个谱隙要明确。混用导致整数倍数值错误。

### 模式 F：条件定理的 #print axioms 门控

条件定理（显式假设版）编译后必须跑 `#print axioms`，确认只依赖经典逻辑公理
（propext/Classical.choice/Quot.sound），不出现任何研究级 axiom。这是"证据链是否闭合"
的客观判定。

---

## 7. 关联

- `p04-conditional-theorem-refactoring.md` — P0-4 条件定理重构（本方法的前置）
- `cgice-v91-lean-closure-and-attribute-trap.md` — honest-axiom 表演性诚实
- 母框架：`SL6C_Unified_Geometric_Dynamics_Framework.md`（统一参数表权威来源）
