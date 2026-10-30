"""
Math Agent Framework — Core Engines
====================================
所有核心引擎均独立于具体数学模型，可复用于任何推导任务。

引擎层次:
    【推导层】
    SymbolicEngine      — SymPy 符号推导 (求导、积分、求解、线性化)
    NumericalEngine     — NumPy/SciPy 数值计算 (网格搜索、优化、模拟)
    QuantEconEngine     — QuantEcon 动态优化 (Riccati/LQ/马尔可夫/博弈论)

    【验证层】
    VerificationEngine          — 符号+数值双重验证 (五层验证框架)
    SageMathEngine              — SageMath CAS 备用验证 (任意精度/代数几何)
    MultiAgentVerificationEngine — QED多Agent对抗验证 (Proposer+Critic+Judge)

    【编排层】
    PipelineEngine      — 流水线编排 (步骤调度、依赖管理、报告聚合)

    【输出层】
    DocumentEngine      — 文档生成 (MD/Quarto/LaTeX/DOCX/JSON)
    FormalProofEngine   — 形式化证明模板 (Lean 4 代码生成)
    VisualizationEngine — 数学可视化 (2D/3D/动画/Manim)

统一验证流水线:
    SymPy符号验证 → 蒙特卡洛数值验证 → SageMath CAS交叉验证
    → Lean 4 形式化证明 → QED多Agent对抗验证
"""

from .symbolic_engine import SymbolicEngine
from .numerical_engine import NumericalEngine
from .verification_engine import VerificationEngine
from .pipeline_engine import PipelineEngine
from .document_engine import DocumentEngine

# 新增引擎 (2026-06-02)
from .formal_proof_engine import FormalProofEngine
from .sagemath_engine import SageMathEngine
from .quantecon_engine import QuantEconEngine
from .multi_agent_verify_engine import MultiAgentVerificationEngine
from .visualization_engine import VisualizationEngine
from .analysis_engine import AnalysisEngine
from .pde_engine import PdeEngine

__all__ = [
    # 推导层
    "SymbolicEngine",
    "NumericalEngine",
    "QuantEconEngine",
    # 验证层
    "VerificationEngine",
    "SageMathEngine",
    "MultiAgentVerificationEngine",
    # 编排层
    "PipelineEngine",
    # 输出层
    "DocumentEngine",
    "FormalProofEngine",
    "VisualizationEngine",
    # 分析学
    "AnalysisEngine",
    # 偏微分方程
    "PdeEngine",
]
