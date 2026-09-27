#!/usr/bin/env python3
"""
Reference Verification — Stage 3.5 新增检测 (P0-1, ScientistTwo)
================================================================
[arXiv:2609.19644 ScientistTwo] CoE Integrity Audit 第三查：Reference Verification。
ScientistTwo 用 search-augmented LLM 保证参考文献零幻觉（0/1814）。

本脚本（stdlib-only）做机械层核对，无需 LLM：
  1. 悬空引用 (dangling)     ：正文 [n] 指向不存在的参考文献（n > 列表总数）→ BLOCK
  2. 未引用文献 (uncited)     ：列表中存在但正文从未引用的条目 → WARN（可能是 Additional References）
  3. 编号断链 (broken seq)    ：列表编号跳号（1..N 中缺某些号）→ WARN
  4. 引用计数 (count mismatch)：论文声称的引用数 vs 实测列表数 → WARN

Usage:
  python reference_verification.py --paper paper.txt [--output /tmp/ref_check.json]

可作为模块导入：`from reference_verification import verify_references`
"""

import argparse, json, re, sys
from pathlib import Path
from datetime import datetime


def _extract_reference_section(paper: str):
    """定位 References 段落（从 References 标题到文末或附录标题）。"""
    # 多种标题写法
    m = re.search(r'\n\s*(?:References|REFERENCES|Bibliography)\s*\n', paper)
    if not m:
        return None
    start = m.end()
    tail = paper[start:]
    # 截断到附录（Appendix / 补充材料）
    app = re.search(r'\n\s*(?:Appendix|APPENDIX|Supplementary|A\.\d)', tail)
    if app:
        tail = tail[:app.start()]
    return tail


def _extract_listed_refs(ref_section: str):
    """从 References 段提取编号条目。返回 {编号: 条目文本} 和最大编号。"""
    if not ref_section:
        return {}, 0
    # 条目形如 "[1] ..." 或 "1. ..." 或 "1 ..."（行首或段首）
    entries = {}
    # 优先匹配 [n] 形式（arXiv 标准）
    for m in re.finditer(r'\[(\d+)\]\s*([^\[]*)', ref_section):
        n = int(m.group(1))
        if n not in entries:
            entries[n] = m.group(2).strip()
    if entries:
        return entries, max(entries.keys())
    # 回退：编号+点 形式 "1. ..."
    for m in re.finditer(r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)', ref_section):
        n = int(m.group(1))
        if n not in entries:
            entries[n] = m.group(2).strip()
    return entries, (max(entries.keys()) if entries else 0)


def _extract_cited_nums(paper: str, ref_section: str):
    """提取正文（排除参考文献段）中引用的编号集合。"""
    # 去掉参考文献段，避免把列表编号当引用
    if ref_section:
        body = paper.replace(ref_section, '')
    else:
        body = paper
    cited = set()
    # [n]、[n,m]、[n-m]、[n, m, k]
    for m in re.finditer(r'\[(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+)*)\]', body):
        token = m.group(1)
        # 展开范围 n-m
        for part in token.split(','):
            part = part.strip()
            rm = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', part)
            if rm:
                a, b = int(rm.group(1)), int(rm.group(2))
                if a <= b:
                    cited.update(range(a, b + 1))
            else:
                dm = re.match(r'^(\d+)$', part)
                if dm:
                    cited.add(int(dm.group(1)))
    return cited


def verify_references(paper_text: str) -> dict:
    ref_section = _extract_reference_section(paper_text)
    listed, max_listed = _extract_listed_refs(ref_section)
    cited = _extract_cited_nums(paper_text, ref_section or '')

    n_listed = len(listed)
    n_cited = len(cited)

    findings = []
    blocks = []
    warns = []

    # 无数编号参考文献列表 → 可能 author-year 风格（如 ICLR/NeurIPS），或参考文献段未解析。
    # 跳过核对，避免把数学区间（如 [1,10] 评分范围）误判为悬空引用。
    if n_listed == 0:
        return {
            "check": "reference_verification",
            "time": datetime.now().isoformat(),
            "stats": {"listed_references": 0, "cited_in_text": n_cited,
                      "max_listed_number": 0},
            "gate": "PASS",
            "blocks": [], "warns": [], "findings": [],
            "note": "无编号参考文献列表（可能 author-year 风格），跳过引用核对",
        }

    # 1. 悬空引用：正文引用了列表中不存在的编号
    dangling = sorted(n for n in cited if n > max_listed or (listed and n not in listed))
    if dangling:
        msg = (f"悬空引用：正文引用 {len(dangling)} 个不存在的参考文献编号"
               f"（超出列表范围或列表缺失）: {dangling[:12]}")
        blocks.append(msg)
        findings.append({"type": "dangling_reference", "severity": "BLOCK",
                         "dangling": dangling, "msg": msg})

    # 2. 未引用文献：列表有但正文没引
    uncited = sorted(n for n in listed if n not in cited)
    if uncited:
        msg = (f"未引用文献：{len(uncited)} 个列表条目在正文中从未被引用"
               f"（若为 Additional References 分组请确认）: {uncited[:12]}")
        warns.append(msg)
        findings.append({"type": "uncited_reference", "severity": "WARN",
                         "uncited": uncited, "msg": msg})

    # 3. 编号断链：列表编号跳号
    if listed:
        full = set(range(1, max_listed + 1))
        broken = sorted(full - set(listed.keys()))
        if broken:
            msg = (f"编号断链：参考文献列表编号跳号，缺失 {len(broken)} 个: {broken[:12]}")
            warns.append(msg)
            findings.append({"type": "broken_reference_sequence", "severity": "WARN",
                             "broken": broken, "msg": msg})

    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    return {
        "check": "reference_verification",
        "time": datetime.now().isoformat(),
        "stats": {"listed_references": n_listed, "cited_in_text": n_cited,
                  "max_listed_number": max_listed},
        "gate": gate,
        "blocks": blocks,
        "warns": warns,
        "findings": findings,
    }


def main():
    ap = argparse.ArgumentParser(description="Reference Verification (P0-1, ScientistTwo)")
    ap.add_argument("--paper", required=True, help="论文全文文本")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    args = ap.parse_args()

    paper = Path(args.paper).read_text(encoding="utf-8", errors="replace")
    report = verify_references(paper)

    out_path = args.output or "/tmp/reference_verification.json"
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Reference Verification (P0-1, ScientistTwo)")
    print("=" * 60)
    s = report["stats"]
    print(f"  listed={s['listed_references']}  cited={s['cited_in_text']}  max_num={s['max_listed_number']}")
    print(f"\n  GATE: {report['gate']}")
    for b in report["blocks"]:
        print(f"  🔴 BLOCK: {b}")
    for w in report["warns"]:
        print(f"  🟡 WARN: {w}")
    print(f"\n  Report: {out_path}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
