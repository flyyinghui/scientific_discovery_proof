# Thinking 模型禁用 + Lean 自定义 attribute + llama.cpp 多 GPU

2026-08-16 会话沉淀：复分析书籍 Ollama 形式化 + V16 @[honest_axiom] attribute 真实现。

## 1. 本地/云端 thinking 模型的 content=0 根治

症状：LLM 生成复杂 prompt（Lean 证明/物理推导）时 `content=""`，但 `reasoning_content` 很长（数万字符）——thinking 阶段吃光了 max_tokens。

| 模型/端点 | thinking 字段 | 禁用 thinking 的正确方式 | 错误方式 |
|---|---|---|---|
| **DeepSeek v4-pro** | `reasoning_content` | payload 加 `"thinking": {"type": "disabled"}` | `"thinking": false`（报 deserialize 错误）；`"enable_thinking": false`（无效）|
| **Ollama qwen3.8**（thinking 模型）| `/api/chat` 的 `message.thinking` | 用 `/api/chat` 取 `message.content`；禁用用 `options.chat_template_kwargs={"enable_thinking": False}` | `/api/generate` 的 `response`（thinking 模型返回空）|
| **llama.cpp llama-server** | `reasoning_content` 字段 | payload 加 `"chat_template_kwargs": {"enable_thinking": False}` | 顶层 `enable_thinking`（无效）；`--reasoning off` 启动参数（无效，模板内建 thinking）|

要点：
- 这些 thinking 模型（qwen3.8、deepseek-v4-pro）**默认启用 thinking**，且 thinking 长度与 prompt 复杂度正相关——复杂数学 prompt 的 thinking 可达 4 万+ 字符，即使 max_tokens=16000 也被吃光。
- 禁用 thinking 后速度提升 **8-24 倍**（qwen3.8 26 秒 vs 之前 22 分钟）。
- memory 旧条目"v4-pro t=0+max_tokens=16000 可靠"已过时——v4-pro 现在也是 thinking 模型，必须 `thinking:{"type":"disabled"}`。

## 2. Lean 4 自定义 tag attribute（@[honest_axiom] 等）

`registerTagAttribute` 注册的 attribute **必须在独立文件**（`initialize` 是文件加载时延迟执行的，同文件内使用 @[attr] 会报 "Unknown attribute"——因为语法解析发生在 initialize 执行之前）。

正确模式（跨文件）：

```lean
-- HonestAttr.lean (独立文件)
import Mathlib
public meta section
open Lean Elab Command Parser.Term Meta
initialize honestAxiomAttr : TagAttribute ←
  registerTagAttribute `honest_axiom "honest research-level axiom marker (machine-auditable)"
initialize phenomAxiomAttr : TagAttribute ←
  registerTagAttribute `phenomenological "phenomenological calibration input marker"
end

-- 主文件: import HonestAttr 后即可 @[honest_axiom] axiom ...
```

- lakefile `roots := #[`HonestAttr, `主模块]`（HonestAttr 必须先编译成 olean）。
- `registerTagAttribute (name : Name) (descr : String)` 返回 `IO TagAttribute`，需要 `initialize x : TagAttribute ←`。
- 机器审计：`TagAttribute.hasTag honestAxiomAttr env decl`（替代 grep 注释文本——grep `-- @[honest_axiom]` 是"表演性诚实"，不是真实 attribute）。
- 失败路径记录：`syntax (name := x) "x" : attr` 声明不够（还报 Unknown attribute）；缺 `public meta section` / `open Meta` 也不行；根本原因是**同文件 initialize 延迟执行**。

## 3. llama.cpp 多 GPU 推理（Windows）

- 下载：api.github.com 可达时用 `llama-b{ver}-bin-win-cuda-12.4-x64.zip`（250MB），GitHub org 是 `ggml-org`（非 ggerganov）。
- 运行：`llama-server -m model.gguf -ngl 99 --tensor-split 1,1,1,1 --port 8081`。
- GGUF 来源：Ollama 模型在 `~/.ollama/models/blobs/sha256-*`（29GB 的是权重，头 4 字节 `GGUF` + `general.name`）。
- **层分割（pipeline）≠ 张量并行**：`--tensor-split` 把不同层放不同 GPU，推理时层顺序执行（GPU 串行），只避免 CPU offload。4×RTX 4000 Ada（80GB）跑 27B q8 得到 6.3 t/s（vs Ollama 2.8 t/s，2.25×）。要 30-60 t/s 需张量并行（vLLM/TensorRT-LLM），llama.cpp 不支持。
- API 是 OpenAI 兼容 `/v1/chat/completions`，thinking 在 `reasoning_content` 字段。

## 4. 复分析书籍批量形式化流程（已验证）

llama-server 多 GPU 生成（禁用 thinking，~26s/定理）→ 编译验证 → 失败 deepseek 校核（`thinking:disabled`）→ 最终 83% 可编译（165/198 定理，陈述 type-correct + sorry 占位）。
- 空文件失败 ~17%（llama 偶发空 content + deepseek 也失败），补跑需加 retry 逻辑（3 次）。
- 去 sorry 需 deepseek 迭代（生成完整证明 → 编译 → 错误反馈 → 修复，最多 3 次），简单定理（收敛/有界/链式法则）可去，公理化对象定理（IsAnalytic 等）需重写为 Mathlib API。
- **最终结果（2026-08-17）**：补跑 33 失败 → 26 成功（总 191 可编译 96%）；去 sorry 157 → 68 成功（总 135 无 sorry = **60% 完整证明**，89 陈述占位 = 40%）。40% 占位集中在 Ch.IV-VIII 复分析核心（Cauchy 定理/留数/Laurent 展开），需 Mathlib `Complex` 复微分/`CircleIntegral` 围道积分库，远超单次会话 API 集成深度。
