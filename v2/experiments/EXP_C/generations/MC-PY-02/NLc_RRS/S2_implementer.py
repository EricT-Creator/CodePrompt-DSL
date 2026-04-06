from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ── Enums ──

class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── Exceptions ──

class CycleError(Exception):
    def __init__(self, cycle: list[str], message: str = "") -> None:
        self.cycle: list[str] = cycle
        msg = message or f"Cycle detected: {' -> '.join(cycle)}"
        super().__init__(msg)


# ── Task Node ──

@dataclass
class TaskNode:
    name: str
    fn: Callable[[], Any]
    depends_on: list[str] = field(default_factory=list)
    result: Any | None = None
    status: TaskStatus = TaskStatus.PENDING


# ── DAG Scheduler ──

class DAGScheduler:
    def __init__(self) -> None:
        self.graph: dict[str, set[str]] = {}
        self.tasks: dict[str, TaskNode] = {}

    def add_task(
        self,
        name: str,
        fn: Callable[[], Any],
        depends_on: list[str] | None = None,
    ) -> None:
        deps: list[str] = depends_on or []
        self.tasks[name] = TaskNode(name=name, fn=fn, depends_on=deps)
        self.graph[name] = set(deps)

        for dep in deps:
            if dep not in self.graph:
                self.graph[dep] = set()

    def validate(self) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in self.graph}
        parent: dict[str, str | None] = {n: None for n in self.graph}

        dependents: dict[str, set[str]] = {n: set() for n in self.graph}
        for node, deps in self.graph.items():
            for dep in deps:
                dependents[dep].add(node)

        def dfs(u: str) -> list[str] | None:
            color[u] = GRAY
            for v in dependents.get(u, set()):
                if color[v] == GRAY:
                    cycle: list[str] = [v, u]
                    curr = u
                    while curr != v:
                        curr = parent[curr]  # type: ignore
                        if curr is None:
                            break
                        cycle.append(curr)
                    cycle.reverse()
                    return cycle
                if color[v] == WHITE:
                    parent[v] = u
                    result = dfs(v)
                    if result is not None:
                        return result
            color[u] = BLACK
            return None

        for node in self.graph:
            if color[node] == WHITE:
                cycle = dfs(node)
                if cycle is not None:
                    raise CycleError(cycle)

    def topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = {n: 0 for n in self.graph}
        dependents: dict[str, list[str]] = {n: [] for n in self.graph}

        for node, deps in self.graph.items():
            in_degree[node] = len(deps)
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = []
                dependents[dep].append(node)

        queue: deque[str] = deque()
        for node, deg in in_degree.items():
            if deg == 0:
                queue.append(node)

        result: list[str] = []

        while queue:
            current = queue.popleft()
            result.append(current)

            for dependent in dependents.get(current, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) < len(self.graph):
            remaining = set(self.graph.keys()) - set(result)
            raise CycleError(
                cycle=list(remaining),
                message=f"Cycle detected involving tasks: {remaining}",
            )

        return result

    def parallel_groups(self) -> list[list[str]]:
        in_degree: dict[str, int] = {n: 0 for n in self.graph}
        dependents: dict[str, list[str]] = {n: [] for n in self.graph}

        for node, deps in self.graph.items():
            in_degree[node] = len(deps)
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = []
                dependents[dep].append(node)

        queue: deque[str] = deque()
        for node, deg in in_degree.items():
            if deg == 0:
                queue.append(node)

        groups: list[list[str]] = []
        visited_count: int = 0

        while queue:
            level: list[str] = list(queue)
            queue.clear()
            groups.append(level)
            visited_count += len(level)

            for current in level:
                for dependent in dependents.get(current, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if visited_count < len(self.graph):
            remaining = set(self.graph.keys()) - {t for g in groups for t in g}
            raise CycleError(
                cycle=list(remaining),
                message=f"Cycle detected involving tasks: {remaining}",
            )

        return groups

    def execute(self) -> dict[str, Any]:
        self.validate()
        groups = self.parallel_groups()
        results: dict[str, Any] = {}

        for group in groups:
            for task_name in group:
                task = self.tasks.get(task_name)
                if task is None:
                    continue

                task.status = TaskStatus.RUNNING
                try:
                    task.result = task.fn()
                    task.status = TaskStatus.COMPLETED
                    results[task_name] = task.result
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.result = str(e)
                    results[task_name] = None
                    raise RuntimeError(
                        f"Task '{task_name}' failed: {e}"
                    ) from e

        return results


# ── Example Usage ──

if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: {"raw": [1, 2, 3, 4, 5]})
    scheduler.add_task("fetch_config", lambda: {"multiplier": 10})
    scheduler.add_task(
        "transform",
        lambda: [x * 10 for x in [1, 2, 3, 4, 5]],
        depends_on=["fetch_data", "fetch_config"],
    )
    scheduler.add_task(
        "validate",
        lambda: True,
        depends_on=["transform"],
    )
    scheduler.add_task(
        "save",
        lambda: "saved to disk",
        depends_on=["validate"],
    )

    print("Topological order:", scheduler.topological_sort())
    print("Parallel groups:", scheduler.parallel_groups())

    results = scheduler.execute()
    print("Results:", results)

    for name, task in scheduler.tasks.items():
        print(f"  {name}: {task.status.value} -> {task.result}")

    print("\nTesting cycle detection...")
    cycle_scheduler = DAGScheduler()
    cycle_scheduler.add_task("A", lambda: None, depends_on=["C"])
    cycle_scheduler.add_task("B", lambda: None, depends_on=["A"])
    cycle_scheduler.add_task("C", lambda: None, depends_on=["B"])

    try:
        cycle_scheduler.validate()
    except CycleError as e:
        print(f"CycleError caught: {e}")
        print(f"Cycle path: {e.cycle}")
