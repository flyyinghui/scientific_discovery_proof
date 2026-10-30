# 公理/定理编号连续化与计数统一（终审后一致性修复）

**触发条件**：终审校核发现 (a) MD 论文公理编号有缺口（如 A1-A25 缺 A6/A17，A16 错位）、(b) MD 声称的公理计数与 Lean 实际漂移（如摘要说 25、引言说 14、结论说 61，Lean 实际 69——三个数字互相矛盾）、(c) Lean 的 axiom 编号（a1-a25）与 MD 的 A1-A25 不对应。

**根因**：多轮修改（每轮新增 axiom/def）后，只改了 Lean 代码，未同步 MD 的计数声明和编号；历史遗留的公理编号有缺口（废除的爆炸原理公理留下空洞 A6/A17）。

## 检测步骤

1. **MD 公理编号缺口**：`re.findall(r'\bA(\d{1,2})\b', md_txt)` → 排序 → 检查是否连续 1..N。
2. **Lean axiom 编号缺口**：`re.findall(r'\ba(\d{1,2})(?=[_\s:(])', lean_txt)` → 排序。注意 Lean 命名是 `a16_master_equation`（a+数字+下划线），`\ba16\b` 不匹配（`_` 是 word char，无 word boundary），必须用 `(?=[_\s:(])` 前瞻。
3. **计数漂移**：grep MD 的 `twenty-five|fourteen|\b61\b|four theorems` 等计数声明，与 Lean 的 `grep -c '^axiom '`（排除注释）对比。MD 里同一"公理总数"出现 3 个不同数字是典型漂移信号。

## 修复工作流（五步）

### 1. 建立重编号映射表（旧 → 新）

把缺口处的编号前移补齐。CGICE 案例（A7→A6, A16→A7, A11→A10, A12→A11, A13→A12, A14→A13, A15→A14, A18-A22→A15-A19, A23-A25→A20-A22）：

```python
mapping = {
    'A25':'A22','A24':'A21','A23':'A20','A22':'A19','A21':'A18',
    'A20':'A17','A19':'A16','A18':'A15',
    'A16':'A7','A15':'A14','A14':'A13','A13':'A12',
    'A12':'A11','A11':'A10','A7':'A6',
}
```

### 2. MD 重编号：re.sub 函数式替换（避免顺序冲突）

⚠️ 顺序冲突陷阱：`A16→A7` 和 `A7→A6` 若用 `str.replace` 顺序执行，先 `A16→A7` 会把新 A7 再被 `A7→A6` 误改。必须用**函数式一次性替换**：

```python
new = re.sub(r'\bA(\d{1,2})\b', lambda m: mapping.get('A'+m.group(1), 'A'+m.group(1)), txt)
```

### 3. Lean 同步重命名（a 编号）

同一映射表，用前瞻正则匹配 a+数字后跟下划线/空格/冒号/括号：

```python
new = re.sub(r'\ba(\d{1,2})(?=[_\s:(])', lambda m: 'a'+mapping.get(m.group(1), m.group(1)), txt)
```

这会同时重命名 axiom 声明（`axiom a16_master_equation`）和所有引用点（`exact a16_master_equation`）。

### 4. 计数统一（MD 三处）

摘要/引言/§8.1/结论的计数声明统一为 Lean 实际值。CGICE 案例：`"twenty-five"`/`"fourteen axioms"`/`"61 axiom"` 全部 → `"21 core physical axioms (A1-A22) + 69 Lean axiom declarations total"`。定理计数补 `"four primary theorems (T1-T4) plus 15 auxiliary theorems and 13 lemmas"`。

### 5. 编译验证 0 sorry

重命名后 `lake build` 确认不破坏编译（引用点同步重命名后应通过）。

## 关键陷阱

- **Lean 重复声明**：新增 `def lambda_par`/`axiom M_Pl` 前先 grep 已有声明。CGICE 文件头部已有 `noncomputable def lambda_par := 35` 和 `M_Pl := 2.435e18`，新增会报 "already been declared"。
- **MD section 标题同步**：重编号后 §3.x 标题里的 `(A8-A12)` 等范围也要同步改（如 §3.2 变 `(A8-A11)`）。
- **A10 是 def 不是 axiom**：重编号时注意某些编号已降级为 `def`（非 axiom），计数时区分。
- **编号前移的物理语义**：重编号后所有正文引用（如"主方程 A16"）都变成新号（A7），要 grep 确认无残留旧号引用。

## 实测案例

CGICE V9.1 终审（2026-08-18）：MD 摘要 25 / 引言 14 / 结论 61 三处计数矛盾 vs Lean 实际 69 axiom；MD A1-A25 有缺口（缺 A6/A17，A16 错位）；Lean a1-a25 缺 a6/a10/a17。修复：55 处 MD 重编号 + 23 处 Lean 重命名 + 6 处计数统一，MD A1-A22 连续 = Lean a1-a22 连续 = 完全对应，编译 3100 jobs 0 sorry。
