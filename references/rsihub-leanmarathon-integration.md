# RSIHub / LeanMarathon 评估与增量嫁接（2026-09-03）

评估两个「多智能体 harness / 自我改进」框架对 **scientific-discovery-proof** 的增强价值。
结论：**只做增量嫁接**（新增 Stage 3.5c 证明 DAG 审计 + Stage 3.6 冻结评估器进化设计），
**不改动现有 5 阶段管线**。现有 Stage 3（PPE 生成 Lean）、Stage 3.5（一致性审计）、
Stage A（递归修复）全部保留。

## 一、两个框架是什么

| 项目 | 定位 | 核心抽象 | 环境要求 | 实测状态 |
|---|---|---|---|---|
| **RSIHub**（simple-agent-lab，Apache 2.0）| 递归自我改进框架（RSI）| `select→evaluate→analyze→mutate→gate→record` 循环 + **冻结评估器** + 有界变异 + 证据持久（archive.jsonl + Git 世代标签）| Python **≥3.12**（当前 venv 3.11，装不了）| 只能提炼概念 |
| **LeanMarathon**（YuanheZ，arXiv:2606.05400）| 多智能体 Lean 自动形式化 harness | **evolving blueprint**（一个 Lean 文件 = 证明骨架 + NL 证明图 + 系统记录）+ 4 角色（Blueprinter/Target-Reviewer/Refiner/Worker）+ 证明 DAG | Codex CLI + Slurm + lean-lsp-mcp + LeanArchitect | verify_blueprint.py **stdlib-only 可跑**，但完整 harness 需 Codex/Slurm |

## 二、LeanMarathon 最有价值模块：证明 DAG + 蓝图契约

`agents/Worker/docs/contracts/blueprint-format.md` 定义了「蓝图文件」——每个 `lemma`/`theorem` 是一个 **DAG 节点**：

- **定义性节点**（`def`/`structure`/`inductive`/`class`/`instance`）= 全局上下文，不进证明 DAG
- **证明节点**（`lemma`/`theorem`）= DAG 节点，带 `statement`/`title`/`proof`（LaTeX + `\cref{}` 引用）/`sorry_using [dep1, dep2, ...]`
- 7 项算法检查（verify_blueprint.py 全部实现，stdlib-only）

**两个我们现有审计（Stage 3.5 L1 是扁平的）缺的新缺陷类：**

| LeanMarathon 检查 | 对应新缺陷类 | 现有审计有吗 |
|---|---|---|
| Rule 5 `sorry_using` 一致性（**双向 \cref ↔ 依赖对等**）| 引用了但未声明 / 声明了但未引用 | ❌ 无 |
| Rule 6 **lemma closeness**（每个 lemma 必须被下游使用）| 冗余引理 / 缺失依赖 | ❌ 无 |

⚠️ **关键设计差异（勿照搬）**：LeanMarathon **禁止 `axiom`**（用 `sorry_using` + `\cref` 显式声明依赖）。但用户的物理证明里 **honest-axiom 是刻意设计**（λ_KLS=35/3、g_TC 等物理参数无法第一性导出）。所以嫁接时**保留 honest-axiom**，只借「依赖显式化」思想——让每个定理**显式列出它依赖哪些 honest-axiom / 引理**，从而可追踪依赖链。

## 三、RSIHub 最有价值模块：冻结评估器进化循环

RSIHub 的「评估器被冻结 + 变异有界 + 证据持久」正好能包裹我们的 Lean 生成：

| RSIHub 概念 | 映射到本管线 |
|---|---|
| **冻结评估器** | MathCode 三工具 + Stage 3.5 审计（确定性、可验证）|
| **可变表面** | Stage 3 的 Lean 生成 prompt/skill（骨架引导法 / honest-axiom 模式）|
| **变异** | 改进生成策略（skeleton stubs → tactic bodies → 完整证明）|
| **证据持久** | archive.jsonl（我们已有 stage35_audit_report.json，可升级为 append-only 世代记录）|

价值：把「生成 Lean → 验证 → 分析失败 → 改 prompt → 再验证」这条**现在人工迭代**的循环**自动化**，用冻结的 Lean 验证器当裁判，让 Lean 生成 skill 自我进化。

⚠️ RSIHub 需 Python 3.12（当前 venv 3.11），无法直接安装。但**循环设计可自实现**（stdlib + DeepSeek SDK 即可，不必装 RSIHub 本体）。

## 四、增量嫁接方案（不改现有管线）

### 新增 Stage 3.5c — 证明 DAG 审计（`scripts/proof_dag_audit.py`，stdlib-only）

在现有 Stage 3.5 L1/L2 之后、Stage 4 之前，新增一个**独立的、可选的** DAG 层：
- 从 Lean 文件解析 `lemma`/`theorem`/`def` 节点 + `sorry_using`/`\cref{}` 依赖
- 检查 2 个新缺陷类：**冗余引理**（lemma closeness）、**引用-声明不对等**（deps parity）
- 输出 `proof_dag_report.json`（节点/边/悬空/冗余）+ 门控（BLOCK=冗余引理或悬空引用）

**不改动** proof_consistency_audit.py / l2.py / lean_recursive_repair.py——它是并列的新层。

### 新增 Stage 3.6 — 冻结评估器进化（设计蓝图，本 reference 文档）

一个**可选**的进化循环，包裹 Stage 3 的 Lean 生成：
- 冻结评估器 = MathCode + Stage 3.5 审计打分
- 变异 = 修改 Lean 生成 prompt/skill
- 记录 = append-only archive.jsonl
- 用 DeepSeek（v4-flash 生成 / v4-pro 分析）驱动，不必装 RSIHub

## 五、落地清单

| 优先级 | 动作 | 落地状态 |
|---|---|---|
| P0 | 新增 `scripts/proof_dag_audit.py`（stdlib-only DAG 审计）| 本会话已写 |
| P0 | 新增本 reference 文档 | 本会话已写 |
| P1 | Stage 3.6 进化循环实现（可选，需 DeepSeek 编排）| 设计已文档化 |
| P2 | 把 DAG 审计接入 pipeline_orchestrator.py（--stages 加 3.5c）| 待做（需用户确认） |

## 附：测试环境约束

- RSIHub：`requires-python >=3.12`，当前 Hermes venv 3.11.15 → 无法 pip 安装，仅提炼概念（若需实跑，可建独立 3.12 venv）。
- LeanMarathon：完整 harness 需 Codex CLI 0.128.0 + Slurm + 4 个外部 MCP server + LeanArchitect 项目根 → 无法在本机跑通，但其 verify_blueprint.py 与 blueprint-format 契约是 stdlib 可复用的。
- 两者 license：RSIHub Apache 2.0，LeanMarathon 见其 LICENSE。
