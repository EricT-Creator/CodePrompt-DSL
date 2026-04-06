from collections import deque
from typing import Callable, Dict, List, Set, Any


class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAGScheduler:
    def __init__(self):
        self._tasks: Dict[str, Callable[[], Any]] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._dependents: Dict[str, Set[str]] = {}

    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already exists")
        self._tasks[name] = func
        if name not in self._dependencies:
            self._dependencies[name] = set()
        if name not in self._dependents:
            self._dependents[name] = set()

    def add_dependency(self, task: str, dependency: str) -> None:
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' not registered")
        if dependency not in self._tasks:
            raise ValueError(f"Dependency '{dependency}' not registered")
        self._dependencies[task].add(dependency)
        self._dependents[dependency].add(task)

    def validate(self) -> bool:
        visited: Set[str] = set()
        in_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            in_stack.add(node)
            path.append(node)

            for dep in self._dependencies.get(node, set()):
                if dep in in_stack:
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    raise CycleError(
                        f"Cycle detected: {' -> '.join(cycle)}"
                    )
                if dep not in visited:
                    dfs(dep)

            path.pop()
            in_stack.remove(node)

        for task_name in self._tasks:
            if task_name not in visited:
                dfs(task_name)

        return True

    def get_execution_order(self) -> List[str]:
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        for name in self._tasks:
            for dep in self._dependencies.get(name, set()):
                in_degree[name] += 1

        queue: deque = deque()
        for name, degree in in_degree.items():
            if degree == 0:
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

    def get_parallel_groups(self) -> List[List[str]]:
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        for name in self._tasks:
            for dep in self._dependencies.get(name, set()):
                in_degree[name] += 1

        groups: List[List[str]] = []
        remaining = dict(in_degree)

        while remaining:
            current_group = [
                name for name, degree in remaining.items() if degree == 0
            ]
            if not current_group:
                raise CycleError("Unexpected cycle detected during grouping")

            groups.append(sorted(current_group))

            for name in current_group:
                del remaining[name]
                for dependent in self._dependents.get(name, set()):
                    if dependent in remaining:
                        remaining[dependent] -= 1

        return groups

    def execute(self) -> Dict[str, Any]:
        order = self.get_execution_order()
        results: Dict[str, Any] = {}

        for task_name in order:
            func = self._tasks[task_name]
            try:
                results[task_name] = {"status": "success", "result": func()}
            except Exception as e:
                results[task_name] = {"status": "error", "error": str(e)}

        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: "raw data fetched")
    scheduler.add_task("clean_data", lambda: "data cleaned")
    scheduler.add_task("validate", lambda: "data validated")
    scheduler.add_task("transform", lambda: "data transformed")
    scheduler.add_task("load", lambda: "data loaded")
    scheduler.add_task("notify", lambda: "notification sent")

    scheduler.add_dependency("clean_data", "fetch_data")
    scheduler.add_dependency("validate", "clean_data")
    scheduler.add_dependency("transform", "validate")
    scheduler.add_dependency("load", "transform")
    scheduler.add_dependency("notify", "load")

    print("Validation:", scheduler.validate())
    print("\nExecution order:", scheduler.get_execution_order())
    print("\nParallel groups:")
    for i, group in enumerate(scheduler.get_parallel_groups()):
        print(f"  Stage {i + 1}: {group}")

    print("\nExecution results:")
    results = scheduler.execute()
    for task, result in results.items():
        print(f"  {task}: {result}")

    print("\n--- Testing cycle detection ---")
    cyclic = DAGScheduler()
    cyclic.add_task("A", lambda: None)
    cyclic.add_task("B", lambda: None)
    cyclic.add_task("C", lambda: None)
    cyclic.add_dependency("A", "B")
    cyclic.add_dependency("B", "C")
    cyclic.add_dependency("C", "A")
    try:
        cyclic.validate()
    except CycleError as e:
        print(f"  CycleError caught: {e}")
