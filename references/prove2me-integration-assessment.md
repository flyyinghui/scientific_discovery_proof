# prove2me_workspace 集成评估（v2.18.0, 2026-10-08）

外部框架：**prove2me**（github.com/prove2me/prove2me_workspace，Lean 4 形式化众包协作平台）。
评估结论：核心价值**不是证明技术**，而是一套「形式化忠实性（faithfulness）审计」机制，
恰好补上 V64 教训（0 sorry/0 axiom 编译通过 ≠ 物理推导成立）的检测方法盲区。

## 一、可移植机制（4 个）

1. **Read-back 盲读回**（mission_auditor.md）：独立 sub-agent 只看 Lean 代码（不给物理意图），
   写「字面断言了什么」的自然语言 read-back；审计者对比 read-back 和意图找 faithfulness gap。
2. **Faithfulness 9 条原则**（mission_captain.md）：忠实性判据，特别是「total function 坏输入
   返回默认值」「边缘输入 vacuous theorem」「假设/结论双向匹配」「定义优先」「证明难度不是关切」。
3. **Reductions 归约分解**（prove.md）：分解为可复用核心引理，父定理在子引理证明后自动组合；
   激励可复用，避免 trivial `have...exact...` 转移。
4. **typeDeps/valueDeps 声明图**（extract_decl_graph.lean）：区分「语句依赖」vs「证明依赖」，
   前者决定定义层，后者决定归约边。

## 二、已落地增量（全部增量嫁接，主线五阶段不动）

| 增量 | 落点 | 落地文件 |
|---|---|---|
| P0-① Read-back 盲读回 | 新增 Stage 3.5a | `scripts/faithfulness_readback.py` + `pipeline_orchestrator.py` 的 `_run_stage35a_faithfulness_readback` |
| P0-② Faithfulness 9 原则 | Stage 3 PPE prompt | `physics_proof_engine/reasoner.py` 的 `_build_proof_prompt`（5 条约束） |
| P1-③ typeDeps/valueDeps | Stage 3.5c 增强 | `scripts/proof_dag_audit.py`（`node_type_and_value` + `unverified_definition_deps`） |
| P1-④ Reduction 可复用激励 | Stage 2.7 增强 | `scripts/preproof_decomposer.py`（`reusability` 字段 + REDUCTION REUSE RULE） |
| P2-⑤ Milestone 里程碑 | 猜想 JSON 增强 | `scripts/milestone_curation.py`（显式 milestones 验证 / 从 required_lemmas 自动提名） |

## 三、验证结果

- `milestone_curation.py`：从 dm_baryon_conjecture.json 自动提名 6 个里程碑（L1-L6），gate=PASS。
- `preproof_decomposer.py`：mock 模式正常，3 section 带 `reusability` 字段。
- `proof_dag_audit.py`：SL6C V4（738 声明）**新检测抓到 13 个「定义层未验证」**——如 `V6`
  （被 rhoAlg/dualNormSq 陈述引用但证明从未使用）、`TTSubspace`、`freeEnergy`、`phantomDensity` 等，
  正是「定义优先」原则要暴露的：定理建立在未验证的定义层上，定义错了则所有用它陈述的定理全错。

## 四、诚实边界

- `faithfulness_readback.py` 的盲读/对比走 DeepSeek v4-flash，是**启发式**审计（LLM 读代码），
  不是形式化保证。真正的 faithfulness 保证仍需人类审计者对比 read-back 和源材料。
- `unverified_definition_deps` 检测是**语法层**的（typeDeps 里引用但 valueDeps 里从未出现），
  可能有假阳性（定义的性质通过实例/typeclass 隐式使用，语法层看不到）——WARN 而非 BLOCK。
