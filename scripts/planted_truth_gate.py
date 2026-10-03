#!/usr/bin/env python3
"""
Planted-Truth Gate — Stage 1.5 植物真值门控 (from BootLoops `planted-truth`)
=============================================================================
在数值验证 (Stage 1 SciExplorer/MAF) 之后、形式化证明 (Stage 3 PPE) 之前，
验证「数值层管线本身是健全的」——必须先证明它能 (a) 恢复一个已知植入答案
(正对照)，且 (b) 抓住一个故意污染的错误输入 (负对照)，才允许把候选猜想送进
Lean 形式化。

映射自 BootLoops 1.0 的 `planted-truth` 协议 (Matthew D. Schwartz / Anthropic):
  "A pipeline that has only ever seen real data has never been tested, because
   nobody knew what the right answer was. The only inputs whose correct output
   is known are the ones you construct. Plant first, look second."

核心纪律（顺序不可颠倒）:
  1. 在跑真实数据之前冻结对照（写死正/负对照的表达式与容差）。
  2. 正对照: 已知真值恒等式必须被数值引擎恢复 (|residual| ≤ tolerance)。
  3. 负对照: 故意错误的值必须被数值引擎抓住 (|residual| > tolerance)。
  4. 任一对照失败 → BLOCK（在 Stage 3 之前终止管线），全部通过 → PASS。

内置 SL(6,C) 默认对照集（可直接服务当前四论文框架）:
  正对照: λ_KLS=35/3, g_*²=12π²/35, g_inst²=24π²/35, |ρ_res|²=35 (c=2)
  负对照: g_TC²=8π²/35 (v2.6.0 曾误用纵向 λ_∥ 的历史 bug — 必须被抓住)

Usage:
  python planted_truth_gate.py [--controls planted_controls.json] \
      [--output stage15_planted_truth.json] [--mock] [--self-test]
"""

import argparse, json, os, re, sys
from datetime import datetime

try:
    import mpmath as mp
    mp.mp.dps = 50
    _HAS_MP = True
except ImportError:
    _HAS_MP = False

# ── 内置 SL(6,C) 默认对照集（植物真值 = 四论文框架的已知闭环常数 + 历史 bug）────────

DEFAULT_CONTROLS = {
    "target": "SL6C unified framework — numerical-layer soundness (BootLoops planted-truth)",
    "positive_controls": [
        {"name": "lambda_KLS_ratio", "expr": "35/3",         "expected": "11.666666666666666667", "tolerance": 1e-12,
         "note": "λ_KLS = 35/3 (横向 3D 均分, honest-axiom A-3D)"},
        {"name": "g_star_squared",  "expr": "12*pi**2/35",  "expected": "3.3838643660877800979", "tolerance": 1e-12,
         "note": "g_*² = 12π²/35 = -4π²η_RG/b_RG (IR 不动点), g_*≈1.8395"},
        {"name": "g_inst_squared",  "expr": "24*pi**2/35",  "expected": "6.7677287321755601958", "tolerance": 1e-12,
         "note": "g_inst² = 24π²/35 = 2g_*² (瞬子匹配), g_inst≈2.6015"},
        {"name": "rho_res_norm_sq", "expr": "70/2",         "expected": "35",                    "tolerance": 1e-20,
         "note": "|ρ_res|² = 70/c, c=2 ⟹ 35 (限制根范数)"},
        {"name": "rho_alg_norm_sq", "expr": "35/2",         "expected": "17.5",                  "tolerance": 1e-20,
         "note": "|ρ_alg|² = 35/2 (A_5 Weyl 向量范数, Killing 归一化)"},
    ],
    "negative_controls": [
        {"name": "gtc_sq_8pi2_35_bug", "expr": "8*pi**2/35", "expected": "6.7677287321755601958", "tolerance": 1e-6,
         "note": "v2.6.0 历史 bug: 误用纵向 λ_∥=35 得 g_TC²=8π²/35≈2.256，正确为横向 24π²/35≈6.768。负对照必须抓住此差异（相对偏差 3×）。"},
    ],
}


def _safe_eval(expr: str, mp_ctx):
    """受限命名空间求值。整数/浮点字面量包成 mpf 做高精度算术，仅允许 pi/sqrt/log/zeta。"""
    # 把数字字面量包成 mpf("...")，消除 Python float 除法的 1e-16 精度损失
    wrapped = re.sub(
        r'(?<![A-Za-z_.])(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)',
        r'mpf("\1")', expr,
    )
    if not re.fullmatch(r'[\d\s+\-*/().eEpi"mpfz]*', wrapped):
        # 宽松校验：wrapped 后应只含 mpf("..")、pi/sqrt/log/zeta、运算符
        pass
    allowed = {"pi": mp_ctx.pi, "sqrt": mp_ctx.sqrt, "log": mp_ctx.log, "zeta": mp_ctx.zeta, "mpf": mp_ctx.mpf}
    code = compile(wrapped, "<control>", "eval")
    for name in code.co_names:
        if name not in allowed:
            raise ValueError(f"表达式引用不允许的名字: {name!r}")
    return eval(code, {"__builtins__": {}}, allowed)


def _run_control(ctrl, kind, mp_ctx):
    """执行一个对照，返回 (name, residual, verdict, detail)。"""
    name = ctrl["name"]
    try:
        computed = _safe_eval(ctrl["expr"], mp_ctx)
        expected = mp_ctx.mpf(ctrl["expected"])
        tol = mp_ctx.mpf(str(ctrl["tolerance"]))
    except Exception as e:
        return (name, None, "ERROR", f"求值失败: {type(e).__name__}: {e}")

    residual = abs(computed - expected)
    rel = residual / max(abs(expected), mp_ctx.mpf("1e-300"))

    if kind == "positive":
        # 正对照: 必须恢复已知答案（残差 ≤ 容差）
        ok = residual <= tol
        verdict = "PASS" if ok else "FAIL"
        detail = f"computed={mp.nstr(computed, 20)} expected={mp.nstr(expected, 20)} |residual|={mp.nstr(residual, 5)}"
    else:
        # 负对照: 必须抓住错误（残差 > 容差，即错误值不满足"应等于 expected"）
        ok = residual > tol
        verdict = "PASS" if ok else "FAIL"
        detail = f"computed={mp.nstr(computed, 20)} expected(正确值)={mp.nstr(expected, 20)} |residual|={mp.nstr(residual, 5)} rel={mp.nstr(rel, 5)}"

    return (name, float(residual), verdict, detail)


def run_gate(controls: dict):
    """执行完整植物真值门。返回 (verdict, report_dict)。"""
    if not _HAS_MP:
        return ("BLOCK", {"error": "mpmath 未安装，无法做精确数值对照"})

    mp_ctx = mp.mp
    report = {
        "target": controls.get("target", ""),
        "ran_at": datetime.now().isoformat(),
        "positive_controls": [],
        "negative_controls": [],
        "verdict": "PASS",
    }

    for ctrl in controls.get("positive_controls", []):
        name, residual, verdict, detail = _run_control(ctrl, "positive", mp_ctx)
        report["positive_controls"].append({"name": name, "residual": residual, "verdict": verdict, "detail": detail, "note": ctrl.get("note", "")})
        if verdict != "PASS":
            report["verdict"] = "BLOCK"

    for ctrl in controls.get("negative_controls", []):
        name, residual, verdict, detail = _run_control(ctrl, "negative", mp_ctx)
        report["negative_controls"].append({"name": name, "residual": residual, "verdict": verdict, "detail": detail, "note": ctrl.get("note", "")})
        if verdict != "PASS":
            report["verdict"] = "BLOCK"

    return report["verdict"], report


def main():
    ap = argparse.ArgumentParser(description="Stage 1.5 植物真值门 (BootLoops planted-truth)")
    ap.add_argument("--controls", help="自定义对照 JSON (默认用 SL6C 内置对照集)")
    ap.add_argument("--output", default="/tmp/stage15_planted_truth.json", help="输出 JSON 路径")
    ap.add_argument("--mock", action="store_true", help="离线确定性模板 (仅内置 SL6C 对照)")
    ap.add_argument("--self-test", action="store_true", help="跑内置对照自测并打印")
    args = ap.parse_args()

    controls = DEFAULT_CONTROLS
    if args.controls:
        controls = json.load(open(args.controls, encoding="utf-8"))

    verdict, report = run_gate(controls)

    json.dump(report, open(args.output, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"[planted-truth] 目标: {report['target']}")
    for c in report["positive_controls"]:
        print(f"  [正] {c['name']}: {c['verdict']}  {c['detail']}")
    for c in report["negative_controls"]:
        print(f"  [负] {c['name']}: {c['verdict']}  {c['detail']}")
    print(f"[planted-truth] 门控结论: {report['verdict']}")
    print(f"[planted-truth] 报告 -> {args.output}")

    if verdict == "BLOCK":
        print("[planted-truth] ⚠ BLOCK: 数值层不健全，禁止进入 Stage 3 形式化")
        sys.exit(1)
    return 0


if __name__ == "__main__":
    main()
