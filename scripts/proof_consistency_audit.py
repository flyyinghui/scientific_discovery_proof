#!/usr/bin/env python3
"""
Formal Proof Consistency Audit — Stage 3.5 审计门
=================================================
在 PPE 形式化证明完成后、AI-Scientist 论文生成前，对 Lean 4 证明做
自洽性 + 诚实性 + 数学正确性三重审计。

固化自 CGICE V9.1 / 三峰 V16 / V17 三轮终审 (2026-08-16) 暴露的六类 P0：
  1. 公理自洽性（爆炸原理检测）
  2. 表演性诚实（注释标签 vs 真实 attribute）
  3. 公理计数不一致
  4. 定理存在性（声称 vs 实际）
  5. := by trivial 空壳（假证明）
  6. 离散谱 vs 连续谱（数学类别错误）

Usage:
  python proof_consistency_audit.py --lean proof.lean [--paper paper.txt]
      [--expected-axioms 14] [--expected-theorems 3]
"""

import argparse, json, re, sys, os
from pathlib import Path
from datetime import datetime

# ── ScientistTwo P0 三检测（同目录 sibling 模块，可选导入） ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    from reference_verification import verify_references as _verify_refs
    from method_code_alignment import align_method_code as _align_mc
    from axiom_ablation import static_ablation as _static_ablation
    _HAS_SCIENTISTTWO = True
except ImportError:
    _HAS_SCIENTISTTWO = False


def is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("--") or s.startswith("/-") or s.startswith("-/")


def strip_block_comments(lean: str) -> str:
    """嵌套感知块注释剥离（正确处理 /- ... -/ 嵌套，含 /-- doc 注释）。

    非贪婪 re.sub(r'/-.*?-/') 无法处理嵌套块注释（如外层注释内嵌套子注释），
    会把被注释掉的 axiom 误判为 active。"""
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


# ======================================================================
# 缺陷定位（P0-3, Colosseum）：把每个缺陷绑定到具体 section/claim
# ======================================================================

_SECTION_PAT = re.compile(
    r'§\s*\d+(?:\.\d+)*'                       # §2.1 / §3
    r'|\bSection\s+\d+'                        # Section 3
    r'|\bSTEP\s+\d+'                           # STEP 6
    r'|\bLemma\s+[A-Za-z_][A-Za-z0-9_]*'       # Lemma L2
    r'|\bTheorem\s+[A-Za-z_][A-Za-z0-9_]*'     # Theorem T1
    r'|\[honest-axiom\s+[A-Za-z0-9_]+\]'       # [honest-axiom A1]
    r'|\bA\d+\b'                               # A1..A28
    r'|\bV\d+\b'                               # V7 NEW
)


def _extract_sections(lines):
    """提取 section 标签（供缺陷定位）。返回 [(line_no, label), ...] 按行号升序。"""
    sections = []
    for i, l in enumerate(lines, 1):
        s = l.strip()
        # 1. Lean section 块
        m = re.match(r'^section\s+(.+)$', s)
        if m:
            sections.append((i, f"section {m.group(1).strip()}"))
            continue
        # 2. 注释头（block/doc/line）含定位关键词
        if s.startswith('/-') or s.startswith('/--') or s.startswith('--'):
            hm = _SECTION_PAT.search(s)
            if hm:
                sections.append((i, hm.group(0).strip()))
    return sections


def _line_to_section(line_no, sections):
    cur = None
    for ln, label in sections:
        if ln <= line_no:
            cur = label
        else:
            break
    return cur


def _localize_findings(findings, raw_lean):
    """为每个 finding 附加 defect_location（section + line），使审阅可操作。

    P0-3 (Colosseum)：全局验证把缺陷绑定到具体 section/claim，而非仅报类型。"""
    lines = raw_lean.splitlines()
    sections = _extract_sections(lines)
    # 可定位字段（按优先级）
    NAME_FIELDS = ("axiom", "theorem", "lhs", "unchallenged", "downgraded",
                   "missing", "dangling", "undeclared", "phantom", "broken",
                   "redundant_axioms", "essential_axioms")
    for f in findings:
        loc = {"section": None, "line": None}
        key = None
        for field in NAME_FIELDS:
            v = f.get(field)
            if isinstance(v, list) and v:
                key = v[0]
                break
            if isinstance(v, str) and v and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', v):
                key = v
                break
        if key:
            for i, l in enumerate(lines, 1):
                if re.search(rf'\b{re.escape(str(key))}\b', l):
                    loc["line"] = i
                    loc["section"] = _line_to_section(i, sections)
                    break
        f["defect_location"] = loc
    return findings


def audit(lean_path: str, paper_path: str = None,
          expected_axioms: int = None, expected_theorems: int = None) -> dict:
    raw_lean = Path(lean_path).read_text(encoding="utf-8", errors="replace")
    # 去除块注释（/- ... -/，含多行 docstring + 嵌套），避免 docstring 中间行被误判为 active 代码
    lean = strip_block_comments(raw_lean)
    lines = lean.splitlines()

    # ── 提取 active 声明（排除注释行） ────────────────────────
    active = [l for l in lines if not is_comment(l)]

    def count_active(pat):
        return sum(1 for l in active if re.search(pat, l))

    axioms = [l.strip() for l in active if re.match(r'^\s*axiom\s', l)]
    theorems = [l.strip() for l in active if re.match(r'^\s*theorem\s', l)]
    lemmas = [l.strip() for l in active if re.match(r'^\s*lemma\s', l)]

    n_axiom = len(axioms)
    n_theorem = len(theorems)
    n_lemma = len(lemmas)
    n_sorry = count_active(r'\bsorry\b')
    n_admit = count_active(r'\badmit\b')
    n_trivial = count_active(r':=\s*by\s+trivial\b')
    n_true_stub = count_active(r':=\s*True\b')

    findings = []
    blocks = []   # 阻断级
    warns = []    # 警告级

    # ── 检测 0: active sorry（未完成证明，最高优先级 BLOCK） ──
    # [GitHub review] n_sorry 此前只进 stats 从未触发 gate —— 一个含 sorry 的
    # 未完成证明会以 gate=PASS 通过审计门。必须在门控前强制 BLOCK。
    if n_sorry > 0:
        msg = f"{n_sorry} 处 active 'sorry'（未完成证明）。gate 必须为 BLOCK。"
        blocks.append(msg)
        findings.append({"type": "active_sorry", "severity": "BLOCK",
                         "count": n_sorry, "msg": msg})

    # ── 检测 2: 表演性诚实 ──────────────────────────────────
    real_attr = sum(1 for l in active if l.strip().startswith('@['))
    # 两种注释标签格式（严格区分）：
    # (a) '-- @[honest_axiom]'：伪装成 Lean attribute 的注释 —— 表演性诚实候选
    # (b) '-- [honest-axiom]'：诚实的概念标签注释 —— 诚实披露，非表演性诚实
    comment_attr_pseudo = sum(1 for l in lines if '-- @[' in l or '--@[' in l)
    comment_attr_honest = sum(1 for l in lines if '-- [honest-axiom]' in l or '--[honest-axiom]' in l)
    if comment_attr_pseudo > 0 and real_attr == 0:
        msg = (f"表演性诚实：{comment_attr_pseudo} 处 '-- @[...]' 注释伪装成 attribute，"
               f"但 0 处真实 Lean attribute。论文不得声称 'declared as @[honest_axiom]'。")
        warns.append(msg)
        findings.append({"type": "performative_honesty", "severity": "WARN",
                         "comment_attrs": comment_attr_pseudo, "real_attrs": real_attr, "msg": msg})
    elif comment_attr_honest > 0 and real_attr == 0:
        # 诚实标签：'-- [honest-axiom]' 是概念标签注释，非 attribute 伪装。
        # 这是诚实披露（若论文明确声明"honest-axiom 是注释标签非 attribute"），不 WARN。
        findings.append({"type": "honest_axiom_comment_labels", "severity": "INFO",
                         "comment_labels": comment_attr_honest, "real_attrs": real_attr,
                         "msg": f"{comment_attr_honest} 处 '-- [honest-axiom]' 概念标签注释"
                                f"（诚实披露，非 attribute 伪装；确认论文未声称 @[honest_axiom]）"})

    # ── 检测 5: := by trivial 空壳 ───────────────────────────
    if n_trivial > 0:
        msg = f"{n_trivial} 处 ':=' by trivial' 空壳证明（编译通过但零数学内容）。"
        warns.append(msg)
        findings.append({"type": "trivial_stub", "severity": "WARN",
                         "count": n_trivial, "msg": msg})
    if n_true_stub > 0:
        msg = f"{n_true_stub} 处 ':=' True' 空壳命题（隐藏 sorry）。"
        warns.append(msg)
        findings.append({"type": "true_stub", "severity": "WARN",
                         "count": n_true_stub, "msg": msg})

    # ── 检测 5b: active admit（等同 sorry，未完成证明） ────────
    # admit 与 sorry 语义相同（接受未证命题），但论文常声称 "0 sorry"
    # 而隐瞒 admit。需单独标记。
    if n_admit > 0:
        msg = (f"{n_admit} 处 active 'admit'（等同 sorry，未完成证明）。"
               f"若论文声称 '0 sorry'，必须同时披露 admit 数量。")
        warns.append(msg)
        findings.append({"type": "active_admit", "severity": "WARN",
                         "count": n_admit, "msg": msg})

    # ── 检测 3: 公理计数不一致 ──────────────────────────────
    if expected_axioms is not None and expected_axioms != n_axiom:
        msg = (f"公理计数不一致：论文声称 {expected_axioms}，Lean 实测 {n_axiom}。"
               f"必须统一为实测数。")
        warns.append(msg)
        findings.append({"type": "axiom_count_mismatch", "severity": "WARN",
                         "claimed": expected_axioms, "actual": n_axiom, "msg": msg})
    if expected_theorems is not None and expected_theorems != n_theorem:
        msg = (f"定理计数不一致：论文声称 {expected_theorems}，Lean 实测 {n_theorem}。")
        warns.append(msg)
        findings.append({"type": "theorem_count_mismatch", "severity": "WARN",
                         "claimed": expected_theorems, "actual": n_theorem, "msg": msg})

    # ── 检测 4: 定理存在性（论文声称 vs Lean 实际） ──────────
    if paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
        # 提取论文中 "theorem X" 或 "theorem x_..." 声称
        claimed = set(re.findall(r'\btheorem\s+`([A-Za-z_][A-Za-z0-9_]*)`', paper))
        declared = set(re.findall(r'^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)', lean, re.M))
        missing = claimed - declared
        # 过滤：编号（"theorem 2"）、英文常见词（"theorem X states/and/..."）
        _EN_WORDS = {'and','or','the','a','an','of','for','in','on','is','are','was','were',
                     'states','shows','proves','establishes','gives','yields','follows','that',
                     'this','it','we','our','which','with','from','by','to','at','as'}
        missing = {m for m in missing if not re.match(r'^\d+$', m) and m.lower() not in _EN_WORDS}
        if missing:
            msg = (f"定理虚假声称：论文提到 {len(missing)} 个 Lean 中不存在的定理: "
                   f"{sorted(missing)[:8]}")
            blocks.append(msg)
            findings.append({"type": "phantom_theorem", "severity": "BLOCK",
                             "missing": sorted(missing), "msg": msg})

    # ── 检测 1: 公理自洽性（等式链矛盾检测） ────────────────
    # 提取 "F t = expr" 或 "F t ≠ expr" 形式的等式（F 是函数名，可带参数）
    # lhs 匹配函数应用形式（如 I_cycle t，而非单个 t）
    eq_map = {}   # 左端标识 -> set of 右端表达式
    neq_pairs = []
    for ax in axioms:
        m = re.match(r'axiom\s+\w+\s*(?:\([^)]*\))?\s*:\s*(.*)', ax)
        if not m:
            continue
        body = m.group(1)
        # 找 "F args = Y"（F 后跟参数，捕获完整函数应用）
        for eqm in re.finditer(r'([A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)*)\s*=\s*([^,;\n]+)', body):
            lhs = eqm.group(1).strip()
            rhs = eqm.group(2).strip()
            # 跳过单字母 lhs、下划线开头 lhs（如 _CC t 是 Λ_CC t 的截断误匹配）、含算符的 lhs
            if len(lhs) <= 1 or ' ' not in lhs or lhs.startswith('_'):
                continue
            if lhs not in eq_map:
                eq_map[lhs] = set()
            eq_map[lhs].add(rhs)
        for neqm in re.finditer(r'([A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)*)\s*≠\s*([^,;\n]+)', body):
            lhs = neqm.group(1).strip()
            rhs = neqm.group(2).strip()
            if len(lhs) <= 1 or ' ' not in lhs or lhs.startswith('_'):
                continue
            neq_pairs.append((lhs, rhs))

    # 检测同名函数应用的 "= 和 ≠" 冲突（简化启发式）
    for lhs, rhs in neq_pairs:
        if lhs in eq_map and eq_map[lhs]:
            msg = (f"公理自洽性警告：`{lhs}` 同时被声明为等于 {sorted(eq_map[lhs])[:3]} "
                   f"和不等于 `{rhs}`。需人工验证是否矛盾（可能触发爆炸原理）。")
            warns.append(msg)
            findings.append({"type": "axiom_consistency_suspect", "severity": "WARN",
                             "lhs": lhs, "eq": sorted(eq_map[lhs])[:3],
                             "neq": rhs, "msg": msg})

    # ── 检测 6: 离散谱 vs 连续谱 ────────────────────────────
    # 检测 "spectrum ... = k * lambda" 或 "lambda_k = k * lambda" 等差谱声称
    spectrum_claim = re.search(
        r'(spectrum|spectral)[^.\n]{0,120}(k\s*[:*]?\s*\w+|\w+\s*=\s*k\s*\*\s*\w+)',
        lean, re.I)
    noncompact_hint = re.search(r'non[- ]?compact|SL\([^)]*\)/SU\(', lean, re.I)
    # 澄清：文件已区分「连续自由谱 (Harish-Chandra)」vs「离散束缚态 (Witten 势阱)」
    spectrum_clarified = re.search(r'absolutely\s+continuous|bound\s+states?|Harish[- ]?Chandra', lean, re.I)
    if spectrum_claim and noncompact_hint and not spectrum_clarified:
        msg = ("离散谱 vs 连续谱：文件同时声称离散谱（等差 λ_k=k·λ）"
               "和非紧对称空间。非紧空间谱是连续的（Plancherel 测度），"
               "离散谱声称是数学类别错误。")
        warns.append(msg)
        findings.append({"type": "discrete_spectrum_on_noncompact", "severity": "WARN",
                         "msg": msg})

    # ── 检测 7-9: RSIAgent 失败模式映射 (v2.8.0) ─────────────
    # [RSIAgent arXiv:2609.15364] 递归自我改进的 3 类失败模式 → 3 条新检测规则：
    #   7. 未挑战假设 (unchallenged axiom)     ← "unchallenged assumptions" (25%)
    #   8. 不确定性降级 (uncertainty downgrade) ← "uncertainty not enforced" (33%)
    #   9. 规则范围丢失 (rule scope loss)       ← "rule scope loss" (67%)

    # ── 检测 7: 未挑战假设 (unchallenged axiom) ──────────────
    # honest-axiom 被声明但从未被任何地方引用（声明行之外 0 次出现）=
    # 冗余假设或表演性诚实变体。用全文件计数（含定理参数类型签名、
    # exact/apply 引用），避免误报「作为条件定理前提被引用的 axiom」。
    axiom_names = re.findall(r'^\s*axiom\s+([A-Za-z_][A-Za-z0-9_]*)\b', lean, re.M)
    unchallenged = []
    for a in axiom_names:
        # 统计 a 在全文件（含类型签名/证明体）的出现次数
        cnt = len(re.findall(rf'\b{re.escape(a)}\b', lean))
        if cnt <= 1:  # 只在声明行出现 = 从未被引用
            unchallenged.append(a)
    if unchallenged:
        msg = (f"未挑战假设：{len(unchallenged)} 个 axiom 全文件中仅声明处出现一次"
               f"（从未被任何 theorem/lemma 的签名或证明体引用 = 冗余假设/表演性诚实）: "
               f"{sorted(unchallenged)[:8]}")
        warns.append(msg)
        findings.append({"type": "unchallenged_axiom", "severity": "WARN",
                         "unchallenged": sorted(unchallenged), "msg": msg})

    # ── 检测 8: 不确定性降级 (uncertainty downgrade) ─────────
    # paper 用确定性动词描述 lean 里实际是 axiom/opaque（honest-axiom）的声明。
    if paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
        proved_claims = set(re.findall(
            r'(?:we\s+prove|is\s+proven|is\s+proved|is\s+established|we\s+establish|'
            r'\bproved\b|\bproven\b|\bestablished\b)\s+`?([A-Za-z_][A-Za-z0-9_]*)`?',
            paper, re.I))
        proved_claims = {c for c in proved_claims
                         if c.lower() not in _EN_WORDS and not re.match(r'^\d+$', c)}
        axiom_opaque_names = set(axiom_names) | set(
            re.findall(r'^\s*opaque\s+([A-Za-z_][A-Za-z0-9_]*)', lean, re.M))
        downgraded = proved_claims & axiom_opaque_names
        if downgraded:
            msg = (f"不确定性降级：论文用确定性动词（prove/proven/established）描述 "
                   f"{len(downgraded)} 个实为 honest-axiom/opaque 的声明"
                   f"（诚实标注在论文传播中被降级）: {sorted(downgraded)[:8]}")
            warns.append(msg)
            findings.append({"type": "uncertainty_downgrade", "severity": "WARN",
                             "downgraded": sorted(downgraded), "msg": msg})

    # ── 检测 9: 规则范围丢失 (rule scope loss) ───────────────
    # paper 把条件定理（带显式前提参数的 theorem）表述为无条件结论。
    if paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
        conditional_theorems = set(re.findall(
            r'^\s*theorem\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(', lean, re.M))
        _scope_hits = 0
        for tname in sorted(conditional_theorems):
            for m in re.finditer(rf'[^.\n]*\b{re.escape(tname)}\b[^.\n]*\.', paper):
                sentence = m.group(0)
                if re.search(r'\bgiven\b|\bassuming\b|\bconditional\b|\bunder\b|'
                             r'\bprovided\b|\bif\b|\bwhen\b|\bsubject\b', sentence, re.I):
                    continue  # 有条件修饰，范围保留，OK
                msg = (f"规则范围丢失：条件定理 `{tname}` 在论文中被无条件表述"
                       f"（缺 given/assuming/conditional 修饰）: {sentence.strip()[:110]}")
                warns.append(msg)
                findings.append({"type": "rule_scope_loss", "severity": "WARN",
                                 "theorem": tname, "sentence": sentence.strip()[:140],
                                 "msg": msg})
                _scope_hits += 1
                break  # 每个定理只报一次
        if _scope_hits == 0:
            # 无规则范围丢失，记录 INFO 供审计追踪
            pass

    # ── 检测 10: Method-Code Alignment (P0-2, ScientistTwo) ──
    # [arXiv:2609.19644] CoE 完整性审计第四查：论文方法段 ↔ Lean 代码逐条对齐。
    # 补 P0-3/P0-4 的反向（Lean→paper），输出 {paper_claim, lean_decl, status} 映射。
    if _HAS_SCIENTISTTWO and paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
        mc = _align_mc(lean, paper)
        for b in mc.get("blocks", []):
            blocks.append(f"[ScientistTwo P0-2] {b}")
        for w in mc.get("warns", []):
            warns.append(f"[ScientistTwo P0-2] {w}")
        for f in mc.get("findings", []):
            f = dict(f); f["type"] = "scientisttwo_" + f["type"]
            findings.append(f)

    # ── 检测 11: Reference Verification (P0-1, ScientistTwo) ──
    # [arXiv:2609.19644] CoE 完整性审计第三查：参考文献零幻觉（0/1814）。
    if _HAS_SCIENTISTTWO and paper_path and Path(paper_path).exists():
        paper = Path(paper_path).read_text(encoding="utf-8", errors="replace")
        rv = _verify_refs(paper)
        for b in rv.get("blocks", []):
            blocks.append(f"[ScientistTwo P0-1] {b}")
        for w in rv.get("warns", []):
            warns.append(f"[ScientistTwo P0-1] {w}")
        for f in rv.get("findings", []):
            f = dict(f); f["type"] = "scientisttwo_" + f["type"]
            findings.append(f)

    # ── 检测 12: Axiom Ablation static (P0-3, ScientistTwo) ──
    # [arXiv:2609.19644] Ablation Critic 思路：公理必要性静态消融。
    # 编译级消融需 Lean 工具链，见 axiom_ablation.py --lean-bin。
    if _HAS_SCIENTISTTWO:
        ab = _static_ablation(lean)
        for b in ab.get("blocks", []):
            blocks.append(f"[ScientistTwo P0-3] {b}")
        for w in ab.get("warns", []):
            warns.append(f"[ScientistTwo P0-3] {w}")
        for f in ab.get("findings", []):
            f = dict(f); f["type"] = "scientisttwo_" + f["type"]
            findings.append(f)

    # ── 缺陷定位 (P0-3, Colosseum)：为每个 finding 附加 section/line ──
    findings = _localize_findings(findings, raw_lean)

    # ── 汇总 ────────────────────────────────────────────────
    gate = "BLOCK" if blocks else ("WARN" if warns else "PASS")

    report = {
        "audit_time": datetime.now().isoformat(),
        "lean_file": lean_path,
        "paper_file": paper_path,
        "stats": {
            "axioms": n_axiom,
            "theorems": n_theorem,
            "lemmas": n_lemma,
            "active_sorry": n_sorry,
            "active_admit": n_admit,
            "trivial_stubs": n_trivial,
            "true_stubs": n_true_stub,
            "real_attributes": real_attr,
            "comment_attributes_pseudo": comment_attr_pseudo,
            "comment_attributes_honest": comment_attr_honest,
        },
        "gate": gate,
        "blocks": blocks,
        "warns": warns,
        "findings": findings,
    }
    return report


def main():
    ap = argparse.ArgumentParser(description="Formal Proof Consistency Audit (Stage 3.5)")
    ap.add_argument("--lean", required=True, help="Lean 4 proof file")
    ap.add_argument("--paper", help="Paper text (for phantom theorem detection)")
    ap.add_argument("--expected-axioms", type=int, help="Claimed axiom count from paper")
    ap.add_argument("--expected-theorems", type=int, help="Claimed theorem count from paper")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()

    report = audit(args.lean, args.paper, args.expected_axioms, args.expected_theorems)

    out_path = args.output or "/tmp/proof_consistency_audit.json"
    Path(out_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print("=" * 60)
    print("Formal Proof Consistency Audit (Stage 3.5)")
    print("=" * 60)
    s = report["stats"]
    print(f"  axioms={s['axioms']}  theorems={s['theorems']}  lemmas={s['lemmas']}")
    print(f"  sorry={s['active_sorry']}  admit={s['active_admit']}  "
          f"trivial_stubs={s['trivial_stubs']}  true_stubs={s['true_stubs']}")
    print(f"  real_attrs={s['real_attributes']}  pseudo_attrs={s['comment_attributes_pseudo']}  honest_labels={s['comment_attributes_honest']}")
    print(f"\n  GATE: {report['gate']}")
    for b in report["blocks"]:
        print(f"  🔴 BLOCK: {b}")
    for w in report["warns"]:
        print(f"  🟡 WARN: {w}")
    print(f"\n  Report: {out_path}")
    return 0 if report["gate"] != "BLOCK" else 1


if __name__ == "__main__":
    sys.exit(main())
