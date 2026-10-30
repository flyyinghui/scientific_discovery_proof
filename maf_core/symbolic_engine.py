"""
SymbolicEngine — 通用符号推导引擎
===================================
基于 SymPy，完全独立于任何特定数学模型。

设计原则:
    - 接收任意 SymPy 表达式和符号，不假设具体模型
    - 所有操作返回结构化结果（含 LaTeX 和数值评估）
    - 支持链式调用（builder pattern）

用法:
    engine = SymbolicEngine()
    result = engine.differentiate(expr, var).simplify().to_latex().evaluate(vals).build()
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

import sympy as sp
import numpy as np


@dataclass
class DerivationResult:
    """单步推导的结构化结果"""
    name: str
    expression_raw: str = ""
    expression_latex: str = ""
    expression_simplified: str = ""
    numerical_value: Optional[float] = None
    steps: List[str] = field(default_factory=list)
    conditions: Dict[str, str] = field(default_factory=dict)
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "expression_raw": self.expression_raw,
            "expression_latex": self.expression_latex,
            "expression_simplified": self.expression_simplified,
            "numerical_value": self.numerical_value,
            "steps": self.steps,
            "conditions": self.conditions,
            "verified": self.verified,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)


class SymbolicEngine:
    """
    通用符号推导引擎。

    核心能力:
        - differentiate: 符号求导（一阶/高阶/偏导）
        - integrate: 符号积分（不定/定积分）
        - solve_equation: 方程求解（单个/方程组）
        - log_linearize: 对数线性化
        - taylor_expand: 泰勒展开
        - compute_elasticity: 弹性计算
        - compute_hessian: Hessian矩阵与驻点分类
        - compute_limit: 极限计算
        - verify_identity: 符号恒等式验证
        - lambdify: 转为NumPy可执行函数
    """

    def __init__(self, simplify_aggressively: bool = True):
        self.simplify_aggressively = simplify_aggressively
        self._symbols: Dict[str, sp.Symbol] = {}
        self._assumptions: Dict[str, Any] = {}
        self._history: List[DerivationResult] = []

    # ── Symbol Management ──

    def declare_symbols(self, symbols: Dict[str, Union[Tuple, Dict]]) -> "SymbolicEngine":
        """
        声明符号及其假设。

        Args:
            symbols: {
                'alpha': (sp.Symbol, {'positive': True, 'real': True}),
                'N': (sp.Symbol, {'positive': True, 'integer': True}),
                # 或简写
                'x': None,  # 普通实变量
            }
        """
        for name, spec in symbols.items():
            if spec is None:
                self._symbols[name] = sp.Symbol(name, real=True)
            elif isinstance(spec, dict):
                self._symbols[name] = sp.Symbol(name, **spec)
            else:
                self._symbols[name] = sp.Symbol(name, **spec) if isinstance(spec, dict) else sp.Symbol(name)
        return self

    def get_symbol(self, name: str) -> sp.Symbol:
        """获取已声明的符号"""
        if name not in self._symbols:
            self._symbols[name] = sp.Symbol(name, real=True)
        return self._symbols[name]

    def get_all_symbols(self) -> Dict[str, sp.Symbol]:
        return self._symbols.copy()

    # ── Core Operations ──

    def differentiate(self, expr, var, order: int = 1, name: str = "") -> "DerivationBuilder":
        """求导: d^n(expr)/d(var)^n"""
        result = sp.diff(expr, var, order)
        if name:
            return DerivationBuilder(self, result, name)
        return DerivationBuilder(self, result, f"d^{order}(·)/d({var})^{order}")

    def integrate(self, expr, var, bounds: Optional[tuple] = None, name: str = "") -> "DerivationBuilder":
        """积分: ∫expr d(var) 或定积分"""
        if bounds:
            result = sp.integrate(expr, (var, bounds[0], bounds[1]))
        else:
            result = sp.integrate(expr, var)
        return DerivationBuilder(self, result, name or "integral")

    def solve_equation(self, equation, variable, name: str = "") -> "DerivationBuilder":
        """解方程: equation = 0"""
        result = sp.solve(equation, variable)
        return DerivationBuilder(self, result, name or f"solve for {variable}")

    def solve_system(self, equations: list, variables: list, name: str = "") -> "DerivationBuilder":
        """解方程组"""
        result = sp.solve(equations, variables, dict=True)
        return DerivationBuilder(self, result, name or "solve system")

    def limit(self, expr, var, point, name: str = "") -> "DerivationBuilder":
        """求极限: lim_{var→point} expr"""
        result = sp.limit(expr, var, point)
        return DerivationBuilder(self, result, name or f"limit as {var}→{point}")

    def taylor_expand(self, expr, var, around: float = 0, order: int = 3, name: str = "") -> "DerivationBuilder":
        """泰勒展开"""
        result = sp.series(expr, var, around, order + 1).removeO()
        return DerivationBuilder(self, result, name or f"Taylor({var}, n={order})")

    def log_linearize(self, expr, name: str = "") -> "DerivationBuilder":
        """对数线性化: ln(expr) 展开"""
        result = sp.expand_log(sp.log(expr), force=True)
        return DerivationBuilder(self, result, name or "log-linearized")

    def compute_elasticity(self, expr, var, name: str = "") -> "DerivationBuilder":
        """弹性: (d(expr)/d(var)) * (var/expr)"""
        deriv = sp.diff(expr, var)
        result = sp.simplify(deriv * var / expr)
        return DerivationBuilder(self, result, name or f"elasticity wrt {var}")

    def compute_hessian(self, expr, variables: list, name: str = "Hessian") -> "DerivationBuilder":
        """Hessian矩阵"""
        n = len(variables)
        H = sp.zeros(n)
        for i in range(n):
            for j in range(n):
                H[i, j] = sp.diff(sp.diff(expr, variables[i]), variables[j])
        result = sp.simplify(H)
        return DerivationBuilder(self, result, name)

    def classify_stationary_point(self, hessian, variables: list) -> Dict[str, Any]:
        """
        驻点分类 (对任意Hessian矩阵)。

        Returns:
            {
                'type': 'minimum'|'maximum'|'saddle'|'degenerate'|'indefinite',
                'determinant': ...,
                'trace': ...,
                'eigenvalues': [...],
                'conditions': {...}
            }
        """
        n = hessian.rows
        det = sp.simplify(hessian.det())
        trace = sp.simplify(hessian.trace())

        classification = {
            "determinant": str(det),
            "trace": str(trace),
            "dimension": n,
        }

        if n == 1:
            h11 = hessian[0, 0]
            classification["type"] = "minimum" if sp.simplify(h11) > 0 else "maximum"
            classification["conditions"] = {"SOC": f"h11 = {h11}"}
        elif n == 2:
            h11 = hessian[0, 0]
            classification.update({
                "h11": str(h11),
                "conditions": {
                    "minimum": f"h11 > 0 AND det > 0",
                    "maximum": f"h11 < 0 AND det > 0",
                    "saddle": "det < 0",
                    "degenerate": "det = 0",
                }
            })
            # Try to add eigenvalues info
            try:
                evals = list(hessian.eigenvals())
                classification["eigenvalues"] = [str(e) for e in evals]
            except Exception:
                pass

        return classification

    def verify_identity(self, expr1, expr2, name: str = "") -> Dict[str, Any]:
        """
        验证符号恒等式: expr1 == expr2?

        Returns:
            {'holds': bool, 'difference': ...}
        """
        diff = sp.simplify(expr1 - expr2)
        holds = diff == 0
        return {
            "name": name or "identity_check",
            "holds": holds,
            "difference": str(diff),
            "verified": holds,
        }

    def lambdify(self, expr, variables: list, module: str = "numpy"):
        """将SymPy表达式转为NumPy可调用函数"""
        return sp.lambdify(variables, expr, module)

    def substitute(self, expr, substitutions: dict):
        """代入数值/符号"""
        return expr.subs(substitutions)

    def simplify(self, expr):
        """简化表达式"""
        if self.simplify_aggressively:
            return sp.simplify(expr)
        return expr

    def to_matrix(self, data: list) -> sp.Matrix:
        """创建SymPy矩阵"""
        return sp.Matrix(data)

    # ═══════════════════════════════════════════════════════════
    # ODE / PDE Methods — 微分方程
    # ═══════════════════════════════════════════════════════════

    def classify_ode(self, expr, func, var, name: str = "") -> Dict[str, Any]:
        """
        分类常微分方程。

        Returns:
            {'type': 'separable'|'linear'|'bernoulli'|'exact'|'homogeneous'|..., 'hints': [...]}
        """
        from sympy.solvers.ode import classify_ode as _classify_ode
        try:
            hints = _classify_ode(expr, func)
            return {
                "name": name or "ODE Classification",
                "equation": str(expr),
                "type": hints[0] if hints else "unknown",
                "all_hints": hints,
                "total_methods": len(hints),
            }
        except Exception as e:
            return {"name": name or "ODE Classification", "error": str(e)}

    def solve_ode(self, expr, func, var, hint: str = "default", ics: Optional[dict] = None, name: str = "") -> "DerivationBuilder":
        """
        求解常微分方程: dsolve(expr, func).

        Args:
            expr: ODE 表达式
            func: 未知函数 (sp.Function('f')(x))
            var: 自变量
            hint: 求解方法 ('default' = 自动选择, 或 'separable', 'linear', 'bernoulli' 等)
            ics: 初始条件 {func.subs(var, x0): y0, sp.diff(func, var).subs(var, x0): y0p, ...}
        """
        try:
            if hint == "default":
                result = sp.dsolve(expr, func, ics=ics)
            else:
                result = sp.dsolve(expr, func, hint=hint, ics=ics)
            return DerivationBuilder(self, result, name or f"ODE Solution: {expr}")
        except Exception as e:
            return DerivationBuilder(self, sp.sympify(str(e)), name or f"ODE Error")

    def solve_ode_system(self, equations: list, funcs: list, var, ics: Optional[dict] = None, name: str = "") -> "DerivationBuilder":
        """求解常微分方程组"""
        result = sp.dsolve(equations, funcs, ics=ics)
        return DerivationBuilder(self, result, name or "ODE System Solution")

    def check_ode_solution(self, expr, sol, func, var, name: str = "") -> Dict[str, Any]:
        """
        验证ODE解: checkodesol(ode, sol).

        Returns:
            {'is_solution': bool, 'residual': ..., 'satisfies_ode': bool}
        """
        from sympy.solvers.ode import checkodesol
        try:
            check = checkodesol(expr, sol, func=func)
            # check is (residual_expr, satisfies_bool)
            return {
                "name": name or "ODE Solution Check",
                "is_solution": bool(check[0]) if isinstance(check, tuple) else bool(check),
                "residual": str(sp.simplify(check[1] if len(check) > 1 else check[0]) if isinstance(check, tuple) else check),
                "satisfies_ode": bool(check[0]) if isinstance(check, tuple) else bool(check),
                "verified": bool(check[1]),
            }
        except Exception as e:
            return {"name": name or "ODE Solution Check", "error": str(e), "verified": False}

    def solve_pde(self, expr, func, vars_tuple, name: str = "") -> "DerivationBuilder":
        """求解偏微分方程: pdsolve(expr, func)"""
        try:
            result = sp.pdsolve(expr, func)
            return DerivationBuilder(self, result, name or f"PDE Solution: {expr}")
        except Exception as e:
            return DerivationBuilder(self, sp.sympify(str(e)), name or "PDE Error")

    def classify_pde(self, expr, func, name: str = "") -> Dict[str, Any]:
        """分类偏微分方程"""
        from sympy.solvers.pde import classify_pde as _classify_pde
        try:
            hints = _classify_pde(expr, func)
            return {
                "name": name or "PDE Classification",
                "equation": str(expr),
                "type": hints[0] if hints else "unknown",
                "all_hints": hints,
            }
        except Exception as e:
            return {"name": name or "PDE Classification", "error": str(e)}

    # ═══════════════════════════════════════════════════════════
    # Analysis Methods — 分析学
    # ═══════════════════════════════════════════════════════════

    def series_expansion(self, expr, var, around: float = 0, order: int = 6, name: str = "") -> "DerivationBuilder":
        """级数展开: series(expr, var, around, order)"""
        result = sp.series(expr, var, around, order + 1).removeO()
        return DerivationBuilder(self, result, name or f"Series of {expr} at {var}={around}")

    def fourier_series(self, func, var, period: tuple, n_terms: int = 5, name: str = "") -> Dict[str, Any]:
        """
        傅里叶级数展开。

        Args:
            func: 周期函数
            period: (lower, upper) 一个完整周期
        """
        try:
            fs = sp.fourier_series(func, (var, period[0], period[1]))
            truncated = fs.truncate(n_terms)
            return {
                "name": name or "Fourier Series",
                "function": str(func),
                "period": period,
                "a0": str(fs.a0),
                "an": str(fs.an),
                "bn": str(fs.bn),
                f"truncated_{n_terms}_terms": str(truncated),
            }
        except Exception as e:
            return {"name": name or "Fourier Series", "error": str(e)}

    def laplace_transform(self, func, t_var, s_var, name: str = "") -> "DerivationBuilder":
        """拉普拉斯变换"""
        result = sp.laplace_transform(func, t_var, s_var, noconds=True)
        return DerivationBuilder(self, result, name or f"L{{{func}}}")

    def inverse_laplace_transform(self, expr, s_var, t_var, name: str = "") -> "DerivationBuilder":
        """逆拉普拉斯变换"""
        result = sp.inverse_laplace_transform(expr, s_var, t_var, noconds=True)
        return DerivationBuilder(self, result, name or f"L⁻¹{{{expr}}}")

    def fourier_transform(self, func, x_var, k_var, name: str = "") -> "DerivationBuilder":
        """傅里叶变换"""
        result = sp.fourier_transform(func, x_var, k_var, noconds=True)
        return DerivationBuilder(self, result, name or f"F{{{func}}}")

    def continuous_domain(self, expr, var, domain=sp.S.Reals, name: str = "") -> Dict[str, Any]:
        """求函数连续域"""
        try:
            cd = sp.calculus.util.continuous_domain(expr, var, domain)
            return {
                "name": name or "Continuous Domain",
                "expression": str(expr),
                "domain": str(cd),
            }
        except Exception as e:
            return {"name": name or "Continuous Domain", "error": str(e)}

    def singularities(self, expr, var, name: str = "") -> Dict[str, Any]:
        """求函数奇点"""
        try:
            sings = sp.calculus.singularities(expr, var)
            return {
                "name": name or "Singularities",
                "expression": str(expr),
                "singularities": [str(s) for s in sings] if sings else [],
                "is_analytic_on_reals": len(sings) == 0 if sings else True,
            }
        except Exception as e:
            return {"name": name or "Singularities", "error": str(e)}

    def sum_series(self, expr, var, limits: tuple, name: str = "") -> "DerivationBuilder":
        """求和 Σ_{var=limits[0]}^{limits[1]} expr"""
        result = sp.summation(expr, (var, limits[0], limits[1]))
        return DerivationBuilder(self, result, name or f"Sum of {expr}")

    def product_series(self, expr, var, limits: tuple, name: str = "") -> "DerivationBuilder":
        """求积 Π"""
        result = sp.product(expr, (var, limits[0], limits[1]))
        return DerivationBuilder(self, result, name or f"Product of {expr}")

    def convergence_test(self, series_expr, var, name: str = "") -> Dict[str, Any]:
        """
        级数收敛性检验 (Ratio Test / Root Test).

        利用 limit |a_{n+1}/a_n| 判断收敛半径。
        """
        try:
            # Ratio test: lim_{n→∞} |a_{n+1} / a_n|
            n = var
            ratio = sp.simplify(series_expr.subs(n, n + 1) / series_expr)
            limit_val = sp.limit(sp.Abs(ratio), n, sp.oo)

            if limit_val == sp.oo:
                verdict = "Divergent (ratio → ∞)"
            elif limit_val == 0:
                verdict = "Absolutely Convergent (ratio → 0)"
            elif limit_val < 1:
                verdict = f"Absolutely Convergent (ratio = {limit_val} < 1)"
            elif limit_val > 1:
                verdict = f"Divergent (ratio = {limit_val} > 1)"
            else:
                verdict = "Inconclusive by Ratio Test (ratio = 1)"

            return {
                "name": name or "Convergence Test",
                "series_term": str(series_expr),
                "test": "Ratio Test",
                "limit_value": str(limit_val),
                "verdict": verdict,
            }
        except Exception as e:
            return {"name": name or "Convergence Test", "error": str(e)}

    def asymptotic_behavior(self, expr, var, point=sp.oo, name: str = "") -> "DerivationBuilder":
        """渐近行为分析: limit + 主导项"""
        result = sp.limit(expr, var, point)
        return DerivationBuilder(self, result, name or f"Asymptotic: {expr} as {var}→{point}")

    # ── History ──

    def get_history(self) -> List[DerivationResult]:
        return self._history

    def clear_history(self):
        self._history = []


class DerivationBuilder:
    """
    推导构建器 — 支持链式调用的 Fluent API。

    用法:
        result = (engine.differentiate(Y, N)
                  .simplify()
                  .to_latex()
                  .with_condition("N > 0", "interior")
                  .evaluate({N: 100, alpha: 0.3, tau: 1.0, A: 1.0})
                  .build())
    """

    def __init__(self, engine: SymbolicEngine, expression, name: str):
        self._engine = engine
        self._expr = expression
        self._name = name
        self._steps: List[str] = []
        self._conditions: Dict[str, str] = {}
        self._metadata: Dict[str, Any] = {}
        self._latex: Optional[str] = None
        self._simplified: Optional[Any] = None
        self._numerical: Optional[float] = None

    def simplify(self) -> "DerivationBuilder":
        self._simplified = self._engine.simplify(self._expr)
        self._steps.append(f"Simplified: {self._simplified}")
        return self

    def to_latex(self) -> "DerivationBuilder":
        expr = self._simplified if self._simplified is not None else self._expr
        try:
            self._latex = sp.latex(expr)
        except Exception:
            self._latex = str(expr)
        return self

    def with_condition(self, condition: str, label: str = "") -> "DerivationBuilder":
        self._conditions[label or f"cond_{len(self._conditions)}"] = condition
        return self

    def with_step(self, description: str) -> "DerivationBuilder":
        self._steps.append(description)
        return self

    def with_metadata(self, **kwargs) -> "DerivationBuilder":
        self._metadata.update(kwargs)
        return self

    def evaluate(self, substitutions: dict) -> "DerivationBuilder":
        """数值评估"""
        expr = self._simplified if self._simplified is not None else self._expr
        try:
            result = float(expr.subs(substitutions))
            self._numerical = result
            self._steps.append(f"Evaluated at {substitutions}: {result}")
        except Exception as e:
            self._steps.append(f"Evaluation failed: {e}")
        return self

    def build(self) -> DerivationResult:
        expr = self._simplified if self._simplified is not None else self._expr
        result = DerivationResult(
            name=self._name,
            expression_raw=str(self._expr),
            expression_latex=self._latex or str(expr),
            expression_simplified=str(expr),
            numerical_value=self._numerical,
            steps=self._steps,
            conditions=self._conditions,
            metadata=self._metadata,
        )
        self._engine._history.append(result)
        return result

    @property
    def raw(self):
        """获取原始SymPy表达式 (用于进一步操作)"""
        return self._simplified if self._simplified is not None else self._expr
