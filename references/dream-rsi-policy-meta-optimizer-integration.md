# Dream-RSI 证明策略元优化器整合（Stage 3.7 P0/P2/P3 落地实录）

**来源**：Dream-RSI: Recursive Self-Improvement through Evolving Worlds（arXiv 2609.14858，Google + DeepMind）
**落地日期**：2026-09-27
**改动文件**：`scripts/proof_policy_optimizer.py`（新增，~440 行，stdlib 核心 + 可选 LLM）

---

## 背景：v2.7.0 借错了层

v2.7.0（2026-09-17）落地了 Dream-RSI 的「重放模拟器」**表层**——`ReplaySimulator` 类统计
5 个**变异策略**的历史成功率 + ε-greedy 选择。但 Dream-RSI 的核心洞察是**优化探索策略本身**，
而非在固定策略间做选择。v2.7.0 把「变异策略」当成了重放对象，而 Dream-RSI 真正要优化的是
「**如何选择**变异策略 + 并行几路 + 何时放弃」这个**决策策略**。

本落地补上这一层：新增 `proof_policy_optimizer.py`，把「证明策略」编码为可执行对象，
用 archive.jsonl 历史重放反馈迭代改进策略参数本身。

---

## 三个落地项

### P0 — 探索策略元优化

`ProofPolicy` 类：把「证明策略」编码为可执行、可评估、可改进的 4 参数对象：

| 参数 | 含义 | 默认 |
|---|---|---|
| `strategy_weights` | 5 个变异策略的偏好权重（决定「选哪个动作」） | 均匀 1.0 |
| `parallelism` (W) | 并行度（一次并行几路变异） | 2 |
| `abandon_threshold` | 放弃阈值（最高选择得分低于此值跳过该决策点） | 0.0 |
| `epsilon` | 探索率（ε-greedy） | 0.15 |

策略开发（`develop_candidates`）：
- **参数扰动**（`mutate_params`，确定性，无 LLM）：权重 ±20%、并行 ±1、放弃阈值 ±0.05、ε ±0.05。
- **LLM 开发**（`_llm_develop_policy`，可选）：v4-flash 读当前策略 + 重放评估报告，产出改进策略 JSON。

### P2 — replay objective 三项

`PolicyReplayEvaluator.evaluate()`：
```
V = Σ(选中动作的预期收益) − β1·(调用次数) + β2·(平均并行度)
```

关键设计分离（对齐 Dream-RSI 的「选择 vs 结果」）：
- **「选择」由策略权重决定**（× 针对性软约束：不针对当前缺陷的策略权重 ×0.05）——策略偏好。
- **「结果」由历史真实结果决定**（该动作在该 condition 下的历史成功率 × 平均 gain）——replay 的确定性返回。

β1/β2 控制「成本 vs 并行」权衡：β2 相对 β1 越大，越倾向高并行（探索更广但成本更高）。

### P3 — 单调性保证

候选策略集始终包含当前策略 π_t（`develop_candidates` 首元素），选 max 保证 `V(π_{t+1}) ≥ V(π_t)`。
验证：`final_score >= init_score` 恒成立（自测断言）。

---

## 与 Stage 3.6 的关系（正交，元层）

| | Stage 3.6（stage36_evolution.py） | Stage 3.7（proof_policy_optimizer.py） |
|---|---|---|
| 优化对象 | **证明代码**（Lean 的修复） | **证明策略**（如何选择变异策略 + 并行 + 放弃） |
| 机制 | 冻结评估器 + 5 固定策略 ε-greedy | 策略参数重放评估 + 迭代改进 |
| 关系 | 进化循环 | 进化循环的**元层** |

两者正交：Stage 3.6 跑进化时，用 Stage 3.7 学到的策略参数（strategy_weights）来指导
「选哪个变异动作」。Stage 3.7 的 archive 输入 = Stage 3.6 的 archive.jsonl 输出。

---

## 验证结果（自测）

```
=== W=1 vs W=2（均匀权重）===
W=1: quality=29.5 cost=2  →  W=2: quality=31.5 cost=4   （并行探索更广，成本更高）
=== β1 惩罚成本 ===
β1=0.1: score=32.1  →  β1=5.0: score=12.5               （增大成本惩罚 → score 下降）
=== β2 奖励并行 ===
β2=0.5: W=2-W=1 差距=2.3  →  β2=5.0: 差距=6.8           （增大并行奖励 → 高并行优势放大）
=== 权重影响选择 ===
偏好 axiom/tactic: quality=29.5  →  偏好 repair_dangling: quality=2.0
=== 全流程 optimize + 单调性 ===
初始 V=32.1 → 最终 V=33.0（P3 单调性保证）
```

---

## 用法

```bash
# 离线全流程自测（不调 LLM）
python proof_policy_optimizer.py --self-test

# 元优化（dry-run：仅参数扰动，无 LLM）
python proof_policy_optimizer.py \
    --archive /path/to/stage36/archive.jsonl \
    --rounds 3 --candidates 8 \
    --beta1 0.1 --beta2 0.5 \
    --output /tmp/policy_opt/ --dry-run

# 元优化（含 LLM 策略开发：v4-flash 读重放轨迹改进策略）
python proof_policy_optimizer.py \
    --archive /path/to/stage36/archive.jsonl \
    --rounds 3 --candidates 8 \
    --output /tmp/policy_opt/
```

输出：`policy_result.json`（best_policy + final_eval + policy_log 每轮策略参数与重放得分）。

---

## 与 Dream-RSI 的对应关系

| Dream-RSI 概念 | Stage 3.7 落地 |
|---|---|
| exploration policy（可执行代码） | `ProofPolicy`（4 参数对象） |
| discovery tree → replay simulator | archive.jsonl 去重 condition → 决策点 |
| offline evaluation | `PolicyReplayEvaluator.evaluate()`（历史重放，不调 LLM） |
| replay objective（质量 − β1·成本 + β2·并行） | `V = quality − β1·cost + β2·avg_parallel`（P2） |
| policy improvement（策略开发 agent） | `develop_candidates`（参数扰动 + 可选 v4-flash） |
| policy selection（单调保证） | 候选集含 π_t，选 max（P3） |

**未落地的部分**：Dream-RSI 的「发现树结构重放」（树 parent-child 关系）留作 P1——
当前 archive.jsonl 是扁平列表，按 condition 去重近似决策点，未重建完整树结构。
