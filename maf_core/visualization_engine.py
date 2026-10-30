"""
VisualizationEngine — 数学可视化引擎
=====================================
生成数学图表和动画，支持 Matplotlib 和 Manim。

能力:
    - 2D 函数曲线 (单变量)
    - 3D 曲面图 (双变量)
    - 等高线图
    - 参数敏感性动画 (matplotlib.animation)
    - Manim 数学动画 (可选)
    - 拐点/极值点标注

输出格式:
    - PNG (静态图, 300 DPI)
    - GIF (动画)
    - MP4 (动画, 需 ffmpeg)
"""

import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass
class VisualizationResult:
    """可视化结果"""
    name: str
    figure_type: str  # '2d_curve' | '3d_surface' | 'contour' | 'animation' | 'manim'
    output_path: str = ""
    status: str = "ok"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "figure_type": self.figure_type,
            "output_path": self.output_path,
            "status": self.status,
            "metadata": self.metadata,
        }


class VisualizationEngine:
    """
    数学可视化引擎。
    """

    def __init__(self, output_dir: str = "./output/figures"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── 2D Function Curve ──

    def plot_2d_curve(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        x_range: Tuple[float, float] = (-5, 5),
        n_points: int = 200,
        title: str = "Function Curve",
        xlabel: str = "x",
        ylabel: str = "f(x)",
        turning_points: Optional[List[Dict[str, Any]]] = None,
        filename: Optional[str] = None,
    ) -> VisualizationResult:
        """
        绘制单变量函数曲线，可选标注拐点。

        Args:
            func: 函数 f(x) -> y
            x_range: x 轴范围
            n_points: 采样点数
            turning_points: [{'x': ..., 'label': ..., 'type': 'max'|'min'|'inflection'}]
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            x = np.linspace(x_range[0], x_range[1], n_points)
            y = func(x)

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(x, y, "b-", linewidth=2, label=title)
            ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
            ax.axvline(x=0, color="gray", linestyle="--", alpha=0.3)

            # 标注拐点
            if turning_points:
                for tp in turning_points:
                    tp_x = tp.get("x", 0)
                    tp_y = func(np.array([tp_x]))[0]
                    color = "red" if tp.get("type") == "max" else "green" if tp.get("type") == "min" else "orange"
                    ax.plot(tp_x, tp_y, "o", color=color, markersize=10)
                    ax.annotate(
                        tp.get("label", f"x={tp_x:.2f}"),
                        (tp_x, tp_y),
                        textcoords="offset points",
                        xytext=(0, 15),
                        ha="center",
                        fontsize=10,
                        color=color,
                    )

            ax.set_xlabel(xlabel, fontsize=12)
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(title, fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)

            if filename is None:
                filename = f"curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(self.output_dir, filename)
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)

            return VisualizationResult(
                name=title,
                figure_type="2d_curve",
                output_path=path,
                metadata={"x_range": x_range, "n_points": n_points, "turning_points": turning_points},
            )
        except ImportError:
            return VisualizationResult(
                name=title,
                figure_type="2d_curve",
                status="unavailable",
                metadata={"error": "matplotlib not installed"},
            )

    # ── 3D Surface ──

    def plot_3d_surface(
        self,
        func: Callable[[np.ndarray, np.ndarray], np.ndarray],
        x_range: Tuple[float, float] = (-5, 5),
        y_range: Tuple[float, float] = (-5, 5),
        n_points: int = 50,
        title: str = "3D Surface",
        xlabel: str = "x",
        ylabel: str = "y",
        zlabel: str = "f(x,y)",
        filename: Optional[str] = None,
    ) -> VisualizationResult:
        """
        绘制双变量函数的三维曲面图。
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D

            x = np.linspace(x_range[0], x_range[1], n_points)
            y = np.linspace(y_range[0], y_range[1], n_points)
            X, Y = np.meshgrid(x, y)
            Z = func(X, Y)

            fig = plt.figure(figsize=(12, 8))
            ax = fig.add_subplot(111, projection="3d")
            surf = ax.plot_surface(X, Y, Z, cmap="viridis", alpha=0.8, edgecolor="none")
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_zlabel(zlabel, fontsize=11)
            ax.set_title(title, fontsize=14)

            if filename is None:
                filename = f"surface_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(self.output_dir, filename)
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)

            z_min, z_max = float(Z.min()), float(Z.max())
            return VisualizationResult(
                name=title,
                figure_type="3d_surface",
                output_path=path,
                metadata={
                    "x_range": x_range,
                    "y_range": y_range,
                    "z_range": [z_min, z_max],
                    "n_points": n_points,
                },
            )
        except ImportError:
            return VisualizationResult(
                name=title,
                figure_type="3d_surface",
                status="unavailable",
                metadata={"error": "matplotlib not installed"},
            )

    # ── Contour Plot ──

    def plot_contour(
        self,
        func: Callable[[np.ndarray, np.ndarray], np.ndarray],
        x_range: Tuple[float, float] = (-5, 5),
        y_range: Tuple[float, float] = (-5, 5),
        n_points: int = 100,
        n_levels: int = 20,
        title: str = "Contour Plot",
        xlabel: str = "x",
        ylabel: str = "y",
        filename: Optional[str] = None,
    ) -> VisualizationResult:
        """绘制等高线图"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            x = np.linspace(x_range[0], x_range[1], n_points)
            y = np.linspace(y_range[0], y_range[1], n_points)
            X, Y = np.meshgrid(x, y)
            Z = func(X, Y)

            fig, ax = plt.subplots(figsize=(10, 8))
            contour = ax.contour(X, Y, Z, levels=n_levels, cmap="viridis")
            ax.clabel(contour, inline=True, fontsize=8)
            ax.set_xlabel(xlabel, fontsize=12)
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(title, fontsize=14)
            ax.grid(True, alpha=0.3)

            if filename is None:
                filename = f"contour_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(self.output_dir, filename)
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)

            return VisualizationResult(
                name=title,
                figure_type="contour",
                output_path=path,
                metadata={"x_range": x_range, "y_range": y_range, "n_levels": n_levels},
            )
        except ImportError:
            return VisualizationResult(
                name=title, figure_type="contour", status="unavailable",
                metadata={"error": "matplotlib not installed"},
            )

    # ── Animation (matplotlib.animation) ──

    def create_animation(
        self,
        func_factory: Callable[[float], Callable[[np.ndarray], np.ndarray]],
        param_range: Tuple[float, float] = (0, 1),
        n_frames: int = 50,
        x_range: Tuple[float, float] = (-5, 5),
        title: str = "Parameter Animation",
        xlabel: str = "x",
        ylabel: str = "f(x)",
        fps: int = 10,
        filename: Optional[str] = None,
    ) -> VisualizationResult:
        """
        创建参数变化动画。

        Args:
            func_factory: 参数值 → 函数的工厂。例: lambda t: lambda x: t*x**2
            param_range: 参数范围
            n_frames: 帧数
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.animation import FuncAnimation

            param_values = np.linspace(param_range[0], param_range[1], n_frames)
            x = np.linspace(x_range[0], x_range[1], 200)

            fig, ax = plt.subplots(figsize=(10, 6))
            line, = ax.plot([], [], "b-", linewidth=2)
            ax.set_xlim(x_range)
            y_all = []
            for t in param_values:
                y_all.append(func_factory(t)(x))
            y_all = np.array(y_all)
            ax.set_ylim(y_all.min() * 1.1, y_all.max() * 1.1)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.3)
            param_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top")

            def init():
                line.set_data([], [])
                param_text.set_text("")
                return line, param_text

            def animate(i):
                t = param_values[i]
                y = func_factory(t)(x)
                line.set_data(x, y)
                param_text.set_text(f"param = {t:.3f}")
                return line, param_text

            anim = FuncAnimation(fig, animate, init_func=init,
                                frames=n_frames, interval=1000//fps, blit=True)

            if filename is None:
                filename = f"animation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
            path = os.path.join(self.output_dir, filename)
            anim.save(path, writer="pillow", fps=fps)
            plt.close(fig)

            return VisualizationResult(
                name=title,
                figure_type="animation",
                output_path=path,
                metadata={"n_frames": n_frames, "fps": fps, "param_range": param_range},
            )
        except ImportError:
            return VisualizationResult(
                name=title, figure_type="animation", status="unavailable",
                metadata={"error": "matplotlib not installed"},
            )

    # ── U-Shape / Inverted-U Visualization ──

    def plot_quadratic_analysis(
        self,
        alpha1: float,
        alpha2: float,
        x_range: Optional[Tuple[float, float]] = None,
        title: str = "Quadratic Form Analysis",
        filename: Optional[str] = None,
    ) -> VisualizationResult:
        """
        绘制二次型函数的 U 型/倒U 型分析图。

        自动标注:
            - 拐点位置
            - 拐点类型 (最小/最大)
            - FOC=0 线
        """
        if x_range is None:
            tp = -alpha1 / (2 * alpha2) if abs(alpha2) > 1e-6 else 0
            x_range = (tp - 3, tp + 3)

        def f(x):
            return alpha1 * x + alpha2 * x**2

        tp_x = -alpha1 / (2 * alpha2) if abs(alpha2) > 1e-6 else None
        if tp_x is not None:
            tp_y = f(np.array([tp_x]))[0]
            is_min = alpha2 > 0
            turning_points = [{
                "x": float(tp_x),
                "label": f"{'Min' if is_min else 'Max'} at x*={tp_x:.2f}",
                "type": "min" if is_min else "max",
            }]
        else:
            turning_points = []

        shape = "U-Shape (Minimum)" if alpha2 > 0 else "Inverted-U (Maximum)" if alpha2 < 0 else "Linear"
        return self.plot_2d_curve(
            func=f,
            x_range=x_range,
            title=f"{title}: {shape}",
            xlabel="x",
            ylabel="f(x)",
            turning_points=turning_points,
            filename=filename,
        )

    # ── CES 3D Surface (专用) ──

    def plot_ces_3d(
        self,
        alpha: float = 0.3,
        tau: float = 1.0,
        A: float = 1.0,
        N_range: Tuple[float, float] = (1, 200),
        tau_range: Tuple[float, float] = (0.5, 2.0),
        filename: Optional[str] = None,
    ) -> VisualizationResult:
        """绘制 CES 生产函数的三维曲面"""
        def ces_surface(N, tau_arr):
            return A * N**(-1) * ((alpha + (1 - alpha) * N) * tau_arr)**(1 / (1 - alpha))

        return self.plot_3d_surface(
            func=ces_surface,
            x_range=N_range,
            y_range=tau_range,
            n_points=50,
            title=f"CES Production Function (α={alpha})",
            xlabel="N (Firms)",
            ylabel="τ (Technology)",
            zlabel="Y (Output)",
            filename=filename or f"ces_3d_alpha{alpha}.png",
        )
