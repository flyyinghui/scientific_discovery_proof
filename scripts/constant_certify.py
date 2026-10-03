#!/usr/bin/env python3
"""
Constant Certification — 闭环常数认证 (from BootLoops `constant-recognition`)
=============================================================================
用 PSLQ 整数关系算法把一个高精度数值认证为「声明常数环」上的闭环形式，
核心纪律来自 BootLoops 1.0 的 `constant-recognition` 协议：

  "An integer-relation algorithm is a fitting machine. Whether the relation
   means anything is decided entirely by choices made BEFORE the search —
   which constants are allowed, how large the integers may be, how many
   digits pay for it all. A hit is cheap; a null is informative only
   against a declared ring."

四条纪律（顺序不可颠倒）:
  1. 声明常数环 (允许的基: π², ζ(3), log 2, √2, 1, ...) 在搜索之前。
  2. 声明系数高度 H 与精度预算在搜索之前。
  3. 算 digit budget: 关系成本 ≈ n·log10(H) 位，盈余 = 工作精度 − 成本。
    盈余太薄 → 搜索是掷硬币；环/高度成本超过精度 → 搜索是演戏。
  4. "找不到就拒绝发明": PSLQ 无解 → 报 NULL(在声明的环内无关系)，
    绝不发明一个"噪声识别成的著名常数"。

内置 SL(6,C) 默认认证目标（可服务当前四论文框架的闭环常数）:
  g_*² = 12π²/35,  g_inst² = 24π²/35,  λ_KLS = 35/3,  |ρ_res|² = 35

Usage:
  python constant_certify.py [--target NAME --value X --ring "pi^2" "1" ...] \
      [--height 1e6] [--digits 50] [--output const_cert.json] [--self-test]
"""

import argparse, json, os, re, sys
from datetime import datetime

try:
    import mpmath as mp
    _HAS_MP = True
except ImportError:
    _HAS_MP = False


# ── 内置 SL(6,C) 默认认证目标 ─────────────────────────────────────────────

DEFAULT_TARGETS = [
    {"name": "g_star_squared",  "expr": "12*pi**2/35", "ring": ["pi**2", "1"],
     "height": 1e8, "expected_relation": "35*g_*² = 12*π²  (系数 [35, -12] 在 {g_*², π²})",
     "note": "g_*² = -4π²η_RG/b_RG, η_RG=-36/35, b_RG=12"},
    {"name": "g_inst_squared",  "expr": "24*pi**2/35", "ring": ["pi**2", "1"],
     "height": 1e8, "expected_relation": "35*g_inst² = 24*π²  (系数 [35, -24])",
     "note": "g_inst² = 8π²/r_⊥ = 24π²/35 = 2g_*²"},
    {"name": "lambda_KLS_ratio", "expr": "35/3", "ring": ["1"],
     "height": 1e6, "expected_relation": "3*λ_KLS = 35  (系数 [3, -35])",
     "note": "λ_KLS = 35/3 (横向 3D 均分, honest-axiom A-3D)"},
    {"name": "rho_res_norm_sq", "expr": "35", "ring": ["1"],
     "height": 1e6, "expected_relation": "1*|ρ_res|² = 35  (系数 [1, -35])",
     "note": "|ρ_res|² = 70/c, c=2"},
]


def _safe_eval(expr: str, mp_ctx):
    # 把数字字面量包成 mpf("...")，消除 Python float 除法的 1e-16 精度损失
    wrapped = re.sub(
        r'(?<![A-Za-z_.])(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)',
        r'mpf("\1")', expr,
    )
    allowed = {"pi": mp_ctx.pi, "sqrt": mp_ctx.sqrt, "log": mp_ctx.log, "zeta": mp_ctx.zeta, "mpf": mp_ctx.mpf}
    code = compile(wrapped, "<cert>", "eval")
    for name in code.co_names:
        if name not in allowed:
            raise ValueError(f"表达式引用不允许名字: {name!r}")
    return eval(code, {"__builtins__": {}}, allowed)


def certify(target_name, target_value, ring_exprs, height, digits):
    """对一个目标值跑 PSLQ，返回 (verdict, detail_dict)。"""
    mp.mp.dps = digits
    try:
        t = mp.mpf(target_value) if isinstance(target_value, str) else mp.mpf(target_value)
        ring_vals = [t] + [_safe_eval(e, mp.mp) for e in ring_exprs]
    except Exception as e:
        return "ERROR", {"error": f"求值失败: {type(e).__name__}: {e}"}

    n = len(ring_vals)  # 含目标共 n 个数
    cost = n * mp.log10(mp.mpf(str(int(height))))  # 关系成本 ≈ n·log10(H)
    surplus = digits - cost

    d = {"name": target_name, "target": mp.nstr(t, digits), "ring": ring_exprs,
         "height": int(height), "working_digits": digits, "digit_cost": float(cost),
         "digit_surplus": float(surplus), "surplus_warning": surplus < 10}

    # PSLQ: 找整数 c_i 使 Σ c_i * ring_vals[i] = 0
    relation = mp.pslq(ring_vals, maxcoeff=int(height), maxsteps=10**4)

    if relation is None:
        d["verdict"] = "NULL"
        d["relation"] = None
        d["message"] = "在声明的环内 (高度 H=%d, 精度 %d 位) 找不到整数关系 —— 拒绝发明。" % (int(height), digits)
        return "NULL", d

    # relation = [c0, c1, c2, ...] 使 c0*target + c1*ring0 + c2*ring1 + ... = 0
    c0 = relation[0]
    if c0 == 0:
        d["verdict"] = "DEGENERATE"
        d["relation"] = list(map(int, relation))
        d["message"] = "r[0]==0 (退化关系): 基之间自身相关，非目标闭环。"
        return "DEGENERATE", d

    # 符号归一化: c0<0 则整体取反，保证闭环形式为「正分子 / 正分母」
    relation = [int(c) for c in relation]
    if c0 < 0:
        relation = [-c for c in relation]
        c0 = relation[0]

    # 目标 = -(c1*ring0 + c2*ring1 + ...) / c0
    terms = []
    for ci, expr in zip(relation[1:], ring_exprs):
        if ci != 0:
            terms.append(f"{(-ci)}*({expr})" if ci < 0 else f"{-ci}*({expr})")
    target_expr = f"({ ' + '.join(terms) if terms else '0' }) / {c0}"
    d["verdict"] = "CLOSED"
    d["relation"] = relation
    d["closed_form"] = f"{target_name} = {target_expr}"
    # 验证残差
    lhs = t
    rhs = sum(ci * v for ci, v in zip(relation[1:], ring_vals[1:])) / (-c0)
    d["residual"] = float(abs(lhs - rhs))
    d["verified_digits"] = int(-mp.log10(max(abs(lhs - rhs), mp.mpf('1e-300'))))
    d["message"] = f"闭环认证成功: {target_name} = {target_expr} (系数高度 {max(abs(c) for c in relation)}, 残差 ~1e-{d['verified_digits']})"
    return "CLOSED", d


def main():
    ap = argparse.ArgumentParser(description="闭环常数认证 (BootLoops constant-recognition)")
    ap.add_argument("--target", help="目标常数名")
    ap.add_argument("--value", help="目标数值 (高精度字符串)")
    ap.add_argument("--ring", nargs="+", default=["pi**2", "1"], help="声明常数环 (如 pi**2, zeta(3), log(2), 1)")
    ap.add_argument("--height", type=float, default=1e8, help="系数高度上限 H")
    ap.add_argument("--digits", type=int, default=50, help="工作精度 (位)")
    ap.add_argument("--output", default="/tmp/constant_cert.json", help="输出 JSON 路径")
    ap.add_argument("--self-test", action="store_true", help="跑内置 SL6C 目标自测")
    args = ap.parse_args()

    if not _HAS_MP:
        print("FATAL: mpmath 未安装"); sys.exit(1)

    if args.self_test or not args.target:
        targets = DEFAULT_TARGETS
    else:
        targets = [{"name": args.target, "expr": None, "value": args.value,
                    "ring": args.ring, "height": args.height, "note": ""}]

    report = {"ran_at": datetime.now().isoformat(), "results": [], "verdict": "ALL_CLOSED"}
    for tg in targets:
        # 计算目标值
        if "expr" in tg and tg["expr"]:
            mp.mp.dps = args.digits
            val = _safe_eval(tg["expr"], mp.mp)
        else:
            val = tg["value"]
        verdict, d = certify(tg["name"], val, tg["ring"], tg["height"], args.digits)
        d["note"] = tg.get("note", "")
        if "expected_relation" in tg:
            d["expected_relation"] = tg["expected_relation"]
        report["results"].append(d)
        print(f"  [{tg['name']}] {verdict}: {d.get('message', d.get('error', ''))}")
        if verdict != "CLOSED":
            report["verdict"] = "HAS_" + verdict

    json.dump(report, open(args.output, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[constant-certify] 结论: {report['verdict']}")
    print(f"[constant-certify] 报告 -> {args.output}")


if __name__ == "__main__":
    main()
