# Kosmos 集成评估与落地 (v2.26.0, 2026-10-24)

> 来源：jimmc414/Kosmos（v0.2.0-alpha，Lu et al. 2024《Kosmos: An AI Scientist for
> Autonomous Discovery》arXiv:2511.02824 的开源实现）
> 深读：`validation/scholar_eval.py`（8 维度）、`validation/null_model.py`（置换检验）、
> `validation/failure_detector.py`（3 类失败模式）、`validation/accuracy_validator.py` +
> `benchmark_dataset.py` + `accuracy_tracker.py`（基准准确率）、`core/convergence.py`（收敛）、
> `core/feedback.py`（反馈循环）、`workflow/ensemble.py`（多运行收敛）、`world_model/`（知识图谱）、
> `compression/compressor.py`（20:1 压缩）。

---

## 一、核心判断

Kosmos 是**实验科学** AI 科学家（统计假设检验），scientific-discovery-proof 是**形式化证明**
（演绎）管线。Kosmos 的增量**不能直接提升「形式化证明」的正确率**（证明正确性由 Lean 编译器
演绎保证），但可移植四个**间接层**机制：

| 层 | 增量 | 落地位置 | 优先级 |
|---|---|---|---|
| 元层 | ground-truth 基准验证 | `proof_benchmark.py` | **P0** |
| 数值层 | 置换检验假阳性检测 | `null_model_probe.py` | P1 |
| 论文层 | 声称强度审计 | `claim_strength_audit.py` | P1 |
| 迭代层 | 收益递减自动停止 | `stage36_evolution.py` 内嵌 | P1 |

---

## 二、P0 — proof_benchmark.py（物理猜想形式化证明基准集）

**动机**：scientific-discovery-proof 宣称的「78%→65% success rate」长期只有「结构完整性 +
历史证据」近似（v2.24.0 诚实边界自认），无独立 ground-truth 基准。本脚本补齐「诚实度量正确率
这个数字本身」。

**机制**：一组已知真假的物理猜想（正例=已知成立的定理；反例=已知为假/混淆的猜想），验证管线
对每条给出正确判断（正例应证明、反例应拒绝），计算准确率。

**种子基准集**（SL(6,C) 四论文的已知事实，6 条）：
- 正例（应能证明）：|ρ|²=35/2（Weyl 范数）、g_TC²=24π²/35（IR 定点）、λ_KLS=35/3（横向谱隙）
- 反例（应拒绝）：g_TC²=8π²/35（历史 bug，误用纵向 λ_∥=35）、|ρ|²=35 在 SU(3,3)（混淆实形式）、
  c_β=3/(64π²) 精确等式（native_decide 假精确，应为误差不等式）

**轻量验证逻辑**（复用门控语义，不依赖 LLM）：
- 正例：0 sorry/admit + 0 axiom + 物理内容非平凡（实质 tactic）
- 反例：任一「不可证明」信号（编译失败 / sorry>0 / axiom>0 / 重言式）

**诚实边界**：种子基准集正例的 `lean_file=None`（需填实际 Lean 路径才能真正验证），当前跑种子
清单时正例记 indeterminate；种子清单的核心价值是**固化 SL(6,C) 已知事实**（防再次踩 g_TC²=8π²/35
这类 bug）+ 提供「正确率」的可测量框架。

---

## 三、P1-1 — null_model_probe.py（数值层置换检验）

**动机**：对抗 LLM 数值验证的「sycophancy loop」——数值发现必须在随机扰动下**消失**，否则是
平凡恒等式/数值巧合/假阳性。

**机制**：置换检验（默认 1000 次，±10% 高斯扰动参数），计算「扰动后仍 ≈ claim 的比例」
（persistence_rate），>50% 即判 persists_in_noise（假阳性）。

**与 planted_truth_gate (v2.13.0) 互补**：
- planted_truth_gate：验证数值引擎能恢复已知答案(正对照) + 抓住污染输入(负对照)
- null_model_probe：验证「数值发现」对参数扰动敏感(对抗数值巧合/平凡恒等)

**诚实边界**：仅当猜想涉及「从数据拟合/校准」时有意义（g_TC 校准、味荷比拟合、谱隙数值印证）；
纯解析推导的猜想（|ρ|²=35）不涉及统计，不适用。

---

## 四、P1-2 — claim_strength_audit.py（论文声称强度审计）

**动机**：检测论文「声称强度」与「Lean 证据强度」的失配，对应「预测度诚实化」原则。

**机制**：词表层检测——扫描强声称词（prove/establish/demonstrate/confirm/derive…）vs 证据链
等级（L0 黄金门控干净 / L1 条件定理·honest-axiom / L2 多 axiom·校准·sorry），强声称 + 弱证据
= 过度声称（WARN/BLOCK）。

**与 Hallucination Clipping (v2.3.0) + physical_content_audit (v2.15.0) 互补**：本脚本是
词表层（声称措辞 vs 证据链强度），不涉及数值。

**诚实边界**：词表匹配是启发式（可能有假阳性，如「prove」用于「attempt to prove」的否定语境）；
需与证据链等级（从 Lean 文件 grep）配合，不能单独作为 BLOCK 门控。

---

## 五、P1-3 — 收益递减自动停止（stage36_evolution.py 内嵌）

**动机**：对应 Kosmos convergence.py 的 diminishing_returns 停止准则。

**机制**：在 Stage 3.6 进化循环的 accepted 分支，追踪最近 N 代 gain（`DIMINISHING_WINDOW=3`），
连续 N 代 gain 严格递减且末代 gain < `DIMINISHING_MIN_GAIN=5.0` → 主动提前停止（省 token + 防过拟合）。

**与现有停止条件并行**：stall_counter（无增益停滞）+ 满分收敛 + 收益递减，三者互补。

---

## 六、未落地（诚实边界）

- **ScholarEval 8 维度评分**：是实验发现的质量评分（novelty/impact/rigor…），不适用于形式化
  证明的演绎正确性，不落地。
- **Ensemble 多运行收敛**：对抗 LLM 非确定性有价值，但成本 ×N，与 v2.25.0 best-first tree
  search 多草稿互补，作 P2 可选（本次未落地）。
- **World Model 知识图谱**：Kosmos 的 world_model 是 Neo4j 存储（Entity/Relationship），
  与 JANUS 的「预执行预测世界模型」同名不同义，J-space 桥接（v2.22.0）已覆盖，无增量。
- **上下文压缩 20:1**：工程优化，与正确率无关，不落地。
- **Kosmos 自己的 79.4% 未复现**（README 自认「Not a reproduction study」）——可移植的是
  机制不是数字。
