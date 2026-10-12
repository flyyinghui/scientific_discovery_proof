# J-space 桥接矩阵动态化 — 落地记录 (v2.22.0, 2026-10-12)

**问题**：`references/jspace-bridge-matrix.md` 描述的 J-space 桥接矩阵是技能里**唯一一个
「文档化但零实现」的幽灵子系统**——SKILL.md Stage 3 宣传「J-space 桥接矩阵 (Brain 170K
神经元)」，但代码路径从未真正调用 brain.recall() 算 J-score；Stage 1 的 `j_score_hint`
是纯占位符 `0.5 + 0.3*(passed/total)`，与大脑和桥接矩阵完全无关；Stage 3 甚至显式传
`--skip-brain-merge`。

## 落地内容（P0-① + P0-②）

### 1. 新脚本 `scripts/jspace_bridge.py` — 动态 J-space + J-score

替代硬编码 12×12 快照，用 `brain.recall()` 真实语义检索**动态重算**：

- **J-score 三成分**（对齐 reference 公式 J = 0.4·sim + 0.3·MI + 0.3·co_activation）：
  - `sim(a,b)` = 概念代表向量的余弦相似度（代表向量 = recall top-k 结果 embedding 的
    相似度加权平均）。负值归零（「支持度」语义下无语义支持 = 0）。
  - `MI(a,b)` = 召回 neuron id 集合的 Jaccard 共现（知识图谱重叠）。
  - `co_activation(a,b)` = 共同召回比例（同时被激活的频率）。
- **动态桥接矩阵**：`build_matrix(concepts)` 对任意概念集重算 N×N 矩阵。
- **概念提取**：`extract_concepts(conjecture)` 从 conjecture.json 的 claims/axioms/targets
  提取相关规范概念（12 个 SL(6,C) 默认概念）。
- **决策**：`decision(j)` 输出 direct_theorem / honest_axiom / postulated_or_reject。
- **标定提示**：`calibrate(matrix)` 基于实际 J-score 分布给阈值重标定建议。

### 2. 接入 pipeline_orchestrator.py

- 新增 `run_jspace_grounding(conjecture_path, output_dir, skip_brain)`：一次性子进程
  （加载 181K 神经元大脑一次 → 算全部概念 J-score → 退出），输出 `stage_jspace.json`。
- 在 main() 里 spec_check 之后、Stage 循环之前运行，结果存 `results['jspace']`。
- Stage 1 的 `j_score_hint` 占位符 → 真实 `path_j_score`（无 jspace 时回退旧启发式）。
- 新增 `--skip-brain` CLI 开关（优雅降级，不阻断管线）。

### 3. J-score 喂给 JANUS 世界模型（闭环）

- `WorldModel.predict(defects, strat_name, j_score=None)`：新增 J-space 先验。
  **j_score ≥ 0.5 → 保护候选不被历史剪枝**（大脑强支持说明概念已充分落地，即使策略
  历史弱也值得一试）；j_score < 0.5 不改变历史剪枝判定。
- `three_criteria_score(..., j_score=None)`：新增 `brain_support` 报告字段（先验，
  **不参与**三标准加权——先验≠奖励准则）。
- `stage36_evolution.py`：新增 `--j-score` CLI 参数，缺省时自动读
  `<output>/../stage_jspace.json` 的 path_j_score，注入世界模型 + 三标准评分。

## 诚实边界（关键）

1. **动态 J-score 值域 ≠ 硬编码矩阵值域**。硬编码矩阵（0.08–0.89）是脑 170K 时的估计
   快照；动态重算后 sim∈[0,1]、MI（Jaccard）在 181K 神经元下通常很小、co_act∈[0,1]。
   因此**决策阈值 0.70/0.50 需按当前脑重标定**——`calibrate()` 输出数据驱动的新阈值
   建议，不盲目沿用旧阈值。
2. **J-score 是「先验支持度」信号，非硬门控**。硬门控仍由 Stage 3.5 审计（自洽性 /
   物理内容 / DAG）负责。无 brain / 超时 → 优雅降级 PASS + note，不阻断管线。
3. **大脑加载昂贵**（181K 神经元 ~35-170s），jspace_bridge 设计为**一次性子进程**
   （懒加载 + 缓存概念签名），绝不内联进每代进化循环（那会让每代重新加载 181K 神经元）。
4. **世界模型的 j_score 保护不改变冻结评估器**：它只影响「是否跳过这次 LLM+编译」，
   幸存者仍走冻结评估器 + 隐藏物理内容审计定最终分数。

## 自测结果（2026-10-12）

```
J(A,B) [相关概念，重叠 2 neuron]: j=0.747, sim=0.993, mi=0.5, co_act=0.667
J(A,C) [孤立概念，零重叠]:        j=0.007, sim=0.017, mi=0.0, co_act=0.0
extract_concepts(conjecture):     ['g_Ricci', 'g_KLS', 'p_M_R']

j_score 先验保护：
  无 j_score  → PRUNE（历史剪枝）
  j_score=0.6 → KEEP（大脑强支持保护）
  j_score=0.1 → PRUNE（大脑弱支持不保护）
```

## 使用

```bash
# J-space 独立运行
python jspace_bridge.py --conjecture conjecture.json --output /tmp/jspace.json
python jspace_bridge.py --concepts "Ricci curvature,KLS spectral gap" --output /tmp/jspace.json
python jspace_bridge.py --self-test        # mock brain 离线自测

# 已接入 pipeline_orchestrator.py（--skip-brain 可跳过）
python pipeline_orchestrator.py --conjecture conjecture.json --stages 1,2,3,4
```

## 与既有框架的关系

- **brain_bridge.py**（physics_proof_engine 内）：保留，是 brain.recall 的检索封装
  （定理检索/找矛盾/策略建议）。本模块是它的**补充**——补上 J-score 桥接矩阵（brain_bridge
  从未实现 J-score）。
- **JANUS 世界模型**（v2.21.0）：J-score 作为「先验支持度」喂给 WorldModel.predict 的
  PRUNE 保护，形成「大脑知识 → 证明策略预筛选」闭环。
- **EmbeddingGemma-2**（Stage 4.5）：独立的 768 维语义空间，与大脑 embedding 空间
  互不相通（P2 级可选优化，未做）。
