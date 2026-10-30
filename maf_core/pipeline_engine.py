"""
PipelineEngine — 通用流水线编排引擎
=====================================
管理多步推导的执行、依赖、中间结果存储和报告聚合。

设计原则:
    - 步骤注册制: 每步注册name+function+dependencies
    - 拓扑排序自动执行
    - 失败不阻塞 (best-effort)
    - 中间结果持久化
"""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PipelineStep:
    """流水线步骤"""
    name: str
    index: int
    description: str
    func: Callable[[Dict[str, Any]], Dict[str, Any]]
    dependencies: List[str] = field(default_factory=list)  # 依赖的步骤名
    tools: List[str] = field(default_factory=list)  # 使用的工具
    timeout_seconds: int = 300
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """步骤执行结果"""
    step_name: str
    status: str  # 'success' | 'failed' | 'skipped'
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class PipelineEngine:
    """
    通用流水线引擎。

    用法:
        pipeline = PipelineEngine("My Pipeline")
        pipeline.add_step("step1", "CES Derivation", ces_func, tools=["SymPy"])
        pipeline.add_step("step2", "IPF Derivation", ipf_func, deps=["step1"])
        pipeline.run(params)
        pipeline.save_report("output.json")
    """

    def __init__(self, name: str = "Derivation Pipeline", output_dir: str = "./output"):
        self.name = name
        self.output_dir = output_dir
        self.steps: Dict[str, PipelineStep] = {}
        self.results: Dict[str, StepResult] = {}
        self._order: List[str] = []  # 执行顺序
        self.metadata: Dict[str, Any] = {
            "pipeline_name": name,
            "started": None,
            "completed": None,
        }
        os.makedirs(output_dir, exist_ok=True)

    def add_step(
        self,
        name: str,
        description: str,
        func: Callable[[Dict[str, Any]], Dict[str, Any]],
        dependencies: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        index: Optional[int] = None,
        timeout: int = 300,
    ) -> "PipelineEngine":
        """注册一个步骤"""
        if index is None:
            index = len(self.steps) + 1

        step = PipelineStep(
            name=name,
            index=index,
            description=description,
            func=func,
            dependencies=dependencies or [],
            tools=tools or [],
            timeout_seconds=timeout,
        )
        self.steps[name] = step
        if name not in self._order:
            self._order.append(name)
        return self

    def _topological_sort(self) -> List[str]:
        """拓扑排序"""
        in_degree = {name: len(step.dependencies) for name, step in self.steps.items()}
        dependents: Dict[str, List[str]] = {name: [] for name in self.steps}
        for name, step in self.steps.items():
            for dep in step.dependencies:
                if dep in dependents:
                    dependents[dep].append(name)

        queue = [name for name, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dep in dependents.get(node, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        # 如果有循环依赖，追加剩余步骤
        for name in self._order:
            if name not in result:
                result.append(name)

        return result

    def run(self, initial_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行流水线。

        Args:
            initial_params: 初始参数字典，传递给第一步

        Returns:
            {'steps': {...}, 'metadata': {...}}
        """
        params = initial_params or {}
        self.metadata["started"] = datetime.now().isoformat()
        pipeline_start = datetime.now()

        execution_order = self._topological_sort()
        print(f"\n{'='*60}")
        print(f"  Pipeline: {self.name}")
        print(f"  Steps: {len(execution_order)} | Order: {' → '.join(execution_order)}")
        print(f"{'='*60}")

        for step_name in execution_order:
            step = self.steps[step_name]
            print(f"\n  [{step.index}] {step.description}...", end=" ")

            result = StepResult(step_name=step_name, status="skipped")

            # Check dependencies
            deps_ok = True
            for dep in step.dependencies:
                if dep not in self.results or self.results[dep].status != "success":
                    print(f"SKIP (dependency '{dep}' not satisfied)")
                    result.error = f"Dependency '{dep}' failed or missing"
                    self.results[step_name] = result
                    deps_ok = False
                    break

            if not deps_ok:
                # 合并前置步骤输出
                for dep in step.dependencies:
                    if dep in self.results:
                        params.update(self.results[dep].output)
                continue

            # Execute
            result.started_at = datetime.now().isoformat()
            step_start = datetime.now()
            try:
                output = step.func(params)
                result.status = "success"
                result.output = output
                params.update(output)  # 后续步骤可访问前置输出
                print(f"OK ({output.get('verified', 'done')})")
            except Exception as e:
                result.status = "failed"
                result.error = str(e)
                import traceback
                traceback.print_exc()
                print(f"FAIL: {e}")

            result.completed_at = datetime.now().isoformat()
            result.duration_seconds = (datetime.now() - step_start).total_seconds()
            self.results[step_name] = result

        self.metadata["completed"] = datetime.now().isoformat()
        self.metadata["duration_seconds"] = (
            datetime.now() - pipeline_start
        ).total_seconds()
        self.metadata["total_steps"] = len(execution_order)
        self.metadata["successful_steps"] = sum(
            1 for r in self.results.values() if r.status == "success"
        )

        return self.collect_results()

    def collect_results(self) -> Dict[str, Any]:
        """收集所有结果"""
        return {
            "metadata": self.metadata,
            "steps": {
                name: {
                    "status": r.status,
                    "duration_s": r.duration_seconds,
                    "output": r.output,
                    "error": r.error,
                }
                for name, r in self.results.items()
            },
        }

    def save_report(self, filename: str = "pipeline_report.json"):
        """保存流水线报告"""
        path = os.path.join(self.output_dir, filename)
        report = self.collect_results()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  Report saved: {path}")
        return path

    def print_summary(self):
        """打印执行摘要"""
        print(f"\n{'='*60}")
        print(f"  Pipeline: {self.name} — Summary")
        print(f"{'='*60}")
        for name, r in self.results.items():
            sym = "✓" if r.status == "success" else "✗" if r.status == "failed" else "○"
            print(f"  [{sym}] {name}: {r.status} ({r.duration_seconds:.1f}s)")
        print(f"  Total: {self.metadata.get('duration_seconds', 0):.1f}s")
