# Stellar Colosseum Integration Assessment (arXiv:2609.15983, Google, 2026-09-15)

> 评估：Stellar Colosseum 多智能体长程研究 harness 对 scientific-discovery-proof 的可移植增量。
> 结论：**不改变主线五阶段管线**，可增量嫁接 5 个独有模块（3 个正确率 + 2 个发现概率）。
> 与已集成 RSIHub/Dream-RSI/RSIAgent/Co-Scientist/ScientistTwo 的 diff 见文末。

## 论文核心（四阶段管线 + 阶段内对抗推理）

Colosseum = model-agnostic many-agent harness，把长程研究分为四阶段：
**Strategy Exploration（探索策略）→ Decomposition（分解 DAG）→ Parallel Proof Construction（并行求解）→ Global Verification（全局验证）**，
阶段内用「并行生成 + 定向证伪 + 重叠随机采样树聚合」。
结果：TCS-Bench 71.0%（Gemini 3.1 Pro + 3.7 Flash）；Codeforces 218/222；独立复现 Erdős 单位距离突破；已集成 Google Antigravity Teamwork「Long Proof」模式。

## 可移植增量（P0-P2 性价比排序）

### P0-1 Targeted Falsification 缺陷分类学 → Stage 3.5 L2 扩展（正确率）
- **Colosseum 独有**：定向证伪的 6 类缺陷：①反例/边界情形 ②无效蕴含/**静默强化假设** ③循环论证/未声明依赖 ④定理误用 ⑤**证明命题 ≠ 目标命题** ⑥**后续 section 所需假设缺失**。
- **当前管线缺口**：Stage 3.5 L2 只有 6 类 P0（公理自相矛盾/表演性诚实/公理计数/幻影定理/空壳/离散谱），**缺 ⑤⑥**（证明的命题与目标命题不一致、后续依赖的假设缺失）和 **②的「静默强化假设」**。
- **嫁接**：`proof_consistency_audit_l2.py` 新增 3 条检测规则：`strengthened_hypothesis`（结论比假设强）、`proved_vs_target_mismatch`（theorem 声明 vs 论文目标命题）、`missing_downstream_assumption`（被下游引用的引理缺前提）。均映射 Colosseum ②⑤⑥。

### P0-2 前向分解为 DAG 子问题 + 局部重试 → 新 Stage 2.7（正确率 + 效率）
- **Colosseum 独有**：**证明前**把猜想分解为「编号 section 骨架 + 依赖 DAG」，独立 section 并行求解，失败 section **局部重试**（不动其他已完成 section）。
- **当前管线缺口**：Stage 3.5c `proof_dag_audit.py` 是**证明后**（backward）提取 DAG；管线证明过程是**整体串行**的（MCTS/ABC 单文件）。
- **嫁接**：新增 `scripts/preproof_decomposer.py`——在 Stage 3 前把 conjecture 分解为 section 级子问题 DAG（v4-pro 生成），Stage 3 改为**按依赖顺序并行**生成各 section 的 Lean 片段再拼装；失败 section 仅重试该段。**注意**：这是对 Stage 3 内部的组织方式升级，不动 Stage 3 的 MCTS/ABC 算法本身。

### P0-3 全局验证缺陷定位 → Stage 3.5 升级（正确率）
- **Colosseum 独有**：全局验证把每个缺陷**绑定到具体 section/claim**；跨 section 依赖错误**同时指出支撑 section 与使用 section**，使审阅可操作。
- **当前管线缺口**：Stage 3.5 报告缺陷但**不定位到 section**，跨 section 依赖错误不识别双方。
- **嫁接**：`proof_consistency_audit.py` 的报告增加 `defect_location`（缺陷所在 section/行号）+ 跨 section 依赖错误的 `{supporting_section, using_section}` 对。

### P1-1 Strategy Exploration + Readiness Gate → 新 Stage 0.5（发现概率，核心杠杆）
- **Colosseum 独有**：**证明前**探索替代证明策略（重构/约化/中间目标/已知结果关联），而非锁定第一个可行想法；readiness gate 判断「路线是否成熟到可分解」（中心约化稳定、未决声明可精确指派、无未决桥接改变架构）。
- **当前管线缺口**：管线从给定 conjecture 直入证明，**不探索「哪条证明路线」**。发现概率的真正杠杆在「选对路线」。
- **嫁接**：新增 `scripts/strategy_explorer.py`——Stage 0 前生成多条候选证明路线（各含机制/所需引理/预期瓶颈/可证伪测试），readiness gate 打分选路，喂给 Stage 3。**与 MAF/SciExplorer 不冲突**（那些验证数值/符号，这个探索路线）。

### P1-2 Knowledge Directory「失败路径」→ Stage 3.6 archive 升级（发现概率）
- **Colosseum 独有**：知识目录记录四类可复用知识，其中**「失败路径 + 精确失败点 + 变体仍可用的条件」**最独特。
- **当前管线缺口**：archive.jsonl 记录因果三元组（actions→conditions→consequences），但**不记录「失败路径的精确失败点 + 变体可行条件」**。
- **嫁接**：`stage36_evolution.py` 的 record 新增 `failed_approach` 字段（route + failure_point + variant_condition），变异前注入「已知失败路径」避免重复。

## 与已集成框架的 diff（避免重复）

| Colosseum 模块 | 已集成等价物 | 是否重复 |
|---|---|---|
| Retaining prior attempts | Dream-RSI replay simulator + archive | 重复（不接） |
| Knowledge directory（theorems/refs/observations） | archive 因果三元组 + 大脑概念 | 部分重复（仅接「失败路径」） |
| Adversarial review | 5-agent Hybrid Review + Stage 3.5 L2 | 部分重复（仅接缺陷分类学 ②⑤⑥） |
| 局部重试 | Stage A strict-superset 递归修复 | 部分重复（Colosseum 是**局部**，Stage A 是整体） |
| Tree overlapping aggregation | MCTS/ABC 树搜索 | 部分重复（不接，边际） |
| **Strategy exploration + readiness gate** | **无** | **新（接）** |
| **前向 DAG 分解 + 并行** | 无（DAG 是 backward 审计） | **新（接）** |
| **缺陷定位到 section** | 无 | **新（接）** |

## 关键教训：Colosseum 比 ScientistTwo 更对口

Colosseum 是**数学/TCS 形式化证明** harness（与 scientific-discovery-proof 同域），非 ScientistTwo 的经验 ML。
其「策略探索→分解→并行→全局验证」四阶段**直接对应**证明管线的正确组织方式。
最核心的可移植洞察：**管线目前从猜想直入证明（Stage 3），缺「探索策略 + readiness gate + 前向分解」三段**——
这是正确率（分解强制显式依赖结构）和发现概率（选对路线）的双重杠杆。

## 落地优先级

- **P0（3 个正确率增量）**：Targeted Falsification 缺陷分类学（扩 L2）+ 前向 DAG 分解 + 缺陷定位。均 stdlib/轻 LLM，直插 Stage 3.5 / Stage 3 前。
- **P1（2 个发现概率增量）**：Strategy Exploration + Readiness Gate（Stage 0.5 前置）+ Knowledge Directory 失败路径（扩 archive）。
- **P2（不接）**：Tree overlapping aggregation / Retaining attempts（与 MCTS/ABC + Dream-RSI 重叠）。

论文全文 text 存 `H:\中国数据\papers\2609.15983_StellarColosseum_text.txt`。
