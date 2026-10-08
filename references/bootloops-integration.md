# BootLoops 集成评估（v2.13.0, 2026-10-02）

> 来源：BootLoops 1.0（Matthew D. Schwartz / Anthropic, 2026-10-01）+ Anthropic《Claude-shaped science》。
> 仓库：`github.com/BootLoops-ai/bootloops`（工具库）+ `github.com/BootLoops-ai/skills`（12 个协议）。
> 本次落地：**Stage 1.5 数值层健全性双门**（`planted_truth_gate.py` + `constant_certify.py`），不动主线五阶段。

---

## 一、BootLoops 是什么（关键定位）

BootLoops 是一个**数值精确性 harness**，不是形式化证明器。它的核心能力是「可核验的数值」：
球算术（每个值带证明误差半径）、PSLQ 整数关系闭环、带证书的递推、认证求积。

它的「另一半」是 12 个**协议 skills**（`github.com/BootLoops-ai/skills`），编码「done 是什么意思」：
一个结果要「在拟合从未见过的点上复现独立路线 + 有正对照证明检查会失败」才算完成。

**关键区分**：BootLoops 的「证明」是数值认证（算到几百位数字），与 `scientific-discovery-proof` 的
「形式化证明」（Lean 4 定理，结论从公理推出）是**两个不同的东西**。BootLoops 不能直接提升 Lean 4
证明本身的正確率——那是 MathCode + Stage 3.5 审计层的职责（已很强）。

---

## 二、诚实 diff：已覆盖 vs 真正缺

把 BootLoops 12 个 skills 逐个对过去：

| BootLoops skill | 精髓 | scientific-discovery-proof 现状 |
|---|---|---|
| `referee-sim` | 模拟审稿人 | ✅ 已覆盖（hybrid review 5-agent） |
| `ref-check` | 核对参考文献 | ✅ 已覆盖（ScientistTwo Reference Verification, v2.9.0） |
| `prose-lint` | 精确与诚实的散文 | ✅ 已覆盖（honest-axiom 纪律） |
| `lit-review` | 文献审阅 | ✅ 已覆盖（多框架） |
| **`planted-truth`** | 管线必须先恢复植入答案 + 抓污染输入 | ❌ **缺**（本次落地 P0） |
| **`constant-recognition`** | PSLQ 前声明环+高度，找不到就拒绝发明 | ❌ **缺**（本次落地 P1） |
| **`independence-bookkeeping`** | 喂过拟合的 oracle 永远不能认证结果 | ⚠️ 部分（有 Hallucination Clipping 但无溯源） |
| `acceptance-gate` | 门在拟合前声明 | ⚠️ 部分（有黄金门控但顺序纪律未显式） |
| `timing-discipline` | 先小规模试点再大跑 | ⚠️ 部分（有 Stage 2 排名但无时序门） |
| `prove-protocol` | 强制结构多样性的多智能体证明 | ⚠️ 部分（generate/audit 同一模型家族） |

**结论**：BootLoops 真正独有、且管线缺失的只有 `planted-truth` + `constant-recognition`（本次落地），
以及 `independence-bookkeeping`（P2，未落地，见 §四）。

---

## 三、本次落地的两个增量（P0 + P1）

### Stage 1.5a 植物真值门（`planted_truth_gate.py`, P0）

纪律：「一个只看过真实数据的管线从未被测试过。唯一知道正确答案的输入是你自己构造的。Plant first, look second。」

- 正对照：已知真值恒等式必须被数值引擎恢复（|残差| ≤ 容差）。
- 负对照：故意错误的值必须被抓住（|残差| > 容差）。
- 任一失败 → BLOCK（Stage 3 前终止）。

内置 SL(6,C) 对照集：5 正（λ_KLS=35/3、g_*²=12π²/35、g_inst²=24π²/35、|ρ_res|²=35、|ρ_alg|²=35/2）
+ 1 负（g_TC²=8π²/35，v2.6.0 历史 bug 作为 canonical 负对照）。

**直接收益**：把「花几小时形式化一个数值上为假的猜想」挡在 Stage 3 之前——效率上最明确的一刀。

### Stage 1.5b 闭环常数认证（`constant_certify.py`, P1）

纪律：「整数关系算法是一台拟合机器。关系是否有意义完全由搜索**之前**的选择决定——允许哪些常数、
整数多大、多少位数字付账。一个 hit 是廉价的；一个 null 只对声明的环才有意义。」

- 先声明环 + 高度 H + 精度预算，再跑 PSLQ。
- digit budget = 工作精度 − n·log10(H)，盈余太薄 = 掷硬币。
- 找不到 → 报 NULL（拒绝发明），绝不报一个「噪声识别成的著名常数」。

内置 SL(6,C) 四个认证目标：g_*²=12π²/35、g_inst²=24π²/35、λ_KLS=35/3、|ρ_res|²=35，全部 CLOSED。

**直接收益**：正是 v2.6.0 修的那个 bug 的同类（g_TC²=8π²/35 vs 24π²/35 差 3 倍）——这类数值错会在
数值层就抓出来，而不是等到 Lean 里发现两个命名空间常数矛盾。

---

## 四、未落地的增量（P2–P4，评估理由）

| 优先级 | 增量 | 未落地理由 |
|---|---|---|
| P2 | `independence-bookkeeping`（溯源记账 + 单向污染规则） | 需给每个数值常数记录溯源（哪个引擎、哪个 fit 用过），改动比 P0/P1 重，且与现有 Hallucination Clipping 有部分重叠。建议下一轮做。 |
| P2 | `prove-protocol` 强制结构多样性（generate/audit 分离上下文） | 需把 audit 换成结构上独立的模型/上下文，是真实但更重的改动。 |
| P3 | `timing-discipline` 时序门（廉价数值试点 → 全量形式化） | 已部分有（Stage 2 排名 + Stage 2.5 课程），锦上添花。 |
| P4 | 工具库环积分机器（Landau/AMFlow/SOFIA/Eichler/Leviathan） | 针对多圈散射振幅，与 SL(6,C) 谱几何/跷跷板/引力波猜想无关。 |

---

## 五、验证

```bash
cd ~/.hermes/skills/scientific-discovery-proof/scripts
python planted_truth_gate.py --self-test   # 6/6 对照 PASS
python constant_certify.py --self-test      # 4/4 目标 CLOSED
```

两个脚本均 stdlib + mpmath（PSLQ 内置），无外部引擎依赖。
