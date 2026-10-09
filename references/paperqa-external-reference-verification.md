# PaperQA2 → Stage 3.5 外部引用真实性核查（嫁接方案）

**评估日期**：2026-10-03
**来源**：Future-House/paper-qa（PaperQA2，v5+，Apache-2.0，9.3k★）
**目标**：把 scientific-discovery-proof 的 Stage 3.5 引用核查从「内部核对」升级为「外部真实性核查」

---

## 一、背景与动机：为什么要嫁接

### 现状缺口

Stage 3.5 的 `reference_verification.py`（ScientistTwo P0-1）只做**内部核对**：
- 正文 `[n]` 引用 ↔ 参考文献表逐条核对
- 悬空引用 → BLOCK，未引用 → WARN

它**无法发现**以下缺陷（这些恰是 memory 里反复踩的坑）：
1. **幻影引用**：正文引用 [58]-[64] 但列表无对应条目（V50 案例：7 条缺失）
2. **元数据错误**：Davidson-Ibarra bound 被引用为 Super-Kamiokande 论文（V50：6 条错误）
3. **不支持引用**：文献存在但**不支持**所引论断（「存在但被张冠李戴」）
4. **外部真实性**：参考文献本身是否真实存在（vs 被 LLM 幻觉出来）

内部核对只能抓「编号是否对齐」，抓不了「引用是否真实、是否正确、是否支持」。

### PaperQA2 补什么

PaperQA2 = 高精度科学文献 RAG + 元数据自动获取，正好补三件事：
1. **元数据层**（Crossref + Semantic Scholar + Unpaywall）：自动获取论文元数据（含 citation counts + retraction check）→ 验证引用**存在性 + 元数据匹配**
2. **RAG 层**（全文检索 + 引用定位）：从本地文献库检索证据段落 → 验证引用**是否支持所引论断**
3. **contradiction detection**：超人类水平的矛盾检测 → 发现「引用与正文断言矛盾」

---

## 二、PaperQA2 机制（最小理解）

```python
from paperqa import Settings, ask

answer = ask(
    "Does the paper by Davidson & Ibarra (2002) support the bound M_R ≈ 10^14 GeV?",
    settings=Settings(paper_directory="<data>/papers"),
)
# answer.formatted_answer  # 带引用的答案（精确到 pages）
# answer.context           # 证据段落摘要
```

核心依赖链：
- **LLM**：LiteLLM（可接 DeepSeek）
- **embedding**：默认 OpenAI，可换本地 sentence-transformers
- **全文搜索**：tantivy（Rust）
- **元数据**：Crossref / Semantic Scholar / Unpaywall

---

## 三、嫁接点：Stage 3.5 新增「外部引用核查」检测

**不动主线五阶段**。在现有 Stage 3.5（一致性审计）的 `reference_verification.py` 之后，新增一个**外部核查脚本**，把「内部核对」升级为「内部 + 外部双层核查」。

```
Stage 3.5 引用核查（升级后）：
├─ P0-1a 内部核对（现有 reference_verification.py，stdlib-only，快）
│   └─ 正文 [n] ↔ 参考文献表 悬空/未引用 核对
└─ P0-1b 外部真实性核查（新增 external_reference_verification.py，需 PaperQA2 + 网络）
    ├─ 每条引用 → 元数据验证（Crossref/S2）：存在性 + 元数据匹配
    ├─ 每条引用 → RAG 支持性验证：是否支持所引论断
    └─ 判定：verified / metadata-mismatch / unsupported / hallucinated
```

---

## 四、脚本接口设计（external_reference_verification.py）

### 输入
- `--paper` 论文 txt（或 MD）
- `--library` 本地文献库目录（PDF/text）
- `--model` LLM（默认 `deepseek/deepseek-flash`）
- `--embedding` embedding 模型（默认本地 sentence-transformers）

### 流程
1. 正则提取参考文献表：`[n] Author(s), "Title", Venue, Year`（复用 reference_verification.py 的解析逻辑）
2. 对每条引用，分两步验证：
   - **Step A 元数据验证**（Crossref/S2 API，无需 LLM）：标题 + 作者 + 年份 + venue 是否匹配真实文献
   - **Step B 支持性验证**（PaperQA2 RAG，需 LLM）：`"Does {Title} by {Author} ({Year}) support the claim {正文引用处断言}?"` 在本地文献库检索
3. 判定 + 门控

### 输出 JSON
```json
{
  "ref_key": "[5]",
  "claimed_metadata": {"title": "...", "authors": "...", "year": "...", "venue": "..."},
  "metadata_status": "verified | metadata-mismatch | hallucinated",
  "support_status": "supported | unsupported | unverified",
  "evidence": {"search_query": "...", "found_url_or_doi": "...", "matched_pages": "..."},
  "severity": "BLOCK | WARN | PASS"
}
```

### 门控规则（对齐 ScientistTwo P0-1 的 severity 标准）

| 判定 | 含义 | severity |
|---|---|---|
| hallucinated | 查无此文献（元数据层查不到） | **BLOCK**（一票否决） |
| metadata-mismatch | 存在但标题/作者/年份/venue 偏差 | **BLOCK** |
| unsupported | 存在但不支持所引论断 | **BLOCK** |
| unverified | 网络受限无法核查 | WARN（降级，标注「未核查」） |
| verified | 四要素全匹配 + 支持 | PASS |

**执行约束**（对齐 F2 引用核查）：无网络时**不得默认 verified**，一律标 unverified 并降级 gate 结论（引文审核未完成 ⇒ 不得 PASS）。

---

## 五、安装配置（WSL 本机，已装包验证）

```bash
# 1. 独立 venv（Python 3.11+）
/usr/local/lib/hermes-agent-v14/venv/bin/python -m venv ~/projects/PaperQA/.venv
~/projects/PaperQA/.venv/bin/pip install "paper-qa>=5" litellm sentence-transformers

# 2. DeepSeek LLM（LiteLLM）
export DEEPSEEK_API_KEY=...   # 从 ~/projects/.env 读

# 3. 配置（paperqa Settings）
from paperqa import Settings
settings = Settings(
    llm="deepseek/deepseek-flash",           # LiteLLM 模型名
    embedding="sentence-transformers/...",   # 本地 embedding（DeepSeek 无 embedding API）
    paper_directory="<data>/papers", # 本地文献库
)
```

### 关键陷阱（本机验证）
1. **DeepSeek 无 embedding API** → 必须用本地 sentence-transformers（或 OpenAI embedding），否则 PaperQA2 默认 OpenAI embedding 会失败。
2. **LiteLLM 模型名**：DeepSeek 只有 `deepseek-flash` / `deepseek-v4-pro` 两个有效名（`deepseek-chat` 已废弃）。
3. **文献库规模**：100+ 篇建议配 Crossref + Semantic Scholar API key（避免 public rate limit）。
4. **首跑慢**：索引构建（PDF 解析 + tantivy 全文索引 + embedding）首次需几分钟。

---

## 六、数据流（增量不动主线）

```
现有主线：Stage 3 (PPE 证明) → Stage 3.5 (一致性审计) → Stage 4 (论文生成)
                        ↑ 在此插入外部核查，不改变 Stage 3/4 的接口

Stage 3.5 内部：
  proof_consistency_audit.py (L1 机械层)
  → reference_verification.py (P0-1a 内部核对，现有)
  → ★ external_reference_verification.py (P0-1b 外部核查，新增，PaperQA2)
  → 门控：任一 BLOCK → Stage 4 不启动
```

**回滚**：外部核查脚本独立，不侵入现有脚本；移除即回到内部核对版本。PaperQA2 依赖装在独立 venv（~/projects/PaperQA/.venv），不污染 Hermes venv。

---

## 七、与现有能力的边界（不重复）

| 能力 | 现有方案 | PaperQA2 增量 |
|---|---|---|
| 内部引用核对 | reference_verification.py（悬空/未引用） | 无（保留） |
| 外部存在性核查 | 无 | ✅ 元数据层（Crossref/S2） |
| 外部支持性核查 | 无 | ✅ RAG 层（证据段落） |
| 概念关联检索 | neural-memory-brain（brain.recall） | 不重复（PaperQA 是精确引用，大脑是语义关联） |

**关键**：PaperQA2 与大脑**互补**——大脑做「证明时概念桥接」（无出处），PaperQA2 做「投稿前引用真实性核查」（精确可追溯引用）。

---

## 八、性价比排序（P0-P4）

| 优先级 | 增量 | 价值 | 成本 |
|---|---|---|---|
| **P1** | P0-1b 外部引用核查（元数据 + 支持性） | 直接治「幻影引用」病（V50 的 7 缺失 + 6 错误） | 中（装 PaperQA2 + 建文献库） |
| P2 | Stage 0 前置文献综述（猜想新颖性判断） | 避免「重新发明已知定理」 | 中 |
| P3 | Stage 2.5 候选新颖性检查 | 锦上添花 | 低 |
| P4 | 矛盾检测（contradiction detection）接入 L2 | 与现有 L2 结构审计部分重叠 | 中 |

**建议先做 P1**——它是唯一直接解决「你反复踩的坑」的增量，且不改变主线。

---

## 九、验证方法

1. 用 V50 的已知缺陷做**负对照**：V50 有 7 条缺失 + 6 条错误引用（Davidson-Ibarra 被引用为 Super-K，Eldan DOI 指向他人），外部核查应全部 BLOCK。
2. 用一条真实引用做**正对照**：如 Coleman-Weinberg 1973（PRD 7, 1888），应 PASS。
3. 验证「不支持引用」：构造一条「文献存在但张冠李戴」的引用，应 BLOCK unsupported。

---

## 附：PaperQA2 关键参考

- 仓库：https://github.com/Future-House/paper-qa
- 论文：https://paper.wikicrow.ai（PaperQA2 超人类性能示例）
- 核心 API：`from paperqa import Settings, ask` / `agent_query`（async）
- 依赖：tantivy（全文搜索）/ LiteLLM（LLM）/ Crossref + Semantic Scholar（元数据）
