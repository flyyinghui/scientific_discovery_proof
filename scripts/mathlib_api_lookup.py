# -*- coding: utf-8 -*-
"""
mathlib_api_lookup.py — mathlib 4.34 API 检索增强模块

用途: 形式化证明补全时, LLM 常因不知道当前 mathlib 4.34 的正确 API 名而失败
      (旧 typeclass 名 OrderedRing→IsOrderedRing; 定理名被重命名/移除)。
      本模块通过 grep mathlib 源码, 检索正确的声明名 + 类型签名 + 相关定理,
      把结果注入 prompt, 命中"模型不知道正确 API 名"这一真实瓶颈。

方法: 离线 grep mathlib 源码 (可靠、快、不依赖 loogle/网络)。
验证: 可选调用 `lake env lean` + `#check` 确认声明存在并取类型签名。
"""
import os, re, subprocess, glob

MATHLIB_SRC = os.environ.get("MATHLIB_SRC", "").strip()  # 指向 mathlib4 源码树
CGICE_DIR = os.environ.get("LEAN_PROJECT", "").strip()   # lake 项目根目录

# 已知的 Is-prefix typeclass 重构映射 (mathlib 4.34)
IS_PREFIX_MAP = {
    'OrderedRing': 'IsOrderedRing',
    'OrderedSemiring': 'IsOrderedSemiring',
    'OrderedCommRing': 'IsOrderedCommRing',
    'OrderedCommSemiring': 'IsOrderedCommSemiring',
    'OrderedAddCommGroup': 'IsOrderedAddCommGroup',
    'OrderedAddCommMonoid': 'IsOrderedAddCommMonoid',
    'OrderedCommGroup': 'IsOrderedCommGroup',
    'OrderedCommMonoid': 'IsOrderedCommMonoid',
    'OrderedGroup': 'IsOrderedGroup',
    'OrderedMonoid': 'IsOrderedMonoid',
    'LinearOrderedRing': 'IsLinearOrderedRing',
    'LinearOrderedSemiring': 'IsLinearOrderedSemiring',
    'LinearOrderedAddCommGroup': 'IsLinearOrderedAddCommGroup',
    'LinearOrderedCommGroup': 'IsLinearOrderedCommGroup',
    'LinearOrderedCommMonoid': 'IsLinearOrderedCommMonoid',
    'TopologicalGroup': 'IsTopologicalGroup',
    'TopologicalRing': 'IsTopologicalRing',
    'Archimedean': 'MulArchimedean',
    'LinearOrderedField': None,  # 无 Is 后继, 需 case-by-case (见检索逻辑)
}

DECL_KINDS = ['class', 'structure', 'theorem', 'lemma', 'def', 'inductive', 'abbrev', 'axiom', 'instance', 'notation', 'noncomputable def', 'noncomputable theorem']


def _grep(pattern, max_results=20):
    """grep mathlib 源码(正则), 返回 [(file, lineno, line), ...]"""
    out = []
    # 用 Python re 扫描(rg 在本机不可用; 源码量大但单次扫描几秒)
    try:
        rx = re.compile(pattern)
    except re.error:
        rx = re.compile(re.escape(pattern))
    count = 0
    for f in glob.glob(os.path.join(MATHLIB_SRC, '**', '*.lean'), recursive=True):
        try:
            for i, ln in enumerate(open(f, encoding='utf-8', errors='ignore'), 1):
                if rx.search(ln):
                    out.append((f, i, ln.rstrip()))
                    count += 1
                    if count >= max_results:
                        return out
        except Exception:
            pass
    return out


def verify_decl(name):
    """检查声明名在 mathlib 4.34 中是否存在, 返回 (exists, [(file,line,line_text)])

    用 (?!\\.) 负向前瞻避免误匹配命名空间前缀(如 structure TopologicalGroup.IsSES)。
    """
    hits = _grep(rf'\b(class|structure|theorem|lemma|def|inductive|abbrev|instance|axiom)\s+{re.escape(name)}(?!\.)', max_results=5)
    return (len(hits) > 0, hits)


def resolve_typeclass(old_name):
    """把旧 typeclass 名解析为 mathlib 4.34 的正确名 + 是否存在"""
    # 1. 先查旧名是否仍存在
    exists, hits = verify_decl(old_name)
    if exists:
        return {'input': old_name, 'resolved': old_name, 'exists': True, 'note': '旧名仍有效', 'hits': hits}
    # 2. 查 Is-prefix 映射
    mapped = IS_PREFIX_MAP.get(old_name)
    if mapped:
        exists2, hits2 = verify_decl(mapped)
        if exists2:
            return {'input': old_name, 'resolved': mapped, 'exists': True, 'note': 'Is-prefix 重构', 'hits': hits2}
        else:
            return {'input': old_name, 'resolved': mapped, 'exists': False, 'note': '映射名也不存在, 需进一步检索', 'hits': hits2}
    # 3. 无映射, 检索近似名
    near = _grep(rf'\b(class|structure)\s+(Is)?{re.escape(old_name)}\b', max_results=10)
    return {'input': old_name, 'resolved': None, 'exists': False, 'note': '无已知映射, 近似命中如下', 'hits': near}


def find_theorems(pattern, max_results=15):
    """按模式检索相关 theorem/lemma 名(用于补证明时找可用引理)"""
    hits = _grep(rf'\b(theorem|lemma)\s+[^\n]*{re.escape(pattern)}[^\n]*:', max_results=max_results)
    return [h for h in hits]


def get_signature(name):
    """提取声明的类型签名(声明行 + 续行直到 := 或换行缩进结束)"""
    exists, hits = verify_decl(name)
    if not exists:
        return None
    f, ln, _ = hits[0]
    sig_lines = []
    try:
        lines = open(f, encoding='utf-8', errors='ignore').read().split('\n')
        for i in range(ln - 1, min(ln + 8, len(lines))):
            l = lines[i]
            sig_lines.append(l)
            # 终止条件: 声明体开始(:= where) 或 空行
            if i > ln - 1 and (':=' in l or ' where' in l or l.strip() == ''):
                break
    except Exception:
        pass
    return '\n'.join(sig_lines)


def retrieve_for_error(error_text, max_theorems=8):
    """从编译错误文本里提取未知标识符, 检索正确 API + 相关定理。

    返回 dict: {unknowns: [...], lookups: {name: result}, theorems: [...], summary: str}
    """
    # 提取 "unknown identifier 'X'" / "unknown constant 'X'" / "typeclass instance problem ... X"
    unknowns = []
    for m in re.finditer(r"unknown (?:identifier|constant)\s+'([^']+)'", error_text):
        unknowns.append(m.group(1))
    for m in re.finditer(r"unknown identifier\s+([A-Za-z_][\w.']*)", error_text):
        unknowns.append(m.group(1))
    unknowns = list(dict.fromkeys(unknowns))  # 去重保序

    lookups = {}
    for u in unknowns:
        lookups[u] = resolve_typeclass(u)

    # 检索与未知标识符相关的定理(按名字片段)
    theorems = []
    for u in unknowns[:3]:
        # 取名字尾部(去命名空间)作检索模式
        short = u.split('.')[-1]
        for t in find_theorems(short, max_results=max_theorems):
            theorems.append(t)
    theorems = theorems[:max_theorems]

    summary_lines = []
    for u, res in lookups.items():
        if res['exists']:
            summary_lines.append(f"  ✓ {u} → {res['resolved']} ({res['note']})")
        else:
            summary_lines.append(f"  ✗ {u} 不存在于 mathlib 4.34 ({res['note']})")
    return {'unknowns': unknowns, 'lookups': lookups, 'theorems': theorems,
            'summary': '\n'.join(summary_lines)}


def check_binders(code, max_check=20):
    """主动检查 Lean 代码里的所有 typeclass binder [Name ...], 返回不存在的旧名 + 正确映射。

    用于编译前(pre-compile)预防: 从源码提取 [X ...] binder, 逐个核对 mathlib 4.34。
    覆盖 "invalid binder annotation, type is not a class instance" 这类不报名字的错误。
    """
    binders = re.findall(r'\[([A-Z][A-Za-z0-9_.]*)\b[^\]]*\]', code)
    binders = list(dict.fromkeys(binders))[:max_check]
    issues = []
    for b in binders:
        # 跳过明显不是 typeclass 的(如 DecidableEq 局部参数、变量名)
        if '.' in b:  # 带命名空间的, 保留
            pass
        exists, _ = verify_decl(b)
        if not exists:
            r = resolve_typeclass(b)
            issues.append({'binder': b, 'resolved': r['resolved'], 'exists': False, 'note': r['note']})
    return issues


def retrieve_from_code(code):
    """从 Lean 源码主动检索(编译前): 检查 binder + 提取可疑标识符。返回 prompt 注入文本。"""
    parts = []
    # 1. 检查 typeclass binder
    issues = check_binders(code)
    if issues:
        lines = ["【mathlib 4.34 typeclass 检查(以下旧名需替换)】"]
        for it in issues:
            if it['resolved']:
                lines.append(f"  ✗ {it['binder']} → 应改为 {it['resolved']}")
            else:
                lines.append(f"  ✗ {it['binder']} 不存在, 需检索替代")
        parts.append('\n'.join(lines))
    return '\n'.join(parts)


def build_prompt_injection(retrieval):
    """把检索结果转成 prompt 注入文本"""
    parts = []
    if retrieval['summary']:
        parts.append("【mathlib 4.34 API 检索结果】")
        parts.append(retrieval['summary'])
    if retrieval['theorems']:
        parts.append("\n相关可用定理(名称+位置):")
        for f, ln, line in retrieval['theorems'][:8]:
            parts.append(f"  - {line.strip()}  [@ {os.path.basename(f)}:{ln}]")
    return '\n'.join(parts)


if __name__ == '__main__':
    # 自测: 几个已知的旧 API 名
    import sys
    test_names = sys.argv[1:] if len(sys.argv) > 1 else ['OrderedRing', 'LinearOrderedField', 'TopologicalGroup', 'Archimedean']
    for n in test_names:
        r = resolve_typeclass(n)
        print(f"\n=== {n} ===")
        print(f"  resolved: {r['resolved']}, exists={r['exists']}, note={r['note']}")
        for f, ln, line in r['hits'][:3]:
            print(f"    {os.path.basename(f)}:{ln}: {line.strip()[:80]}")
