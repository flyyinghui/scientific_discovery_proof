# ScientistTwo Integration Assessment (arXiv:2609.19644, Google Cloud AI Research, 2026-09-17)

> 评估：ScientistTwo 多智能体自主科研框架对 scientific-discovery-proof 的可移植增量。
> 结论：**不改变主线五阶段管线**，可增量嫁接 5 个独有模块（3 个正确率 + 2 个发现概率），
> 与已集成的 RSIHub / Dream-RSI / RSIAgent / Co-Scientist 无重叠。

## 论文核心（六智能体闭环）

ScientistTwo = 完全自主多智能体科研框架，输入一个问题 → 输出论文 + 可复现代码库。
六智能体闭环：Idea Generator → Evaluator（subset→full）→ Analyzer（ablation）→ Writer → Peer-Review（rebuttal）→ Meta-Review。
结果：86/107 超越人类 SOTA（80.4%），+25.2% 平均相对增益；ScholarPeer 7.5/10（91.9% 录取），
Stanford Agentic Reviewer 5.7/10（72.1%，唯一过关）；CoE 完整性审计 4/4 通过（0/1814 引用幻觉）。

## 可移植增量（P0-P3 性价比排序）

### P0-1 Reference Verification — 参考文献零幻觉核查（正确率，未覆盖）
- **ScientistTwo 独有**：search-augmented LLM 逐条验证参考文献存在性，达成 0/1814 幻觉。
- **当前管线缺口**：Stage 3.5 的 Hallucination Clipping 只核对**数值声明 ↔ Lean 地面真相**，
  **不核对参考文献**。用户论文历史多次出现「30% 引文错位」「12 条幻影引用」。
- **嫁接**：新增 `scripts/reference_verification.py`，正则提取 `[n]` 引用 → 与参考文献表逐条比对
  （存在性 + 编号一致性 + 正文↔列表映射），悬空/错位 → BLOCK，缺失 → WARN。

### P0-2 Method-Code Alignment — 论文方法段 ↔ Lean 代码逐条对齐（正确率，未覆盖）
- **ScientistTwo 独有**：Coding Agent 逐行审计「论文方法描述 ↔ 代码实现」是否一致。
- **当前管线缺口**：Stage 3.5 的 P0-3（公理计数不匹配）/ P0-4（幻影定理）是**单向**（论文声称 → Lean 存在性），
  缺**双向逐条对齐**（论文 §2.3 声称的每个定理/公理 → Lean 中对应的 `theorem`/`axiom` 声明体是否真的一致）。
- **嫁接**：扩展 `proof_consistency_audit.py`，新增「paper-side claim → lean-side declaration」映射表核对，
  报告 `{paper_claim, lean_decl, status: matched/mismatch/missing}`。

### P0-3 Ablation-Based Axiom Essentiality — 公理必要性消融（正确率，未覆盖）
- **ScientistTwo 独有**：Ablation Planner/Critic 逐组件消融，隔离增益来源，剪除冗余组件。
- **当前管线缺口**：Stage 3.5 DAG-2 只检查「honest-axiom 是否被引用」，但**被引用 ≠ 必要**
  （公理可能被加进 theorem 声明但证明体从未用到）。这是「表演性诚实」的更隐蔽变体。
- **嫁接**：新增 `scripts/axiom_ablation.py`，对每个 honest-axiom 做**反事实消融**：
  注释掉该 axiom → 重编译 → 若目标 theorem 仍编译通过 → 该 axiom 冗余（BLOCK 或 WARN）；
  若编译失败 → 必要（保留）。这是比 DAG-2 更强的必要性判据。

### P1-1 Novelty Checker — 猜想新颖性评分（发现概率，未覆盖）
- **ScientistTwo 独有**：Novelty Checker 给候选 idea 打新颖性分，优先高原创方向。
- **当前管线缺口**：SimpleTES 只按 fit/validity 排名（rpucg + UCB），**不评新颖性**，
  可能优先「拟合好但增量」的猜想，抑制「前沿但未验证」的猜想。
- **嫁接**：扩展 `curriculum_planner.py` 的候选队列，新增 `novelty_score` 字段
  （v4-pro 判断「该猜想是否越过已知边界，而非对现有结果的微调」），与 UCB 组合排序。

### P1-2 Limitation Resolution — 理论局限驱动的猜想生成（发现概率，较高成本）
- **ScientistTwo 独有**：Limitation Extractor/Verifier 先识别 SOTA 局限，再针对性生成 idea。
- **当前管线缺口**：管线从给定 `conjecture.json` 起步，**不主动生成猜想**。
  「发现物理规律概率」的真正杠杆在于：在知识边界缺口处（honest-axiom、开放问题）种猜想。
- **嫁接**：新增 Stage 0.5 前置脚本 `scripts/limitation_extractor.py`，输入当前理论框架的
  honest-axiom 清单 + 开放问题 → v4-pro 输出「局限 → 可检验猜想」候选 → 喂给 Stage 0/1。
  **注意**：此为前置增量，不改变 Stage 0-4 主线，仅扩展猜想输入源。

## 与已集成框架的 diff（避免重复）

| ScientistTwo 模块 | 已集成等价物 | 是否重复 |
|---|---|---|
| Subset→full 筛选 | MAF Stage 0 符号预验证 | 重复（不接） |
| Idea evolution（探索/利用） | UCB (v2.3) + Replay Simulator (v2.7) | 重复（不接） |
| Rebuttal 新实验 | Stage 2.5 Curriculum（RSIAgent 变体队列） | 部分重复（仅补闭环阈值） |
| Meta-Review Accept/Refine | 5-agent Hybrid Review + Stage 3.5 门控 | 重复（不接） |
| Result Comparison 严格改进 | Stage 3.6 冻结评估器门控 | 重复（不接） |

## 关键教训：类型错配

ScientistTwo 是**经验 ML 研究代理**（跑 benchmark、测 metric），scientific-discovery-proof 是
**理论物理形式化证明管线**（SymPy 符号 + Lean 4 验证）。不能 1:1 移植实验机制，只能移植
**可抽象的模式**：完整性审计（引用/方法-代码对齐）→ 直接映射；消融（组件必要性）→ 公理消融；
新颖性/局限 → 猜想生成。**「跑新实验」对形式化证明的对应物是「生成新证明变体」**（已由
Curriculum Planner 承载），非真的跑 benchmark。

## 落地优先级

- **P0（3 个正确率增量）**：Reference Verification + Method-Code Alignment + Axiom Ablation，均 stdlib-only 或轻 LLM，直接插入 Stage 3.5 门控。
- **P1（2 个发现概率增量）**：Novelty Checker（低改，扩展 curriculum）+ Limitation Extractor（中改，Stage 0.5 前置）。
- **P2/P3（不接）**：与已集成 RSIHub/Dream-RSI/RSIAgent/Co-Scientist 重复的模块。

完整评估见会话记录；论文全文 PDF + text 存 `~/data/papers\2609.19644_ScientistTwo.{pdf,txt}`。
