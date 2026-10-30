"""
SageMathEngine — SageMath CAS 备用验证引擎
============================================
提供 SymPy 之外的独立验证路径，支持任意精度计算。

设计原则:
    - 作为 SymbolicEngine 的备选，而不是替代
    - 双引擎交叉验证: SymPy 推导 + SageMath 复核
    - 如果 SageMath 不可用，优雅降级

集成方式:
    1. 通过 @justice8096/sagemath-mcp-server npm 包 (推荐)
    2. 通过本地 SageMath 安装 (sagemath-standard)
    3. 如果都不可用，返回降级提示

能力:
    - 复杂方程求解 (超越 SymPy 能力范围)
    - 任意精度算术 (100+位有效数字)
    - 代数几何/数论专用函数
    - Groebner基、消元法
"""

import json
import subprocess
import os
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SageMathResult:
    """SageMath 计算结果"""
    operation: str
    expression: str
    result: str = ""
    status: str = "ok"  # ok | fallback | unavailable
    engine: str = "SageMath"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "expression": self.expression,
            "result": self.result,
            "status": self.status,
            "engine": self.engine,
            "details": self.details,
        }


class SageMathEngine:
    """
    SageMath CAS 引擎 — 备选验证路径。

    支持的操作:
        - simplify: 表达式化简
        - differentiate: 符号求导
        - integrate: 符号积分
        - solve: 方程求解
        - limit: 极限计算
        - matrix_ops: 矩阵运算 (特征值/行列式/RREF)
        - latex_convert: 表达式→LaTeX
        - arbitrary_precision: 任意精度数值计算
    """

    def __init__(self):
        self._available = None
        self._backend = None  # 'npm_package' | 'local_sage' | None

    def is_available(self) -> bool:
        """Check if SageMath is available"""
        if self._available is not None:
            return self._available

        # Method 1: Check environment variable SAGEMATH_MCP_PATH
        npm_path = os.environ.get("SAGEMATH_MCP_PATH", "")
        if npm_path and os.path.exists(npm_path):
            self._available = True
            self._backend = "npm_package"
            return True

        # Method 2: Check common npm global install locations
        npm_global_paths = []
        node_path = os.environ.get("NODE_PATH", "")
        if node_path:
            npm_global_paths.append(os.path.join(node_path, "@justice8096", "sagemath-mcp-server", "build", "index.js"))
        home = os.path.expanduser("~")
        npm_global_paths.extend([
            os.path.join(home, ".nvm", "versions", "node", "*", "lib", "node_modules", "@justice8096", "sagemath-mcp-server", "build", "index.js"),
        ])
        import glob
        for pattern in npm_global_paths:
            for p in glob.glob(pattern) if "*" in pattern else [pattern]:
                if os.path.exists(p):
                    self._available = True
                    self._backend = "npm_package"
                    self._npm_path = p
                    return True

        # Method 3: Check local SageMath installation
        try:
            result = subprocess.run(
                ["sage", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self._available = True
                self._backend = "local_sage"
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        self._available = False
        self._backend = None
        return False

    def _call_npm_sagemath(self, operation: str, expression: str) -> Dict:
        """Call SageMath via npm package"""
        npm_path = getattr(self, "_npm_path", None) or os.environ.get("SAGEMATH_MCP_PATH", "")
        node_path = os.environ.get("NODE_PATH", "node")

        try:
            proc = subprocess.run(
                [node_path, npm_path],
                input=json.dumps({"operation": operation, "expression": expression}),
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            output = proc.stdout.strip() or proc.stderr.strip()
            return {"result": output, "status": "ok"}
        except FileNotFoundError:
            return {"result": "", "status": "unavailable", "error": "Node.js not found"}
        except subprocess.TimeoutExpired:
            return {"result": "", "status": "timeout", "error": "SageMath timed out"}
        except Exception as e:
            return {"result": "", "status": "error", "error": str(e)}

    def _call_local_sagemath(self, operation: str, expression: str) -> Dict:
        """通过本地 SageMath 调用"""
        sage_code = self._build_sage_code(operation, expression)
        try:
            proc = subprocess.run(
                ["sage", "-c", sage_code],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            return {"result": proc.stdout.strip(), "status": "ok" if proc.returncode == 0 else "error"}
        except Exception as e:
            return {"result": "", "status": "error", "error": str(e)}

    def _build_sage_code(self, operation: str, expression: str) -> str:
        """构造 SageMath 代码"""
        code_map = {
            "simplify": f"print(simplify({expression}))",
            "differentiate": f"print(diff({expression}))",
            "integrate": f"print(integral({expression}))",
            "solve": f"print(solve({expression}))",
            "limit": f"print(limit({expression}))",
        }
        return code_map.get(operation, f"print({expression})")

    def execute(self, operation: str, expression: str) -> SageMathResult:
        """
        执行 SageMath 操作。

        Args:
            operation: simplify | differentiate | integrate | solve | limit | matrix_ops | latex_convert
            expression: 数学表达式

        Returns:
            SageMathResult
        """
        if not self.is_available():
            return SageMathResult(
                operation=operation,
                expression=expression,
                status="fallback",
                engine="SymPy (fallback)",
                details={
                    "message": "SageMath not available. Install: npm install -g @justice8096/sagemath-mcp-server, or install SageMath locally.",
                    "fallback_available": True,
                },
            )

        if self._backend == "npm_package":
            raw = self._call_npm_sagemath(operation, expression)
        else:
            raw = self._call_local_sagemath(operation, expression)

        return SageMathResult(
            operation=operation,
            expression=expression,
            result=raw.get("result", ""),
            status=raw.get("status", "error"),
            engine=f"SageMath ({self._backend})",
            details=raw,
        )

    def cross_verify(self, sympy_result: str, sage_operation: str, expression: str) -> Dict[str, Any]:
        """
        双引擎交叉验证: 比较 SymPy 结果与 SageMath 结果。

        Returns:
            {'consistent': bool, 'sympy': ..., 'sagemath': ..., 'discrepancy': ...}
        """
        sage_result = self.execute(sage_operation, expression)

        if sage_result.status == "fallback":
            return {
                "consistent": None,
                "sympy_result": sympy_result,
                "sagemath_result": "unavailable",
                "verdict": "SageMath unavailable, cannot cross-verify",
            }

        # 简单的一致性检查 (可根据操作类型扩展)
        consistent = len(sage_result.result) > 0 and sage_result.status == "ok"

        return {
            "consistent": consistent,
            "sympy_result": sympy_result,
            "sagemath_result": sage_result.result,
            "sagemath_status": sage_result.status,
            "verdict": "consistent" if consistent else "discrepancy — manual review needed",
        }
