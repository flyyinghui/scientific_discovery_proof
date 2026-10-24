# EmbeddingGemma-2 Lean 引理检索模型 — 接入 scientific-discovery-proof

> 接入日期：2026-10-13
> 模型包：`D:\AI_Training\EmbeddingGemma2_Lean检索模型_v2\embeddinggemma-2-lean`（1.5 GB，sentence-transformers 格式）
> 接入目标：scientific-discovery-proof v2.22.0+（Stage 3 引理召回 / Stage 4.5 引用语义核查 / J-space sim 后端）
> 依据：`D:\AI_Training\EmbeddingGemma2_Lean检索模型_v2\README_接入方法.md`

---

## 一、模型速览

| 项 | 值 |
|---|---|
| 基座 | `google/embeddinggemma-2`（740M 多模态：文本塔 + 音频塔 + 视觉塔） |
| 文本维度 | 768（text_config: hidden 512 × 24 层，per-layer 特殊配置） |
| 微调数据 | openai_math Lean 证明依赖对 377,098 对（→ 双命中 349,234） |
| 微调方式 | 全参微调，MNRL（MultipleNegativesRankingLoss），batch 256，2 epochs，bf16 |
| 性能 | **recall@10 = 0.5505**（增强文本口径），纯名字口径 0.4663，基座 0.3225 |

任务定义：给定定理名，召回其 Lean 依赖 DAG 中的引理/定义（top-10 命中率）。

---

## 二、环境（独立 venv，勿用 Hermes 主 venv）

```
~/models/EmbeddingGemma2_Lean检索模型_v2/venv/bin/python
```

| 依赖 | 训练版本 | 本机安装版本 | 备注 |
|---|---|---|---|
| torch | 2.11.0+cu128 | **2.5.1+cu121** | 本机 P620（Pascal 6.1）只支持到 cu121 |
| transformers | 5.19.0 | 5.19.0 | **必须 5.x**（4.57.3 不认识 `embedding_gemma2` 架构） |
| sentence-transformers | 6.1.0 | 6.1.0 | |
| numpy | — | <2（torch 2.5.1 兼容） | |

**关键版本陷阱**：
1. Hermes 主 venv（`/usr/local/lib/hermes-agent/venv`）是 transformers 4.57.3 + torch 2.5.1+cu121，
   **不认识 `embedding_gemma2` 架构**（`AutoConfig` 报 "model type `embedding_gemma2` not recognized"）。
   因此**必须独立 venv**，不可复用主 venv。
2. 训练机用 torch 2.11.0+cu128（CUDA 12.8），本机 P620 是 Pascal 架构（算力 6.1）+ CUDA 12.0 驱动，
   **跑不了 cu128**。本机用 torch 2.5.1+cu121（cu121 兼容 CUDA 12.0 驱动 + Pascal）。
3. 模型权重是 **bf16**（1376 张量），P620（Pascal）**不支持 bf16**。加载时必须
   `torch_dtype=torch.float32`（`load_model(dtype="float32")`，脚本默认值）。

安装命令（清华镜像）：
```bash
cd ~/models/EmbeddingGemma2_Lean检索模型_v2
./venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch==2.5.1+cu121
./venv/bin/python -m pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    "transformers==5.19.0" "sentence-transformers==6.1.0" accelerate
```

---

## 三、声明库（declarations.jsonl）

增强文本（sig 120 + doc 60）依赖「短名 → signature + docstring」映射。本机已从
`~/projects/openai_math-main/lean`（150,912 个 .lean 文件）重新解析生成：

```
~/models/EmbeddingGemma2_Lean检索模型_v2/declarations.jsonl
```

- 解析器：`parse_lean_declarations.py`（同目录）
- 每行：`{"name": 短名, "kind": theorem/def/lemma/..., "signature": ..., "docstring": ...}`
- 短名 = 点分名最后一段，冲突保留首见
- **注意**：微调模型语义偏 openai_math（OAI 命名空间）。对 Mathlib 风格命名或本项目自制定理的
  迁移效果未测（README 诚实边界 3）。跨库使用需重新评估。

### 3.1 精选 18 万库 + 预建索引（已完成，2026-10-13）

README 的「18 万声明」实指**微调依赖对里真实出现的唯一 theorem 名**（非全库 185 万）。已构建：

```
declarations_18w.jsonl   # 167,310 条（唯一 theorem 名，覆盖率 100%）
index/emb.npy            # 514 MB（167,310 × 768 float32）
index/names.json         # 5.2 MB（167,310 个名字）
```

- 构建脚本：`build_18w_index.py`（提取依赖对唯一 theorem 名 → 匹配签名 → 建索引，总耗时 ~69 分钟）
- 依赖对来源：`~/projects/lean_dep_pairs/dep_pairs_final.jsonl`（406,045 对）
- **召回已验证**：`resolutionCokernelMap` 正确召回 `resolutionCokernelMap_injective`(0.66) /
  `resolutionMap_cokernel`(0.65) / `..._surjective`(0.63) / `..._comp`(0.63) / `..._exact`(0.62) 等同族定理，
  语义高度相关。
- 查询时直接用缓存索引（`--decls declarations_18w.jsonl`），无需重建。

---

## 四、三个接入点

### 4.1 Stage 3 引理召回（主用途）

**脚本**：`scripts/lean_lemma_retriever.py`（已落地）

为 PPE-V5.1Hybrid 的证明搜索（MCTS/ABC）提供「给定定理 → 候选引理/定义」召回。

```bash
# 用独立 venv 运行
P=~/models/EmbeddingGemma2_Lean检索模型_v2/venv/bin/python
cd ~/.hermes/scientific-discovery-proof/scripts

# 建索引（首次，编码 18 万声明；GPU ~2min / CPU ~30+min，缓存到 index/）
$P lean_lemma_retriever.py --build-index --device cuda

# 召回（定理名）
$P lean_lemma_retriever.py --query resolutionCokernelMap --top-k 10

# 召回（自由文本）
$P lean_lemma_retriever.py --text "spectral gap of Laplacian" --top-k 10
```

核心 API（供 Stage 3 内联调用）：
```python
from lean_lemma_retriever import LemmaRetriever, load_model, load_decls
model = load_model("cuda")            # P620 用 "cpu" 或 "cuda"（float32）
decls = load_decls()
r = LemmaRetriever(model, list(decls.keys()), decls)
r.build_index()                        # 或 r.load_index() 复用缓存
r.recall("resolutionCokernelMap", top_k=10)   # [(name, cos), ...]
```

### 4.2 Stage 4.5 语义引用核查升级（可选，未默认替换）

`scripts/semantic_reference_check.py` 当前用 `litert-community/embeddinggemma-2-740m-litert-lm`
（int4 QAT，真实引用相似度挤在 0.68–0.80 窄带）。本模型是同源 740M 的全精度 transformers 版，
可替换编码后端（Tukey 下界相对离群逻辑不变）：

```python
# semantic_reference_check.py 后端替换（保留 Tukey 逻辑）
sim = model.encode([query], normalize_embeddings=True) @ \
      model.encode(docs, normalize_embeddings=True).T
```

**诚实边界**：本模型未在「引用核查」任务上微调，属任务迁移使用。若引用核查精度关键，
建议对照 text-embedding-3-large（README 4.2 节）。

### 4.3 J-space 桥接 sim 后端（可选，未默认替换）

`scripts/jspace_bridge.py` 的 J-score 三成分 `J = 0.4·sim + 0.3·MI + 0.3·co_activation`，
其中 `sim` 当前由 `brain.recall()` 的 embedding 相似度计算。本模型可作**更贴合形式化数学的
sim 后端**（概念代表向量余弦）：

```python
sim = cos(enrich(concept_a), enrich(concept_b))   # 本模型 768 维向量
```

**诚实边界**：新后端值域与脑向量不同，替换后须按 `jspace_bridge.py` 的 `calibrate()`
重标定阈值（README 4.3 节）。当前**未默认替换**（保持主线稳定），作为可切换后端记录。

---

## 五、诚实边界（来自 README 第八节 + 本机实测补充）

1. **闭环未验证**：0.5505 是离线 recall@10（测试集同分布）。在真实 Lean 证明搜索中的
   引理召回收益尚未验证，需接入 Stage 3 后跑实际证明任务对比。
2. **训练/推理口径**：训练与评估均用紧凑增强文本（sig 120/doc 60）。推理口径变化需重测。
3. **领域局限**：微调数据全来自 openai_math（OAI 命名空间）。对 Mathlib / 自制定理迁移未测。
4. **hard negatives 有害**（-19%）：不要用本模型自挖难负例重训（README 第二节）。
5. **量化未做**：bf16/fp32 原样，未转 LiteRT/GGUF。int4 会显著损失窄带区分度。
6. **本机 bf16 陷阱**：P620（Pascal）不支持 bf16，加载必须 float32（脚本默认已处理）。
7. **本机性能实测（2026-10-13）**：
   - 模型加载 ~110–124s（多模态三塔 + bf16→float32，一次性）
   - 编码吞吐 **~72 条/s**（P620 GPU float32，batch 64–128）
   - **全量 185 万声明建索引 ≈ 7 小时**（P620 低端 GPU vs 训练机 20GB 高端 GPU 的 ~100 倍差距）
   - 因此**不要在本机跑全量 `--build-index`**。实际部署应**按需编码子集**：把当前证明
     任务涉及的候选声明（从 Lean import 列表提取，几百到几千条）传入 `LemmaRetriever(model, names, decls)`，
     编码该子集 + 召回（秒级）。全量索引仅作训练机上的可选任务。
8. **召回语义已验证**（1000 条抽样）：`coordinateVector` 正确召回自身(1.0) + `Space`(0.70,
   其类型) + `RealMatrix`/`Basis`/`Pair` 等语义相关声明；`exists_noncoordinate_polynomial`
   召回自身(1.0) + 相关多项式/坐标定理。召回排序语义合理。

---

## 六、文件清单

| 文件 | 说明 |
|---|---|
| `D:\AI_Training\EmbeddingGemma2_Lean检索模型_v2\embeddinggemma-2-lean\` | 模型源目录（sentence-transformers 格式） |
| `D:\AI_Training\EmbeddingGemma2_Lean检索模型_v2\venv\` | 独立 venv（torch 2.5.1+cu121 + transformers 5.19.0） |
| `D:\AI_Training\EmbeddingGemma2_Lean检索模型_v2\declarations.jsonl` | 声明库（从 openai_math 解析） |
| `D:\AI_Training\EmbeddingGemma2_Lean检索模型_v2\parse_lean_declarations.py` | 声明库解析器 |
| `scientific-discovery-proof/scripts/lean_lemma_retriever.py` | Stage 3 引理召回器（本技能新增） |
| `scientific-discovery-proof/references/embeddinggemma2-lean-integration.md` | 本文档 |
