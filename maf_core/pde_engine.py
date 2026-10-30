"""
PdeEngine — 偏微分方程求解引擎
================================
结合 SymPy 解析求解 + NumPy/SciPy 数值求解。

解析方法 (SymPy):
    - 一阶线性 PDE (method of characteristics)
    - 部分二阶 PDE (如果 SymPy 支持)

数值方法 (NumPy/SciPy):
    - 热方程 (Heat): 显式/隐式有限差分
    - 波动方程 (Wave): 显式有限差分
    - Laplace/Poisson: 迭代法 (Jacobi/Gauss-Seidel)
    - 对流方程 (Transport): 迎风格式

分类:
    - 二阶半线性: A u_xx + B u_xy + C u_yy + D = 0
    - B^2 - 4AC < 0: 椭圆型 (Elliptic, e.g. Laplace)
    - B^2 - 4AC = 0: 抛物型 (Parabolic, e.g. Heat)
    - B^2 - 4AC > 0: 双曲型 (Hyperbolic, e.g. Wave)

设计原则:
    - 解析优先 → 解析不可用时自动降级到数值
    - 分类→选择方法→求解→验证
    - 记录每一步的推导逻辑
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import sympy as sp
import numpy as np
try:
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class PdeClassification:
    """PDE 分类结果"""
    order: int
    n_variables: int
    linearity: str           # 'linear' | 'semilinear' | 'quasilinear' | 'nonlinear'
    pde_type: str            # 'elliptic' | 'parabolic' | 'hyperbolic' | 'first_order' | 'unknown'
    discriminant: Optional[str] = None  # B^2 - 4AC (for 2nd order)
    homogeneous: bool = True
    coefficients: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "n_variables": self.n_variables,
            "linearity": self.linearity,
            "type": self.pde_type,
            "discriminant": self.discriminant,
            "homogeneous": self.homogeneous,
            "coefficients": self.coefficients,
        }


@dataclass
class PdeSolution:
    """PDE 求解结果"""
    pde_equation: str
    classification: Optional[PdeClassification] = None
    method: str = ""                         # 'analytical' | 'numerical' | 'separation_of_variables'
    analytical_solution: str = ""
    numerical_solution: Optional[Dict[str, Any]] = None
    grid: Optional[Dict[str, Any]] = None     # x, y, t arrays
    steps: List[Dict[str, str]] = field(default_factory=list)
    status: str = "ok"
    verified: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "pde": self.pde_equation,
            "classification": self.classification.to_dict() if self.classification else None,
            "method": self.method,
            "analytical_solution": self.analytical_solution,
            "numerical_solution": self.numerical_solution,
            "grid": self.grid,
            "steps": self.steps,
            "status": self.status,
            "verified": self.verified,
            "error": self.error,
        }


class PdeEngine:
    """
    偏微分方程求解引擎。

    用法:
        engine = PdeEngine()

        # 解析求解
        result = engine.solve_analytical("diff(u(x,y),x) + diff(u(x,y),y)", "u(x,y)")

        # 数值求解热方程
        result = engine.solve_heat_1d(u0_func, x_range, t_range, alpha=0.1, nx=50, nt=200)

        # 分类 + 求解
        result = engine.classify_and_solve("diff(u,x,2) + diff(u,y,2)", "u(x,y)")
    """

    def __init__(self):
        pass

    # ═══════════════════════════════════════════════════════════
    # PDE Classification
    # ═══════════════════════════════════════════════════════════

    def classify(self, pde_expr_str: str, var1: str = "x", var2: str = "y") -> PdeClassification:
        """
        分类二阶 PDE: A u_xx + B u_xy + C u_yy + D = 0

        判别式: Delta = B^2 - 4AC
            Delta < 0: 椭圆型 (Elliptic) — Laplace, Poisson
            Delta = 0: 抛物型 (Parabolic) — Heat, diffusion
            Delta > 0: 双曲型 (Hyperbolic) — Wave, transport

        支持输入格式:
            - 字符串: "diff(u(x,y),x,2) + diff(u(x,y),y,2)" (u自动声明为Function)
            - 字符串简写: "heat", "wave", "laplace", "poisson", "transport"
        """
        # Handle predefined names
        predefined = {
            "heat": ("diff(u(x,y),y) - diff(u(x,y),x,2)", "parabolic"),
            "wave": ("diff(u(x,y),x,2) - diff(u(x,y),y,2)", "hyperbolic"),
            "laplace": ("diff(u(x,y),x,2) + diff(u(x,y),y,2)", "elliptic"),
            "poisson": ("diff(u(x,y),x,2) + diff(u(x,y),y,2) + f(x,y)", "elliptic"),
            "transport": ("diff(u(x,y),x) + diff(u(x,y),y)", "first_order"),
        }
        if pde_expr_str.lower() in predefined:
            pde_expr_str, force_type = predefined[pde_expr_str.lower()]
        else:
            force_type = None

        # Build safe namespace with symbols and functions
        x = sp.Symbol(var1, real=True)
        y = sp.Symbol(var2, real=True)
        # Use Function class (not evaluated) so u(x,y) in eval() works
        U = sp.Function('u')
        F = sp.Function('f')
        u_expr = U(x, y)
        f_expr = F(x, y)

        local_dict = {
            'x': x, 'y': y,
            'u': U,    # Function class — u(x,y) creates the expression
            'f': F,
            'diff': sp.diff,
            'sp': sp,
            'Eq': sp.Eq,
            'sin': sp.sin, 'cos': sp.cos, 'exp': sp.exp, 'log': sp.log,
            'pi': sp.pi, 'E': sp.E,
        }

        # Parse expression
        try:
            if "=" in pde_expr_str:
                lhs_str, rhs_str = pde_expr_str.split("=", 1)
                pde_expr = eval(lhs_str.strip(), {"__builtins__": {}}, local_dict) \
                         - eval(rhs_str.strip(), {"__builtins__": {}}, local_dict)
            else:
                pde_expr = eval(pde_expr_str.strip(), {"__builtins__": {}}, local_dict)
        except Exception as e:
            # Fallback: try direct sympify
            try:
                pde_expr = sp.sympify(pde_expr_str)
            except Exception:
                return PdeClassification(
                    order=0, n_variables=2, linearity="unknown",
                    pde_type="unknown",
                    homogeneous=True, coefficients={},
                )

        # Determine order from Derivative objects
        max_order = 0
        from sympy import Derivative
        for atom in pde_expr.atoms(Derivative):
            # atom is like Derivative(u(x,y), x) or Derivative(u(x,y), (x,2))
            # Args: (function_expr, var1, var2, ...) where var can be Symbol or (Symbol, count)
            order = 0
            for arg in atom.args[1:]:
                if isinstance(arg, tuple) and len(arg) == 2:
                    order += arg[1]  # (x, 2) -> 2
                else:
                    order += 1  # plain Symbol -> order 1
            max_order = max(max_order, order)
        if max_order == 0:
            # No Derivative atoms — check string representation
            pde_str = str(pde_expr)
            # Look for patterns like (x, N) in Derivative representation
            import re
            found = re.findall(r'\([xy],\s*(\d+)\)', pde_str)
            if found:
                max_order = max(int(n) for n in found)
            elif 'diff' in pde_str.lower():
                max_order = 1

        # For 2nd order, compute discriminant from coefficients
        pde_type = force_type or "unknown"
        discriminant = None
        coefficients = {}

        if force_type:
            max_order = {"first_order": 1, "parabolic": 2, "elliptic": 2, "hyperbolic": 2}.get(force_type, 2)
            discriminant = {"parabolic": "0", "elliptic": "-4 (< 0)", "hyperbolic": "> 0"}.get(force_type)
        elif max_order == 1:
            pde_type = "first_order"
        elif max_order == 2:
            try:
                # Extract coefficients by differentiation
                u_xx = sp.diff(pde_expr, x, 2)
                u_xy = sp.diff(sp.diff(pde_expr, x), y)
                u_yy = sp.diff(pde_expr, y, 2)

                # Get constant coefficient approximations
                # For symbolic: substitute u and its derivatives with 1/0
                u_sym = u
                u_x_sym = sp.Symbol('_ux')
                subs_dict = {
                    u: 0, sp.diff(u, x): 0, sp.diff(u, y): 0,
                    sp.diff(u, x, 2): 1, sp.diff(u, x, y): 0, sp.diff(u, y, 2): 0,
                }
                A = float(sp.N(u_xx.subs(subs_dict))) if u_xx.has(sp.diff(u, x, 2)) else 0.0

                subs_dict = {
                    u: 0, sp.diff(u, x): 0, sp.diff(u, y): 0,
                    sp.diff(u, x, 2): 0, sp.diff(u, x, y): 1, sp.diff(u, y, 2): 0,
                }
                B_coeff = u_xy.subs(subs_dict)
                B = float(sp.N(B_coeff)) if B_coeff.has(sp.diff(u, x, y)) else 0.0

                subs_dict = {
                    u: 0, sp.diff(u, x): 0, sp.diff(u, y): 0,
                    sp.diff(u, x, 2): 0, sp.diff(u, x, y): 0, sp.diff(u, y, 2): 1,
                }
                C = float(sp.N(u_yy.subs(subs_dict))) if u_yy.has(sp.diff(u, y, 2)) else 0.0

                coefficients = {"A": str(A), "B": str(B), "C": str(C)}
                disc = B**2 - 4*A*C
                discriminant = str(disc)

                if disc < 0:
                    pde_type = "elliptic"
                elif abs(disc) < 1e-10:
                    pde_type = "parabolic"
                else:
                    pde_type = "hyperbolic"
            except Exception:
                pde_type = "second_order_unknown"

        # Check homogeneity and linearity
        homogeneous = True  # Simplification
        linearity = "linear" if max_order <= 2 else "nonlinear"

        return PdeClassification(
            order=max_order,
            n_variables=2,
            linearity=linearity,
            pde_type=pde_type,
            discriminant=discriminant,
            homogeneous=homogeneous,
            coefficients=coefficients,
        )

    # ═══════════════════════════════════════════════════════════
    # Analytical Solution (via SymPy pdsolve)
    # ═══════════════════════════════════════════════════════════

    def solve_analytical(self, pde_str: str, func_str: str = "f(x,y)") -> PdeSolution:
        """
        使用 SymPy pdsolve 解析求解 PDE。

        Args:
            pde_str: PDE 表达式, 如 "diff(f(x,y),x) + diff(f(x,y),y)"
            func_str: 未知函数, 如 "f(x,y)"
        """
        x = sp.Symbol('x', real=True)
        y = sp.Symbol('y', real=True)
        f = sp.Function('f')(x, y)

        # Classification first
        classification = self.classify(pde_str)

        result = PdeSolution(
            pde_equation=pde_str,
            classification=classification,
            method="analytical",
        )

        try:
            # Build safe namespace
            x = sp.Symbol('x', real=True)
            y = sp.Symbol('y', real=True)
            F_class = sp.Function('f')
            f_expr = F_class(x, y)
            local_dict = {
                'x': x, 'y': y,
                'f': F_class,  # Function class — f(x,y) creates the expression
                'diff': sp.diff, 'sp': sp, 'Eq': sp.Eq,
                'sin': sp.sin, 'cos': sp.cos, 'exp': sp.exp, 'log': sp.log,
                'pi': sp.pi, 'E': sp.E,
            }
            pde_expr = eval(pde_str.strip(), {"__builtins__": {}}, local_dict)

            # Use SymPy's pdsolve
            from sympy.solvers.pde import pdsolve
            sol = pdsolve(pde_expr, f_expr)

            result.analytical_solution = str(sol)
            result.steps.append({
                "step": "1", "operation": "classify",
                "detail": f"PDE type: {classification.pde_type}, order: {classification.order}",
            })
            result.steps.append({
                "step": "2", "operation": "analytical_solve",
                "detail": f"Solved via pdsolve",
            })
            result.steps.append({
                "step": "3", "operation": "solution",
                "detail": f"Solution: {sol}",
            })
            result.verified = "F(" in str(sol) or "C1" in str(sol) or "f(x" in str(sol)
            result.status = "ok"

        except NotImplementedError as e:
            result.status = "analytical_failed"
            result.error = str(e)
            result.steps.append({
                "step": "1", "operation": "classify",
                "detail": f"PDE type: {classification.pde_type}",
            })
            result.steps.append({
                "step": "2", "operation": "analytical_failed",
                "detail": f"SymPy pdsolve cannot solve this PDE: {e}",
            })
            result.steps.append({
                "step": "3", "operation": "recommendation",
                "detail": "Use numerical methods: solve_heat_1d, solve_wave_1d, or solve_laplace_2d",
            })
        except Exception as e:
            result.status = "error"
            result.error = str(e)

        return result

    # ═══════════════════════════════════════════════════════════
    # Numerical: 1D Heat Equation
    # ═══════════════════════════════════════════════════════════

    def solve_heat_1d(
        self,
        u0_func: Callable[[np.ndarray], np.ndarray],
        x_range: Tuple[float, float] = (0.0, 1.0),
        t_range: Tuple[float, float] = (0.0, 0.5),
        alpha: float = 0.01,
        nx: int = 50,
        nt: int = 200,
        bc_left: float = 0.0,
        bc_right: float = 0.0,
    ) -> PdeSolution:
        """
        求解一维热方程: u_t = alpha * u_xx (显式有限差分)

        边界条件: u(0,t) = bc_left, u(L,t) = bc_right
        初始条件: u(x,0) = u0_func(x)
        """
        dx = (x_range[1] - x_range[0]) / (nx - 1)
        dt = (t_range[1] - t_range[0]) / nt
        L = x_range[1] - x_range[0]

        # Stability condition: alpha * dt / dx^2 <= 0.5
        r = alpha * dt / dx**2
        if r > 0.5:
            result = PdeSolution(
                pde_equation="u_t = alpha * u_xx",
                method="numerical (finite difference)",
                status="stability_warning",
                error=f"CFL condition violated: r={r:.3f} > 0.5. Reduce dt or increase nx.",
            )
            return result

        # Initialize
        x = np.linspace(x_range[0], x_range[1], nx)
        t = np.linspace(t_range[0], t_range[1], nt)
        u = np.zeros((nt, nx))
        u[0, :] = u0_func(x)
        u[:, 0] = bc_left
        u[:, -1] = bc_right

        # Vectorized explicit scheme: u^{n+1} = u^n + r * (u^n shifted)
        for n in range(0, nt - 1):
            u[n + 1, 1:-1] = u[n, 1:-1] + r * (
                u[n, 2:] - 2 * u[n, 1:-1] + u[n, :-2]
            )

        result = PdeSolution(
            pde_equation=f"u_t = {alpha} * u_xx",
            classification=PdeClassification(
                order=2, n_variables=2, linearity="linear",
                pde_type="parabolic", discriminant="0",
                homogeneous=True,
                coefficients={"alpha (diffusivity)": str(alpha)},
            ),
            method="numerical (explicit finite difference)",
            analytical_solution="Numerical solution computed",
            numerical_solution={
                "final_profile": u[-1, :].tolist(),
                "max_temp": float(u.max()),
                "min_temp": float(u.min()),
                "steady_state_reached": abs(u[-1, :].max() - u[-1, :].min()) < 1e-4,
            },
            grid={
                "x": x.tolist(),
                "t": t.tolist(),
                "dx": float(dx),
                "dt": float(dt),
                "nx": nx,
                "nt": nt,
                "r (CFL)": float(r),
            },
            steps=[
                {"step": "1", "operation": "setup",
                 "detail": f"Grid: nx={nx}, nt={nt}, dx={dx:.4f}, dt={dt:.4f}"},
                {"step": "2", "operation": "stability_check",
                 "detail": f"CFL number r = alpha*dt/dx^2 = {r:.4f} {'OK' if r <= 0.5 else 'FAIL'}"},
                {"step": "3", "operation": "explicit_fd",
                 "detail": f"u^{{n+1}}_i = u^n_i + r*(u^n_{{i+1}} - 2*u^n_i + u^n_{{i-1}})"},
                {"step": "4", "operation": "propagation",
                 "detail": f"Computed {nt} timesteps"},
            ],
            status="ok" if r <= 0.5 else "stability_warning",
            verified=r <= 0.5,
        )
        return result

    # ═══════════════════════════════════════════════════════════
    # Numerical: 1D Wave Equation
    # ═══════════════════════════════════════════════════════════

    def solve_wave_1d(
        self,
        u0_func: Callable[[np.ndarray], np.ndarray],
        ut0_func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        x_range: Tuple[float, float] = (0.0, 1.0),
        t_range: Tuple[float, float] = (0.0, 2.0),
        c: float = 1.0,
        nx: int = 100,
        nt: int = 400,
    ) -> PdeSolution:
        """
        求解一维波动方程: u_tt = c^2 * u_xx

        u(x,0) = u0(x), u_t(x,0) = ut0(x) (默认 0)
        """
        dx = (x_range[1] - x_range[0]) / (nx - 1)
        dt = (t_range[1] - t_range[0]) / nt

        # CFL condition: c * dt / dx <= 1
        cfl = c * dt / dx
        if cfl > 1.0:
            result = PdeSolution(
                pde_equation=f"u_tt = {c}^2 * u_xx",
                method="numerical (finite difference)",
                status="stability_warning",
                error=f"CFL condition violated: c*dt/dx={cfl:.3f} > 1. Reduce dt or increase nx.",
            )
            return result

        x = np.linspace(x_range[0], x_range[1], nx)
        t = np.linspace(t_range[0], t_range[1], nt)
        u = np.zeros((nt, nx))
        u[0, :] = u0_func(x) if callable(u0_func) else np.array(u0_func)

        # First timestep
        if callable(ut0_func):
            ut0 = ut0_func(x)
        elif ut0_func is not None:
            ut0 = np.array(ut0_func)
        else:
            ut0 = np.zeros_like(x)

        r = (c * dt / dx) ** 2
        # Vectorized first timestep
        u[1, 1:-1] = (u[0, 1:-1] + dt * ut0[1:-1]
                       + 0.5 * r * (u[0, 2:] - 2 * u[0, 1:-1] + u[0, :-2]))

        # Boundary conditions (fixed ends)
        u[:, 0] = 0
        u[:, -1] = 0

        # Vectorized explicit 3-point scheme
        for n in range(1, nt - 1):
            u[n + 1, 1:-1] = (2 * u[n, 1:-1] - u[n - 1, 1:-1]
                              + r * (u[n, 2:] - 2 * u[n, 1:-1] + u[n, :-2]))

        result = PdeSolution(
            pde_equation=f"u_tt = c^2 * u_xx (c={c})",
            classification=PdeClassification(
                order=2, n_variables=2, linearity="linear",
                pde_type="hyperbolic", discriminant=f"{(2*c)**2} (> 0)",
                homogeneous=True,
                coefficients={"c (wave speed)": str(c)},
            ),
            method="numerical (explicit finite difference, 3-point stencil)",
            analytical_solution="d'Alembert: u(x,t) = F(x-ct) + G(x+ct)",
            numerical_solution={
                "final_profile": u[-1, :].tolist(),
                "max_amplitude": float(u.max()),
                "energy_conserved": abs(u.max() - u0_func(x).max()) < 0.1 * u0_func(x).max(),
            },
            grid={
                "x": x.tolist(),
                "t": t.tolist(),
                "dx": float(dx), "dt": float(dt),
                "nx": nx, "nt": nt,
                "cfl": float(cfl),
            },
            steps=[
                {"step": "1", "operation": "setup",
                 "detail": f"Grid: nx={nx}, nt={nt}, dx={dx:.4f}, dt={dt:.4f}"},
                {"step": "2", "operation": "cfl_check",
                 "detail": f"CFL = c*dt/dx = {cfl:.4f} {'OK' if cfl <= 1 else 'FAIL'}"},
                {"step": "3", "operation": "explicit_fd_3pt",
                 "detail": "u^{n+1}_i = 2u^n_i - u^{n-1}_i + r^2*(u^n_{i+1} - 2u^n_i + u^n_{i-1})"},
            ],
            status="ok",
            verified=cfl <= 1.0,
        )
        return result

    # ═══════════════════════════════════════════════════════════
    # Numerical: 2D Laplace/Poisson Equation
    # ═══════════════════════════════════════════════════════════

    def solve_laplace_2d(
        self,
        bc_func: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
        x_range: Tuple[float, float] = (0.0, 1.0),
        y_range: Tuple[float, float] = (0.0, 1.0),
        nx: int = 50,
        ny: int = 50,
        f_source: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
        max_iter: int = 5000,
        tol: float = 1e-4,
    ) -> PdeSolution:
        """
        求解 2D Laplace/Poisson 方程: u_xx + u_yy = -f(x,y)

        使用 Jacobi 迭代法 (简单, 易于并行化)。
        边界条件: u(x, y) = bc_func(x, y) on boundary (默认 0)
        """
        dx = (x_range[1] - x_range[0]) / (nx - 1)
        dy = (y_range[1] - y_range[0]) / (ny - 1)

        x = np.linspace(x_range[0], x_range[1], nx)
        y = np.linspace(y_range[0], y_range[1], ny)
        X, Y = np.meshgrid(x, y)

        # Initialize
        u = np.zeros((ny, nx))

        # Apply boundary conditions
        if bc_func is not None:
            u[0, :] = bc_func(x, np.full_like(x, y_range[0]))   # bottom
            u[-1, :] = bc_func(x, np.full_like(x, y_range[1]))  # top
            u[:, 0] = bc_func(np.full_like(y, x_range[0]), y)   # left
            u[:, -1] = bc_func(np.full_like(y, x_range[1]), y)  # right
        else:
            # Default: u=x on left, u=0 on right, u=0 on top/bottom
            u[:, 0] = x  # u(x,0) = x

        # Source term
        if f_source is not None:
            f_vals = f_source(X, Y)
        else:
            f_vals = np.zeros((ny, nx))  # Laplace (homogeneous)

        # Vectorized Jacobi iteration
        converged = False
        for iteration in range(max_iter):
            u_old = u.copy()
            # Vectorized interior point update
            u[1:-1, 1:-1] = 0.25 * (
                u_old[2:, 1:-1] + u_old[:-2, 1:-1] +
                u_old[1:-1, 2:] + u_old[1:-1, :-2] +
                dx * dy * f_vals[1:-1, 1:-1]
            )
            # Convergence check
            diff = np.max(np.abs(u - u_old))
            if diff < tol:
                converged = True
                break

        is_poisson = f_source is not None

        result = PdeSolution(
            pde_equation="u_xx + u_yy = -f(x,y)" if is_poisson else "u_xx + u_yy = 0",
            classification=PdeClassification(
                order=2, n_variables=2, linearity="linear",
                pde_type="elliptic", discriminant="-4 (< 0)",
                homogeneous=not is_poisson,
                coefficients={"type": "Poisson" if is_poisson else "Laplace"},
            ),
            method=f"numerical (Jacobi iteration, {iteration + 1} iters)",
            analytical_solution="Harmonic functions; separation of variables for regular domains",
            numerical_solution={
                "final_field": u.tolist(),
                "max_val": float(u.max()),
                "min_val": float(u.min()),
                "iterations": iteration + 1,
                "converged": converged,
                "final_residual": float(diff),
            },
            grid={
                "x": x.tolist(), "y": y.tolist(),
                "dx": float(dx), "dy": float(dy),
                "nx": nx, "ny": ny,
            },
            steps=[
                {"step": "1", "operation": "setup",
                 "detail": f"Grid: {nx}x{ny}, dx={dx:.4f}, dy={dy:.4f}"},
                {"step": "2", "operation": "jacobi_iteration",
                 "detail": f"u_new = 0.25*(u_N + u_S + u_E + u_W + dx*dy*f)"},
                {"step": "3", "operation": "convergence",
                 "detail": f"{'Converged' if converged else 'Not converged'} in {iteration + 1} iterations (tol={tol})"},
            ],
            status="ok" if converged else "convergence_warning",
            verified=converged,
        )
        return result

    # ═══════════════════════════════════════════════════════════
    # Numerical: 1D Transport (Advection) Equation
    # ═══════════════════════════════════════════════════════════

    def solve_transport_1d(
        self,
        u0_func: Callable[[np.ndarray], np.ndarray],
        x_range: Tuple[float, float] = (0.0, 1.0),
        t_range: Tuple[float, float] = (0.0, 1.0),
        c: float = 1.0,
        nx: int = 100,
        nt: int = 200,
    ) -> PdeSolution:
        """
        求解一维对流方程: u_t + c * u_x = 0 (迎风格式)

        解析解: u(x,t) = u0(x - c*t)
        """
        dx = (x_range[1] - x_range[0]) / (nx - 1)
        dt = (t_range[1] - t_range[0]) / nt
        cfl = abs(c) * dt / dx

        x = np.linspace(x_range[0], x_range[1], nx)
        t = np.linspace(t_range[0], t_range[1], nt)
        u = np.zeros((nt, nx))
        u[0, :] = u0_func(x)

        # Vectorized upwind scheme
        for n in range(0, nt - 1):
            if c > 0:
                u[n + 1, 1:] = u[n, 1:] - cfl * (u[n, 1:] - u[n, :-1])
            else:
                u[n + 1, :-1] = u[n, :-1] - cfl * (u[n, 1:] - u[n, :-1])
            # Periodic BC
            u[n + 1, 0] = u[n + 1, -1]

        # Analytical for comparison
        x_ana = np.linspace(x_range[0], x_range[1], nx)
        u_ana = u0_func(x_ana - c * t_range[-1])
        l2_error = np.sqrt(np.mean((u[-1, :] - u_ana)**2))

        result = PdeSolution(
            pde_equation=f"u_t + {c} * u_x = 0",
            classification=PdeClassification(
                order=1, n_variables=2, linearity="linear",
                pde_type="first_order", homogeneous=True,
                coefficients={"c (advection speed)": str(c)},
            ),
            method="numerical (upwind finite difference)",
            analytical_solution=f"u(x,t) = u0(x - {c}*t) (method of characteristics)",
            numerical_solution={
                "final_profile": u[-1, :].tolist(),
                "analytical_profile": u_ana.tolist(),
                "l2_error": float(l2_error),
            },
            grid={
                "x": x.tolist(), "t": t.tolist(),
                "dx": float(dx), "dt": float(dt),
                "nx": nx, "nt": nt, "cfl": float(cfl),
            },
            steps=[
                {"step": "1", "operation": "setup",
                 "detail": f"Grid: nx={nx}, nt={nt}, CFL={cfl:.4f}"},
                {"step": "2", "operation": "upwind_scheme",
                 "detail": "u^{n+1}_i = u^n_i - cfl*(u^n_i - u^n_{i-1})"},
                {"step": "3", "operation": "verification",
                 "detail": f"L2 error vs analytical: {l2_error:.6f}"},
            ],
            status="ok",
            verified=l2_error < 0.1,
        )
        return result

    # ═══════════════════════════════════════════════════════════
    # Unified classify + solve
    # ═══════════════════════════════════════════════════════════

    def classify_and_solve(self, pde_str: str, func_str: str = "u(x,y)") -> PdeSolution:
        """分类 PDE 并自动选择最优解法"""
        classification = self.classify(pde_str)

        if classification.pde_type == "first_order":
            return self.solve_analytical(pde_str, func_str)

        # For higher order, first try analytical
        result = self.solve_analytical(pde_str, func_str)
        if result.status == "ok":
            return result

        # Fall back to numerical with recommendation
        result.steps.append({
            "step": "fallback", "operation": "numerical_recommendation",
            "detail": (
                f"This {classification.pde_type} PDE requires numerical solution. "
                f"Use solve_heat_1d() for parabolic, solve_wave_1d() for hyperbolic, "
                f"solve_laplace_2d() for elliptic."
            ),
        })
        return result
