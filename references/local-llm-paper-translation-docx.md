# 本地 LLM 翻译学术论文 + 图表生成 + DOCX 组装（2026-08-19 验证）

把英文论文 MD 翻译为中文 DOCX，并用论文核心观点生成科技图表插入对应章节。全流程本地化（无云端 API）。

## 工作流（四步）

1. **分块翻译**（本地 thinking 模型，禁用 thinking）
2. **生成科技图表**（matplotlib + Microsoft YaHei + 冷色系）
3. **组装 DOCX**（python-docx + 图表插入映射）
4. **验证**（图表数量 + 译文完整性）

## 1. 分块翻译

- 模型：qwen3.8:27b-q8_0（llama-server 8081，多 GPU `--tensor-split 1,1,1,1`）
- **禁用 thinking**：`chat_template_kwargs: {"enable_thinking": False}` —— 不加则 thinking 吃光 max_tokens 返回 content=""（Qwen3.8 禁用后 ~10 字符/秒，翻译 48 字符样本 4.7s）
- 分块：按空行 `re.split(r'\n\s*\n', txt)` 分段落，每块合并到 ~2000 英文字符（82K 字符论文 → 36 块）
- **保留 LaTeX 公式**：prompt 明确 "Preserve ALL LaTeX formulas ($...$ and $$...$$), math notation, section numbers, and [bracketed] tags EXACTLY as-is. Translate only the prose text."
- **增量保存**：每块翻译完写 `translation_partial.txt`（后台长任务防丢失，~40 分钟/36 块）
- 失败容错：单块异常 `except` 保留原文继续

## 2. 科技图表（冷色系 + 中文）

- 环境：base conda python（matplotlib 3.9.2），**不要**依赖 SciencePlots（直接用 rcParams 更稳）
- 字体：`plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']` + `axes.unicode_minus = False`
- **Pitfall（复发）：`figures_zh/` 目录必须先 `mkdir -p` 再保存**，否则 `FileNotFoundError: No such file or directory: '...fig1.png'`（matplotlib savefig 不自动建目录）
- **所有 Unicode 数学符号替换 ASCII**（Microsoft YaHei 无 math glyph，Pitfall #11 in scientific-visualization）：`λ→lambda, ρ→rho, ²→^2, →->, ≈~, ×x, √→sqrt, ∞→inf`
- 冷色系：#2E86AB（青蓝正相关）/ #A23B72（紫红负相关）

论文核心观点 → 图表映射（CGICE 案例，5 图）：
| 图 | 内容 | 对应章节 |
|----|------|---------|
| fig1 | 双阶段 RG 流（g_TC 0.5→2.60，μ_c 相变）| §7.3 |
| fig2 | Fokker-Planck 协方差耗散（122 阶）| §7.2 |
| fig3 | 双谱隙（λ_∥=35 vs λ_⊥=35/3）| §2.7 |
| fig4 | 宇宙相变时间线 | 摘要 |
| fig5 | η_k=72/35 第一性原理 + g*=2.60 | §7.3 |

## 3. DOCX 组装

- python-docx 中文字体：`style.font.name = 'Microsoft YaHei'` + `style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')`（**必须设 eastAsia**，否则中文不生效）
- 图表插入映射 `fig_map = [(章节标题关键词, 图片文件名), ...]`，遍历段落遇到 `#` 标题含关键词时 `doc.add_picture(..., width=Inches(5.5))`
- LaTeX 公式 `$$...$$` 保留为居中文本（不尝试转 OMML）
- 引用块 `>` → 缩进段落；`**bold**` → 加粗 run

## 陷阱

- `ps aux` 在 Windows 不可用（FileNotFoundError）——进程检查用 `requests.get(port/health)` 探活即可
- 后台翻译用 `terminal(background=True, notify_on_complete=True)`，日志写工作目录（MSYS /tmp 与 Windows temp 不通）
- 分块太大（>3000 字符）会让 thinking 模型慢到超时；太小（<500）块数爆炸
