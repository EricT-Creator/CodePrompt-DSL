"""DAG Task Scheduler — Python 3.10+ standard library only."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable


# ─── Custom Exception ─────────────────────────────────────────


class CycleError(Exception):
    """Raised when a cycle is detected in the task dependency graph."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


# ─── Dataclasses ──────────────────────────────────────────────


@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]
    dependencies: set[str] = field(default_factory=set)


@dataclass
class ExecutionGroup:
    level: int
    tasks: list[str]


@dataclass
class ExecutionResult:
    task: str
    success: bool
    result: Any
    error: str | None
    duration: float


@dataclass
class SchedulerResult:
    order: list[str]
    groups: list[ExecutionGroup]
    results: list[ExecutionResult]
    success: bool


# ─── Task Scheduler ───────────────────────────────────────────


class TaskScheduler:
    """DAG task scheduler with topological sort, cycle detection, and parallel grouping."""

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}
        self._edges: dict[str, set[str]] = {}  # task -> dependencies (incoming)
        self._reverse_edges: dict[str, set[str]] = {}  # task -> dependents (outgoing)

    def add_task(
        self,
        name: str,
        callable: Callable[[], Any],
        dependencies: list[str] | None = None,
    ) -> None:
        """Add a task with optional dependencies."""
        deps = set(dependencies) if dependencies else set()
        node = TaskNode(name=name, callable=callable, dependencies=deps)
        self._nodes[name] = node
        self._edges[name] = set(deps)

        if name not in self._reverse_edges:
            self._reverse_edges[name] = set()

        for dep in deps:
            if dep not in self._edges:
                self._edges[dep] = set()
            if dep not in self._reverse_edges:
                self._reverse_edges[dep] = set()
            self._reverse_edges[dep].add(name)

    def remove_task(self, name: str) -> None:
        """Remove a task from the scheduler."""
        if name not in self._nodes:
            return

        # Remove from dependents' dependency sets
        for dependent in self._reverse_edges.get(name, set()):
            self._edges.get(dependent, set()).discard(name)

        # Remove from dependencies' reverse edge sets
        for dep in self._edges.get(name, set()):
            self._reverse_edges.get(dep, set()).discard(name)

        del self._nodes[name]
        self._edges.pop(name, None)
        self._reverse_edges.pop(name, None)

    def topological_sort(self) -> list[str]:
        """Perform topological sort using Kahn's algorithm. Raises CycleError if a cycle exists."""
        # Compute in-degrees
        in_degree: dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = len(self._edges.get(node, set()) & set(self._nodes.keys()))

        # Initialize queue with zero in-degree nodes
        queue: deque[str] = deque()
        for node, deg in in_degree.items():
            if deg == 0:
                queue.append(node)

        sorted_order: list[str] = []

        while queue:
            current = queue.popleft()
            sorted_order.append(current)

            for dependent in self._reverse_edges.get(current, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(sorted_order) < len(self._nodes):
            # Cycle detected — extract cycle path
            remaining = set(self._nodes.keys()) - set(sorted_order)
            cycle = self._extract_cycle(remaining)
            raise CycleError(cycle)

        return sorted_order

    def _extract_cycle(self, remaining: set[str]) -> list[str]:
        """Extract cycle path from remaining nodes using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in remaining}
        parent: dict[str, str | None] = {n: None for n in remaining}

        def dfs(node: str) -> list[str] | None:
            color[node] = GRAY
            for dep in self._edges.get(node, set()):
                if dep not in remaining:
                    continue
                if color[dep] == GRAY:
                    # Found cycle — reconstruct
                    cycle = [dep, node]
                    current = node
                    while current != dep:
                        current = parent.get(current, dep) or dep
                        if current == dep:
                            break
                        cycle.append(current)
                    cycle.reverse()
                    cycle.append(dep)
                    return cycle
                if color[dep] == WHITE:
                    parent[dep] = node
                    result = dfs(dep)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for node in remaining:
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return result

        return list(remaining)[:3] + [list(remaining)[0]]

    def detect_cycle(self) -> list[str] | None:
        """Returns the cycle path if found, else None."""
        try:
            self.topological_sort()
            return None
        except CycleError as e:
            return e.cycle

    def parallel_groups(self) -> list[ExecutionGroup]:
        """Group independent tasks for parallel execution using Kahn's level-based approach."""
        in_degree: dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = len(self._edges.get(node, set()) & set(self._nodes.keys()))

        queue: deque[str] = deque()
        for node, deg in in_degree.items():
            if deg == 0:
                queue.append(node)

        groups: list[ExecutionGroup] = []
        level = 0

        while queue:
            current_level: list[str] = []
            next_queue: deque[str] = deque()

            while queue:
                node = queue.popleft()
                current_level.append(node)

            for node in current_level:
                for dependent in self._reverse_edges.get(node, set()):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_queue.append(dependent)

            groups.append(ExecutionGroup(level=level, tasks=sorted(current_level)))
            level += 1
            queue = next_queue

        return groups

    def execute(self) -> SchedulerResult:
        """Run tasks in dependency order. Returns SchedulerResult."""
        order = self.topological_sort()
        groups = self.parallel_groups()
        results: list[ExecutionResult] = []
        all_success = True
        failed_tasks: set[str] = set()

        for group in groups:
            for task_name in group.tasks:
                node = self._nodes.get(task_name)
                if not node:
                    continue

                # Check if any dependency failed
                dep_failed = any(d in failed_tasks for d in node.dependencies)
                if dep_failed:
                    results.append(
                        ExecutionResult(
                            task=task_name,
                            success=False,
                            result=None,
                            error="Dependency failed",
                            duration=0.0,
                        )
                    )
                    failed_tasks.add(task_name)
                    all_success = False
                    continue

                start = time.perf_counter()
                try:
                    result = node.callable()
                    duration = time.perf_counter() - start
                    results.append(
                        ExecutionResult(
                            task=task_name,
                            success=True,
                            result=result,
                            error=None,
                            duration=duration,
                        )
                    )
                except Exception as exc:
                    duration = time.perf_counter() - start
                    results.append(
                        ExecutionResult(
                            task=task_name,
                            success=False,
                            result=None,
                            error=str(exc),
                            duration=duration,
                        )
                    )
                    failed_tasks.add(task_name)
                    all_success = False

        return SchedulerResult(
            order=order,
            groups=groups,
            results=results,
            success=all_success,
        )


# ─── Main (demonstration) ────────────────────────────────────

if __name__ == "__main__":
    scheduler = TaskScheduler()

    scheduler.add_task("fetch_data", lambda: {"rows": 100})
    scheduler.add_task("validate", lambda: "validated", dependencies=["fetch_data"])
    scheduler.add_task("parse_csv", lambda: "parsed", dependencies=["fetch_data"])
    scheduler.add_task("transform", lambda: "transformed", dependencies=["validate", "parse_csv"])
    scheduler.add_task("load_db", lambda: "loaded", dependencies=["transform"])
    scheduler.add_task("generate_report", lambda: "report_done", dependencies=["transform"])

    print("Topological order:", scheduler.topological_sort())
    print("Parallel groups:")
    for g in scheduler.parallel_groups():
        print(f"  Level {g.level}: {g.tasks}")

    result = scheduler.execute()
    print(f"\nExecution success: {result.success}")
    for r in result.results:
        print(f"  {r.task}: {'OK' if r.success else 'FAIL'} ({r.duration:.4f}s)")

    # Cycle detection demo
    cycle_sched = TaskScheduler()
    cycle_sched.add_task("A", lambda: None, dependencies=["C"])
    cycle_sched.add_task("B", lambda: None, dependencies=["A"])
    cycle_sched.add_task("C", lambda: None, dependencies=["B"])

    cycle = cycle_sched.detect_cycle()
    print(f"\nCycle detected: {cycle}")
