"""
MC-PY-02: DAG Task Scheduler
Engineering Constraints: Python 3.10+, stdlib only. No networkx/graphlib.
Output as class. Full type annotations. CycleError on cycles. Single file.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

# ── Exceptions ──────────────────────────────────────────────────────────


class CycleError(Exception):
    def __init__(self, message: str, cycle: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.cycle = cycle

    def __str__(self) -> str:
        base = f"CycleError: {self.message}"
        if self.cycle:
            return f"{base}\nCycle: {' -> '.join(self.cycle)}"
        return base

    def get_info(self) -> Dict[str, Any]:
        return {"error": "cycle", "message": self.message, "cycle": self.cycle, "length": len(self.cycle) if self.cycle else 0}


# ── Enums / Data ────────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskNode:
    task_id: str
    task_fn: Callable[..., Coroutine[Any, Any, Any]]
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    priority: int = 0


@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"task_id": self.task_id, "success": self.success, "result": self.result, "error": self.error, "time": self.execution_time}


@dataclass
class SchedulerResult:
    success: bool
    execution_order: List[str]
    results: Dict[str, ExecutionResult]
    total_tasks: int
    completed: int
    failed: int
    total_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "total_time": self.total_time,
            "order": self.execution_order,
        }


# ── DAG ─────────────────────────────────────────────────────────────────


class DAG:
    def __init__(self) -> None:
        self.tasks: Dict[str, TaskNode] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_task(
        self,
        task_id: str,
        task_fn: Callable[..., Coroutine[Any, Any, Any]],
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
    ) -> TaskNode:
        if task_id in self.tasks:
            raise ValueError(f"Task already exists: {task_id}")

        node = TaskNode(task_id=task_id, task_fn=task_fn, priority=priority)

        if dependencies:
            for dep in dependencies:
                if dep not in self.tasks:
                    raise ValueError(f"Dependency does not exist: {dep}")
                node.dependencies.add(dep)
                self.tasks[dep].dependents.add(task_id)
                self.adjacency[dep].add(task_id)
                self.reverse_adjacency[task_id].add(dep)

        self.tasks[task_id] = node
        return node

    @property
    def entry_nodes(self) -> Set[str]:
        return {tid for tid in self.tasks if not self.reverse_adjacency.get(tid)}

    @property
    def exit_nodes(self) -> Set[str]:
        return {tid for tid in self.tasks if not self.adjacency.get(tid)}

    def get_ready_tasks(self) -> List[str]:
        ready: List[str] = []
        for tid, node in self.tasks.items():
            if node.status != TaskStatus.PENDING:
                continue
            deps_done = all(self.tasks[d].status == TaskStatus.COMPLETED for d in node.dependencies)
            if deps_done:
                ready.append(tid)
        ready.sort(key=lambda t: self.tasks[t].priority, reverse=True)
        return ready

    def reset(self) -> None:
        for node in self.tasks.values():
            node.status = TaskStatus.PENDING
            node.result = None
            node.error = None
            node.execution_time = None


# ── Cycle Detection ─────────────────────────────────────────────────────


class CycleDetector:
    def __init__(self, dag: DAG) -> None:
        self.dag = dag

    def detect(self) -> List[List[str]]:
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(tid: str) -> None:
            visited.add(tid)
            rec_stack.add(tid)
            path.append(tid)

            for dep_id in self.dag.adjacency.get(tid, set()):
                if dep_id in rec_stack:
                    idx = path.index(dep_id)
                    cycles.append(path[idx:] + [dep_id])
                elif dep_id not in visited:
                    dfs(dep_id)

            rec_stack.discard(tid)
            path.pop()

        for task_id in self.dag.tasks:
            if task_id not in visited:
                dfs(task_id)

        return cycles

    def has_cycles(self) -> bool:
        return len(self.detect()) > 0


# ── Topological Sort (Kahn's) ───────────────────────────────────────────


class TopologicalSorter:
    def __init__(self, dag: DAG) -> None:
        self.dag = dag

    def sort(self) -> List[str]:
        in_degree: Dict[str, int] = {tid: 0 for tid in self.dag.tasks}
        for tid in self.dag.tasks:
            for dep in self.dag.adjacency.get(tid, set()):
                in_degree[dep] = in_degree.get(dep, 0) + 1

        queue = sorted(
            [tid for tid, deg in in_degree.items() if deg == 0],
            key=lambda t: self.dag.tasks[t].priority,
            reverse=True,
        )
        result: List[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for dep_id in self.dag.adjacency.get(current, set()):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)
            queue.sort(key=lambda t: self.dag.tasks[t].priority, reverse=True)

        if len(result) != len(self.dag.tasks):
            remaining = set(self.dag.tasks.keys()) - set(result)
            raise CycleError(f"Cycle detected, unprocessed: {remaining}", cycle=list(remaining))

        return result

    def sort_layers(self) -> List[List[str]]:
        in_degree: Dict[str, int] = {tid: 0 for tid in self.dag.tasks}
        for tid in self.dag.tasks:
            for dep in self.dag.adjacency.get(tid, set()):
                in_degree[dep] = in_degree.get(dep, 0) + 1

        layers: List[List[str]] = []
        remaining = set(self.dag.tasks.keys())

        while remaining:
            layer = sorted(
                [t for t in remaining if in_degree.get(t, 0) == 0],
                key=lambda t: self.dag.tasks[t].priority,
                reverse=True,
            )
            if not layer:
                raise CycleError("Cycle detected during layer sort", cycle=list(remaining))

            layers.append(layer)
            for tid in layer:
                remaining.discard(tid)
                for dep in self.dag.adjacency.get(tid, set()):
                    in_degree[dep] -= 1

        return layers


# ── Scheduler ───────────────────────────────────────────────────────────


class DAGScheduler:
    def __init__(self, dag: DAG, max_workers: int = 4) -> None:
        self.dag = dag
        self.max_workers = max_workers
        self._detector = CycleDetector(dag)
        self._sorter = TopologicalSorter(dag)
        self._validate()

    def _validate(self) -> None:
        cycles = self._detector.detect()
        if cycles:
            raise CycleError(f"DAG contains {len(cycles)} cycle(s)", cycle=cycles[0])

    async def execute(self) -> SchedulerResult:
        start = time.time()
        self.dag.reset()

        layers = self._sorter.sort_layers()
        flat_order: List[str] = []
        results: Dict[str, ExecutionResult] = {}
        semaphore = asyncio.Semaphore(self.max_workers)

        async def run_task(task_id: str) -> ExecutionResult:
            async with semaphore:
                node = self.dag.tasks[task_id]
                node.status = TaskStatus.RUNNING
                t0 = time.time()
                try:
                    result = await node.task_fn()
                    elapsed = time.time() - t0
                    node.status = TaskStatus.COMPLETED
                    node.result = result
                    node.execution_time = elapsed
                    return ExecutionResult(task_id=task_id, success=True, result=result, execution_time=elapsed)
                except Exception as e:
                    elapsed = time.time() - t0
                    node.status = TaskStatus.FAILED
                    node.error = str(e)
                    node.execution_time = elapsed
                    return ExecutionResult(task_id=task_id, success=False, error=str(e), execution_time=elapsed)

        for layer in layers:
            tasks = [asyncio.create_task(run_task(tid)) for tid in layer]
            layer_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, tid in enumerate(layer):
                flat_order.append(tid)
                res = layer_results[i]
                if isinstance(res, Exception):
                    results[tid] = ExecutionResult(task_id=tid, success=False, error=str(res))
                    self.dag.tasks[tid].status = TaskStatus.FAILED
                else:
                    results[tid] = res

        total_time = time.time() - start
        completed = sum(1 for r in results.values() if r.success)
        failed = sum(1 for r in results.values() if not r.success)

        return SchedulerResult(
            success=failed == 0,
            execution_order=flat_order,
            results=results,
            total_tasks=len(self.dag.tasks),
            completed=completed,
            failed=failed,
            total_time=total_time,
        )

    def get_topological_order(self) -> List[str]:
        return self._sorter.sort()

    def get_execution_layers(self) -> List[List[str]]:
        return self._sorter.sort_layers()

    def get_critical_path(self) -> List[str]:
        """Longest path through the DAG (by number of nodes)."""
        memo: Dict[str, int] = {}

        def longest(tid: str) -> int:
            if tid in memo:
                return memo[tid]
            children = self.dag.adjacency.get(tid, set())
            if not children:
                memo[tid] = 1
            else:
                memo[tid] = 1 + max(longest(c) for c in children)
            return memo[tid]

        if not self.dag.tasks:
            return []

        for tid in self.dag.tasks:
            longest(tid)

        # Trace back from max
        path: List[str] = []
        current = max(self.dag.tasks, key=lambda t: memo.get(t, 0))
        while current:
            path.append(current)
            children = self.dag.adjacency.get(current, set())
            if not children:
                break
            current = max(children, key=lambda c: memo.get(c, 0))

        return path


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    async def main() -> None:
        dag = DAG()

        async def task_a() -> str:
            await asyncio.sleep(0.1)
            return "A done"

        async def task_b() -> str:
            await asyncio.sleep(0.05)
            return "B done"

        async def task_c() -> str:
            await asyncio.sleep(0.08)
            return "C done"

        async def task_d() -> str:
            await asyncio.sleep(0.03)
            return "D done"

        dag.add_task("a", task_a, priority=1)
        dag.add_task("b", task_b, priority=2)
        dag.add_task("c", task_c, dependencies=["a", "b"])
        dag.add_task("d", task_d, dependencies=["c"])

        scheduler = DAGScheduler(dag, max_workers=4)

        print("Topological order:", scheduler.get_topological_order())
        print("Layers:", scheduler.get_execution_layers())
        print("Critical path:", scheduler.get_critical_path())

        result = await scheduler.execute()
        print(f"\nExecution result: {result.to_dict()}")

        for tid, er in result.results.items():
            print(f"  {tid}: {er.to_dict()}")

    asyncio.run(main())
