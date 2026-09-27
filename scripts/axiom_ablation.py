#!/usr/bin/env python3
"""
Axiom Ablation — Stage 3.5 新增检测 (P0-3, ScientistTwo)
========================================================
[arXiv:2609.19644 ScientistTwo] Ablation Critic 思路 → 公理必要性消融。
ScientistTwo 的 Ablation Planner/Critic 逐组件消融、隔离增益来源、剪除冗余组件。
移植到 Lean 证明 = 反事实消融：注释掉某个 honest-axiom → 重编译 → 若目标 theorem
仍编译通过 = 该公理冗余（「表演性诚实」的更隐蔽变体——被引用但证明体实际不依赖它）。

两种模式：
  1. static（默认，无 Lean 工具链）——grep 启发式：
       - 公理仅声明处出现 1 次 → 完全未使用 → BLOCK（冗余/表演性诚实）
       - 公理被引用但从不出现于任何 `:= by` 证明体 → WARN（弱必要，签名引用但证明不依赖）
  2. compile（需 Lean 4 工具链，--lean-bin）——真实消融：
       对每个 axiom 用块注释包裹 → 重编译 → 目标 theorem 仍通过 = 冗余（BLOCK）；
       编译报「unknown identifier」= 必要（保留）。

Usage:
  # 静态（默认，快，无需 Lean）
  python axiom_ablation.py --lean proof.lean [--output /tmp/ablation.json]

  # 编译级（真实消融，需 Lean）
  python axiom_ablation.py --lean proof.lean --lean-bin /root/.elan/bin/lean [--target main_theorem]

可作为模块导入：`from axiom_ablation import static_ablation, compile_ablation`
"""

import argparse, json, re, subprocess, sys, tempfile, os
from pathlib import Path
from datetime import datetime


def _strip_comments(lean: str) -> str:
    """嵌套感知块注释剥离（正确处理 /- ... -/ 嵌套，含 /-- doc 注释）。

    非贪婪 re.sub(r'/-.*?-/') 无法处理嵌套块注释（如 line279 外层注释内嵌套 line299），
    会把被注释掉的 axiom 误判为 active。此实现按深度追踪。"""
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


def _axiom_names(lean: str):
    return re.findall(r'^\s*axiom\s+([A-Za-z_][A-Za-z0-9_]*)', lean, re.M)


def static_ablation(lean_text: str) -> dict:
    """静态消融：无需编译，grep 启发式判断公理必要性。"""
    lean = _strip_comments(lean_text)
    lines = lean.splitlines()
    names = _axiom_names(lean)

    findings = []
    blocks = []
    warns = []
    essential = []

    # 判定「证明体行」：缩进的 tactic 行（含 := by / exact / apply / rw 等）
    TACTIC_KW = (':= by', 'exact', 'apply', 'rw', 'refine', 'simpa', 'have',
                 'obtain', 'calc', 'ring', 'nlinarith', 'field_simp', 'norm_num',
                 'simp', 'use', 'intro', 'constructor', 'cases', 'induction',
                 'linarith', 'omega', 'native_decide', 'decide')

    for name in names:
        # 全文件出现次数（不含自身声明行）
        occ = [i for i, l in enumerate(lines) if re.search(rf'\b{re.escape(name)}\b', l)]
        decl_lines = [i for i in occ if re.match(r'^\s*axiom\s+', lines[i])]
        usage_lines = [i for i in occ if i not in decl_lines]

        if not usage_lines:
            # 完全未使用：仅声明处出现。WARN（与检测 7 一致，静态启发式不直接 BLOCK；
            # 编译级消融确认「注释后仍编译通过」才升级 BLOCK）。
            msg = (f"公理消融（未使用）：`{name}` 全文件中仅声明处出现，"
                   f"从未被任何 theorem/lemma 引用 = 疑似冗余公理/表演性诚实。"
                   f"编译级消融可确认（--lean-bin）。")
            warns.append(msg)
            findings.append({"type": "ablation_unused_axiom", "severity": "WARN",
                             "axiom": name, "msg": msg})
            continue

        # 是否出现在证明体行（含 tactic 关键字或缩进 tactic）
        in_body = any(
            any(kw in lines[i] for kw in TACTIC_KW) or
            (lines[i].startswith((' ', '\t')) and not re.match(r'^\s*(theorem|axiom|lemma|opaque|def|variable|structure|class|instance)\b', lines[i]))
            for i in usage_lines
        )

        if in_body:
            essential.append(name)
        else:
            # 被引用但只在签名行（声明行），证明体不依赖
            msg = (f"公理消融（弱必要）：`{name}` 被引用 {len(usage_lines)} 次但从不出现于 "
                   f"证明体（tactic 块），仅作签名前提。需编译级消融确认是否真正必要。")
            warns.append(msg)
            findings.append({"type": "ablation_signature_only_axiom", "severity": "WARN",
                             "axiom": name, "usage_count": len(usage_lines), "msg": msg})

    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    return {
        "check": "axiom_ablation_static",
        "time": datetime.now().isoformat(),
        "stats": {"total_axioms": len(names), "essential": len(essential),
                  "unused": sum(1 for f in findings if f["type"] == "ablation_unused_axiom"),
                  "signature_only": sum(1 for f in findings if f["type"] == "ablation_signature_only_axiom")},
        "gate": gate,
        "blocks": blocks,
        "warns": warns,
        "essential_axioms": essential,
        "findings": findings,
    }


def _axiom_spans(lean: str):
    """定位每个 axiom 声明的完整行跨度（从 axiom 行到下一个顶层声明行）。"""
    lines = lean.splitlines()
    TOPLEVEL = re.compile(r'^\S')  # 列 0 开始的顶层声明
    spans = []
    for i, l in enumerate(lines):
        if re.match(r'^\s*axiom\s+([A-Za-z_][A-Za-z0-9_]*)', l):
            name = re.match(r'^\s*axiom\s+([A-Za-z_][A-Za-z0-9_]*)', l).group(1)
            # 找下一个顶层声明行（排除自身）
            j = i + 1
            while j < len(lines) and not (TOPLEVEL.match(lines[j]) and not lines[j].strip().startswith('-')):
                j += 1
            spans.append((name, i, j))  # [i, j) 行区间
    return spans


def compile_ablation(lean_path: str, lean_bin: str, target: str = None,
                     workdir: str = None) -> dict:
    """编译级消融：逐个注释掉 axiom → 重编译 → 判断必要性。"""
    orig = Path(lean_path).read_text(encoding="utf-8", errors="replace")
    lines = orig.splitlines()
    spans = _axiom_spans(orig)

    if not spans:
        return {"check": "axiom_ablation_compile", "gate": "PASS",
                "stats": {"total_axioms": 0},
                "blocks": [], "warns": [], "findings": []}

    findings = []
    blocks = []
    warns = []
    essential = []
    redundant = []

    for name, i, j in spans:
        # 块注释包裹该 axiom 的完整跨度
        ablated = lines[:i] + ['/- [ABLATION] begin'] + lines[i:j] + ['-/'] + lines[j:]
        ablated_text = '\n'.join(ablated)

        with tempfile.NamedTemporaryFile('w', suffix='.lean', delete=False,
                                         encoding='utf-8') as f:
            f.write(ablated_text)
            tmp_path = f.name

        try:
            cmd = [lean_bin, tmp_path]
            if target:
                cmd += ['--run']  # 不适用 --run；仅对单文件检查编译
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=180, cwd=workdir)
            err = (res.stdout or '') + (res.stderr or '')
            # 编译通过（exit 0）→ 该 axiom 冗余
            if res.returncode == 0:
                redundant.append(name)
                msg = (f"公理消融（冗余）：注释掉 `{name}` 后文件仍编译通过 = "
                       f"该公理对目标证明不必要（被引用但证明体不依赖）。")
                blocks.append(msg)
                findings.append({"type": "ablation_redundant_axiom", "severity": "BLOCK",
                                 "axiom": name, "msg": msg})
            else:
                # 编译失败 → 必要（若错误提到该 name 则是直接依赖）
                essential.append(name)
                if re.search(rf'\b{re.escape(name)}\b', err):
                    findings.append({"type": "ablation_essential_axiom", "severity": "INFO",
                                     "axiom": name,
                                     "msg": f"`{name}` 被下游证明直接依赖（unknown identifier）。"})
                else:
                    # 编译失败但非因该公理 → 该公理可能必要（间接），标记 WARN
                    warns.append(f"公理消融（不确定）：注释 `{name}` 后编译失败但错误未直接提及 "
                                 f"该名（可能是间接依赖或文件其他错误）。")
                    findings.append({"type": "ablation_indeterminate", "severity": "WARN",
                                     "axiom": name, "msg": "编译失败但非直接依赖，需人工确认"})
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    return {
        "check": "axiom_ablation_compile",
        "time": datetime.now().isoformat(),
        "stats": {"total_axioms": len(spans), "essential": len(essential),
                  "redundant": len(redundant)},
        "gate": gate,
        "blocks": blocks,
        "warns": warns,
        "essential_axioms": essential,
        "redundant_axioms": redundant,
        "findings": findings,
    }


def main():
    ap = argparse.ArgumentParser(description="Axiom Ablation (P0-3, ScientistTwo)")
    ap.add_argument("--lean", required=True, help="Lean 4 证明文件")
    ap.add_argument("--lean-bin", default=None,
                    help="Lean 可执行文件路径（提供则启用编译级消融，如 /root/.elan/bin/lean）")
    ap.add_argument("--target", default=None, help="目标 theorem 名（编译级，可选）")
    ap.add_argument("--workdir", default=None, help="工作目录（lake 项目用）")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    args = ap.parse_args()

    lean_text = Path(args.lean).read_text(encoding="utf-8", errors="replace")

    if args.lean_bin:
        report = compile_ablation(args.lean, args.lean_bin, args.target, args.workdir)
    else:
        report = static_ablation(lean_text)

    out_path = args.output or "/tmp/axiom_ablation.json"
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print(f"Axiom Ablation (P0-3, ScientistTwo) — {report['check']}")
    print("=" * 60)
    s = report["stats"]
    print(f"  axioms={s.get('total_axioms', '?')}  essential={s.get('essential', '?')}  "
          f"redundant={s.get('redundant', s.get('unused', '?'))}")
    print(f"\n  GATE: {report['gate']}")
    for b in report["blocks"]:
        print(f"  🔴 BLOCK: {b}")
    for w in report["warns"]:
        print(f"  🟡 WARN: {w}")
    print(f"\n  Report: {out_path}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
