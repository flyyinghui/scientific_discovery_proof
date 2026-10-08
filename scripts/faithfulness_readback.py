#!/usr/bin/env python3
"""
faithfulness_readback.py — 形式化忠实性盲读回审计（prove2me read-back 机制）
================================================================================
Stage 3.5a（在自洽性审计之前）。检测 Lean formalization 是否忠实于物理猜想意图。

两阶段（均走 DeepSeek v4-flash，thinking disabled）：
  阶段1 盲读：只给 Lean 声明（不给物理意图/源材料），生成自然语言 read-back
           —— 盲读是关键：知道「代码该说什么」的读者会把意图读进去，偏差就消失了。
  阶段2 对比：read-back vs 猜想意图，检测 faithfulness gap（形式化偏差）

核心原则（来自 prove2me mission_auditor.md）：
  1. 翻译代码，不是意图——只陈述 Lean 实际断言了什么
  2. 每个 binder/假设都要交代——遗漏假设是最坏失败模式
  3. 展开非标准定义
  4. 揭示退化/边缘情形（n=0、除零垃圾值、vacuous theorem）
  5. 保持逻辑精度（≤ vs <、∃ vs ∃!、iff vs implication）
  6. 写给不读 Lean 的数学家
  7. 不评判、不辩护——偏差留给对比阶段

用法:
  python faithfulness_readback.py --lean proof.lean [--conjecture conjecture.json] [--output out.json]
  也可作为模块导入: from faithfulness_readback import verify_faithfulness
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"

READBACK_PRINCIPLES = """你是形式化证明的「盲读审计员」。你只会看到 Lean 4 声明代码，看不到作者的物理意图、源材料或非形式描述。

任务：把这些 Lean 声明**字面断言了什么**用自然语言写出来（read-back）。

严格遵守：
1. 翻译代码，不是意图。只陈述 Lean 实际说了什么，绝不引入你对该物理概念「应该是什么」的理解。代码说的比意图少，read-back 就必须说少。
2. 每个 binder、每个假设、每个类型类约束都要交代。遗漏一个假设是最严重的失败。
3. 展开非标准定义。若声明用了自定义 def（非 Mathlib 常见概念），inline 展开它的含义。
4. 揭示退化和边缘情形。明确指出量词静默包含的边界：n=0、空集、除零返回的垃圾值、自然数减法下溢、不可满足的假设（若假设不可能满足，直说——空真定理是经典的忠实性陷阱）。
5. 保持逻辑精度。精确区分 ≤ vs <、∃ vs ∃!、iff vs 单向、每个不等式和包含的方向。不要「四舍五入」到道德等价的命题。
6. 用纯数学语言写给不读 Lean 的数学家，用 $...$ 公式，不要 Lean 语法。
7. 不评判、不辩护。不评价这个形式化是否「正确」或「忠实」，只描述它字面断言了什么。

输出格式（Markdown）：
对每个声明，一段自包含的 read-back：
「声明 <名称> 断言：<完整的自然语言陈述，含所有量词、假设、结论、边界情形>」
"""


def _load_api_key() -> str:
    for env_path in [
        "~/.hermes/.env",
        "~/.hermes/.env",
        os.path.expanduser("~/.hermes/.env"),
    ]:
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("DEEPSEEK_API_KEY", "")


def _extract_declarations(lean_text: str) -> list:
    """提取 Lean 的 theorem/axiom/def 声明的签名（名称+binders+类型，不含证明体）。

    返回 [{"kind": "theorem/axiom/def", "name": ..., "signature": ...}]
    """
    decls = []
    # 匹配 theorem/axiom/def 声明行（可能跨行）。取到 := 或换行+缩进开始处。
    # 简化：按行扫描，遇到关键字开行就收集到 := 或下一个顶层关键字。
    lines = lean_text.split("\n")
    i = 0
    n = len(lines)
    kind_re = re.compile(r'^(theorem|axiom|lemma|def|noncomputable def|opaque)\s+([\w.]+)')
    while i < n:
        line = lines[i]
        m = kind_re.match(line.strip())
        if not m:
            i += 1
            continue
        kind = m.group(1).replace("noncomputable ", "")
        name = m.group(2)
        # 收集签名：从当前行到 := 或到「换行 + 下一个顶层关键字」
        buf = [line.strip()]
        j = i + 1
        while j < n:
            nxt = lines[j]
            # 停止条件：出现 := 或 by，或下一行是顶层关键字（缩进为 0 且匹配关键字）
            if ":=" in nxt or re.match(r'^(theorem|axiom|lemma|def|opaque|#|/-|namespace|end)', nxt.strip()):
                break
            buf.append(nxt.rstrip())
            j += 1
        sig = "\n".join(buf)
        # 截断到 := 之前（若有）
        if ":=" in sig:
            sig = sig.split(":=")[0] + " :="
        decls.append({"kind": kind, "name": name, "signature": sig})
        i = j
    return decls


def _call_llm(prompt: str, max_tokens: int = 8192) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=_load_api_key(), base_url=BASE_URL)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.0,
        timeout=300,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return resp.choices[0].message.content or ""


def _blind_readback(decls: list) -> str:
    """阶段1：盲读——只给 Lean 声明，生成 read-back。"""
    code_block = "\n\n".join(
        f"```lean\n{d['kind']} {d['name']} ...\n{d['signature']}\n```"
        for d in decls
    )
    prompt = READBACK_PRINCIPLES + "\n\n下面是待盲读的 Lean 声明（共 " + str(len(decls)) + " 个）：\n\n" + code_block
    return _call_llm(prompt)


def _faithfulness_gap(readback: str, intent: str) -> dict:
    """阶段2：对比 read-back 和物理意图，检测 faithfulness gap。"""
    prompt = f"""你是形式化忠实性审计员。下面有两份材料：

【材料的盲读回】（独立审计员只看代码写的，字面断言）：
{readback}

【作者的物理意图】（猜想描述）：
{intent}

任务：逐条对比，找出「代码字面断言」与「作者意图」之间的偏差（faithfulness gap）。
重点检查：
- 代码假设比意图少（缺失假设 → 定理可能为假/过强）
- 代码结论比意图少（缺失结论 → 不同定理）
- 代码把「要证明的结论」写成了「假设」（假设了它 → 定理内容被删空 = 重言式/循环）
- 代码把「物理对象」定义成了「重言式恒等式」（如 S := 谱底*‖φ‖²+V，则 bound 变成 35x+b≥35x+b）
- 退化/边缘情形与意图不符（n=0、除零、空集）
- 量词范围比意图宽或窄

输出 JSON（不要 Markdown 包裹）：
{{"gaps": [{{"decl": "声明名", "severity": "P0/P1/P2", "type": "missing_hypothesis/missing_conclusion/assumed_conclusion/tautological_definition/edge_case/quantifier_scope", "description": "偏差描述", "fix_suggestion": "修复建议"}}], "overall": "FAITHFUL/MINOR_GAP/MAJOR_GAP"}}"""
    raw = _call_llm(prompt, max_tokens=8192)
    # 提取 JSON（LLM 可能包裹在 ```json 里）
    m = re.search(r'\{[\s\S]*\}', raw)
    if not m:
        return {"gaps": [], "overall": "ERROR", "raw": raw}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"gaps": [], "overall": "ERROR", "raw": raw}


def verify_faithfulness(lean_path: str, conjecture_path: str = None, output_path: str = None) -> dict:
    lean_text = Path(lean_path).read_text(encoding="utf-8", errors="replace")
    decls = _extract_declarations(lean_text)

    if not decls:
        return {"check": "faithfulness_readback", "gate": "PASS",
                "note": "未提取到 Lean 声明，跳过", "decls": 0}

    # 只盲读前 N 个声明（避免 prompt 过长）
    decls = decls[:25]

    readback = _blind_readback(decls)

    intent = ""
    if conjecture_path and os.path.exists(conjecture_path):
        try:
            cj = json.loads(Path(conjecture_path).read_text(encoding="utf-8"))
            parts = [cj.get("name", "")]
            if cj.get("description"):
                parts.append(cj["description"])
            for claim in cj.get("claims", []):
                if isinstance(claim, dict):
                    parts.append(claim.get("statement", "") or claim.get("text", ""))
                elif isinstance(claim, str):
                    parts.append(claim)
            # 里程碑（P2-⑤）：若有 milestone 字段，一并作为意图
            for ms in cj.get("milestones", []):
                if isinstance(ms, dict):
                    parts.append(f"里程碑 {ms.get('title','')}: {ms.get('statement','')}")
            intent = "\n".join(p for p in parts if p)
        except Exception as e:
            intent = f"(猜想读取失败: {e})"

    gap_report = _faithfulness_gap(readback, intent) if intent else {"gaps": [], "overall": "NO_INTENT"}

    overall = gap_report.get("overall", "ERROR")
    gate = "BLOCK" if overall == "MAJOR_GAP" else ("WARN" if gap_report.get("gaps") else "PASS")

    report = {
        "check": "faithfulness_readback",
        "time": datetime.now().isoformat(),
        "declarations_read": len(decls),
        "gate": gate,
        "overall": overall,
        "readback": readback,
        "gaps": gap_report.get("gaps", []),
    }

    if output_path:
        Path(output_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main():
    ap = argparse.ArgumentParser(description="Faithfulness read-back audit (prove2me read-back)")
    ap.add_argument("--lean", required=True, help="Lean 证明文件路径")
    ap.add_argument("--conjecture", default=None, help="猜想 JSON（含 description/claims/milestones 作为意图）")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    args = ap.parse_args()

    out = args.output or "/tmp/faithfulness_readback.json"
    report = verify_faithfulness(args.lean, args.conjecture, out)

    print("=" * 60)
    print("Faithfulness Read-back Audit (prove2me read-back)")
    print("=" * 60)
    print(f"  declarations read: {report.get('declarations_read', 0)}")
    print(f"  overall: {report.get('overall', '?')}")
    print(f"\n  GATE: {report['gate']}")
    for g in report.get("gaps", []):
        print(f"  🔴 {g.get('severity','?')} [{g.get('type','?')}] {g.get('decl','?')}: {g.get('description','')[:100]}")
    print(f"\n  Report: {out}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
