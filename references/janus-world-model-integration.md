# JANUS 世界模型集成 — 评估与落地 (v2.21.0, 2026-10-12)

**来源论文**：JANUS: Predict-Verify-Evolve（中科院计算所 AI 安全国重，arXiv:2610.13194）
**开源主页**：https://github.com/bilemond/JANUS

## 论文核心机制

JANUS 用「共同进化世界模型」解决长程自主研究的**反馈延迟**问题（LLM 变异 + 编译
的反馈太慢、太贵）。三阶段循环：

```
Predict（预测）: 世界模型执行前三标准打分 → refine/select/prune
Verify（验证）:  executor 实现并评估选中候选
Evolve（进化）:  成功/失败轨迹蒸馏为层次技能 + 探索策略技能 + 协调协议
```

论文报告 **3.74× 样本效率加速**（vs Codex，实验计数），消融证实研究 agent 与
世界模型互补（单独用 agent 或单独用世界模型都不如共同进化）。

## 评估结论（与既有框架的互补性）

JANUS 最独特的增量是**世界模型（预执行预测）**——在昂贵 executor 之前用三标准
打分预筛选候选。对照本技能已集成的框架：

| 框架 | 定位 | 与 JANUS 的关系 |
|---|---|---|
| RSIHub 冻结评估器 | 事后定论（候选不能改写评分规则） | JANUS 世界模型是**事前预筛选**，不替代冻结评估器 |
| Dream-RSI 重放模拟器 | archive.jsonl 历史统计（策略成功率） | JANUS 世界模型**复用** ReplaySimulator 的历史统计做预测 |
| AIDE² 隐藏评分 | 外层用隐藏分数防 reward-hack | JANUS 三标准是**预筛选排序**，不改变最终门控 |
| AIDE² 点火测试 | RSI Level 2 诊断 | 正交 |

**关键诚实边界**：
1. 世界模型是**预筛选器**，不能替代 RSIHub 的冻结评估器（否则违反「评估器不能被
   候选改写」原则）。
2. JANUS 的 3.74× 是「实验计数」，非 token/时间——论文没展示世界模型的计算开销
   是否被抵消。**移植时世界模型必须比 Lean 编译快一个数量级才有意义**。本落地的
   世界模型是纯历史统计（O(archive 大小)，毫秒级），远快于 LLM 变异 + 编译，满足
   此约束。

## P0 落地内容

### P0-① 世界模型（预执行预测）— `scripts/world_model_prescreen.py`

`WorldModel.predict(defects, strategy)` 用 archive.jsonl 历史预测一次
(strategy × condition) 变异的结果：

- **predicted_gain**：期望分数提升（condition 级历史 → strategy 级历史 → 冷启动 0）
- **zero_sorry_prob**：达成 0 sorry 的概率（历史接受率，含 learn_on_pass）
- **verdict**：`KEEP` / `PRUNE`（有足够历史 + 预测无增益 + 0-sorry 概率低 → PRUNE）

已接入 `stage36_evolution.py` 进化循环：每代变异前调用 `world_model.predict()`，
PRUNE 则跳过本次 LLM 变异 + 编译（省成本），记录 `world_model_pruned=True` 到
archive。**PRUNE 只省成本，不替代冻结评估器**——幸存者仍走冻结评估器 + 隐藏
物理内容审计定最终分数。

### P0-② 三标准评分（价值 + 信息增益 + 探索效用）— 同脚本 `three_criteria_score()`

把 JANUS 三标准落到 Stage 3.6 候选评估，补当前只有「单一缺陷扣分」的缺口：

| 标准 | 落地 | 补的缺口 |
|---|---|---|
| ① 价值 value | 冻结评估器分数 + predicted_gain | 已有（冻结评分） |
| ② 信息增益 info_gain | 盲区缺陷占比（历史从未修复成功的类型）+ 新 condition 奖励 | **新增**：区分「重复已知修复」vs「学到全新信息」 |
| ③ 探索效用 explore | UCB `sqrt(2·ln N / n)`（欠采样策略加分） | **新增**：Stage 3.6 进化循环里缺探索项（Stage 2 有 UCB，Stage 3.6 没有） |

已接入 `stage36_evolution.py`：每个 archive record 新增 `three_criteria` 字段。
三标准**不替代**冻结评估器，只做预筛选排序 + 记录归档；最终接受/拒绝仍由
冻结评估器分数 + 隐藏物理内容审计（AIDE² P1-③）决定。

## 使用

```bash
# 世界模型 + 三标准评分 离线自测
cd ~/.hermes/skills/scientific-discovery-proof/scripts
python world_model_prescreen.py --self-test

# 已自动接入 stage36_evolution.py（无需额外参数）
python stage36_evolution.py --lean /path/to/proof.lean --generations 3 --output /tmp/stage36/
```

## 自测结果（2026-10-12）

```
三标准评分（sorry=2, axiomatize, 冻结分 60）:
  value=60.0, predicted_gain=20.0, info_gain=0.0, exploration_utility=0.937
世界模型 predict（axiomatize × sorry，有成功历史）:  predicted_gain=20.0, 0-sorry=1.0 → KEEP
世界模型 predict（deduplicate × redundant，有失败历史）: predicted_gain=-10.0, 0-sorry=0.0 → PRUNE
世界模型 predict（repair_dangling × dangling，冷启动）:   predicted_gain=0.0, 0-sorry=None → KEEP
```

## 诚实边界汇总

1. 世界模型是**预筛选器**（省成本），不是最终门控——冻结评估器 + 隐藏物理内容
   审计仍然决定接受/拒绝。
2. 三标准是**排序 + 归档**信号，不改变接受判定——避免用「探索效用」给低质量
   证明放行（那会 reward-hack 探索奖励）。
3. 世界模型纯历史统计，**无 LLM**，确定性——候选者无法改写，满足 RSIHub 的
   「评估器冻结」原则。
4. 冷启动（无历史）时 info_gain=1.5（所有缺陷都是盲区 + 新 condition），探索
   效用=1.0——世界模型不会在冷启动时误剪枝（`n_history < MIN_HISTORY` 强制 KEEP）。
