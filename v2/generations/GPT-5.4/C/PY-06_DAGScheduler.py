from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Callable


class CycleError(Exception):
    pass


class DAGScheduler:
    def __init__(self) -> None:
        self._tasks: dict[str, Callable[[], Any]] = {}
        self._dependencies: dict[str, set[str]] = defaultdict(set)
        self._dependents: dict[str, set[str]] = defaultdict(set)

    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already exists")
        self._tasks[name] = func
        self._dependencies.setdefault(name, set())
        self._dependents.setdefault(name, set())

    def add_dependency(self, task: str, depends_on: str) -> None:
        if task not in self._tasks or depends_on not in self._tasks:
            raise KeyError("Both task and dependency must be added before linking")
        if task == depends_on:
            raise CycleError("A task cannot depend on itself")
        self._dependencies[task].add(depends_on)
        self._dependents[depends_on].add(task)

    def validate(self) -> None:
        self._topological_layers(raise_on_cycle=True)

    def get_execution_order(self) -> list[str]:
        layers = self._topological_layers(raise_on_cycle=True)
        ordered: list[str] = []
        for layer in layers:
            ordered.extend(sorted(layer))
        return ordered

    def get_parallel_groups(self) -> list[set[str]]:
        return [set(group) for group in self._topological_layers(raise_on_cycle=True)]

    def execute(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for task_name in self.get_execution_order():
            results[task_name] = self._tasks[task_name]()
        return results

    def _topological_layers(self, raise_on_cycle: bool) -> list[set[str]]:
        indegree = {task: len(self._dependencies[task]) for task in self._tasks}
        ready = deque(sorted(name for name, degree in indegree.items() if degree == 0))
        layers: list[set[str]] = []
        processed = 0

        while ready:
            layer_size = len(ready)
            current_layer: set[str] = set()
            for _ in range(layer_size):
                task_name = ready.popleft()
                current_layer.add(task_name)
                processed += 1
                for dependent in sorted(self._dependents[task_name]):
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        ready.append(dependent)
            layers.append(current_layer)

        if raise_on_cycle and processed != len(self._tasks):
            remaining = sorted(name for name, degree in indegree.items() if degree > 0)
            raise CycleError(f"Cycle detected involving: {', '.join(remaining)}")
        return layers


if __name__ == "__main__":
    scheduler = DAGScheduler()
    scheduler.add_task("fetch", lambda: "fetch done")
    scheduler.add_task("clean", lambda: "clean done")
    scheduler.add_task("train", lambda: "train done")
    scheduler.add_task("report", lambda: "report done")
    scheduler.add_dependency("clean", "fetch")
    scheduler.add_dependency("train", "clean")
    scheduler.add_dependency("report", "train")
    scheduler.validate()
    print("order:", scheduler.get_execution_order())
    print("parallel groups:", scheduler.get_parallel_groups())
    print("results:", scheduler.execute())
