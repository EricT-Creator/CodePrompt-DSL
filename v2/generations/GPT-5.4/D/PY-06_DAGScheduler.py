from __future__ import annotations

from collections import defaultdict
from typing import Callable


class CycleError(Exception):
    pass


class DAGScheduler:
    def __init__(self) -> None:
        self._tasks: dict[str, Callable[[], object]] = {}
        self._dependencies: dict[str, set[str]] = defaultdict(set)
        self._dependents: dict[str, set[str]] = defaultdict(set)

    def add_task(self, name: str, func: Callable[[], object]) -> None:
        if not name.strip():
            raise ValueError("Task name must not be empty")
        if name in self._tasks:
            raise ValueError(f"Task already exists: {name}")
        self._tasks[name] = func
        self._dependencies[name]
        self._dependents[name]

    def add_dependency(self, task: str, dependency: str) -> None:
        if task not in self._tasks:
            raise KeyError(f"Unknown task: {task}")
        if dependency not in self._tasks:
            raise KeyError(f"Unknown dependency: {dependency}")
        if task == dependency:
            raise CycleError("Task cannot depend on itself")

        self._dependencies[task].add(dependency)
        self._dependents[dependency].add(task)

    def validate(self) -> None:
        state: dict[str, int] = {name: 0 for name in self._tasks}
        trail: list[str] = []

        def dfs(node: str) -> None:
            if state[node] == 1:
                cycle_start = trail.index(node)
                cycle = trail[cycle_start:] + [node]
                raise CycleError("Cycle detected: " + " -> ".join(cycle))
            if state[node] == 2:
                return

            state[node] = 1
            trail.append(node)
            for dependency in sorted(self._dependencies[node]):
                dfs(dependency)
            trail.pop()
            state[node] = 2

        for task_name in sorted(self._tasks):
            if state[task_name] == 0:
                dfs(task_name)

    def get_execution_order(self) -> list[str]:
        self.validate()
        indegree = {name: len(self._dependencies[name]) for name in self._tasks}
        ready = sorted(name for name, count in indegree.items() if count == 0)
        order: list[str] = []

        while ready:
            current = ready.pop(0)
            order.append(current)
            for dependent in sorted(self._dependents[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
            ready.sort()

        if len(order) != len(self._tasks):
            raise CycleError("Unable to resolve a complete execution order")
        return order

    def get_parallel_groups(self) -> list[list[str]]:
        self.validate()
        indegree = {name: len(self._dependencies[name]) for name in self._tasks}
        available = sorted(name for name, count in indegree.items() if count == 0)
        groups: list[list[str]] = []

        while available:
            current_group = available[:]
            groups.append(current_group)
            next_available: list[str] = []
            for task_name in current_group:
                for dependent in sorted(self._dependents[task_name]):
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        next_available.append(dependent)
            available = sorted(next_available)

        if sum(len(group) for group in groups) != len(self._tasks):
            raise CycleError("Unable to compute parallel groups for the DAG")
        return groups

    def execute(self) -> dict[str, object]:
        results: dict[str, object] = {}
        for task_name in self.get_execution_order():
            results[task_name] = self._tasks[task_name]()
        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()
    scheduler.add_task("fetch", lambda: "fetch done")
    scheduler.add_task("transform", lambda: "transform done")
    scheduler.add_task("report", lambda: "report done")
    scheduler.add_dependency("transform", "fetch")
    scheduler.add_dependency("report", "transform")

    print("execution order:", scheduler.get_execution_order())
    print("parallel groups:", scheduler.get_parallel_groups())
    print("results:", scheduler.execute())
