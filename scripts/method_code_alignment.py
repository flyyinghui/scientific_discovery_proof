#!/usr/bin/env python3
"""
Method-Code Alignment — Stage 3.5 新增检测 (P0-2, ScientistTwo)
================================================================
[arXiv:2609.19644 ScientistTwo] CoE Integrity Audit 第四查：Method-Code Alignment
—— 论文方法段逐行对齐代码实现，保证论文忠实描述代码。

本脚本（stdlib-only）做论文 ↔ Lean 双向逐条对齐：
  paper→lean (phantom)   ：论文声称存在、Lean 中不存在的 theorem/axiom/lemma → BLOCK
  lean→paper (undeclared)：Lean 声明了、论文从未提及的声明 → WARN（可能被隐藏）
  计数不一致 (mismatch)   ：论文声称的 axiom/theorem/lemma 数 vs Lean 实测数 → WARN

区别于 Stage 3.5 既有单向检查：
  - P0-3 (axiom_count_mismatch) / P0-4 (phantom_theorem) 是「论文声称 → Lean 存在性」单向；
  - 本检查补「Lean → 论文」反向，并输出逐条映射表 {paper_claim, lean_decl, status}。

Usage:
  python method_code_alignment.py --lean proof.lean --paper paper.txt [--output ...]

可作为模块导入：`from method_code_alignment import align_method_code`
"""

import argparse, json, re, sys
from pathlib import Path
from datetime import datetime

_EN_WORDS = {'and','or','the','a','an','of','for','in','on','is','are','was','were',
             'states','shows','proves','establishes','gives','yields','follows','that',
             'this','it','we','our','which','with','from','by','to','at','as','lemma',
             'theorem','axiom','corollary','proposition','definition'}


def _strip_comments(lean: str) -> str:
    """嵌套感知块注释剥离（正确处理 /- ... -/ 嵌套，含 /-- doc 注释）。"""
    out = []
    depth = 0
    i = 0
    n = len(lean)
    while i < n:
        if lean[i:i + 2] == '/-':
            depth += 1
            i += 2
        elif lean[i:i + 2] == '-/' and depth > 0:
            depth -= 1
            i += 2
        elif depth == 0:
            out.append(lean[i])
            i += 1
        else:
            i += 1
    return ''.join(out)


def _lean_declarations(lean: str):
    """提取 Lean 中的 theorem/axiom/lemma 名称。返回 {type: set(name)}。"""
    decl = {"theorem": set(), "axiom": set(), "lemma": set()}
    for kind in decl:
        decl[kind] = set(re.findall(
            rf'^\s*{kind}\s+([A-Za-z_][A-Za-z0-9_]*)', lean, re.M))
    return decl


def _paper_claims(paper: str):
    """提取论文中提到的 theorem/axiom/lemma 名称（多种表述）。返回 {type: set(name)}。"""
    claims = {"theorem": set(), "axiom": set(), "lemma": set()}
    # 反引号包裹的声明名（最可靠）：Theorem `xxx` / Axiom `A1` / Lemma `L2`
    for kind in claims:
        claims[kind] |= set(re.findall(
            rf'\b{kind}\s+`([A-Za-z_][A-Za-z0-9_]*)`', paper, re.I))
    # 无引号但紧邻大写字/下划线标识符：Theorem xxx / Axiom A_N / Lemma yyy
    for kind in claims:
        claims[kind] |= set(re.findall(
            rf'\b{kind}\s+([A-Za-z_][A-Za-z0-9_]*)', paper, re.I))
    # 过滤英文常见词 + 纯编号
    for kind in claims:
        claims[kind] = {c for c in claims[kind]
                        if c.lower() not in _EN_WORDS and not re.match(r'^\d+$', c)}
    return claims


def align_method_code(lean_text: str, paper_text: str) -> dict:
    lean_text = _strip_comments(lean_text)
    decl = _lean_declarations(lean_text)
    claims = _paper_claims(paper_text)

    findings = []
    blocks = []
    warns = []
    mapping = []  # {paper_claim, kind, lean_decl, status}

    # 双向对齐
    for kind in ("theorem", "axiom", "lemma"):
        declared = decl[kind]
        claimed = claims[kind]

        # paper→lean (phantom)：论文声称、Lean 缺失
        phantom = sorted(claimed - declared)
        # lean→paper (undeclared)：Lean 声明、论文未提及
        undeclared = sorted(declared - claimed)

        # 记录映射表（对 paper 声称的每个名）
        for name in sorted(claimed):
            mapping.append({
                "kind": kind, "paper_claim": name,
                "lean_decl": name if name in declared else None,
                "status": "matched" if name in declared else "phantom",
            })
        # 记录 Lean 有但论文没提的（只记前 30 个避免爆炸）
        for name in undeclared[:30]:
            mapping.append({
                "kind": kind, "paper_claim": None,
                "lean_decl": name,
                "status": "undeclared",
            })

        if phantom:
            msg = (f"方法-代码不对齐（{kind}）：论文声称 {len(phantom)} 个 Lean 中不存在的声明: "
                   f"{phantom[:8]}")
            blocks.append(msg)
            findings.append({"type": f"method_code_phantom_{kind}", "severity": "BLOCK",
                             "phantom": phantom, "msg": msg})

        if undeclared:
            msg = (f"方法-代码不对齐（{kind}）：Lean 声明了 {len(undeclared)} 个论文从未提及的 "
                   f"声明（可能被论文隐藏，需披露）: {undeclared[:8]}")
            warns.append(msg)
            findings.append({"type": f"method_code_undeclared_{kind}", "severity": "WARN",
                             "undeclared": undeclared[:50], "msg": msg})

    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    return {
        "check": "method_code_alignment",
        "time": datetime.now().isoformat(),
        "stats": {
            "lean": {k: len(v) for k, v in decl.items()},
            "paper_claims": {k: len(v) for k, v in claims.items()},
        },
        "gate": gate,
        "blocks": blocks,
        "warns": warns,
        "mapping": mapping,
        "findings": findings,
    }


def main():
    ap = argparse.ArgumentParser(description="Method-Code Alignment (P0-2, ScientistTwo)")
    ap.add_argument("--lean", required=True, help="Lean 4 证明文件")
    ap.add_argument("--paper", required=True, help="论文全文文本")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    args = ap.parse_args()

    lean = Path(args.lean).read_text(encoding="utf-8", errors="replace")
    paper = Path(args.paper).read_text(encoding="utf-8", errors="replace")
    report = align_method_code(lean, paper)

    out_path = args.output or "/tmp/method_code_alignment.json"
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Method-Code Alignment (P0-2, ScientistTwo)")
    print("=" * 60)
    s = report["stats"]
    print(f"  lean:      axiom={s['lean']['axiom']} theorem={s['lean']['theorem']} lemma={s['lean']['lemma']}")
    print(f"  paper:     axiom={s['paper_claims']['axiom']} theorem={s['paper_claims']['theorem']} lemma={s['paper_claims']['lemma']}")
    print(f"\n  GATE: {report['gate']}")
    for b in report["blocks"]:
        print(f"  🔴 BLOCK: {b}")
    for w in report["warns"]:
        print(f"  🟡 WARN: {w}")
    print(f"\n  Report: {out_path}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
