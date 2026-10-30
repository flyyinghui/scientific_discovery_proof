# Stage 3 引理召回：已微调的 EmbeddingGemma-2 检索器（2026-10-12 落地）

给 Stage 3（MCTS/ABC 证明搜索的引理/依赖召回）用的领域适配检索模型与调用口径。

## 可用资产

- **达标模型**：`D:\embeddinggemma_ft\embeddinggemma-2-lean\`（sentence-transformers 格式，768 维，`SentenceTransformer(path)` 直接加载）
- **富文本声明库**：`D:\embeddinggemma_ft\declarations.jsonl`（1,785,549 条 OAI.* 声明：名字 + 类型签名 + docstring），由 `parse_lean_declarations.py` 从 openai_math 源码库（150,911 个 .lean，现已解压于 `<WORK_DIR>\openai_math-main\lean\`）扫描得到
- **冻结评测集**：`D:\embeddinggemma_ft\v4_test_split.json`（13,941 对，both-hit 子集）
- **对比评测脚本**：`D:\embeddinggemma_ft\eval_fusion.py`（2×2 因子设计：base/v2 × 纯名字/增强文本）

## 关键性能数字（同一测试集 13,061 query）

| 配置 | recall@10 |
|---|---|
| base + 纯名字 | 0.3225 |
| base + 增强文本 | 0.4911 |
| v2 微调 + 纯名字 | 0.4663 |
| **v2 微调 + 增强文本** | **0.5505（推荐上线口径）** |

## 调用口径（必须遵守，否则达不到 0.5505）

```python
def enrich(name, decls):            # decls = declarations.jsonl 载入的 name -> {signature, docstring}
    words = name_to_text(name)      # 下划线→空格 + 驼峰拆词
    parts = [words]
    if sig := decls.get(name, {}).get("signature"): parts.append("type " + sig[:120])
    if doc := decls.get(name, {}).get("docstring"):  parts.append(doc[:60])
    return " | ".join(parts)

model = SentenceTransformer("<PATH>")
model.max_seq_length = 64           # 与训练口径一致
# query（待证定理）与 doc（候选依赖）都必须走 enrich()，缺声明时降级为纯词化名字
```

- query 与 doc **同构增强**（两侧都 enrich），只增强一侧会退化
- 文本必须裁剪到 ~120+60 字符；整段签名+doc 会膨胀序列并压垮单卡显存
- 声明库里查不到的名字降级为纯词化名字（覆盖率：theorem 99.7% / dependency 93.8%）

## 已知边界（勿重复踩）

- **不要再用 hard negative 挖掘做增量训练**：实测劣化 0.4716 → 0.3801。GT 只记录「实际被引用」的依赖、不完整，自挖 top 相似项里大量是真相关项 → 标签噪声
- **不要再尝试全参重训增强文本**（除非换更大显存）：单卡 20GB 下长文本 page fault 空转；LoRA 被 peft 白名单挡住（`Gemma4ClippableFeature` 同族自定义层不支持）
- 详细案例与工程约束见技能 `mlops/embedding-retrieval-finetuning` 的 `references/text-enrichment-beats-retraining.md`
