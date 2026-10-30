# scientific-discovery-proof · 独立分发包

从「科学发现 → 形式化证明 → 论文生成」的五阶段管线，含 Harness² RSI 多智能体回环。

**版本** 2.25.0　**打包日期** 2026-10-29

---

## 这是什么

一条端到端的物理/数学研究管线：

```
Stage −1  安全审查（dual-use 初筛）
Stage 0   符号审计（SymPy 恒等式 + 5 层验证）
Stage 1   数值发现（SciExplorer 致命错误检测）
Stage 2   候选排序（SimpleTES + UCB 探索）
Stage 3   形式化证明（PPE + MathCode + Lean 4）
Stage 3.5 一致性审计（六类 P0 缺陷 + L2 结构层 + 物理内容 + DAG）
Stage 4   论文生成（AI-Scientist V2 风格 IMRAD）
```

外加 **MVP-0/1/2** 三层新架构（Harness² RSI）：

```
proof_harness.py      harness 层（prompt_style / memory_policy / scaffold / tools / parallelism）
agent_fleet.py        10 个 L2 agent 的 mock 实现 + Arbiter（唯一判定入口）
trajectory_diff.py    多轨迹对比，抽「首个分歧步 + 归因」
jev_arbiter_bridge.py Jev-Omni 判别器（只排序，代码级禁止进 gate）
mvp0_smoke.py         4 路并行最小闭环（离线 4 秒跑完三代进化）
agent_fleet_real.py   10 agent 真实现（读真实 Lean 文件 + 调真实审计）
proof_llm.py          stdlib LLM 后端（缓存 + 三级降级）
agent_llm.py          P01/T07 接真 LLM
```

---

## 依赖

### 必需

| 依赖 | 用途 | 安装 |
|---|---|---|
| Python ≥ 3.10 | 全部脚本 | — |
| stdlib only | 大多数脚本零依赖 | 无需装包 |

### 按需

| 依赖 | 用途 | 安装 |
|---|---|---|
| `sympy` `scipy` `numpy` | Stage 0 符号审计 | `pip install sympy scipy numpy` |
| Lean 4（`lean` / `lake`） | Stage 3 编译验证 | 见下 |
| mathlib4 | Lean 证明依赖 | `lake exe cache get` |
| `openai` 或任意 OpenAI 兼容 API | LLM 调用 | 仅 `proof_llm.py` 走 stdlib urllib，不强制 |
| Jev-Omni（可选） | 候选排序 | 见 harness2 技能 |

### Lean 4 安装（Windows）

```bash
# 1. 下二进制（github 被墙时用镜像前缀）
curl -L -o lean4.zip \
  "https://ghfast.top/https://github.com/leanprover/lean4/releases/download/v4.34.0-rc1/lean-4.34.0-rc1-windows.zip"
# 2. 解压，把 bin/ 加进 PATH
lean --version     # 应输出 Lean (version 4.34.0-rc1, ...)
```

### mathlib4

```bash
git clone --depth 1 https://ghfast.top/https://github.com/leanprover-community/mathlib4.git
cd mathlib4
lake exe cache get        # 从 lakecache.blob.core.windows.net 下 olean（Azure，通常不被墙）
```

`import Mathlib` 是全量依赖，olean 约 6 GB。只想验证纯 Lean 核心语法（无 mathlib tactic）可跳过。

---

## 快速开始

```bash
cd scripts

# ① 离线自测（零依赖，几秒）
python proof_harness.py --self-test
python trajectory_diff.py --self-test
python agent_fleet.py --self-test
python jev_arbiter_bridge.py --self-test
python mvp0_smoke.py --self-test          # 4 路并行 + 三代进化闭环

# ② 真文件审计（需 Lean 文件；无编译器时 4 个 agent 自动降级）
python agent_fleet_real.py --lean path/to/proof.lean

# ③ 接真 LLM（需 OPENAI 兼容端点）
export PROOF_LLM_KEY=sk-...               # 或写进 <YOUR_HOME>/.env
python proof_llm.py                       # 连通性自测
python agent_llm.py --self-test           # P01 真生成 + memory 对比

# ④ 4 路并行真生成
python agent_llm.py --styles concise detailed --output runs.json
```

---

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `PROOF_LLM_KEY` / `DEEPSEEK_API_KEY` | 从 `.env` 读 | LLM key（不写进任何文件） |
| `PROOF_LLM_BASE` | `https://api.deepseek.com/v1` | 任何 OpenAI 兼容端点 |
| `PROOF_LLM_MODEL` | `deepseek-v4-pro` | 形式化建议用 reasoning 模型 |
| `PROOF_LLM_MAX_TOKENS` | `32768` | ⚠️ 见下方坑 |
| `PROOF_LLM_CACHE` | `%TEMP%/proof_llm_cache` | 磁盘缓存目录 |
| `JEV_HOST` | `http://127.0.0.1:9411` | Jev-Omni 端点（不可用会自动降级） |

---

## 三个必须先知道的坑

### ① reasoning 模型的 thinking 会吃光 max_tokens

```
max_tokens=16    content=''      finish=length  reasoning_tokens=16    ← 全给思考
max_tokens=256   content='PONG'  finish=stop    reasoning_tokens=21
```

**形式化任务不要用 2048/4096**，会静默返回空串。本项目默认 32768，并在
`finish=length 且 reasoning_tokens≥90%` 时自动扩预算重试。

### ② Windows 上 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 会搞坏 CUDA 分配器

症状：所有 KSampler/comfy 节点报 `[Errno 22] Invalid argument`，连最小 SDXL 流程都失败。
**别加这个变量**。

### ③ 双轨/多 harness 对比必须先取 step 交集

按「相当步数」比较会得出完全相反的结论（本项目实测：错误对比显示 trace_A 分叉 100%，
取 step 交集后实际只差 −0.1%）。

---

## 核心设计原则

1. **判定与排序分离**：`arbitrate()` 是唯一能写 `lean_ok / sorry / axioms / verdict` 的函数。
   Jev-Omni 概率进 gate 会抛 `JevMisuseError`。
2. **单维编辑**：每个 harness 变体只改一个维度 → 分歧可归因到具体维度。
3. **单调性优先**：Compose 发现基线已 `lean_ok=True` 就停手，不退化。
4. **诚实标注降级**：无 Lean 时 4 个 agent 标 `[degraded: no lean]`，不假装编译成功。

---

## 目录

```
scientific-discovery-proof/
├── SKILL.md                    主文档（v2.25.0，含 MVP-0/1/2 三章）
├── README.md
├── references/                 110+ 篇方法与踩坑记录
├── scripts/                    37 个可执行脚本
│   ├── pipeline_orchestrator.py      主流程编排
│   ├── proof_consistency_audit.py    Stage 3.5 L1 审计
│   ├── physical_content_audit.py     定义重言式检测
│   ├── proof_dag_audit.py            证明 DAG 审计
│   ├── proof_harness.py          ★ Harness² harness 层
│   ├── agent_fleet.py            ★ L2 agent + Arbiter
│   ├── agent_fleet_real.py       ★ 10 agent 真实现
│   ├── trajectory_diff.py        ★ 轨迹对比归因
│   ├── proof_llm.py              ★ LLM 后端
│   ├── agent_llm.py              ★ P01/T07 真 LLM
│   ├── mvp0_smoke.py             ★ 4 路并行最小闭环
│   └── jev_arbiter_bridge.py     ★ Jev 排序桥
├── config/
├── examples/
└── maf_core/                   MAF 符号审计内核
```

★ = MVP-0/1/2 新增

---

## 引用

本技能综合了以下工作的方法（详见 `references/`）：

- Harness²（Google Research，Propose–Probe–Compose）
- RSIAgent / RSIHub / AIDE²（递归自我改进）
- JANUS（Predict-Verify-Evolve，arXiv:2610.13194）
- Stellar Colosseum（arXiv:2609.15983）
- BootLoops 1.0（planted-truth / constant-recognition）
- Gemini Co-Scientist（arXiv:2608.26701）
- Dream-RSI（arXiv:2609.14858）
- prove2me（形式化忠实性）
- ScientistTwo（arXiv:2609.19644）
- RSIHub + LeanMarathon（冻结评估器进化）

---

## 许可与免责

本分发包为研究方法工具集，**不构成形式化保证**。任何标记为 WARN 的检测都是启发式，
不是证明。论文使用前请人工复核所有审计结论。
