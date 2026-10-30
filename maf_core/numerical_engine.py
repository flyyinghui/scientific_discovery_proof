"""
NumericalEngine — 通用数值计算引擎
====================================
基于 NumPy/SciPy，独立于特定数学模型。

核心能力:
    - grid_search: 参数网格搜索
    - monte_carlo_sample: 蒙特卡洛参数采样
    - optimize: 数值优化（最小化/最大化）
    - compute_turning_point: 拐点数值计算
    - delta_method_se: Delta方法标准误
    - distribution_stats: 分布统计量
"""

import json
import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np
from scipy import optimize, stats


@dataclass
class NumericalResult:
    """数值计算结果"""
    name: str
    n_samples: int = 0
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    ci_95: Tuple[float, float] = (0, 0)
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "n_samples": self.n_samples,
            "mean": self.mean,
            "median": self.median,
            "std": self.std,
            "ci_95": list(self.ci_95),
            "min": self.min_val,
            "max": self.max_val,
            "metadata": self.metadata,
        }


class NumericalEngine:
    """
    通用数值计算引擎。
    """

    def __init__(self, default_seed: int = 42):
        self.default_seed = default_seed
        np.random.seed(default_seed)

    def set_seed(self, seed: int):
        np.random.seed(seed)

    # ── Grid Search ──

    def grid_search(
        self,
        func: Callable,
        param_ranges: Dict[str, Tuple[float, float]],
        n_points: int = 50,
        n_dims: int = 2,
    ) -> Dict[str, Any]:
        """
        参数空间网格搜索。

        Args:
            func: 目标函数 f(param1, param2, ...)
            param_ranges: {'param1': (min, max), ...}
            n_points: 每维度点数
            n_dims: 前n_dims个参数做网格，其余取中值

        Returns:
            {'grid': meshgrids, 'values': 函数值数组, 'optimum': 最优值位置}
        """
        keys = list(param_ranges.keys())
        grid_params = keys[:n_dims]
        fixed_params = keys[n_dims:]

        grids = []
        for key in grid_params:
            lo, hi = param_ranges[key]
            grids.append(np.linspace(lo, hi, n_points))

        meshes = np.meshgrid(*grids, indexing="ij")
        values = np.zeros_like(meshes[0])

        fixed_vals = {
            k: (param_ranges[k][0] + param_ranges[k][1]) / 2
            for k in fixed_params
        }

        for idx in np.ndindex(meshes[0].shape):
            kw = {grid_params[i]: meshes[i][idx] for i in range(len(grid_params))}
            kw.update(fixed_vals)
            values[idx] = func(**kw)

        opt_idx = np.unravel_index(
            np.argmin(values) if "min" in str(func) else np.argmax(values),
            values.shape
        )
        optimum = {grid_params[i]: meshes[i][opt_idx] for i in range(len(grid_params))}
        optimum["value"] = float(values[opt_idx])

        return {
            "grids": {k: v.tolist() for k, v in zip(grid_params, grids)},
            "meshes": [m.tolist() for m in meshes],
            "values": values.tolist(),
            "optimum": optimum,
            "value_range": [float(values.min()), float(values.max())],
        }

    # ── Monte Carlo ──

    def monte_carlo_sample(
        self,
        param_generator: Callable[[], Dict[str, float]],
        compute_fn: Callable[[Dict[str, float]], Optional[float]],
        n_samples: int = 10000,
        filter_valid: Optional[Callable[[float], bool]] = None,
        name: str = "monte_carlo",
    ) -> NumericalResult:
        """
        蒙特卡洛采样。

        Args:
            param_generator: 随机参数生成器，返回参数字典
            compute_fn: 计算函数，接受参数字典，返回数值（或None表示跳过）
            n_samples: 采样数
            filter_valid: 额外过滤器

        Returns:
            NumericalResult
        """
        samples = []
        for _ in range(n_samples):
            params = param_generator()
            val = compute_fn(params)
            if val is not None and (filter_valid is None or filter_valid(val)):
                samples.append(val)

        if not samples:
            return NumericalResult(name=name, n_samples=0)

        arr = np.array(samples)
        return NumericalResult(
            name=name,
            n_samples=len(arr),
            mean=float(np.mean(arr)),
            median=float(np.median(arr)),
            std=float(np.std(arr)),
            ci_95=(
                float(np.percentile(arr, 2.5)),
                float(np.percentile(arr, 97.5)),
            ),
            min_val=float(arr.min()),
            max_val=float(arr.max()),
        )

    # ── Optimization ──

    def find_extremum(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: Optional[List[Tuple[float, float]]] = None,
        method: str = "L-BFGS-B",
        find_minimum: bool = True,
    ) -> Dict[str, Any]:
        """
        数值优化寻找极值点。

        Returns:
            {'x_opt': [...], 'f_opt': ..., 'success': bool, 'message': str}
        """
        f = func if find_minimum else lambda x: -func(x)

        if bounds:
            result = optimize.minimize(f, x0, method=method, bounds=bounds)
        else:
            result = optimize.minimize(f, x0, method=method)

        return {
            "x_opt": result.x.tolist(),
            "f_opt": float(result.fun) if find_minimum else float(-result.fun),
            "success": bool(result.success),
            "message": result.message,
            "nit": result.nit,
        }

    # ── Delta Method ──

    def delta_method_se(
        self,
        turning_point_expr: Callable[[Dict[str, float]], float],
        gradient_expr: Callable[[Dict[str, float]], Dict[str, float]],
        param_estimates: Dict[str, float],
        vcov_matrix: np.ndarray,
        param_names: List[str],
    ) -> Dict[str, Any]:
        """
        Delta方法计算拐点标准误。

        对 g(θ) = -θ1/(2*θ2):
            Var(g) ≈ ∇gᵀ · Σ · ∇g

        Args:
            turning_point_expr: f(params) -> float, 拐点公式
            gradient_expr: f(params) -> dict, 梯度{param: d(tp)/d(param)}
            param_estimates: 参数估计值
            vcov_matrix: 协方差矩阵
            param_names: 参数名列表

        Returns:
            {'turning_point': ..., 'se': ..., 'ci_95': [...]}
        """
        tp = turning_point_expr(param_estimates)
        grad_dict = gradient_expr(param_estimates)
        grad = np.array([grad_dict[p] for p in param_names])

        var_tp = grad @ vcov_matrix @ grad
        se_tp = np.sqrt(max(var_tp, 0))

        return {
            "turning_point": tp,
            "se": se_tp,
            "ci_95": [tp - 1.96 * se_tp, tp + 1.96 * se_tp],
            "variance": var_tp,
            "gradient": grad_dict,
        }

    # ── Distribution Stats ──

    def distribution_stats(self, data: np.ndarray, name: str = "distribution") -> NumericalResult:
        """计算分布的基本统计量"""
        return NumericalResult(
            name=name,
            n_samples=len(data),
            mean=float(np.mean(data)),
            median=float(np.median(data)),
            std=float(np.std(data)),
            ci_95=(
                float(np.percentile(data, 2.5)),
                float(np.percentile(data, 97.5)),
            ),
            min_val=float(data.min()),
            max_val=float(data.max()),
        )

    def empirical_percentile(self, data: np.ndarray, value: float) -> float:
        """计算经验值在分布中的分位数"""
        return float(np.mean(data < value) * 100)
