# prove2me_workspace 二次评估（v2.18.0 之后的补充深读）

评估对象：`prove2me_workspace-main.zip`（<project>，已解压 `prove2me_workspace/`）
评估目的：找出对 scientific-discovery-proof 技能的增量价值，**不改变既有物理猜想形式化证明管线流程**（主线 Stage −1 → 0 → 1 → 2 → 2.5 → 3 → 3.5 → 4 不动）。

---

## 一、结论摘要

prove2me 的核心价值是**「形式化忠实性（faithfulness）方法论」**，不是证明技术。

- **v2.18.0（2026-10-08）已落地 5 项**：read-back 盲读回 / faithfulness 5 约束注入 PPE prompt / typeDeps·valueDeps 区分 / reduction 可复用激励 / milestone 里程碑。
- **本次深读全库**（SKILL.md + 13 个 reference + 2 个 Lean 脚本 + example），发现 **6 项 v2.18.0 遗漏的新增量**，全部可增量嫁接、不动主线五阶段。

v2.18.0 只读了 4 个文件（mission_auditor / mission_captain 的 9 原则 / prove.md 的 reductions / extract_decl_graph），漏掉了 mission_description（7 原则）、mission_solver（scout + disproof）、extract_sketch_info（sketch oracle）、以及 mission_captain 的 faithfulness 原则完整版（8 条，只落地了 5 条）。

---

## 二、新发现增量（按 P0-P4 性价比排序）

### P0-① Mission Description「Target 强度分层」→ 猜想 JSON 前置规范

**来源**：`references/mission_description.md` §3 Target

> 「order from weakest to strongest, make the goal the weakest stable statement: a goal with hard-coded constants is invalidated by the next improvement, while a goal asserting only the shape of the truth survives.」

**增量价值**：猜想 JSON 目前只声明「目标命题」，没有「目标强度分层」规范。这条原则要求：
- 目标 = **最弱的稳定陈述**（断言「真相的形状」），不是硬编码常数。
- 硬编码常数的目标会被下一个改进推翻（对应 V64 教训：`S := 谱底·‖φ‖²+V` 这种硬编码定义是 faithfulness gap）。

**嫁接方式**：在 `conjecture.json` 的 schema 里加一个可选字段 `target_strength`（`weakest_stable` / `hardcoded_constant`），或在 Stage 0 前用一条检查规则提示「目标是否硬编码常数」。**不动主线**。

---

### P0-② Mission Description「Formalization scope 前置排除平凡化」→ 猜想 JSON 前置声明

**来源**：`references/mission_description.md` §6 Formalization scope

> 「If the statement admits a trivializing formalization (a vacuous hypothesis, a definition under which the claim is trivially true, a hard-coded easy special case), rule it out in one sentence.」

**增量价值**：这是**前置声明**，与 `physical_content_audit.py`（v2.15.0 的**事后检测**）互补——在定义猜想时就显式排除三类平凡化（vacuous hypothesis / trivial-true definition / hard-coded special case），而不是等编译通过后再抓重言式。

**嫁接方式**：`conjecture.json` 加 `anti_trivialization` 字段（一句话排除平凡化），Stage 3 PPE 生成 Lean 时注入该约束。**不动主线**。

---

### P1-③ Faithfulness 8 原则完整版（3 条未充分落地）

**来源**：`references/mission_captain.md` §KEY principles（8 条，v2.18.0 只落地了 5 条注入 PPE prompt）

v2.18.0 漏掉的 3 条：

- **原则 3 — total function 坏输入默认值**：Lean 里除零、`Real.log` 负数、自然数减法、`sInf` 空集、无界集上确界、不可积函数积分都返回默认值（通常 `0`）而非报错。形式化前必须决定退化输入怎么处理，要么加源材料有的假设，要么用能表示源值的类型（`EReal` / `ℝ≥0∞`）。
- **原则 5 — edge inputs 边缘输入**：在空类型、`n=0`、空集、零阈值、**不可满足假设**（hypothesis 无实例可满足）、**vacuous conclusion** 上评估陈述。假设不可满足或结论仅空真，编码就是错的（即使定理可证）。
- **原则 6 — Verify formulas by hand**：接受转录前，用一个小具体实例手算验证每个常数、符号、不等式方向、边界下标。

**增量价值**：原则 3 和 5 是 `physical_content_audit.py` 目前**没有显式覆盖**的退化检测（现有检测聚焦「重言式」「空壳」，没覆盖「total function 默认值」和「不可满足假设 / vacuous conclusion」）。原则 6 与 Stage 1.5b `constant_certify.py`（PSLQ 认证）互补——PSLQ 是数值认证，原则 6 是「小实例手算」的符号级验证。

**嫁接方式**：把 3 条补进 `physics_proof_engine/reasoner.py` 的 `_build_proof_prompt`（现在只有 5 条），并可把原则 5 的「不可满足假设 / vacuous conclusion」作为 `physical_content_audit.py` 的新检测类（第 13/14 条）。**不动主线**。

---

### P1-④ Disproof 反证分支（管线缺口）

**来源**：`references/prove.md` §Submit a disproof + `mission_solver.md` §3 Attempt（three moves）

> 三种移动：**Direct proof** / **Disproof**（证明整个量化陈述的否定）/ **Reduction**（归约草图）。

**增量价值**：scientific-discovery-proof 的管线目前只有「证明」分支，**没有「反证」分支**。对「假猜想」的检测（Stage 1.5a planted-truth gate 的负对照是「检测污染输入」，不是「主动反证猜想」），主动尝试证明猜想的否定是一个补充——如果反证成功，说明猜想本身是错的，应提前终止而非继续投入 Stage 3 证明。

**嫁接方式**：Stage 2（SimpleTES 排名）后、Stage 3 证明前，加一个可选的 Stage 2.6 反证探测（或并入 Stage 1.5a 负对照的语义扩展）。**不动主线**，作为可选旁路。

---

### P2-⑤ sketch oracle（extract_sketch_info.lean）→ Lean AST 精确定位

**来源**：`scripts/extract_sketch_info.lean`（177 行 Lean meta-programming）

**核心洞察**：用 Lean 的 **InfoTree**（`infoState := { enabled := true }`）精确定位两个位置，**而不是 regex**：
1. **valStart**：`:=`（或 `where`/equation 块）的确切位置——声明在哪里结束、证明体从哪里开始。sketch stub = `text[declStart:valStart] ++ ": by sorry"`。
2. **ref facts**：每个项目常量引用的精确 source range（`start`/`end`），重命名按 range 而非 pattern-matching。

**增量价值**：对应 memory 里反复踩的坑——「DeepSeek 生成 `:= by trivial` 空壳检测」「嵌套注释 sorry 假阳性」（`/- -/` 可嵌套，正则会误判被注释的 axiom 为 active）、「声明 vs 证明体边界」。用编译器 AST 定位，比正则可靠得多。

**嫁接方式**：新增 `scripts/lean_decl_ast.py`（或复用该 .lean 脚本），在 Stage 3.5 的 `physical_content_audit.py` 里用 AST 定位 `:=` 位置判定「浅层证明」，替代部分 regex。**不动主线**，是 Stage 3.5 的检测精度增强。

---

### P2-⑥ Scout before you attempt（失败路径侦察）→ archive.jsonl 增强

**来源**：`references/mission_solver.md` §2 Scout before you attempt

> 读 edit history（被 captain 拒绝的形式化路径 + reason）、读 FAILED/CE/WA 提交、读 discussion dead-ends、读 backlinks——**避免重试已拒绝的方法、避免重走已失败的路径**。

**增量价值**：与已有的 `archive.jsonl` `failed_approach` 字段（Colosseum P1-2）互补，但新增两个概念：
- **权威拒绝路径 + reason**（captain/审稿人拒绝，附理由）—— 比「自己失败」更硬的信号。
- **读别人的失败**（FAILED/CE/WA 提交）—— 分布式失败知识，而非单一 agent 的 archive。

**嫁接方式**：`stage36_evolution.py` 的 record 里，把 `failed_approach` 升级为「拒绝方 + reason」结构；archive 注入时优先检索「权威拒绝」路径。**不动主线**。

---

### P3-⑦ Read-back 的「独立证词」定位深化（可选，哲学层）

**来源**：`references/mission_captain.md` §Read-backs: independent testimony for the audit

**增量价值**：v2.18.0 已落地 read-back（Stage 3.5a），但 prove2me 的定位更深——read-back 是审计的**「独立证词」（independent testimony）**，是第三方视角，不是 LLM 的自我检查。这个哲学深化影响的是「read-back 应由独立 sub-agent（不同模型/不同 prompt）执行」这一实践，而非新的检测。

**嫁接方式**：`faithfulness_readback.py` 的盲读 sub-agent 改用**不同的模型/温度/prompt**（与证明生成 agent 隔离），强化「独立证词」属性。**可选**。

---

## 三、性价比总表

| 优先级 | 增量 | 落点 | 性质 | 针对的问题 |
|---|---|---|---|---|
| P0 | ① Target 强度分层 | conjecture.json 前置 | 规范 | V64 硬编码常数 |
| P0 | ② 前置排除平凡化 | conjecture.json 前置 | 规范 | V64 重言式（前置）|
| P1 | ③ Faithfulness 原则 3/5/6 | PPE prompt + content_audit | 检测 | total function 默认值 / vacuous |
| P1 | ④ Disproof 反证分支 | Stage 2.6 旁路 | 能力缺口 | 假猜想主动反证 |
| P2 | ⑤ sketch oracle | Stage 3.5 AST 定位 | 工具 | 空壳/嵌套注释 sorry 假阳性 |
| P2 | ⑥ Scout 失败侦察 | archive.jsonl 增强 | 记忆 | 权威拒绝路径复用 |
| P3 | ⑦ 独立证词定位 | readback sub-agent 隔离 | 哲学 | read-back 可信度 |

---

## 四、诚实边界

- ① ② 是「前置声明」规范，不产生新的形式化保证——它们让猜想定义更诚实，但平凡化仍需 `physical_content_audit.py` 事后检测兜底。
- ③ 原则 5 的「不可满足假设 / vacuous conclusion」检测仍是启发式（需要 LLM 判断「假设是否可满足」），不是可判定检测。
- ④ 反证分支需要 LLM 主动尝试证明否定，成功率取决于 LLM 的证明能力，不是确定性门控。
- ⑤ sketch oracle 需要本地 Lean toolchain 编译通过后才能跑（oracle 只对可编译代码有意义），且宏展开生成的引用不可见（caveat 里已声明）。
- ⑥ ⑦ 是流程/哲学增强，不产生新的 BLOCK 门控。
