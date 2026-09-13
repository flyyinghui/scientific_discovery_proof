# RSIHub Lean 桥接（Stage 3.6 落地）

把 scientific-discovery-proof 的 Stage 3.6「冻结评估器进化循环」正式接入 RSIHub，
用 RSIHub 的 **真实 operator 类**（`deepseek_lean` mutate）+ **冻结评估器**
（`lean_eval`）+ append-only `archive.jsonl` 做 Lean 证据链的自我进化。

## 组件清单

| 组件 | 路径 | 说明 |
|---|---|---|
| RSIHub mutate operator | `~/AI_for_Science/RSIHub/library/mutate/deepseek_lean.py` | DeepSeek v4-pro 诊断 + v4-flash 重写 Lean（有界） |
| RSIHub 冻结评估器 | `~/AI_for_Science/RSIHub/library/evaluators/lean_eval.py` | MathCode 风格确定性评分 |
| RSIHub 配方 | `~/AI_for_Science/RSIHub/recipes/lean_proof/evolve.yaml` | 完整 wiring（hillclimb + jsonl） |
| 桥接脚本 | `scripts/rsihub_lean_bridge.py`（本技能） | 零-Docker 驱动 RSIHub 循环 |
| RSIHub 技能 | skill: `rsihub` | 框架用法 + 配方文档 |

## 调用方式（scientific-discovery-proof 启动时）

```bash
cd ~/AI_for_Science/RSIHub
.venv/bin/python <skill-dir>/scripts/rsihub_lean_bridge.py \
    --lean /path/to/proof.lean \
    --generations 3 \
    --output /tmp/lean_evo \
    [--dry-run]   # 只跑冻结评估器，不调 DeepSeek
```

## 循环语义（对齐 RSIHub 可信性保证）

1. **select** → `newest`（取最新接受的父代）
2. **rollout** → `noop`（评估是确定性的，无 benchmark 采样）
3. **analyze** → 冻结评估器的缺陷报告（确定性检测，非 LLM 判断）
4. **mutate** → `deepseek_lean`：v4-pro 诊断根因 + v4-flash 重写（只改 `target/**/*.lean`）
5. **gate** → `hillclimb`（strict：只接受分数严格提升）
6. **record** → `jsonl`（append-only `archive.jsonl` 谱系）

## 冻结评分公式（候选者不可改写）

```
score = 100 − 20·sorry − 15·admit − 10·(trivial+True_stub) − 30·compile_failed
```

**冗余引理 / 未用 axiom / 悬空引用仅记录不计分**——honest-axiom 物理证明合法携带
大量未用 axiom（诚实披露研究级前提）与证据链引理（中间结果），且 DAG 审计的
「悬空引用」常是注释里的旧公理名（真悬空会编译失败）。这与 Hybrid Review 的结论
一致：V17 三峰引力波证明 0 sorry / 0 admit / 编译通过，即满分 100。

## 与 Stage A（lean_recursive_repair）的差异

- **Stage A**：单点 sorry 修复（flat self-refinement）
- **Stage 3.6 / RSIHub**：多维冻结评分驱动的多代进化 + 严格门控 + 证据链谱系

## 测试结果（2026-09-04）

- `deepseek_lean` operator：`--describe` / `--validate-config` 通过（stage=mutate）
- `lean_eval` 冻结评估器：对 V17 三峰引力波证明（0 sorry）返回 score=100.0
- 桥接 dry-run：0.3s 完成，`archive.jsonl` + `best_proof.lean` + `result.json` 正确产出

## 陷阱

- `library` 是仓库根顶层包（非 `src/`），桥接脚本需 `sys.path` 同时加仓库根 + `src/`。
- 桥接脚本必须用 RSIHub venv（3.12）运行：`cd ~/AI_for_Science/RSIHub && .venv/bin/python ...`。
- 完整 `evolve run` 配方仍需 harbor/local 评估 plumbing；桥接脚本是零-Docker 的等价路径。
