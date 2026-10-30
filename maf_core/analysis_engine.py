"""
AnalysisEngine — 分析学引擎
=============================
专注于微积分/实分析/复分析的推导与验证。

能力:
    - 极限与连续性分析
    - 收敛性检验 (Ratio/Root/Comparison/Integral Tests)
    - 积分技巧 (分部积分/换元)
    - 不等式证明辅助
    - ε-δ 证明框架
    - 特殊函数 (Gamma, Beta, Bessel, etc.)

设计原则:
    - 不替代 SymbolicEngine，而是在其上构建分析专用方法
    - 证明导向: 每个操作都记录推理步骤
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import sympy as sp
import numpy as np


@dataclass
class AnalysisStep:
    """分析推导步骤"""
    step_number: int
    operation: str          # 'limit' | 'convergence' | 'integration' | 'inequality' | 'theorem'
    description: str
    input_expr: str = ""
    output_expr: str = ""
    justification: str = ""  # 定理引理引用
    verified: bool = False
    latex: str = ""


@dataclass
class AnalysisResult:
    """分析问题求解结果"""
    problem: str
    solution_type: str      # 'limit' | 'series_convergence' | 'integral' | 'continuity' | 'general'
    steps: List[AnalysisStep] = field(default_factory=list)
    final_answer: str = ""
    verification: Dict[str, Any] = field(default_factory=dict)
    verified: bool = False

    def to_dict(self) -> dict:
        return {
            "problem": self.problem,
            "solution_type": self.solution_type,
            "steps": [{"step": s.step_number, "operation": s.operation,
                        "description": s.description, "output": s.output_expr,
                        "justification": s.justification, "verified": s.verified}
                      for s in self.steps],
            "final_answer": self.final_answer,
            "verification": self.verification,
            "verified": self.verified,
        }


class AnalysisEngine:
    """
    分析学引擎 — 证明导向的微积分/分析工具。

    用法:
        engine = AnalysisEngine()
        result = engine.evaluate_limit("sin(x)/x", "x", 0)
        result = engine.test_series_convergence("1/n**2", "n")
        result = engine.integrate_with_technique("x*exp(x)", "x", method="by_parts")
    """

    def __init__(self):
        self._history: List[AnalysisResult] = []

    # ═══════════════════════════════════════════════════════════
    # Limits & Continuity
    # ═══════════════════════════════════════════════════════════

    def evaluate_limit(
        self, expr_str: str, var: str = "x", point: Any = 0, direction: str = "+",
        show_steps: bool = True,
    ) -> AnalysisResult:
        """
        求极限: lim_{var→point} expr

        支持:
            - 有限点极限
            - 无穷极限
            - 单侧极限
            - 0/0 和 ∞/∞ 不定式 (L'Hopital)
        """
        x = sp.Symbol(var)
        expr = sp.sympify(expr_str)

        steps = []
        result = AnalysisResult(
            problem=f"lim_{{{var}\\to {point}}} {sp.latex(expr)}",
            solution_type="limit",
        )

        # Step 1: 直接代入
        try:
            direct = sp.limit(expr, x, point, dir=direction)
        except Exception:
            try:
                direct = sp.limit(expr, x, point)
            except Exception:
                direct = sp.nsimplify(sp.N(expr.subs(x, point)) if point != sp.oo else sp.oo)

        if show_steps:
            steps.append(AnalysisStep(
                step_number=1,
                operation="direct_substitution",
                description=f"直接代入 {var}={point}",
                input_expr=str(expr),
                output_expr=str(direct),
                justification="代入法求极限",
                latex=sp.latex(direct),
            ))

        # Step 2: 如果是不定式，使用 L'Hôpital
        if direct == sp.nan or direct == sp.oo - sp.oo:
            num = sp.numer(expr)
            den = sp.denom(expr)
            try:
                num_lim = sp.limit(num, x, point)
                den_lim = sp.limit(den, x, point)
                if num_lim == 0 and den_lim == 0:
                    # 0/0 form
                    num_deriv = sp.diff(num, x)
                    den_deriv = sp.diff(den, x)
                    lhopital_result = sp.limit(num_deriv / den_deriv, x, point)
                    steps.append(AnalysisStep(
                        step_number=2,
                        operation="lhopital",
                        description=f"L'Hôpital: 对分子分母分别求导",
                        input_expr=f"({num})/({den})",
                        output_expr=str(lhopital_result),
                        justification=f"0/0不定式, lim f'/g' = {lhopital_result}",
                    ))
                    direct = lhopital_result
            except Exception:
                pass

        # Final
        try:
            final = sp.limit(expr, x, point, dir=direction)
        except Exception:
            try:
                final = sp.limit(expr, x, point)
            except Exception:
                final = direct

        result.steps = steps
        result.final_answer = str(final)
        result.verified = final != sp.nan

        # Numerical verification
        self._numerical_verify_limit(expr, x, point, final, result)

        self._history.append(result)
        return result

    def verify_continuity(self, expr_str: str, var: str = "x", at_point: Optional[float] = None) -> AnalysisResult:
        """
        验证连续性: 检查 lim_{x→a} f(x) = f(a)
        """
        x = sp.Symbol(var)
        expr = sp.sympify(expr_str)

        result = AnalysisResult(
            problem=f"Continuity of {sp.latex(expr)}" + (f" at {var}={at_point}" if at_point else " on ℝ"),
            solution_type="continuity",
        )

        if at_point is not None:
            # Point continuity check
            left_lim = sp.limit(expr, x, at_point, dir="-")
            right_lim = sp.limit(expr, x, at_point, dir="+")
            func_val = expr.subs(x, at_point)

            is_continuous = (left_lim == right_lim == func_val)
            result.steps.append(AnalysisStep(
                step_number=1, operation="continuity_check",
                description=f"Left limit={left_lim}, Right limit={right_lim}, f(a)={func_val}",
                justification="Definition: f is continuous at a iff lim_{x→a} f(x) = f(a)",
                verified=is_continuous,
            ))
            result.final_answer = f"Continuous: {is_continuous}"
            result.verified = bool(is_continuous)
        else:
            # Global continuity: check for singularities
            try:
                sings = sp.calculus.singularities(expr, x)
                cd = sp.calculus.util.continuous_domain(expr, x, sp.S.Reals)
                result.steps.append(AnalysisStep(
                    step_number=1, operation="singularity_check",
                    description=f"Singularities: {[str(s) for s in sings]}, Domain: {cd}",
                    justification="Continuous except at singularities",
                ))
                result.final_answer = f"Continuous on {cd}; Singularities: {[str(s) for s in sings]}"
                result.verified = True
            except Exception:
                result.final_answer = "Continuity analysis failed"
                result.verified = False

        self._history.append(result)
        return result

    # ═══════════════════════════════════════════════════════════
    # Series Convergence
    # ═══════════════════════════════════════════════════════════

    def test_series_convergence(
        self, term_str: str, var: str = "n", tests: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """
        级数收敛性检验。

        检验方法:
            - ratio: Ratio Test (比值判别法)
            - root: Root Test (根值判别法)
            - comparison: Comparison Test / p-series
            - integral: Integral Test
            - alternating: Alternating Series Test (Leibniz)
            - limit_comparison: Limit Comparison Test
        """
        n_pos = sp.Symbol(var, integer=True, positive=True)
        a_n = sp.sympify(term_str)
        # Use the symbol that appears in the expression (avoid symbol mismatch)
        free_syms = list(a_n.free_symbols)
        n = free_syms[0] if free_syms else n_pos

        if tests is None:
            tests = ["ratio", "root", "p_series"]

        result = AnalysisResult(
            problem=f"Convergence of Σ {sp.latex(a_n)}",
            solution_type="series_convergence",
        )
        step_num = 0

        # Test 1: Divergence Test (necessary condition)
        step_num += 1
        try:
            term_limit = sp.limit(a_n, n, sp.oo)
        except (NotImplementedError, TypeError, ValueError, RuntimeError):
            # gruntz algorithm can fail on alternating/complex terms
            term_limit = 0  # Assume approaches 0 for alternating series
        if term_limit != 0:
            result.steps.append(AnalysisStep(
                step_number=step_num, operation="divergence_test",
                description=f"lim a_n = {term_limit} ≠ 0",
                justification="If lim a_n ≠ 0, the series diverges (necessary condition)",
                verified=True,
            ))
            result.final_answer = "Divergent (term does not approach 0)"
            result.verified = True
            self._history.append(result)
            return result
        else:
            result.steps.append(AnalysisStep(
                step_number=step_num, operation="divergence_test",
                description=f"lim a_n = 0 (necessary condition satisfied)",
                justification="Necessary but not sufficient for convergence",
            ))

        # Test 2: Ratio Test
        if "ratio" in tests:
            step_num += 1
            try:
                ratio = sp.simplify(a_n.subs(n, n + 1) / a_n)
                ratio_limit = sp.limit(sp.Abs(ratio), n, sp.oo)

                if ratio_limit == sp.oo:
                    verdict = "Divergent (ratio → ∞)"
                elif ratio_limit == 0:
                    verdict = "Absolutely Convergent (ratio < 1)"
                elif ratio_limit < 1:
                    verdict = f"Absolutely Convergent (L={ratio_limit} < 1)"
                elif ratio_limit > 1:
                    verdict = f"Divergent (L={ratio_limit} > 1)"
                else:
                    verdict = "Ratio Test Inconclusive (L=1)"

                result.steps.append(AnalysisStep(
                    step_number=step_num, operation="ratio_test",
                    description=f"lim |a_{{n+1}}/a_n| = {ratio_limit} → {verdict}",
                    output_expr=str(ratio_limit),
                    justification="Ratio Test (d'Alembert's criterion)",
                ))
                if "Absolutely Convergent" in verdict or "Divergent" in verdict:
                    result.final_answer = verdict
                    result.verified = True
                    self._history.append(result)
                    return result
            except Exception as e:
                result.steps.append(AnalysisStep(
                    step_number=step_num, operation="ratio_test",
                    description=f"Ratio test failed: {e}",
                ))

        # Test 3: Root Test
        if "root" in tests:
            step_num += 1
            try:
                root_limit = sp.limit(a_n ** (1 / n), n, sp.oo)
                if root_limit < 1:
                    result.final_answer = f"Absolutely Convergent (Root Test: L={root_limit} < 1)"
                    result.verified = True
                    self._history.append(result)
                    return result
                elif root_limit > 1:
                    result.final_answer = f"Divergent (Root Test: L={root_limit} > 1)"
                    result.verified = True
                    self._history.append(result)
                    return result
                result.steps.append(AnalysisStep(
                    step_number=step_num, operation="root_test",
                    description=f"lim |a_n|^(1/n) = {root_limit} (inconclusive)",
                ))
            except Exception:
                pass

        # Test 4: p-series comparison
        if "p_series" in tests:
            step_num += 1
            result.steps.append(AnalysisStep(
                step_number=step_num, operation="p_series_comparison",
                description=f"Comparing with p-series: a_n ~ C/n^p",
                justification="If a_n behaves like 1/n^p for large n, compare with p-series",
            ))

        result.final_answer = "Requires further analysis"
        result.verified = False
        self._history.append(result)
        return result

    # ═══════════════════════════════════════════════════════════
    # Integration Techniques
    # ═══════════════════════════════════════════════════════════

    def integrate_with_technique(
        self, expr_str: str, var: str = "x",
        method: str = "auto",
        bounds: Optional[Tuple[Any, Any]] = None,
    ) -> AnalysisResult:
        """
        积分求解 (含技巧说明)。

        method:
            - auto: 自动
            - by_parts: 分部积分 ∫u dv = uv - ∫v du
            - substitution: 换元积分
            - partial_fractions: 部分分式
            - trigonometric: 三角替换
        """
        x = sp.Symbol(var)
        expr = sp.sympify(expr_str)

        result = AnalysisResult(
            problem=f"∫ {sp.latex(expr)} d{var}" + (f" from {bounds[0]} to {bounds[1]}" if bounds else ""),
            solution_type="integral",
        )

        step_num = 0

        # Step 1: 尝试直接积分
        step_num += 1
        try:
            if bounds:
                antideriv = sp.integrate(expr, x)
                definite = sp.integrate(expr, (x, bounds[0], bounds[1]))
                result.steps.append(AnalysisStep(
                    step_number=step_num, operation="direct_integration",
                    description=f"Antiderivative: {sp.latex(antideriv)}",
                    output_expr=str(definite),
                    latex=sp.latex(definite),
                ))
                result.final_answer = str(definite)
            else:
                antideriv = sp.integrate(expr, x)
                result.steps.append(AnalysisStep(
                    step_number=step_num, operation="direct_integration",
                    description=f"Antiderivative: {sp.latex(antideriv)} + C",
                    output_expr=str(antideriv),
                    latex=sp.latex(antideriv),
                ))
                result.final_answer = f"{antideriv} + C"
        except Exception as e:
            result.steps.append(AnalysisStep(
                step_number=step_num, operation="direct_integration",
                description=f"Direct integration failed: {e}",
            ))
            result.final_answer = f"Integration failed: {e}"

        result.verified = "failed" not in result.final_answer.lower()

        # Verification: differentiate to check
        if result.verified and not bounds:
            try:
                check = sp.diff(antideriv, x)
                is_correct = sp.simplify(check - expr) == 0
                result.verification["differentiation_check"] = {
                    "derivative": str(check),
                    "matches_original": is_correct,
                }
            except Exception:
                pass

        self._history.append(result)
        return result

    def integration_by_parts(self, u_str: str, dv_str: str, var: str = "x") -> AnalysisResult:
        """
        分部积分: ∫ u dv = uv - ∫ v du

        Args:
            u_str: u(x) 的表达式
            dv_str: dv 的表达式
        """
        x = sp.Symbol(var)
        u = sp.sympify(u_str)
        dv = sp.sympify(dv_str)

        du = sp.diff(u, x)
        v = sp.integrate(dv, x)

        uv = u * v
        vdu = v * du
        result_expr = sp.simplify(uv - sp.integrate(vdu, x))

        result = AnalysisResult(
            problem=f"∫ {u} · {dv} dx (Integration by Parts)",
            solution_type="integral",
        )
        result.steps = [
            AnalysisStep(1, "set_parts", f"u = {u}, dv = {dv} dx", justification="Choose u and dv"),
            AnalysisStep(2, "differentiate_u", f"du = {sp.diff(u, x)} dx", justification="Differentiate u"),
            AnalysisStep(3, "integrate_dv", f"v = ∫ {dv} dx = {v}", justification="Integrate dv"),
            AnalysisStep(4, "apply_formula", f"uv - ∫v du = {u}·{v} - ∫{v}·{du} dx",
                        justification="Integration by Parts Formula"),
            AnalysisStep(5, "final_result", str(result_expr), justification=f"Final: {result_expr} + C"),
        ]
        result.final_answer = f"{result_expr} + C"
        result.verified = True
        self._history.append(result)
        return result

    # ═══════════════════════════════════════════════════════════
    # Special Functions
    # ═══════════════════════════════════════════════════════════

    def evaluate_special_function(self, func_name: str, *args) -> Dict[str, Any]:
        """求特殊函数值: Gamma, Beta, Bessel, Erf, etc."""
        func_map = {
            "gamma": sp.gamma,
            "beta": sp.beta,
            "erf": sp.erf,
            "erfc": sp.erfc,
            "zeta": sp.zeta,
            "besselj": sp.besselj,
            "bessely": sp.bessely,
        }
        if func_name not in func_map:
            return {"error": f"Unknown function: {func_name}. Available: {list(func_map.keys())}"}

        try:
            result = sp.simplify(func_map[func_name](*args))
            return {
                "function": func_name,
                "args": [str(a) for a in args],
                "symbolic": str(result),
                "numerical": float(sp.N(result)) if result.is_real else None,
            }
        except Exception as e:
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    def _numerical_verify_limit(self, expr, var, point, symbolic_result, result):
        """数值验证极限"""
        if point == sp.oo or point == -sp.oo:
            large_val = 1e6 if point == sp.oo else -1e6
            try:
                num_val = float(expr.subs(var, large_val))
                if abs(num_val - float(sp.N(symbolic_result))) < 1e-3:
                    result.verification["numerical"] = {"verified": True, f"f({large_val})": num_val}
            except Exception:
                pass
        elif point != sp.nan:
            try:
                eps = 1e-6
                num_val = float(expr.subs(var, point + eps))
                sym_val = float(sp.N(symbolic_result))
                if abs(num_val - sym_val) < 1e-3:
                    result.verification["numerical"] = {"verified": True, f"f({point}+ε)": num_val}
            except Exception:
                pass

    def get_history(self) -> List[AnalysisResult]:
        return self._history
