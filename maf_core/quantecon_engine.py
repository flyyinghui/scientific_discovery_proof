"""
QuantEconEngine — 动态优化与定量经济学引擎
============================================
封装 QuantEcon.py 用于动态经济模型求解。

能力:
    - solve_discrete_riccati: Riccati 方程 (LQ 动态规划)
    - LinearStateSpace: 状态空间模型的脉冲响应/稳态分布
    - MarkovChain: 马尔可夫链稳态分布/遍历性
    - game_theory: 纳什均衡求解
    - optimize: 线性规划/二分法/根求解
    - kalman: 卡尔曼滤波

设计原则:
    - 可选依赖: 未安装 QuantEcon 时优雅降级
    - 返回结构化结果 (JSON 可序列化)
"""

import json
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class QuantEconResult:
    """QuantEcon 计算结果"""
    operation: str
    status: str = "ok"  # ok | unavailable | error
    engine: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "status": self.status,
            "engine": self.engine,
            "result": self.result,
            "interpretation": self.interpretation,
        }


class QuantEconEngine:
    """
    QuantEcon 动态优化引擎。
    """

    def __init__(self):
        self._available = None
        self._qe = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import quantecon as qe
            self._qe = qe
            self._available = True
        except ImportError:
            self._available = False
        return self._available

    def _get_qe(self):
        if not self.is_available():
            raise ImportError(
                "QuantEcon not installed. Install: pip install quantecon"
            )
        return self._qe

    # ── Riccati Equation ──

    def solve_discrete_riccati(
        self,
        A: Optional[np.ndarray] = None,
        B: Optional[np.ndarray] = None,
        Q: Optional[np.ndarray] = None,
        R: Optional[np.ndarray] = None,
    ) -> QuantEconResult:
        """
        求解离散时间 Riccati 方程: X = A'XA - A'XB(R+B'XB)^(-1)B'XA + Q

        用于线性二次动态规划:
            min Σ (x_t'Q x_t + u_t'R u_t)
            s.t. x_{t+1} = A x_t + B u_t

        Args:
            A: 状态转移矩阵 (n×n)
            B: 控制矩阵 (n×k)
            Q: 状态权重 (n×n, 半正定)
            R: 控制权重 (k×k, 正定)
        """
        if not self.is_available():
            return QuantEconResult(
                operation="solve_discrete_riccati",
                status="unavailable",
                engine="QuantEcon (not installed)",
                interpretation="Install: pip install quantecon",
            )

        qe = self._get_qe()

        # 默认值: 简单的一维优化问题
        if A is None:
            A = np.array([[1.0, 0.0], [0.0, 0.9]])
        if B is None:
            B = np.array([[0.0], [1.0]])
        if Q is None:
            Q = np.array([[1.0, 0.0], [0.0, 0.0]])
        if R is None:
            R = np.array([[1.0]])

        try:
            X = qe.solve_discrete_riccati(A, B, Q, R)
            return QuantEconResult(
                operation="solve_discrete_riccati",
                status="ok",
                engine=f"QuantEcon {qe.__version__}",
                result={
                    "solution_X": X.tolist(),
                    "A_shape": list(A.shape),
                    "B_shape": list(B.shape),
                },
                interpretation=(
                    "Riccati 解 X 给出最优值函数 V(x) = x'Xx。"
                    "最优控制律: u_t = -(R + B'XB)^(-1) B'XA x_t。"
                    "在稳态增长模型中，X 的特征值揭示收敛速度。"
                ),
            )
        except Exception as e:
            return QuantEconResult(
                operation="solve_discrete_riccati",
                status="error",
                result={"error": str(e)},
            )

    # ── Linear State Space ──

    def linear_state_space(
        self,
        A: Optional[np.ndarray] = None,
        B: Optional[np.ndarray] = None,
        C: Optional[np.ndarray] = None,
        D: Optional[np.ndarray] = None,
        impulse_steps: int = 10,
    ) -> QuantEconResult:
        """
        线性状态空间模型: x_{t+1} = A x_t + B w_t, y_t = C x_t + D w_t

        计算脉冲响应函数 (IRF)。
        """
        if not self.is_available():
            return QuantEconResult(
                operation="linear_state_space",
                status="unavailable",
                engine="QuantEcon (not installed)",
            )

        qe = self._get_qe()

        if A is None:
            A = np.array([[1.0, 0.0], [0.0, 0.9]])
        if B is None:
            B = np.array([[0.0], [1.0]])
        if C is None:
            C = np.array([[1.0, 0.0]])
        if D is None:
            D = np.array([[0.0]])

        try:
            lss = qe.LinearStateSpace(A, B, C, D)
            impulse = lss.impulse_response(impulse_steps)

            return QuantEconResult(
                operation="linear_state_space",
                status="ok",
                engine=f"QuantEcon {qe.__version__}",
                result={
                    "impulse_response": impulse.flatten().tolist(),
                    "steps": impulse_steps,
                    "stationary": abs(impulse[-1][0]) < 1e-4,
                },
                interpretation=(
                    f"脉冲响应 (前 {impulse_steps} 期) 显示冲击的传播路径。"
                    f"稳态: {'已收敛' if abs(impulse[-1][0]) < 1e-4 else '未收敛'}。"
                ),
            )
        except Exception as e:
            return QuantEconResult(
                operation="linear_state_space",
                status="error",
                result={"error": str(e)},
            )

    # ── Markov Chain ──

    def markov_chain(
        self,
        P: Optional[np.ndarray] = None,
        state_labels: Optional[List[str]] = None,
    ) -> QuantEconResult:
        """
        马尔可夫链分析: 转移矩阵 → 稳态分布 + 遍历性。

        Args:
            P: 转移概率矩阵 (n×n, 行和为1)
            state_labels: 状态标签
        """
        if not self.is_available():
            return QuantEconResult(
                operation="markov_chain",
                status="unavailable",
                engine="QuantEcon (not installed)",
            )

        qe = self._get_qe()

        if P is None:
            # 默认: 两状态经济周期
            P = np.array([[0.8, 0.2], [0.3, 0.7]])
        if state_labels is None:
            state_labels = [f"State_{i}" for i in range(P.shape[0])]

        try:
            mc = qe.MarkovChain(P)
            stationary = mc.stationary_distributions[0]

            return QuantEconResult(
                operation="markov_chain",
                status="ok",
                engine=f"QuantEcon {qe.__version__}",
                result={
                    "transition_matrix": P.tolist(),
                    "stationary_distribution": {
                        state_labels[i]: round(float(stationary[i]), 4)
                        for i in range(len(stationary))
                    },
                    "is_ergodic": bool(mc.is_ergodic),
                    "num_states": P.shape[0],
                },
                interpretation=(
                    f"稳态分布: { {state_labels[i]: round(float(stationary[i]), 3) for i in range(len(stationary))} }。"
                    f"该链{'是' if mc.is_ergodic else '不是'}遍历的。"
                ),
            )
        except Exception as e:
            return QuantEconResult(
                operation="markov_chain",
                status="error",
                result={"error": str(e)},
            )

    # ── Nash Equilibrium ──

    def nash_equilibrium(
        self,
        payoff_matrix_1: Optional[np.ndarray] = None,
        payoff_matrix_2: Optional[np.ndarray] = None,
    ) -> QuantEconResult:
        """
        两人博弈纳什均衡求解。

        Args:
            payoff_matrix_1: 玩家1的支付矩阵
            payoff_matrix_2: 玩家2的支付矩阵
        """
        if not self.is_available():
            return QuantEconResult(
                operation="nash_equilibrium",
                status="unavailable",
                engine="QuantEcon (not installed)",
            )

        qe = self._get_qe()

        if payoff_matrix_1 is None:
            # 默认: 囚徒困境
            payoff_matrix_1 = np.array([[-1, -5], [0, -3]])
            payoff_matrix_2 = np.array([[-1, 0], [-5, -3]])

        try:
            from quantecon import game_theory as gt
            g = gt.NormalFormGame((payoff_matrix_1, payoff_matrix_2))
            nash_list = list(g.support_enumeration())

            return QuantEconResult(
                operation="nash_equilibrium",
                status="ok",
                engine=f"QuantEcon {qe.__version__}",
                result={
                    "payoff_matrix_player1": payoff_matrix_1.tolist(),
                    "payoff_matrix_player2": payoff_matrix_2.tolist(),
                    "nash_equilibria": [
                        {"player1_strategy": [round(float(p), 3) for p in eq[0]],
                         "player2_strategy": [round(float(p), 3) for p in eq[1]]}
                        for eq in nash_list
                    ],
                    "num_equilibria": len(nash_list),
                },
                interpretation=f"找到 {len(nash_list)} 个纳什均衡。",
            )
        except Exception as e:
            return QuantEconResult(
                operation="nash_equilibrium",
                status="error",
                result={"error": str(e)},
            )
