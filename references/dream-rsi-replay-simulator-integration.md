# Dream-RSI 重放模拟器整合（Stage 3.6 P0-P2 落地实录）

**来源**：Dream-RSI: Recursive Self-Improvement through Evolving Worlds（arXiv 2609.14858，Google + DeepMind）
**落地日期**：2026-09-17
**改动文件**：`stage3_ppe/replay_strategies.py`（新增）+ `stage3_ppe/stage36_evolution.py`（改造）

---

## 核心洞察对齐

Dream-RSI 一句话：「**积累的发现历史本身就是一个可重放的模拟器**」。

Stage 3.6 原本的 `archive.jsonl` 只是**被动记录**（存分数 + 缺陷 + 是否接受）。本落地把它升级为**主动重放预筛选器**——统计各变异策略的历史成功率 + 对各类缺陷的修复率，在每代变异前排序推荐。

---

## 三个落地项

### P0 — archive.jsonl → Replay Simulator

`ReplaySimulator` 类（`replay_strategies.py`）：

- `strategy_stats()`：各策略 `{attempts, accepted, success_rate, avg_gain}`
- `defect_repair_rate()`：各策略对各类缺陷的修复率（依据 `defects_before` → `defects` 差值）
- `rank_strategies(defects, epsilon)`：ε-greedy 排序

**评分公式**（针对性是硬门槛）：
```
targeted = 策略 targets 与当前活跃缺陷的重叠数
if targeted == 0:  score = 0.05 × success   # 不针对当前缺陷，几乎不推荐
else:              score = success × (0.5 + 0.5 × targeted)
```
历史失败惩罚：若策略对某活跃缺陷的历史修复率为 0，`success ×= 0.5`。

### P1 — off-policy 反馈（盲区检测）

`blind_spots(defects)`：返回当前活跃缺陷中「历史上从未被任何策略成功修复过」的类型。

作用：注入 `_analyze` 诊断 prompt 的【历史盲区警告】，提示 LLM「常规方法可能无效，请尝试全新思路」。

### P2 — 变异策略显式化

单一「诊断→修复」拆成 5 个可独立评估的策略：

| 策略 | 针对性缺陷 | 描述 |
|---|---|---|
| `repair_dangling` | dangling_refs | 修复悬空引用 / 补齐缺失声明 |
| `axiomatize` | sorry, admit | sorry/admit 改写为诚实公理或真实证明体 |
| `tactic_complete` | trivial_or_true_stub | 消除 `:= by trivial` / `:= True` 空壳 |
| `lemma_decompose` | sorry, trivial_or_true_stub | 分解过长定理为中间引理 |
| `deduplicate` | redundant_lemmas, unused_axioms | 删除冗余引理 / 未用 axiom |

每代用 `replay.choose(defects, epsilon)` 做 ε-greedy 选择（ε=0.15），`_mutate` 按策略 `focus` 定制 prompt。

---

## archive.jsonl 新字段

```json
{
  "generation": 1,
  "score": 62.0,
  "defects": {...},
  "accepted": true,
  "parent_score": 42.0,
  "gain": 20.0,
  "mutation_strategy": "axiomatize",       // 新增：本次变异用的策略
  "defects_before": {...},                 // 新增：变异前缺陷（用于修复率统计）
  "timestamp": "..."
}
```

旧记录（缺 `mutation_strategy`）在 `load()` 里归为 `unknown`，不计入统计，向后兼容。

---

## 验证结果

### 冷启动（无历史）
```
[Gen 0] score=42.0  sorry=1 admit=1 空壳=1 冗余引理=2 未用axiom=1
[Replay] 策略推荐（冷启动，针对性排序）:
  axiomatize       score=0.750 针对性=2 历史成功率=—
  lemma_decompose  score=0.750 针对性=2
  deduplicate      score=0.750 针对性=2
  tactic_complete  score=0.500 针对性=1
  repair_dangling  score=0.025 针对性=0   ← 无悬空缺陷，不推荐
[Replay] 历史盲区: sorry, admit, trivial_or_true_stub, redundant_lemmas, unused_axioms（全部）
```

### 读历史 archive（跨运行累计）
```
[Replay] 策略推荐（历史驱动）:
  axiomatize       score=0.750 针对性=2 历史成功率=1.0 尝试=1   ← 历史成功，排第一
  lemma_decompose  score=0.750 针对性=2 历史成功率=—
  deduplicate      score=0.750 针对性=2 历史成功率=—
  repair_dangling  score=0.025 针对性=0
  tactic_complete  score=0.000 针对性=1 历史成功率=0.0 尝试=1   ← 历史失败，被惩罚
[Replay] 历史盲区: admit, trivial_or_true_stub, redundant_lemmas, unused_axioms（sorry 不再是盲区）
```

关键信号：`axiomatize` 因历史成功（1.0）排第一；`tactic_complete` 因历史失败（0.0）被惩罚到 0；盲区从 5 类降到 4 类（sorry 已被历史修复）。

---

## 用法

```bash
# 自测 replay 模块（离线，不调 LLM）
python replay_strategies.py --self-test

# 进化（含 replay 策略选择）
python stage36_evolution.py \
    --lean /path/to/proof.lean \
    --generations 5 \
    --epsilon 0.15 \
    --output /tmp/stage36_out/

# 只评估 + 看 replay 推荐（不调 LLM）
python stage36_evolution.py --lean /path/to/proof.lean --dry-run
```

---

## 与 Dream-RSI 的对应关系

| Dream-RSI 概念 | Stage 3.6 落地 |
|---|---|
| 发现历史（discovery trees） | `archive.jsonl`（跨运行 append-only）|
| replay simulator | `ReplaySimulator`（strategy_stats + defect_repair_rate）|
| dreaming（离线评估）| `rank_strategies` + `blind_spots`（不调 LLM，纯历史统计）|
| off-policy 反馈 | 盲区检测 + 历史成功率惩罚，注入诊断 prompt |
| 探索策略（exploration policy）| 5 个 `MUTATION_STRATEGIES` + ε-greedy `choose()` |
| self-improving loop | 每代 `replay.records.append(record)` 即时扩展重放池 |

**未落地的部分**：Dream-RSI 的「探索策略本身的元优化」（用重放数据改进策略参数，如调整 ε 或策略 focus）留作后续 P2+。当前 ε 固定 0.15。
