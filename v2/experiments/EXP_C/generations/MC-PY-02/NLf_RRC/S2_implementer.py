"""DAG Task Scheduler with topological sort, cycle detection, and parallel grouping."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Exceptions ───────────────────────────────────────────────────────────────


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
    result: Any
    error: str | None
    duration: float


@dataclass
class SchedulerResult:
    order: list[str]
    groups: list[ExecutionGroup]
    results: list[ExecutionResult]
    success: bool


# ── TaskScheduler ────────────────────────────────────────────────────────────


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
        self._edges[name] = deps
        self._reverse_edges.setdefault(name, set())

        for dep in deps:
            self._reverse_edges.setdefault(dep, set()).add(name)
            self._edges.setdefault(dep, set())

    def remove_task(self, name: str) -> None:
        """Remove a task and all its edges."""
        if name not in self._nodes:
            return

        # Remove from dependents' dependency lists
        for dependent in self._reverse_edges.get(name, set()):
            self._edges.get(dependent, set()).discard(name)

        # Remove from dependencies' reverse edge lists
        for dep in self._edges.get(name, set()):
            self._reverse_edges.get(dep, set()).discard(name)

        del self._nodes[name]
        self._edges.pop(name, None)
        self._reverse_edges.pop(name, None)

    def topological_sort(self) -> list[str]:
        """Perform topological sort using Kahn's algorithm. Raises CycleError if cycle found."""
        if not self._nodes:
            return []

        # Compute in-degrees
        in_degree: dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = len(self._edges.get(node, set()) & set(self._nodes.keys()))

        # Initialize queue with zero in-degree nodes
        queue: deque[str] = deque()
        for node, degree in in_degree.items():
            if degree == 0:
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
            # Cycle detected — find the cycle path
            remaining = set(self._nodes.keys()) - set(sorted_order)
            cycle_path = self._find_cycle_path(remaining)
            raise CycleError(cycle_path)

        return sorted_order

    def detect_cycle(self) -> list[str] | None:
        """Returns the cycle path if found, else None."""
        try:
            self.topological_sort()
            return None
        except CycleError as exc:
            return exc.cycle

    def parallel_groups(self) -> list[ExecutionGroup]:
        """Group independent tasks by execution level using Kahn's algorithm."""
        if not self._nodes:
            return []

        in_degree: dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = len(self._edges.get(node, set()) & set(self._nodes.keys()))

        queue: deque[str] = deque()
        for node, degree in in_degree.items():
            if degree == 0:
                queue.append(node)

        groups: list[ExecutionGroup] = []
        level = 0
        processed = 0

        while queue:
            current_batch: list[str] = list(queue)
            queue.clear()

            groups.append(ExecutionGroup(level=level, tasks=sorted(current_batch)))
            processed += len(current_batch)

            for node in current_batch:
                for dependent in self._reverse_edges.get(node, set()):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            queue.append(dependent)

            level += 1

        if processed < len(self._nodes):
            remaining = set(self._nodes.keys()) - {
                t for g in groups for t in g.tasks
            }
            cycle_path = self._find_cycle_path(remaining)
            raise CycleError(cycle_path)

        return groups

    def execute(self) -> SchedulerResult:
        """Run tasks in dependency order. Returns execution results."""
        order = self.topological_sort()
        groups = self.parallel_groups()
        results: list[ExecutionResult] = []
        all_success = True
        failed_tasks: set[str] = set()

        for group in groups:
            for task_name in group.tasks:
                node = self._nodes[task_name]

                # Check if any dependency failed
                deps_failed = bool(node.dependencies & failed_tasks)
                if deps_failed:
                    results.append(
                        ExecutionResult(
                            task=task_name,
                            success=False,
                            result=None,
                            error="Skipped: dependency failed",
                            duration=0.0,
                        )
                    )
                    failed_tasks.add(task_name)
                    all_success = False
                    continue

                start = time.monotonic()
                try:
                    result = node.callable()
                    duration = time.monotonic() - start
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
                    duration = time.monotonic() - start
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

    # ── Private Helpers ──────────────────────────────────────────────────

    def _find_cycle_path(self, remaining: set[str]) -> list[str]:
        """Find actual cycle path using DFS among remaining nodes."""
        visited: set[str] = set()
        rec_stack: dict[str, int] = {}
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            rec_stack[node] = len(path)
            path.append(node)

            for dep in self._edges.get(node, set()):
                if dep not in remaining:
                    continue
                if dep in rec_stack:
                    idx = rec_stack[dep]
                    cycle = path[idx:] + [dep]
                    return cycle
                if dep not in visited:
                    result = dfs(dep)
                    if result is not None:
                        return result

            path.pop()
            del rec_stack[node]
            return None

        for node in remaining:
            if node not in visited:
                cycle = dfs(node)
                if cycle is not None:
                    return cycle

        return list(remaining)[:5] + [list(remaining)[0]] if remaining else []


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scheduler = TaskScheduler()

    scheduler.add_task("fetch_data", lambda: {"rows": 100})
    scheduler.add_task("validate", lambda: "validated", dependencies=["fetch_data"])
    scheduler.add_task("parse_csv", lambda: "parsed", dependencies=["fetch_data"])
    scheduler.add_task("transform", lambda: "transformed", dependencies=["validate", "parse_csv"])
    scheduler.add_task("load_db", lambda: "loaded", dependencies=["transform"])
    scheduler.add_task("send_report", lambda: "sent", dependencies=["load_db"])

    print("Topological order:", scheduler.topological_sort())
    print()

    groups = scheduler.parallel_groups()
    for g in groups:
        print(f"Level {g.level}: {g.tasks}")
    print()

    result = scheduler.execute()
    print(f"Success: {result.success}")
    for r in result.results:
        print(f"  {r.task}: {'OK' if r.success else 'FAIL'} ({r.duration:.4f}s) -> {r.result or r.error}")
