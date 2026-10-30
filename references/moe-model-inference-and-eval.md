# MoE 模型本地推理 + 模型能力评估

**固化来源**: 2026-08-17 DeepSeek-V4-Flash-Q4_K_XL vs Qwen3.8:27B-Q8_0 数学证明能力评估 + GPU 加载实验。

## 1. MoE 模型（DeepSeek V4 Flash Q4_K_XL）的 llama.cpp 加载参数

DeepSeek V4 Flash 是 **284B MoE** 模型，Q4_K_XL 量化 = 144.4 GB 单文件（MERGED 版）。

- 硬件：4×RTX 4000 Ada（20 GB each = 80 GB 总显存）+ 536 GB 系统内存。
- **错误参数** `--n-gpu-layers 40`：40 层 × 每层 34 GB > 单卡 20 GB → `cudaMalloc failed: out of memory`（"failed to fit params to free device memory"）。
- **正确参数**：`--n-gpu-layers 16 --cpu-moe --ctx-size 8192`（16 层 attention 在 GPU，MoE expert 层全部 CPU offload）。
  - `--cpu-moe` / `--n-cpu-moe N` 是 llama.cpp 的 MoE 专用开关（`-cmoe` / `-ncmoe N`）。
  - 加载后 GPU 只占 ~3 GB × 4，剩余显存可再加载一个 27B 稠密模型（qwen3.8）作生成器。

## 2. 本地 Q4_K_XL 的推理速度约束（关键结论，2026-08-18 重大修正）

**Q4_K_XL 是 thinking 模型**（同 DeepSeek v4-pro / qwen3.8 / llama-server 全系）。未禁用 thinking 时：
- 简单任务（单行 theorem）：0.96 字符/秒（warm-up 后）
- 复杂任务（6.7K 字符审查 prompt）：**0 字符**——thinking 推理吃光 max_tokens（实测 1178s 浪费，content 为空）

**禁用 thinking 后：7.72 字符/秒**（`chat_template_kwargs: {"enable_thinking": False}`，实测 1024s 生成 7910 字符完整论文审查报告，较未禁用 8-20 倍提速）。

**结论修正**：之前的"本地 Q4_K_XL 太慢不可用/只适合单点验证"是基于未禁用 thinking 的测速。禁用 thinking 后本地 Q4_K_XL 可用于**长任务**（论文审查、深度校核，~17 分钟/报告），但仍比 DeepSeek API（秒级）慢一个数量级。分工：批量校核仍优先 API；单点深度审查可用本地 Q4_K_XL（免 API 费用、数据本地）。

**调用模板（llama-server OpenAI 兼容接口）**：
```python
payload = {
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 2000, "temperature": 0.0, "stream": False,
    "chat_template_kwargs": {"enable_thinking": False},  # 必加，否则复杂任务 0 字符
}
r = requests.post("http://127.0.0.1:11435/v1/chat/completions", json=payload, timeout=3600)
```

## 3. 模型数学证明能力排序（实测 + 历史）

DeepSeek V4（284B MoE）>> Qwen3.8:27B（稠密）在 Lean 4 证明能力上：

- 历史实证：SL(6,C) 四论文 + 复分析 209 定理中，所有 0 sorry 真证明（P0-6 链式法则、T2 ODE 解析解、去 sorry 68 成功）均由 DeepSeek 完成；qwen3.8 只生成 type-correct 陈述 + 占位（40% 一次通过，需校核）。
- 实测：两者都生成 0 sorry 完整证明，但 DeepSeek 更简洁模块化（先引理后定理），qwen3.8 冗长（T4 达 6273 字符）。
- **最优分工**（已验证）：qwen3.8 作批量生成器（快速出陈述）+ DeepSeek API 作校核器（修复到 0 sorry）。

## 4. llama-server Windows 进程管理 pitfall

- **MSYS bash 的 PID 空间 ≠ Windows PID**。`ps aux` 第 2 列是 MSYS PID（`kill -9` 用这个），最后一列（`?` 后的数字）是 Windows PID（`netstat -ano` / `taskkill //PID` 用这个）。用错会导致 `kill: (PID) - No such process`。
- `taskkill //F //IM llama-server.exe` 和 `taskkill //F //PID <winpid>` 在 MSYS bash 里会**超时**（不是失败，是 hang）。可靠做法：
  1. `ps aux | grep llama` 拿 MSYS PID（第 2 列）
  2. `kill -9 <msys_pid>`（可一次杀多个）
  3. `nvidia-smi --query-gpu=memory.used` 确认显存释放到 ~几 MiB
- llama-server 是常驻进程（不 exit），`process wait` 永远等到 timeout；就绪判断用轮询 `GET /health`。

## 5. 模型评估方法论（Lean 4 证明能力）

- 测试任务设计（从易到难）：T1 算术（norm_num）、T2 二次型标量乘法（BilinForm/QuadraticForm）、T3 链式法则（deriv_exp）、T4 ODE 解析解（弛豫解）。
- **陷阱：编译环境会误判**。用某个 formal-proof-lib 目录 `lake env lean` 单文件编译时，若该目录的 lakefile require 了错误的 mathlib olean 路径，会报 `object file '...\CGICE\.lake\packages\mathlib\...' error`——这是环境错误不是模型错误。T1 缺 `import Mathlib` 也会报 compile=false（模型只输出 theorem 行）。评估前先给代码补 `import Mathlib` 再编译。
- 评估维度：生成速度、0-sorry 完整证明、模块化程度（引理→定理）、编译通过率（修正环境后）。
