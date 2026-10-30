# 神经记忆大脑挂接（neural_memory_data，2026-10-13 重新挂接）

给 `scripts/jspace_bridge.py` 的动态 J-score 提供真实大脑后端。**已在本机验证通过**。

## 数据与代码位置

| 资产 | 位置 | 规模 |
|---|---|---|
| 大脑数据 | `<WORK_DIR>\neural_memory_data\` | 181,488 神经元 / 8,442,530 连接 |
| ├ neurons.json | 同上 | 939 MB |
| ├ embeddings.npy | 同上 | 185.7 MB（181,348 × 256 维 float32） |
| ├ connectivity.parquet | 同上 | 137.8 MB |
| ├ embedding_ids.json | 同上 | 3.6 MB（id 为 `n000000` 编号式，非语义名） |
| ├ evolution_state.json / meta.json | 同上 | 3.0 MB / 94 B |
| 大脑代码 | `<WORK_DIR>\neural_memory_brain.py` | `NeuralMemoryBrain` 类 |
| 原始压缩包 | `<WORK_DIR>\neural_memory_data.rar` | 381 MB（保留） |

## 路径解析（jspace_bridge.py 内建，env 优先）

```
数据目录: 显式参数 > $NEURAL_MEMORY_DIR > 候选探测(<WORK_DIR>\neural_memory_data,
          <WORK_DIR>\pyhsics_proof__engine_v5Hybrid\neural_memory_data,
          ~/projects/ai_for_science/neural_memory_data) > 末位回退
代码目录: $NEURAL_MEMORY_CODE_DIR > 探测含 neural_memory_brain.py 的目录
          (<WORK_DIR>, <WORK_DIR>) > ~/projects/ai_for_science
```

探测判据：数据目录须含 `embeddings.npy`；代码目录须含 `neural_memory_brain.py`。**无本机路径硬编码**——换机器只需把数据放到任一候选位或设 env。

## 运行环境要求

- **numpy 必需**（系统 `py` 无 numpy，勿用）。本机可用解释器：
  - `<LEAN_PROJECT>\.conda\python.exe`（numpy 2.3.5，推荐）
  - `D:\embeddinggemma_ft\venv\Scripts\python.exe`（numpy 2.5.4）
- 无需 faiss/hnswlib（后端为 numpy 矩阵余弦检索）

## 接口契约（新旧后端差异，适配层已兼容）

`NeuralMemoryBrain.recall(query, top_k) -> List[Dict]`，字段：
```python
{"title": content[:80], "content": ..., "activation": float,  # ← 余弦相似度字段名是 activation 不是 similarity
 "neurotransmitter": "Glutamate"}
```
- **无 `id` 字段**（新后端召回结果不带 neuron id）
- **无 `graph.neurons`** 结构（旧 jspace_bridge 依赖此属性取 embedding，会导致 J-score 恒 0）
- 代表向量正确取法：`brain._embed_query(concept)`（匹配神经元 embedding 的归一化均值）
- 底层矩阵：`brain._ids`（181,348 个 `nXXXXXX`）+ `brain._embeddings_normed`（256 维）

`jspace_bridge.py` 的 `_concept_signature()` 已实现三级兼容：
1. 旧后端：`r["id"]` + `graph.neurons[id].embedding`
2. 新后端逐条：`_embedding_for_result(r)`（按 content 反查 `_ids`/`_embeddings_normed`，含前缀匹配兜底）
3. 新后端回退：`brain._embed_query(concept)` 作代表向量

## 验证结果（2026-10-13 实测）

```bash
# 1) 离线自测（mock brain，不加载 181K 神经元）
<conda_python> scripts/jspace_bridge.py --self-test        # → 自测通过 ✓

# 2) 真实挂接自检（~23 秒加载）
<conda_python> scripts/brain_hookup_check.py
```

实测输出：
```
resolved data_dir : <WORK_DIR>\neural_memory_data
resolved code_dir : <WORK_DIR>
brain loaded in 22.7s
recall('KLS spectral gap') -> 0.9293 / 0.9280 / 0.9276
J-score pair: {"j": 0.3886, "sim": 0.9715, "mi": 0.0, "co_activation": 0.0, "valid": true}
```

## 诚实边界

1. **mi / co_activation 在真实大脑上恒为 0**：top-20 召回集合在 181K 神经元里几乎不重叠（Jaccard≈0），因此 J ≈ 0.4·sim，二、三成分实际不贡献信号。这是数据规模决定的，非 bug。
2. **id 为编号式（`n000000`）**：召回结果无法直接映射回定理名，只能提供语义相似度信号；如需"召回 → 引理名"，须另建 id↔名字映射表（当前无此映射）。
3. **加载昂贵（~23 s）**：设计为一次性子进程（`run_jspace_grounding`），不可内联进每代进化循环。
4. **阈值须重标定**：动态 J-score 值域与硬编码 12×12 快照不同，用 `calibrate()` / `calibration_hint` 按当前脑分布定阈值，勿沿用 0.70/0.50。
