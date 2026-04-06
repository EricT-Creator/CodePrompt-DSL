from __future__ import annotations

from typing import Callable, Any, Dict, List, Set, Optional
from collections import defaultdict, deque


class CycleError(Exception):
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle)}")


class DAGScheduler:
    def __init__(self):
        self._tasks: Dict[str, Callable[[], Any]] = {}
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        self._tasks[name] = func
        if name not in self._dependencies:
            self._dependencies[name] = set()

    def add_dependency(self, task: str, depends_on: str) -> None:
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' not registered")
        if depends_on not in self._tasks:
            raise ValueError(f"Task '{depends_on}' not registered")
        self._dependencies[task].add(depends_on)
        self._dependents[depends_on].add(task)

    def validate(self) -> None:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self._dependencies.get(node, set()):
                if dep not in visited:
                    dfs(dep)
                elif dep in rec_stack:
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    raise CycleError(cycle)

            path.pop()
            rec_stack.discard(node)

        for task_name in self._tasks:
            if task_name not in visited:
                dfs(task_name)

    def get_execution_order(self) -> List[str]:
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        for name, deps in self._dependencies.items():
            in_degree[name] = len(deps)

        queue: deque[str] = deque()
        for name, deg in in_degree.items():
            if deg == 0:
                queue.append(name)

        order: List[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in self._dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        for name, deps in self._dependencies.items():
            in_degree[name] = len(deps)

        groups: List[Set[str]] = []
        remaining = dict(in_degree)

        while remaining:
            current_group: Set[str] = set()
            for name, deg in remaining.items():
                if deg == 0:
                    current_group.add(name)

            if not current_group:
                break

            groups.append(current_group)

            for name in current_group:
                del remaining[name]

            for name in remaining:
                deps_in_group = self._dependencies[name] & current_group
                remaining[name] -= len(deps_in_group)

        return groups

    def execute(self) -> Dict[str, Any]:
        order = self.get_execution_order()
        results: Dict[str, Any] = {}

        for task_name in order:
            func = self._tasks[task_name]
            try:
                results[task_name] = func()
            except Exception as e:
                results[task_name] = e
                raise RuntimeError(
                    f"Task '{task_name}' failed: {e}"
                ) from e

        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: print("Fetching data...") or "data")
    scheduler.add_task("parse", lambda: print("Parsing...") or "parsed")
    scheduler.add_task("validate", lambda: print("Validating...") or "valid")
    scheduler.add_task("transform", lambda: print("Transforming...") or "transformed")
    scheduler.add_task("load", lambda: print("Loading...") or "loaded")
    scheduler.add_task("report", lambda: print("Reporting...") or "done")

    scheduler.add_dependency("parse", "fetch_data")
    scheduler.add_dependency("validate", "parse")
    scheduler.add_dependency("transform", "validate")
    scheduler.add_dependency("load", "transform")
    scheduler.add_dependency("report", "load")

    print("Execution order:", scheduler.get_execution_order())
    print("Parallel groups:", scheduler.get_parallel_groups())
    print()
    results = scheduler.execute()
    print("\nResults:", results)

    print("\n--- Testing cycle detection ---")
    s2 = DAGScheduler()
    s2.add_task("A", lambda: None)
    s2.add_task("B", lambda: None)
    s2.add_task("C", lambda: None)
    s2.add_dependency("A", "B")
    s2.add_dependency("B", "C")
    s2.add_dependency("C", "A")
    try:
        s2.validate()
    except CycleError as e:
        print(f"CycleError caught: {e}")
