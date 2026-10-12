# MAF-SDP Integration — 嵌入说明文档

**版本**: 1.0 | **日期**: 2026-08-05
**组件**: math-agent-framework (MAF) × scientific-discovery-proof (SDP) × SciExplorer

---

## 一、嵌入架构

```
                        ┌──────────────────────────────────┐
                        │       物理猜想 (conjecture.json)    │
                        └──────────────┬───────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │  MAF Symbolic    │    │  SciExplorer P0  │    │  Neural Brain    │
   │  Audit           │    │  数值预验证       │    │  J-space 桥接    │
   │  (SymPy代数检验)  │    │  (LLM实验)       │    │  (170K神经元)    │
   └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
            │                       │                       │
            └───────────┬───────────┴───────────┬───────────┘
                        ▼                       ▼
              ┌─────────────────────────────────────────┐
              │  MAF 5-Level + SciExplorer P1 联合验证    │
              │  L1:符号 → L2:FOC/SOC → L3:边界 →        │
              │  L4:反例搜索(50K) → L5:链一致性           │
              │  + SciExplorer MCTS 节点过滤              │
              └──────────────┬──────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ MAF Multi-   │ │ SDP MCTS     │ │ SDP ABC      │
   │ Agent Verify │ │ 证明树搜索   │ │ 蜂群优化     │
   │ (P/C/J对抗)  │ │              │ │              │
   └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
          └────────┬───────┴────────┬───────┘
                   ▼                ▼
          ┌────────────────────────────────┐
          │  Phase 2: 双门验证              │
          │  ├─ MathCode-V2 (Lean 验证)     │
          │  └─ MAF + SciExplorer P2 (闭环) │
          └───────────────┬────────────────┘
                          ▼
          ┌────────────────────────────────┐
          │  Phase 3-5: 论文生成            │
          └────────────────────────────────┘
```

---

## 二、MAF vs SciExplorer 共调用评估

### 2.1 能力对比

| 维度 | SciExplorer | MAF | 互补性 |
|------|-------------|-----|:---:|
| **验证方式** | LLM 生成 Python 实验 | SymPy 符号推导+结构化验证 | ✅ 互补 |
| **反例搜索** | LLM 引导参数扫描 | 全局优化 (50K iterations) | ✅ MAF更系统 |
| **恒等式检查** | 无 (LLM only) | `sp.simplify(LHS - RHS) == 0` | ✅ MAF独有 |
| **方程求解** | LLM 写代码近似解 | SymPy `solve_equation()` 闭式解 | ✅ MAF更精确 |
| **多Agent对抗** | 单 LLM agent | Proposer+Critic+Judge | ✅ MAF独有 |
| **物理领域知识** | DeepSeek 广阔物理知识 | 纯数学 (无物理先验) | ✅ SciExplorer独有 |
| **代码执行** | Python sandbox | NumPy/SciPy/SymPy | 相当 |
| **复杂物理模型** | CW/RG/FRG/seesaw 脚手架 | 通用数学 | ✅ SciExplorer独有 |

### 2.2 共调用决策矩阵

| 场景 | SciExplorer | MAF | 共调用收益 |
|------|:----------:|:---:|:---------:|
| P0 猜想预验证 | ✅ 主要 | ✅ 辅助 | ⭐⭐⭐ 最高 — 防代数错误 |
| P1 MCTS节点过滤 | ✅ 数值可行性 | ✅ 5层验证 | ⭐⭐⭐ 最高 — 互补验证 |
| P2 sorry闭环 | ✅ 实验驱动 | ⚠️ 有限 | ⭐⭐ 中等 — 反例搜索辅助 |
| 多Agent对抗 | ❌ 不支持 | ✅ 主要 | ⭐⭐⭐ 最高 — MAF独有 |
| 符号恒等式 | ❌ 不支持 | ✅ 主要 | ⭐⭐⭐ 最高 — MAF独有 |

### 2.3 共调用模式

```python
# 模式 1: 并行共调用 (P0)
MAF.symbolic_audit(conjecture)  ||  SciExplorer.p0_validate(conjecture)
                    ↓                         ↓
            symbolic_report           sciexplorer_report
                    └──────────┬──────────┘ → CombinedVerdict

# 模式 2: 串行共调用 (P1)
SciExplorer.p1_filter(node) → MAF.verify_5level(node) → expand/trim

# 模式 3: MAF-only (对抗验证)
MAF.adversarial_verify(claim) → {ACCEPTED|REJECTED|NEEDS_REVISION}
```

---

## 三、桥接模块 API

```python
from maf_bridge import MAFBridge
bridge = MAFBridge()

# P0: 符号审计 → 捕获代数错误 (如对数正交公式 1149≠6)
result = bridge.symbolic_audit(conjecture_dict)
# → {'status': 'PASS'|'FAIL'|'COND', 'checks': [...], 'fatal_errors': [...]}

# P1: 5层验证 → 反例搜索 (50K全局优化)
report = bridge.verify_5level(claims_list, param_ranges_dict)
# → VerificationReport with L1-L5 test results

# P2: 对抗验证 → Proposer+Critic+Judge
verdict = bridge.adversarial_verify(claim, context)
# → {'verdict': 'ACCEPTED'|'REJECTED', 'vote_counts': {...}}

# 联合验证 (MAF + SciExplorer cocall)
combined = bridge.combined_verify(conjecture_dict, sciexplorer_result)

# 完整流水线
pipeline = bridge.build_pipeline(conjecture_dict)
pipeline.run({})
```

---

## 四、定量预期

| 指标 | 仅 SDP | + SciExplorer | + MAF |
|------|:------:|:-------------:|:-----:|
| P0 致命错误检出 | ~30% | ~92% | **~98%** |
| MCTS 有效分支率 | ~35% | ~65% | **~75%** |
| 端到端证明成功率 | ~25% | ~55% | **~65%** |
| 反例发现率 | ~10% | ~25% | **~50%** |

---

## 五、文件清单

| 文件 | 路径 |
|------|------|
| MAF框架 | `D:\AI_for_Science\math-agent-framework\` |
| 桥接模块 | `maf_bridge.py` (MAF根目录) |
| SDP技能 | `~/.hermes/skills/scientific-discovery-proof/` |
| SciExplorer | `sciexplorer/` (zip解压) |

---

*由 MAF Bridge v1.0 × SDP Pipeline × SciExplorer 联合 | 2026-08-05*
