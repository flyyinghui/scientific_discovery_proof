#!/usr/bin/env python3
"""
semantic_reference_check.py — 幻影引用语义检测（EmbeddingGemma-2 集成）
========================================================================
在 reference_verification.py 的机械核对（编号层：悬空/未引用/断链）之上，
加一层**语义匹配**：用 EmbeddingGemma-2 计算「正文引用 [n] 处的上下文」vs
「参考文献 [n] 条目文本」的余弦相似度。低相似度 → 疑似幻影引用
（引用了编号，但内容与文献主题无关 —— 对应 brain.recall 幻觉引用的同类问题）。

依赖（可选）:
  - litert-lm-api + embeddinggemma.py（EmbeddingGemma-2 模型）
  - 若 embeddinggemma 不可用，自动降级为 PASS + note（不阻塞管线）

Usage:
  python semantic_reference_check.py --paper paper.txt [--threshold 0.4] [--output /tmp/sem_ref.json]
  # 也可作为模块导入: from semantic_reference_check import verify_semantic_references
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from datetime import datetime

# EmbeddingGemma-2 封装位置（可被环境变量覆盖）
_EMBEDDING_MODULE_DIR = "~/models/embeddinggemma-2-740m"

# 语义相似度阈值：低于此值判为「疑似幻影引用」
_DEFAULT_THRESHOLD = 0.40
# 正文引用处的上下文窗口（前后字符数）
_CONTEXT_CHARS = 120


def _import_embeddinggemma():
    """尝试导入 embeddinggemma 封装。失败返回 None（优雅降级）。"""
    try:
        if _EMBEDDING_MODULE_DIR not in sys.path:
            sys.path.insert(0, _EMBEDDING_MODULE_DIR)
        import embeddinggemma  # noqa: F401
        return embeddinggemma
    except Exception:
        return None


def _extract_reference_section(paper: str):
    m = re.search(r'\n\s*#{0,6}\s*(?:References|REFERENCES|Bibliography)\s*\n', paper)
    if not m:
        return None
    start = m.end()
    tail = paper[start:]
    app = re.search(r'\n\s*(?:Appendix|APPENDIX|Supplementary|A\.\d)', tail)
    if app:
        tail = tail[:app.start()]
    return tail


def _extract_listed_refs(ref_section: str):
    if not ref_section:
        return {}, 0
    entries = {}
    for m in re.finditer(r'\[(\d+)\]\s*([^\[]*)', ref_section):
        n = int(m.group(1))
        if n not in entries:
            entries[n] = m.group(2).strip()
    if entries:
        return entries, max(entries.keys())
    for m in re.finditer(r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)', ref_section):
        n = int(m.group(1))
        if n not in entries:
            entries[n] = m.group(2).strip()
    return entries, (max(entries.keys()) if entries else 0)


def _extract_cited_nums(paper: str, ref_section: str):
    body = paper.replace(ref_section, '') if ref_section else paper
    cited = set()
    for m in re.finditer(r'\[(\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+)*)\]', body):
        token = m.group(1)
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


def _citation_contexts(paper: str, ref_section: str, cited_nums):
    """提取每个被引用编号在正文中的引用上下文（前后 _CONTEXT_CHARS 字符）。

    返回 {编号: [上下文文本列表]}（同一编号可能被引用多次）。
    """
    body = paper.replace(ref_section, '') if ref_section else paper
    contexts = {}
    for n in sorted(cited_nums):
        contexts[n] = []
        for m in re.finditer(r'\[%d\]' % n, body):
            s = max(0, m.start() - _CONTEXT_CHARS)
            e = min(len(body), m.end() + _CONTEXT_CHARS)
            ctx = body[s:e].replace('\n', ' ').strip()
            contexts[n].append(ctx)
    return contexts


def verify_semantic_references(paper_text: str, threshold: float = _DEFAULT_THRESHOLD) -> dict:
    eg = _import_embeddinggemma()
    if eg is None:
        return {
            "check": "semantic_reference_check",
            "time": datetime.now().isoformat(),
            "gate": "PASS",
            "blocks": [], "warns": [], "findings": [],
            "note": "EmbeddingGemma-2 不可用（未安装 litert-lm-api 或模型缺失），跳过语义层",
        }

    ref_section = _extract_reference_section(paper_text)
    listed, max_listed = _extract_listed_refs(ref_section)
    cited = _extract_cited_nums(paper_text, ref_section or '')

    if not listed or not cited:
        return {
            "check": "semantic_reference_check",
            "time": datetime.now().isoformat(),
            "gate": "PASS",
            "blocks": [], "warns": [], "findings": [],
            "note": "无数编号文献或正文无引用，跳过语义核对",
        }

    contexts = _citation_contexts(paper_text, ref_section or '', cited)
    findings = []
    warns = []
    checked = 0
    low = []
    all_scores = []  # (ref_num, best_score, ref_text)

    for n in sorted(cited):
        if n not in listed:
            continue  # 悬空引用交给 reference_verification.py 处理
        ref_text = listed[n]
        ctx_list = contexts.get(n, [])
        if not ctx_list:
            continue
        scores = []
        for ctx in ctx_list:
            try:
                q = eg.embed(ctx)
                r = eg.embed(ref_text)
                scores.append(eg.cosine(q, r))
            except Exception as e:
                warns.append(f"引用[{n}] embedding 失败: {e}")
                break
        checked += 1
        best = max(scores) if scores else 0.0
        all_scores.append((n, round(best, 4), ref_text[:80]))

    # 相对离群检测：Tukey 下界（Q1 - 1.5×IQR），比绝对阈值更鲁棒——
    # 学术文本的「背景相似度」天然落在 0.6-0.7，幻影引用应显著低于该分布下界。
    if all_scores:
        vals = sorted(s for _, s, _ in all_scores)
        q1 = vals[len(vals) // 4]
        q3 = vals[(3 * len(vals)) // 4]
        iqr = q3 - q1
        tukey_low = q1 - 1.5 * iqr
        # 绝对阈值兜底：明显低于语义无关下限
        floor = min(threshold, tukey_low) if tukey_low > 0 else threshold
        low = [(n, s, t) for n, s, t in all_scores if s < floor]

    if low:
        msg = f"疑似幻影引用：{len(low)} 个引用语义相似度显著低于分布（< {floor:.3f}）"
        warns.append(msg)
        findings.append({
            "type": "phantom_reference_semantic",
            "severity": "WARN",
            "threshold": round(floor, 4),
            "tukey_low": round(tukey_low, 4) if all_scores else None,
            "low_similarity": [{"ref": n, "score": s, "ref_text": t} for n, s, t in low],
            "all_scores": [{"ref": n, "score": s} for n, s, _ in all_scores],
            "msg": msg,
        })

    gate = "WARN" if warns else "PASS"
    return {
        "check": "semantic_reference_check",
        "time": datetime.now().isoformat(),
        "stats": {"checked_references": checked, "low_similarity_count": len(low)},
        "gate": gate,
        "blocks": [],
        "warns": warns,
        "findings": findings,
        "all_scores": [{"ref": n, "score": s, "ref_text": t} for n, s, t in all_scores],
    }


def main():
    ap = argparse.ArgumentParser(description="Semantic phantom-reference check (EmbeddingGemma-2)")
    ap.add_argument("--paper", required=True, help="论文全文文本")
    ap.add_argument("--threshold", type=float, default=_DEFAULT_THRESHOLD, help="语义相似度阈值")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    args = ap.parse_args()

    paper = Path(args.paper).read_text(encoding="utf-8", errors="replace")
    report = verify_semantic_references(paper, args.threshold)

    out_path = args.output or "/tmp/semantic_reference_check.json"
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Semantic Reference Check (EmbeddingGemma-2)")
    print("=" * 60)
    print(f"  threshold={args.threshold}")
    if "note" in report and report["note"]:
        print(f"  note: {report['note']}")
    else:
        s = report.get("stats", {})
        print(f"  checked={s.get('checked_references', 0)}  low_similarity={s.get('low_similarity_count', 0)}")
    print(f"\n  GATE: {report['gate']}")
    for w in report["warns"]:
        print(f"  🟡 WARN: {w}")
    for f in report["findings"]:
        if f.get("low_similarity"):
            for item in f["low_similarity"][:10]:
                print(f"    ref[{item['ref']}] score={item['score']}  {item['ref_text']}")
    print(f"\n  Report: {out_path}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
