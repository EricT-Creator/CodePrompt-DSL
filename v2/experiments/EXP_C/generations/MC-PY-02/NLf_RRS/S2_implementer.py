"""DAG Task Scheduler — hand-written topological sort with cycle detection."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Custom Exception ─────────────────────────────────────────────────────────


class CycleError(Exception):
    """Raised when a cycle is detected in the task dependency graph."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle: list[str] = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


# ── Data Classes ─────────────────────────────────────────────────────────────


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
    result: Any = None
    error: str | None = None
    duration: float = 0.0


@dataclass
class SchedulerResult:
    order: list[str]
    groups: list[ExecutionGroup]
    results: list[ExecutionResult]
    success: bool


# ── TaskScheduler ────────────────────────────────────────────────────────────


class TaskScheduler:
    """DAG-based task scheduler with topological sort and cycle detection."""

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}
        self._edges: dict[str, set[str]] = {}  # task -> set of dependencies
        self._reverse_edges: dict[str, set[str]] = {}  # task -> set of dependents

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
        self._edges[name] = deps
        self._reverse_edges.setdefault(name, set())

        for dep in deps:
            self._reverse_edges.setdefault(dep, set()).add(name)
            self._edges.setdefault(dep, set())

    def remove_task(self, name: str) -> None:
        """Remove a task from the graph."""
        if name not in self._nodes:
            raise KeyError(f"Task '{name}' not found")

        # Remove from dependents' reverse edges
        for dep in self._edges.get(name, set()):
            self._reverse_edges.get(dep, set()).discard(name)

        # Remove dependents that depend on this task
        for dependent in self._reverse_edges.get(name, set()):
            self._edges.get(dependent, set()).discard(name)

        del self._nodes[name]
        self._edges.pop(name, None)
        self._reverse_edges.pop(name, None)

    def topological_sort(self) -> list[str]:
        """Perform topological sort using Kahn's algorithm. Raises CycleError if cycle detected."""
        if not self._nodes:
            return []

        # Compute in-degrees
        in_degree: dict[str, int] = {name: 0 for name in self._nodes}
        for name, deps in self._edges.items():
            if name in self._nodes:
                for dep in deps:
                    if dep in self._nodes:
                        in_degree[name] = in_degree.get(name, 0)

        # Recompute properly
        in_degree = {name: 0 for name in self._nodes}
        for name in self._nodes:
            for dep in self._edges.get(name, set()):
                if dep in self._nodes:
                    in_degree[name] += 1

        queue: deque[str] = deque()
        for name, deg in in_degree.items():
            if deg == 0:
                queue.append(name)

        sorted_order: list[str] = []
        while queue:
            node = queue.popleft()
            sorted_order.append(node)
            for dependent in self._reverse_edges.get(node, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(sorted_order) < len(self._nodes):
            remaining = set(self._nodes.keys()) - set(sorted_order)
            cycle = self._find_cycle(remaining)
            raise CycleError(cycle)

        return sorted_order

    def detect_cycle(self) -> list[str] | None:
        """Returns the cycle path if found, else None."""
        try:
            self.topological_sort()
            return None
        except CycleError as e:
            return e.cycle

    def parallel_groups(self) -> list[ExecutionGroup]:
        """Group independent tasks by execution level using Kahn's algorithm."""
        if not self._nodes:
            return []

        in_degree: dict[str, int] = {name: 0 for name in self._nodes}
        for name in self._nodes:
            for dep in self._edges.get(name, set()):
                if dep in self._nodes:
                    in_degree[name] += 1

        current_level: list[str] = [n for n, d in in_degree.items() if d == 0]
        groups: list[ExecutionGroup] = []
        level = 0
        visited = 0

        while current_level:
            groups.append(ExecutionGroup(level=level, tasks=sorted(current_level)))
            visited += len(current_level)
            next_level: list[str] = []
            for node in current_level:
                for dependent in self._reverse_edges.get(node, set()):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_level.append(dependent)
            current_level = next_level
            level += 1

        if visited < len(self._nodes):
            remaining = set(self._nodes.keys()) - {
                t for g in groups for t in g.tasks
            }
            cycle = self._find_cycle(remaining)
            raise CycleError(cycle)

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
                # Check if any dependency failed
                node = self._nodes[task_name]
                dep_failed = any(d in failed_tasks for d in node.dependencies)

                if dep_failed:
                    results.append(ExecutionResult(
                        task=task_name,
                        success=False,
                        error="Skipped: dependency failed",
                        duration=0.0,
                    ))
                    failed_tasks.add(task_name)
                    all_success = False
                    continue

                start = time.perf_counter()
                try:
                    result = node.callable()
                    duration = time.perf_counter() - start
                    results.append(ExecutionResult(
                        task=task_name,
                        success=True,
                        result=result,
                        duration=round(duration, 6),
                    ))
                except Exception as e:
                    duration = time.perf_counter() - start
                    results.append(ExecutionResult(
                        task=task_name,
                        success=False,
                        error=str(e),
                        duration=round(duration, 6),
                    ))
                    failed_tasks.add(task_name)
                    all_success = False

        return SchedulerResult(
            order=order,
            groups=groups,
            results=results,
            success=all_success,
        )

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _find_cycle(self, nodes: set[str]) -> list[str]:
        """Extract a cycle path from a set of nodes using DFS."""
        visited: set[str] = set()
        rec_stack: list[str] = []
        rec_set: set[str] = set()

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            rec_stack.append(node)
            rec_set.add(node)

            for dep in self._edges.get(node, set()):
                if dep not in nodes:
                    continue
                if dep in rec_set:
                    # Found cycle — extract path
                    idx = rec_stack.index(dep)
                    return rec_stack[idx:] + [dep]
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result

            rec_stack.pop()
            rec_set.discard(node)
            return None

        for node in nodes:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle

        return list(nodes)[:3] + [list(nodes)[0]] if nodes else []


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scheduler = TaskScheduler()

    scheduler.add_task("fetch_data", lambda: {"rows": 100})
    scheduler.add_task("validate", lambda: "validated", dependencies=["fetch_data"])
    scheduler.add_task("parse_csv", lambda: "parsed", dependencies=["fetch_data"])
    scheduler.add_task("transform", lambda: "transformed", dependencies=["validate", "parse_csv"])
    scheduler.add_task("load_db", lambda: "loaded", dependencies=["transform"])
    scheduler.add_task("generate_report", lambda: "report done", dependencies=["transform"])
    scheduler.add_task("notify", lambda: "notified", dependencies=["load_db", "generate_report"])

    print("Order:", scheduler.topological_sort())
    print("Groups:", [(g.level, g.tasks) for g in scheduler.parallel_groups()])

    result = scheduler.execute()
    print(f"Success: {result.success}")
    for r in result.results:
        print(f"  {r.task}: {'OK' if r.success else 'FAIL'} ({r.duration:.4f}s)")

    # Test cycle detection
    scheduler2 = TaskScheduler()
    scheduler2.add_task("A", lambda: None, dependencies=["C"])
    scheduler2.add_task("B", lambda: None, dependencies=["A"])
    scheduler2.add_task("C", lambda: None, dependencies=["B"])

    cycle = scheduler2.detect_cycle()
    print(f"Cycle: {cycle}")
