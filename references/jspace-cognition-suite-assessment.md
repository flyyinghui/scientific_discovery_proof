# J-Space 概念澄清与 J-Space-Cognition-Suite 评估 (2026-08-17)

## 两个 "J-space" 是不同概念 — 不要混淆

| 概念 | 是什么 | 作用 |
|------|--------|------|
| **SDP 管线的 J-space** (SKILL.md 架构图里的 "J-space" 标签) | Neural Brain — 167K 神经元物理知识库 (`neurons.json` ~910MB), HNSW/关键词检索做概念桥接 | 提供**领域知识** (物理概念桥接给 PPE 证明) |
| **J-Space-Cognition-Suite-V3.6** (zip: <WORK_DIR>/J-Space-Cognition-Suite-V3.6-main.zip) | 模型不可知的**推理时认知控制层** (不改权重, prompt 协议 + `jspace.py` 账本) | 提供**认知控制** (工作空间管理/失败检测/状态保持) |

结论: **不能互相替换**, 作用互补。最优是叠加 (Brain 提供知识 + J-Space 套件提供控制), 而非替换。

## J-Space-Cognition-Suite 核心

- 处理四类推理损失: 工作集过载 / 表征漂移 / 无控制重试 / 过早完成
- 机制: 选择性工作空间加载 / 广播枢纽 / 稠密轨 (`✓` 已验证 / `?` 未可用 / `✗` 已证伪)
- 组件: `j-space/SKILL.md` + 9 个 modules + `scripts/jspace.py` (账本: seam/note/core/check/open/close)

## Benchmark 数据 (DeepSeek V4-Flash-0731 vs + J-Space V3.6)

| Benchmark | 裸 | +J-Space | 提升 |
|-----------|----|----------|------|
| HLE (w/o tools) | 37.8 | 45.5 | +7.7 |
| HLE (w/ tools) | 51.5 | 60.6 | +9.1 |
| NL2Repo | 54.2 | 70.2 | +16.0 |
| DeepSWE | 54.4 | 67.4 | +13.0 |
| 速度 / Token 效率 | 0.43 / 0.38 | 1.09 / 0.84 | 2.53× / 2.21× |

## 对 HermesAgent 的价值

J-Space 套件的机制 (约束保持/失败检测/诊断携带重试) 直接命中 HermesAgent 做多步推理 (形式化证明、多文件修改) 的痛点。可作为 skill 加载 (j-space skill), 让 agent 在长任务中通过 `jspace.py` 账本保持状态。单次运行结果, 无多次均值。
