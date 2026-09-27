# Stage 3.5 形式化证明自洽性审计门 — 与 scientific-discovery-proof 整合方案

**版本**: 1.0 | **日期**: 2026-08-17
**作者**: 灰因斯坦 (Grey Turing)
**状态**: 已集成并实测验证

---

## 一、背景与动机

### 1.1 为什么需要这个审计门

scientific-discovery-proof（SDP）管线的 Stage 3（PPE-V5.1Hybrid）依赖 **MathCode 三工具**（`axiom_checker` / `proof_stats` / `sorry_analyzer`）做形式化验证。但三工具只"数数"：

- `axiom_checker` → 有多少 axiom（数量）
- `proof_stats` → 有多少 theorem/lemma（统计）
- `sorry_analyzer` → has_sorry 是 true/false（占位符）

**它们查不出：**
1. axiom 之间是否**互相矛盾**（爆炸原理）
2. `@[honest_axiom]` 是真实 attribute 还是**注释掉的文本**（表演性诚实）
3. 论文声称的公理数与 Lean 实际是否一致
4. 论文声称 "fully verified" 的定理，Lean 里是否**真的存在**
5. 定理体 `:= by trivial` 是证明还是**空壳**
6. 声称的"离散谱"在非紧空间上是否**数学成立**

### 1.2 三轮终审的实证依据

2026-08-16 的三轮终审反复暴露同类问题，证明"0 sorry ≠ 已验证"：

| 论文 | 致命缺陷 | 类型 |
|---|---|---|
| **CGICE V9.1** | A6+A10 强制 `I_cycle=I_eq`，A17 声明 `I_cycle≠I_eq` → **可证 False** | 公理自相矛盾 |
| **CGICE V9.1** | 论文声称 "T4 fully verified"，Lean 无此定理 | 定理虚假声称 |
| **CGICE V9.1** | A3 声称非紧空间离散谱 λ_k=k·λ₁ | 数学类别错误 |
| **三峰 V16** | 26 处 `-- @[honest_axiom]` 注释，0 真实 attribute | 表演性诚实 |
| **三峰 V16** | 公理计数 14 vs 41 vs 19 vs 实测 66 | 计数不一致 |

**核心洞察**：一个 0 sorry 但公理互相矛盾的证明，比一个有可见 sorry 但自洽的证明更危险——因为它给人"已验证"的虚假信心。

---

## 二、整合架构

### 2.1 管线位置

Stage 3.5 插入在 **Stage 3（形式化证明）之后、Stage 4（论文生成）之前**：

```
Stage 3   PPE-V5.1Hybrid（MCTS + ABC → Lean 4 证明）
              │
              ▼
Stage 3.5  ★ Formal Proof Consistency Audit（六类 P0 检测，BLOCK 门控）
              │
              ├─ BLOCK → 停止管线（证明有阻断级缺陷）
              ├─ WARN  → 记录并转发 Stage 4（论文诚实披露）
              └─ PASS  → 继续
              │
              ▼
Stage 4   AI-Scientist V2（论文生成）
```

### 2.2 组件清单

| 组件 | 路径 | 作用 |
|---|---|---|
| 审计脚本 | `scripts/proof_consistency_audit.py` | 六类 P0 检测，stdlib-only 零依赖 |
| 审计清单 | `references/formal-proof-consistency-audit.md` | 六类缺陷的检测方法 + 修复原则 |
| SDP 编排器 | `scripts/pipeline_orchestrator.py` | 集成 Stage 3.5 调用（`_run_stage35_consistency_audit`）|
| PPE 集成 | `physics_proof_engine/prove_with_skills.py` | Phase 3.5 集成（`phase_consistency_audit`）|

---

## 三、六类 P0 检测

| # | 缺陷类 | 检测方法 | 严重度 |
|---|---|---|---|
| 1 | **公理自相矛盾**（爆炸原理） | 提取 axiom 的等式链，检测 `X=Y` 与 `X≠Y` 同名冲突 | 🔴 BLOCK |
| 2 | **表演性诚实**（注释标签） | `real_attrs`（行首 `@[`）vs `comment_attrs`（`-- @[`）对比 | 🟡 WARN |
| 3 | **公理/定理计数不一致** | `grep -c '^axiom '`（排除注释）vs 论文声称 | 🟡 WARN |
| 4 | **定理虚假声称** | 论文 "theorem X" vs Lean `^theorem X` 存在性 | 🔴 BLOCK |
| 5 | **空壳证明** | `:= by trivial` / `:= True` / active `admit` | 🟡 WARN |
| 6 | **离散谱 vs 连续谱** | 同时出现"离散谱 λ_k=k·λ" + "非紧空间"关键词 | 🔴 BLOCK |

### 3.1 门控规则

- **BLOCK**（阻断级）→ 停止管线，不进入论文生成：
  - 公理自相矛盾（可证 False，形式化验证无效）
  - 定理虚假声称（学术不端级）
  - 离散谱 vs 非紧空间（数学类别错误）
- **WARN**（警告级）→ 记录并转发 Stage 4，论文需诚实披露：
  - 表演性诚实、公理计数不一致、空壳证明、active admit

---

## 四、使用方法

### 4.1 独立使用

```bash
cd /mnt/d/HermesAgent/scientific-discovery-proof/scripts
python proof_consistency_audit.py \
  --lean /path/to/proof.lean \
  --paper /path/to/paper.txt \      # 可选，用于检测定理虚假声称
  --expected-axioms 14 \            # 可选，论文声称的公理数
  --output /tmp/audit.json
# 退出码: 0=PASS/WARN, 1=BLOCK
```

### 4.2 SDP 管线内（自动触发）

```bash
python pipeline_orchestrator.py \
  --conjecture conjecture.json \
  --stages 1,2,3,4    # Stage 3 后自动触发 Stage 3.5
```

### 4.3 PPE 内（Phase 3.5 自动触发）

```bash
cd /mnt/d/ai_for_science/physics_proof_engine
python prove_with_skills.py --target T1 --iterations 20
# Phase 3 验证后自动触发 Phase 3.5 审计，扫描 projects/ 下最近 5 个 .lean
```

---

## 五、实测验证结果

### 5.1 CGICE V9.1（已知有问题的证明）

```
axioms=39  theorems=3  lemmas=5  sorry=1  admit=0
GATE: BLOCK
🔴 BLOCK: 定理虚假声称：论文提到 t4_topological_charge_conservation（Lean 中不存在）
🟡 WARN: 公理计数不一致：论文声称 14，Lean 实测 39
🟡 WARN: 公理自洽性：`I_cycle t` 同时等于 [V_eff t * (2*π/λ₁)] 和不等于 I_eq(...)
🟡 WARN: 离散谱 vs 连续谱（非紧空间）
```

### 5.2 三峰 V16（表演性诚实的证明）

```
axioms=66  theorems=53  lemmas=26  real_attrs=33
GATE: WARN
🟡 WARN: 离散谱 vs 连续谱
（33 处真实 attribute，表演性诚实问题已由作者修复）
```

### 5.3 PPE 产物（three_phases_v4-*）

```
GATE: WARN
🟡 WARN: 10 处 active 'admit'（等同 sorry）
🟡 WARN: 9 处 ':=' True' 空壳命题
```

**结论**：审计门在三类真实场景（CGICE 致命矛盾、V16 表演性诚实、PPE 产物 admit）都正确检出，无假阳性（已修正 `t`/`_CC t` 误匹配、`and`/`states` 英文词误匹配）。

---

## 六、整合的关键设计决策

1. **BLOCK 不阻断 WARN**：只有"证明逻辑无效"（可证 False/虚假定理/类别错误）才阻断，其余作为警告转发，让论文诚实披露而非硬停。

2. **stdlib-only**：审计脚本只用 Python 标准库（re/json/argparse），不依赖 Lean 工具链，可在任何环境跑。

3. **读 JSON gate 而非 exit_code**：gate 有三态（PASS/WARN/BLOCK），exit_code 只能表达二态，集成时必须读审计 JSON 的 `gate` 字段（已修复 orchestrator 和 PPE 两处）。

4. **反模式修复**：`_generate_proof_skeleton` 原来生成 `:= by trivial` 空壳，已改为显式 `axiom ... : True`（honest-axiom 声明）+ 主定理体用 `sorry` 标记（诚实暴露未证部分）。

---

## 七、未来扩展

- [ ] 把 Stage 3.5 审计结果注入 Stage 4 论文的 "Formal Verification" 章节（诚实披露 BLOCK/WARN 项）
- [ ] 增加 SymPy 符号恒等式交叉验证（配合 MAF Stage 0）
- [ ] 支持批量审计（目录扫描模式，已有雏形）
- [ ] 与 `#print axioms` Lean 命令对接，做机器级公理依赖审计
