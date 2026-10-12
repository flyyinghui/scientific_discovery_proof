# AIDE²/RSI 集成记录（v2.20.0, 2026-10-12）

## 来源

- Weco AI《Recursive Self-Improvement of AI Research Agents》（2026-09-22，AIDE² 实验）
- 项目解读《AIDE²: The First Evidence of Recursive Self-Improvement》

AIDE² 是第一个「净正递归自我改进」（RSI Level 1）的实验证据：双层架构（外层 agent 优化内层
agent 代码，~10% 接受率），8 天 100 步产出 7 个连续改进版本，泛化到 3 个外部基准打败 2 年手调
基线，且 reward-hacking 率从 63% 自发降到 34%。

## 与已有框架的覆盖对比

scientific-discovery-proof v2.19.0 已集成的 8 个框架中，RSI 相关已有 3 个，覆盖 AIDE² ~80% 机制：

| AIDE² 机制 | 已覆盖 | 来源 |
|---|---|---|
| 双层 RSI（外层优化内层）| ✅ | RSIHub v2.4.0（Stage 3.6 进化循环）|
| 冻结评估器 | ✅ | RSIHub（MathCode 确定性评分）|
| 严格门控（拒绝退化）| ✅ | RSIHub（严格改进门控）|
| 防 reward hack | ✅ | RSIAgent v2.14.0（`_detect_reward_hack`）|
| 失败路径记录 | ✅ | Colosseum v2.11.0 + prove2me v2.19.0 |
| 重放历史 | ✅ | Dream-RSI v2.7.0（replay_strategies）|
| 策略元优化 | ✅ | Dream-RSI v2.12.0（proof_policy_optimizer）|
| RSI 等级评估（Level 0-3）| ❌ → **本次落地** | — |
| 点火测试（ignition）| ❌ → **本次落地** | — |
| 隐藏评分机制（hidden score）| ⚠️ → **本次落地** | — |

## 三项增量落地

### P0-① RSI 等级评估（`stage36_evolution.py` 新增 `assess_rsi_level`）

进化循环总结时输出 `rsi_level_assessment` 字段，诚实标注处于哪个 AIDE² 阶梯：

- **Level 0 委托**：无净正增益（best_score ≤ seed_score 或未运行进化）。
- **Level 1 净正**：产生净正改进（best_score > seed_score）。
- **Level 2 点火**：改进自身改进能力（由 ignition_test.py 独立诊断，本函数默认 inconclusive）。
- **Level 3 拐点**：永不声称（AIDE² 也明确否认达到拐点）。

同时量化接受率（P3-⑤）：`acceptance_rate = n_accepted / n_total`（AIDE² ~10% 接受率的对等指标）。

### P0-② 点火测试（新 `scripts/ignition_test.py`）

读 archive.jsonl，按 generation 分前/后两半比较接受率 + 平均 gain：

- 后期接受率显著高于早期（≥15 个百分点）或后期平均 gain 显著更高（≥5 分）→ 点火弱信号（Level 2 候选）。
- 否则 → 净正（Level 1）。

这是「改进自身改进能力」的唯一可操作诊断（AIDE² 的点火测试：发现的 agent 重坐外层循环达同样
天花板步数更少——本脚本用「接受率趋势」作为离线代理）。

### P1-③ 隐藏评分机制（`stage36_evolution.py` gate 阶段）

把评分拆双通道：

- **可见分数**：`evaluate_lean` 的 score（编译 0 sorry 等）。
- **隐藏分数**：`_run_content_audit` 调用 `physical_content_audit.py` 的 BLOCK 数（定义重言式/字面恒等式）。

gate 逻辑：只在可见分数提高 + 无 reward hack 时才跑隐藏审计，物理内容零重言式才通过。
AIDE² 借此把 reward-hacking 率从 63%→34%——隐藏标准（物理内容非平凡）而非可见标准（0 sorry）才是
真正门槛。

## 用法

```bash
# Stage 3.6 进化循环（自动输出 rsi_level_assessment）
python stage36_evolution.py --lean /path/to/proof.lean --output /tmp/stage36/

# 点火测试（独立诊断 Level 2）
python ignition_test.py --archive /tmp/stage36/archive.jsonl --output /tmp/ignition.json
```

## 诚实边界

1. **P0-① 是诚实标注**：只区分 Level 0/1，Level 2 由 ignition_test 诊断，Level 3 永不声称。
   这与「预测度会计」方法论一致——防止把「净正改进」误标为「点火/智能爆炸」。
2. **P0-② 是趋势诊断**：接受率趋势是「改进自身改进能力」的弱代理，非严格证明。
   AIDE² 的点火测试本身也是「不明确」（统计不显著）。
3. **P1-③ 是事前预防**：物理内容非平凡门槛是启发式，非形式化保证；真正的阻断靠
   Stage 3.5 审计 + physical_content_audit 的 BLOCK 门控。
