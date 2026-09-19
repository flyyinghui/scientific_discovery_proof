# RSIAgent Integration (v2.8.0)

**来源**：RSIAgent: Autonomous Exploration for Recursive Self-improvement in New Environments
(arXiv:2609.15364, Aether AI, 2026-09-14)

**集成日期**：2026-09-19 | **论文**：`~/ai_for_science/papers/RSIAgent_2609.15364.pdf`

## 论文核心

RSIAgent 是 training-free 多智能体递归自我改进框架，通过自主记忆构建让 agent 适应新环境：

1. **三智能体 harness**：
   - **Actor Agent**（可进化记忆）：主策略，执行代码动作，维护持久记忆（环境知识/可复用程序/经验教训）
   - **Verifier Agent**（环境反馈接地）：独立评估者，与 actor 私有推理隔离，接地于环境反馈
   - **Curriculum Agent**（引导探索）：决定「下一步探索什么」，生成前置技能/信息性变体/失败驱动练习/压力测试

2. **Broad-then-deep 两阶段探索**：
   - **BRS**（广递归探索）：并行探索多样方向，构建广泛理解
   - **DRS**（深递归探索）：顺序深挖，聚焦知识缺口/硬案例/边界条件，逐步加难

3. **因果记忆**：actions → conditions → consequences 的可复用因果三元组（非被动事实记录）

4. **记忆冻结复用**：探索后冻结记忆，测试时直接复用，零参数更新

**消融证据**：full RSI 74.54% vs broad-only 65.52% vs deep-only 56.50%（broad + deep 缺一不可）。

## 移植决策：哪些嫁接、哪些不嫁接

scientific-discovery-proof 已集成 RSI 家族三成员（RSIHub v2.4 / Dream-RSI v2.7 / Co-Scientist v2.3），
所以只移植 RSIAgent 的**独有增量**，避免重复：

| RSIAgent 模块 | 已有雏形 | 移植决策 |
|---|---|---|
| Curriculum Agent | 无（管线是被动固定五阶段）| ✅ **P1 新增 Stage 2.5** |
| Broad 广搜 | MCTS + 5 方案自我进化 | ❌ 已有，不重复 |
| Deep 深挖 | Stage A 递归修复 | ❌ 已有，不重复 |
| 因果记忆三元组 | archive.jsonl 被动记录 + Dream-RSI mutation_strategy | ⏸ 暂缓（P3，需 archive schema 升级）|
| Verifier 隔离 | L2 用 DeepSeek 但未隔离 | ⏸ 暂缓（P4，低优先级）|
| 失败模式映射 | Stage 3.5 六类 P0 | ✅ **P0 新增 3 条规则** |

## 落地内容

### P0 — Stage 3.5 三条失败模式检测规则

改 `scripts/proof_consistency_audit.py`，新增检测 7/8/9（映射 RSIAgent 三大失败模式）：

| 检测 | RSIAgent 失败模式 | 占比 | 触发条件 | 反触发条件 |
|---|---|---|---|---|
| 7. unchallenged_axiom | unchallenged assumptions | 25% | axiom 全文件仅声明处出现 1 次 | 被任何 theorem 签名/证明体/exact 引用 |
| 8. uncertainty_downgrade | uncertainty not enforced | 33% | paper 用 prove/proven/established 描述实为 axiom/opaque 的声明 | paper 明确用 honest-axiom/postulate/assumption |
| 9. rule_scope_loss | rule scope loss | 67% | paper 无条件表述条件定理（带参数前提）| paper 用 given/assuming/conditional/under/if |

**验证**（三大时空相 V18：137 axioms / 153 theorems / 0 sorry）：
- 检测 7 报 59 个未挑战 axiom（真冗余假设，如 ORF_self/H0sq_pos/KLS_concentration_axiom 从未被引用）
- 检测 8 报 1 个（`metric` 被确定性动词描述但实为 opaque）
- 检测 9 报 3 个（dual_involution/main_isotropic_vanishing/source_sum_zero 被无条件表述）

### P1 — Stage 2.5 Curriculum Planner

新增 `scripts/curriculum_planner.py`，在 SimpleTES 排名后、PPE 证明前生成证明变体任务队列。

**五大任务类型**：
1. `weaken_premise` — 移除一条 honest-axiom，检验定理是否仍成立（找冗余公理）
2. `strengthen_premise` — 增加边界条件，检验证明链鲁棒性
3. `boundary_case` — 边界反例搜索（对应 MAF 50K 反例的课程化）
4. `axiom_recombine` — 不同 honest-axiom 子集组合，找最小充分集
5. `stress_test` — 移除关键 axiom，确认定理坍塌（验证 axiom 必要性）

**集成点**（`pipeline_orchestrator.py`）：
- `STAGE_SCRIPTS` 新增 `'2.5'` 定义
- 新增 `run_stage25_curriculum()` 函数
- `main()` 中 `--stages` 解析加入 `'2.5'`，循环中 `elif stage_num == '2.5'`

**调用**：
```bash
python curriculum_planner.py --conjecture conjecture.json \
    --ranked stage2_ranked_candidates.json --archive archive.jsonl \
    --output stage25_curriculum.json [--mock]
```

**LLM vs mock**：有 API key 时用 v4-flash（thinking disabled）生成针对性变体（实测暗物质拓扑缺陷
猜想生成 8 个高质量任务：非幂律淬火率弱化、±10% KZ 指数扰动、偏置 Z2 势压力测试等）；
无 key 回退确定性 mock 模板（3 axiom × weaken+stress + 全局 boundary/strengthen/recombine）。

### P2 — Stage 3.6d Deep Refinement (DRS)

新增 `scripts/deep_refinement.py`，实现 RSIAgent broad-then-deep 的 deep 阶段（顺序深挖）：

- **聚焦单一盲区缺陷**：`_select_target_defect()` 优先选历史盲区（从未修复成功的缺陷），
  否则按 DEFECT_PRIORITY 最严重。
- **难度递增阶梯**（每轮针对目标缺陷提高要求）：
  - difficulty 0: 基础修复（补证明体 / 诚实公理化）
  - difficulty 1: + 边界条件显式化
  - difficulty 2: + 反例搜索（验证鲁棒性）
  - difficulty 3: + 最小充分集（删除冗余公理）
- **与 Stage 3.6 互补**：Stage 3.6 = broad（ε-greedy 多策略综合进化），
  Stage 3.6d = deep（聚焦单缺陷深挖）。RSIAgent 消融证据：full > broad > deep，
  deep 是 broad 之上的增益补充。

### P3 — archive.jsonl 因果三元组升级

`replay_strategies.py` + `stage36_evolution.py`，把 archive 从「被动记录」升级为
actions→conditions→consequences 可复用因果记忆：

- `defect_signature(defects)` — 缺陷 dict → condition 签名（如 `sorry&admit`）
- `ReplaySimulator.causal_rules()` — 提取 (action=mutation_strategy, condition=缺陷签名,
  consequence=成功率/gain) 三元组
- `ReplaySimulator.condition_match(defects)` — 返回当前缺陷签名下的历史成功先例
- `stage36_evolution.py` record 新增 `condition` 字段 + `_analyze` 注入「成功先例」

**核心洞察**：同一 action 在不同 condition 下效果不同（如 axiomatize 在 sorry&admit 下
成功率 1.0，deduplicate 在同一 condition 下 0.0），condition 维度让策略选择更精准。

## 关键教训

1. **检测 7 的假阳性陷阱**：初版用「证明体引用」检测未挑战 axiom，误报 85 个（把「作为定理
   参数类型被引用的 axiom」漏算）。修复：改用「全文件出现次数 ≤ 1」判定——axiom 名作为
   `(h : AxiomName)` 参数类型出现时也被计入引用。

2. **失败模式 → 检测规则映射的粒度**：RSIAgent 的 7 类失败模式里，只有 3 类能在 lean+paper
   输入下机械检测（unchallenged/uncertainty/scope）。其余 4 类（target-skill mismatch /
   grounding gaps / coverage gaps / fidelity gaps）需要 L2 LLM 层或 archive 层，本次不落地。

3. **不动主线的增量嫁接**：P0/P1 都不改动现有五阶段管线的 Stage 0/1/2/3/4 逻辑，只新增
   Stage 2.5 脚本 + Stage 3.5 检测规则，符合「增量嫁接不改主线」的原则。

## 未落地（后续可选）

- **P4**：Verifier 隔离（L2 用独立模型实例，不与 actor 共享上下文）
- **P5**：记忆冻结复用（证明模板库冻结，跨猜想迁移）
- **P6**：Stage 2.5 课程队列与 Stage 3.6d 深挖的闭环（课程生成的任务队列当前是
  独立产出，未自动反馈到 Stage 3 的 MCTS 分支选择）
