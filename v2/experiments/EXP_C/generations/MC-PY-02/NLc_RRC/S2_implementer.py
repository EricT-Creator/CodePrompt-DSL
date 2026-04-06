from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ─── Exceptions ───────────────────────────────────────────────────────────────

class CycleError(Exception):
    def __init__(self, cycle: list[str], message: str = "") -> None:
        self.cycle: list[str] = cycle
        msg = message or f"Cycle detected: {' -> '.join(cycle)}"
        super().__init__(msg)


# ─── Task Status ──────────────────────────────────────────────────────────────

class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── Task Node ────────────────────────────────────────────────────────────────

@dataclass
class TaskNode:
    name: str
    fn: Callable[[], Any]
    depends_on: list[str] = field(default_factory=list)
    result: Any | None = None
    status: TaskStatus = TaskStatus.PENDING


# ─── DAG Scheduler ────────────────────────────────────────────────────────────

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
        deps: list[str] = depends_on if depends_on is not None else []
        self.tasks[name] = TaskNode(name=name, fn=fn, depends_on=deps)
        self.graph[name] = set(deps)
        for dep in deps:
            if dep not in self.graph:
                self.graph[dep] = set()

    def validate(self) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {node: WHITE for node in self.graph}
        parent: dict[str, str | None] = {node: None for node in self.graph}

        dependents: dict[str, set[str]] = {node: set() for node in self.graph}
        for node, deps in self.graph.items():
            for dep in deps:
                dependents[dep].add(node)

        def dfs(node: str) -> None:
            color[node] = GRAY
            for neighbor in dependents.get(node, set()):
                if color[neighbor] == GRAY:
                    cycle = _extract_cycle(node, neighbor, parent)
                    raise CycleError(cycle)
                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor)
            color[node] = BLACK

        for node in self.graph:
            if color[node] == WHITE:
                dfs(node)

    def topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = {node: 0 for node in self.graph}
        dependents: dict[str, list[str]] = {node: [] for node in self.graph}

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
            node = queue.popleft()
            result.append(node)
            for dependent in dependents.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) < len(self.graph):
            remaining = set(self.graph.keys()) - set(result)
            raise CycleError(
                cycle=list(remaining),
                message=f"Cycle detected among tasks: {remaining}",
            )

        return result

    def parallel_groups(self) -> list[list[str]]:
        in_degree: dict[str, int] = {node: 0 for node in self.graph}
        dependents: dict[str, list[str]] = {node: [] for node in self.graph}

        for node, deps in self.graph.items():
            in_degree[node] = len(deps)
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = []
                dependents[dep].append(node)

        current_level: list[str] = [n for n, d in in_degree.items() if d == 0]
        groups: list[list[str]] = []
        visited: int = 0

        while current_level:
            groups.append(sorted(current_level))
            visited += len(current_level)
            next_level: list[str] = []
            for node in current_level:
                for dependent in dependents.get(node, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_level.append(dependent)
            current_level = next_level

        if visited < len(self.graph):
            remaining = set(self.graph.keys()) - {n for g in groups for n in g}
            raise CycleError(
                cycle=list(remaining),
                message=f"Cycle detected among tasks: {remaining}",
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
                    raise

        return results


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_cycle(
    current: str,
    back_to: str,
    parent: dict[str, str | None],
) -> list[str]:
    cycle: list[str] = [back_to]
    node: str | None = current
    while node is not None and node != back_to:
        cycle.append(node)
        node = parent.get(node)
    cycle.append(back_to)
    cycle.reverse()
    return cycle


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: {"raw": [1, 2, 3]})
    scheduler.add_task("parse_config", lambda: {"threshold": 2})
    scheduler.add_task(
        "filter_data",
        lambda: [x for x in [1, 2, 3] if x > 2],
        depends_on=["fetch_data", "parse_config"],
    )
    scheduler.add_task(
        "transform",
        lambda: [6],
        depends_on=["filter_data"],
    )
    scheduler.add_task(
        "save_results",
        lambda: "saved",
        depends_on=["transform"],
    )

    print("Topological order:", scheduler.topological_sort())
    print("Parallel groups:", scheduler.parallel_groups())

    results = scheduler.execute()
    print("Execution results:", results)

    for name, task in scheduler.tasks.items():
        print(f"  {name}: status={task.status.value}, result={task.result}")

    print("\n--- Cycle detection test ---")
    cyclic = DAGScheduler()
    cyclic.add_task("A", lambda: None, depends_on=["C"])
    cyclic.add_task("B", lambda: None, depends_on=["A"])
    cyclic.add_task("C", lambda: None, depends_on=["B"])
    try:
        cyclic.validate()
    except CycleError as e:
        print(f"CycleError caught: {e}")
        print(f"Cycle path: {e.cycle}")
