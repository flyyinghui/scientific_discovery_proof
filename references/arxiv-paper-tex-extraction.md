# arXiv 论文下载与公式提取（无 web 工具时的可用路径）

场景：需要"读外部论文并调用其方程"（如把 PDE-JEPA 的 Eq.13 注入仿真代码），但会话无 web_search/web_fetch 工具。2026-10-13 实测可行链路（PDE-JEPA arXiv:2609.34715 全方程提取成功）。

## 1. 检索（arXiv API，curl 可达）

```bash
# ✅ 无引号查询可用（带引号的 %22 查询本次返回空）
curl -s --max-time 40 \
  "https://export.arxiv.org/api/query?search_query=all:PDE-JEPA&max_results=10&sortBy=relevance" \
  -o "<WORK_DIR>/pdejepa.xml"
```

解析（Atom XML，`ns = {'a': 'http://www.w3.org/2005/Atom'}`）：`a:entry` → `a:id`（abs URL，取末尾 ID 如 2609.34715v1）/ `a:title` / `a:published`。
顺带拿相关论文：`search_query=all:<关键词>` 一次可能返回同族 3 篇（PDE-JEPA / PI-JEPA / JEPA-control），一并下载即构成"论文系列"。

## 2. 下载（HTML 优先 + PDF 备份）

```bash
curl -sL --max-time 90 "https://arxiv.org/html/<ID>" -o paper.html   # LaTeXML 版，含 MathML，公式可提取
curl -sL --max-time 120 "https://arxiv.org/pdf/<ID>"  -o paper.pdf
```

**首选 HTML**：LaTeXML 输出把公式放进 `alttext="..."` 属性（LaTeX 源码），正则抽取即可拿到 `\frac{}{}`、`\theta` 等原始记号；PDF 需额外解析器且公式常被打散。

## 3. 转文本（保留公式）

```python
import re, html
raw = open(src, encoding="utf-8", errors="ignore").read()
raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
raw = re.sub(r'alttext="([^"]*)"', r" [\1] ", raw)          # ★ 公式 LaTeX 进正文（关键一步）
raw = re.sub(r"</(p|div|li|h[1-6]|tr|section|figure|table)>", "\n", raw, flags=re.I)
raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
raw = re.sub(r"<[^>]+>", " ", raw)
raw = html.unescape(raw)
raw = re.sub(r"[ \t]+", " ", raw); raw = re.sub(r"\n\s*\n+", "\n", raw)
```

输出 100K 字符级纯文本，`grep -n "4 Method\|B\.3 Predictor"` 即可定位章节，`read_file` 精读方程段（本次取了 Eq.4–17 全部核心方程）。

## 坑

1. **MSYS `/tmp` 与 Windows Python 不互通**：`curl -o /tmp/x.xml` 后 `py -c "open('/tmp/x.xml')"` 会 FileNotFoundError。一律落到 `D:/...` 等 Windows 可见路径。
2. **arXiv API 带引号查询可能返回空**：`search_query=all:%22PDE-JEPA%22` 本次为空，去掉引号正常。
3. 本机 HF/GitHub 可达性不定，但 `arxiv.org` / `export.arxiv.org` 实测可达（先 `curl -sI` 探活再下载）。
4. 下载路径中含项目名的目录先 `mkdir -p`（如 `<WORK_DIR>/pde_jepa/`），论文与提取文本同目录存放便于复现。
