# 本地 LLM 混合模式形式化证明流水线（2026-08-17 实测）

三模型分工批量编译数学书籍（Mathematics for Physicists）的完整经验，含可复用的技巧与陷阱。

## 三模型分工

| 模型 | 角色 | 适用场景 |
|------|------|---------|
| qwen3.8:27b-q8（本地，8081）| 批量生成器 | 短定理陈述（签名骨架下 70% 直接通过）|
| DeepSeek-V4-Flash-Q4_K_XL（本地 MoE，11435）| 短定理校核 | ~200 字符证明，0.5 字符/秒 |
| DeepSeek API（v4-pro，thinking disabled）| 长定理校核 | 秒级，但 subtle Mathlib API 也修不了 |

## 签名骨架技巧（关键发现）

**现象**：qwen3.8 批量生成 Lean 定理，无骨架直接通过率 0/8（0%）；prompt 带定理签名骨架后 7/10（70%）。

**做法**：prompt 必须给出完整 theorem 签名骨架，模型只填证明体：
```
theorem inv_mul {G : Type*} [Group G] (a b : G) : (a*b)⁻¹ = b⁻¹*a⁻¹ := by ...
```
骨架让模型避免"猜签名 + 猜 API"双重失败。这是批量生成短定理的最优路径。

## compile_check 假 OK 陷阱

**现象**：空文件（只有 `import Mathlib`，16 字节）也能 `lake env lean` 编译通过（exit 0），造成"假 OK"误报。

**修复**：compile_check 必须同时检查代码含 theorem/lemma/def：
```python
ok = r.returncode == 0 and ('theorem' in code or 'lemma' in code or 'def' in code)
```
没有 theorem 的空文件不是有效证明。

## DeepSeek Q4_K_XL 本地 MoE 推理

- 144GB MoE 模型（284B 参数），4×20GB 显存装不下，必须 `--cpu-moe`（MoE 层全 CPU）
- 启动：`llama-server.exe -m ...Q4_K_XL-MERGED.gguf --n-gpu-layers 16 --cpu-moe --ctx-size 8192`
- 速度 0.5 字符/秒（warm-up 后快 2.6 倍），只能编译 ~200 字符短定理（~7 分钟/个）
- 长定理（>500 字符）900s 超时；方案：30min timeout + 失败提升 60min
- `--n-gpu-layers 40` 会 OOM（单层 34GB > 单卡 20GB），必须降层数 + cpu-moe

## Mathlib 复杂 API 局限（诚实）

三个模型（qwen3.8 + Q4_K_XL + DeepSeek API）都无法自动修复这些 API：
- **Finset.sum 代数**：sum_congr 需 `apply` 非 `rw`；sum_add_distrib/mul_sum 的 rewrite 顺序
- **InnerProductSpace typeclass**：norm_inner_le_norm 参数匹配（连手动"正确版"都可能 Application type mismatch）
- **Matrix.det**：行列式理论

**对策**：领域专用模型 Llemma 7B（proof-pile-2 训练，含大量 Mathlib 证明），或人工查 Mathlib 源码精确定位。

## DeepSeek API 校核局限

对 subtle Mathlib API 错误，DeepSeek API 3 次迭代输出几乎相同代码（如 1175/1175/1175 字符），"重新生成"策略无效——不针对编译错误精确定位。对简单 tactic 错误（rw→apply）能给出方向，对复杂 API 反复生成相同错误。`simp [dot, mul_comm]` 不会在 Finset.sum 内部应用 mul_comm（需 `apply sum_congr rfl; intro i hi; rw [mul_comm]`）。

## 成功案例

- 14 个真实编译通过的短定理（集合/群/环/映射/域基础），全部 0 sorry
- 签名骨架 + qwen3.8 是短定理批量编译的最优路径（70% 直接通过）
- Q4_K_XL 能编译短定理（复合单射/群单位元唯一/域零因子），证明本地 MoE 推理有效

## Llemma 7B 下载（Mathlib 领域模型）

- 位置：`<WORK_DIR>/models/llemma-7b/`（26.96GB fp32，3 分片 + tokenizer）
- 来源：EleutherAI/llemma_7b，hf-mirror 非 gated 可下载（huggingface.co 本体不可达）
- proof-pile-2 训练（Lean 4 证明数据），是处理 Mathlib 复杂 API 的领域专用模型
- DeepSeek-Prover-V1.5（更强但 gated 401 + ModelScope 404）；InternLM2-Math-7B 在 ModelScope 可下载
