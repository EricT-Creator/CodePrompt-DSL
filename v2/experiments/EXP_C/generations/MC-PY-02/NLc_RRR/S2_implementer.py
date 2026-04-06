from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---- Enums ----

class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---- Exceptions ----

class CycleError(Exception):
    def __init__(self, cycle: list[str], message: str = "Cycle detected in DAG") -> None:
        self.cycle: list[str] = cycle
        super().__init__(f"{message}: {' -> '.join(cycle)}")


# ---- Task Node ----

@dataclass
class TaskNode:
    name: str
    fn: Callable[[], Any]
    depends_on: list[str] = field(default_factory=list)
    result: Any | None = None
    status: TaskStatus = TaskStatus.PENDING


# ---- DAG Scheduler ----

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
        deps = depends_on or []
        self.tasks[name] = TaskNode(name=name, fn=fn, depends_on=deps)
        self.graph[name] = set(deps)

        # Ensure all dependency names exist in graph
        for dep in deps:
            if dep not in self.graph:
                self.graph[dep] = set()

    def validate(self) -> None:
        """Run DFS-based cycle detection. Raises CycleError if any cycle exists."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {name: WHITE for name in self.graph}
        parent: dict[str, str | None] = {name: None for name in self.graph}

        def _build_dependents() -> dict[str, set[str]]:
            """Build reverse adjacency: task -> set of tasks that depend on it."""
            dependents: dict[str, set[str]] = {name: set() for name in self.graph}
            for name, deps in self.graph.items():
                for dep in deps:
                    dependents[dep].add(name)
            return dependents

        dependents = _build_dependents()

        def dfs(node: str, path: list[str]) -> None:
            color[node] = GRAY
            path.append(node)

            for neighbor in dependents.get(node, set()):
                if color[neighbor] == GRAY:
                    # Found a cycle - extract cycle path
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    raise CycleError(cycle=cycle)
                elif color[neighbor] == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor, path)

            path.pop()
            color[node] = BLACK

        for node in self.graph:
            if color[node] == WHITE:
                dfs(node, [])

    def topological_sort(self) -> list[str]:
        """Kahn's algorithm for topological sort. Raises CycleError if cycle detected."""
        in_degree: dict[str, int] = {name: 0 for name in self.graph}

        # Build reverse adjacency (dependents)
        dependents: dict[str, set[str]] = {name: set() for name in self.graph}
        for name, deps in self.graph.items():
            for dep in deps:
                dependents[dep].add(name)
                in_degree[name] = in_degree.get(name, 0)

        # Compute in-degrees
        for name, deps in self.graph.items():
            in_degree[name] = len(deps)

        queue: deque[str] = deque()
        for name, degree in in_degree.items():
            if degree == 0:
                queue.append(name)

        result: list[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)

            for dependent in dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) < len(self.graph):
            # Cycle detected - find cycle for error message
            remaining = [n for n in self.graph if n not in set(result)]
            raise CycleError(cycle=remaining, message="Topological sort incomplete, cycle detected among")

        return result

    def parallel_groups(self) -> list[list[str]]:
        """Return tasks grouped by execution level for parallel execution."""
        in_degree: dict[str, int] = {}
        dependents: dict[str, set[str]] = {name: set() for name in self.graph}

        for name, deps in self.graph.items():
            in_degree[name] = len(deps)
            for dep in deps:
                dependents[dep].add(name)

        groups: list[list[str]] = []
        remaining: set[str] = set(self.graph.keys())

        queue: deque[str] = deque()
        for name in self.graph:
            if in_degree[name] == 0:
                queue.append(name)

        while queue:
            current_group: list[str] = []
            next_queue: deque[str] = deque()

            while queue:
                node = queue.popleft()
                current_group.append(node)
                remaining.discard(node)

                for dependent in dependents.get(node, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)

            if current_group:
                groups.append(sorted(current_group))

            queue = next_queue

        if remaining:
            raise CycleError(
                cycle=list(remaining),
                message="Parallel grouping incomplete, cycle detected among",
            )

        return groups

    def execute(self, max_workers: int = 4, fail_fast: bool = True) -> dict[str, Any]:
        """Execute all tasks in topological order with parallel groups."""
        self.validate()
        groups = self.parallel_groups()
        results: dict[str, Any] = {}

        for group in groups:
            if len(group) == 1:
                # Single task, run directly
                task_name = group[0]
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
                    task.result = e
                    results[task_name] = e
                    if fail_fast:
                        raise
            else:
                # Multiple tasks, run concurrently
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_name: dict[Any, str] = {}
                    for task_name in group:
                        task = self.tasks.get(task_name)
                        if task is None:
                            continue
                        task.status = TaskStatus.RUNNING
                        future = executor.submit(task.fn)
                        future_to_name[future] = task_name

                    for future in as_completed(future_to_name):
                        task_name = future_to_name[future]
                        task = self.tasks[task_name]
                        try:
                            task.result = future.result()
                            task.status = TaskStatus.COMPLETED
                            results[task_name] = task.result
                        except Exception as e:
                            task.status = TaskStatus.FAILED
                            task.result = e
                            results[task_name] = e
                            if fail_fast:
                                raise

        return results

    def reset(self) -> None:
        """Reset all task statuses and results."""
        for task in self.tasks.values():
            task.status = TaskStatus.PENDING
            task.result = None


# ---- Demo ----

if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: "raw_data")
    scheduler.add_task("parse_csv", lambda: "parsed_csv", depends_on=["fetch_data"])
    scheduler.add_task("parse_json", lambda: "parsed_json", depends_on=["fetch_data"])
    scheduler.add_task("merge", lambda: "merged", depends_on=["parse_csv", "parse_json"])
    scheduler.add_task("validate", lambda: "validated", depends_on=["merge"])
    scheduler.add_task("export", lambda: "exported", depends_on=["validate"])

    # Topological sort
    order = scheduler.topological_sort()
    print(f"Topological order: {order}")

    # Parallel groups
    groups = scheduler.parallel_groups()
    print(f"Parallel groups: {groups}")

    # Execute
    results = scheduler.execute()
    print(f"Results: {results}")

    # Task statuses
    for name, task in scheduler.tasks.items():
        print(f"  {name}: {task.status.value} -> {task.result}")

    # Cycle detection test
    print("\n--- Cycle Detection Test ---")
    bad_scheduler = DAGScheduler()
    bad_scheduler.add_task("A", lambda: None, depends_on=["C"])
    bad_scheduler.add_task("B", lambda: None, depends_on=["A"])
    bad_scheduler.add_task("C", lambda: None, depends_on=["B"])

    try:
        bad_scheduler.validate()
    except CycleError as e:
        print(f"CycleError caught: {e}")
        print(f"Cycle: {e.cycle}")
