from typing import Callable, Dict, List, Set, Any


class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAGScheduler:
    def __init__(self):
        self._tasks: Dict[str, Callable[[], Any]] = {}
        self._dependencies: Dict[str, Set[str]] = {}

    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already exists")
        self._tasks[name] = func
        if name not in self._dependencies:
            self._dependencies[name] = set()

    def add_dependency(self, task: str, depends_on: str) -> None:
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' not found")
        if depends_on not in self._tasks:
            raise ValueError(f"Dependency '{depends_on}' not found")
        self._dependencies[task].add(depends_on)

    def validate(self) -> bool:
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
                    raise CycleError(
                        f"Cycle detected: {' -> '.join(cycle)}"
                    )

            path.pop()
            rec_stack.remove(node)

        for task_name in self._tasks:
            if task_name not in visited:
                dfs(task_name)

        return True

    def get_execution_order(self) -> List[str]:
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        dependents: Dict[str, List[str]] = {name: [] for name in self._tasks}

        for task, deps in self._dependencies.items():
            in_degree[task] = len(deps)
            for dep in deps:
                dependents[dep].append(task)

        queue: List[str] = sorted(
            [name for name, deg in in_degree.items() if deg == 0]
        )
        order: List[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for dependent in sorted(dependents[current]):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()

        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        dependents: Dict[str, List[str]] = {name: [] for name in self._tasks}

        for task, deps in self._dependencies.items():
            in_degree[task] = len(deps)
            for dep in deps:
                dependents[dep].append(task)

        groups: List[Set[str]] = []
        current_group = {name for name, deg in in_degree.items() if deg == 0}

        while current_group:
            groups.append(current_group)
            next_group: Set[str] = set()
            for task in current_group:
                for dependent in dependents[task]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_group.add(dependent)
            current_group = next_group

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

    scheduler.add_task("fetch_data", lambda: "data fetched")
    scheduler.add_task("parse_data", lambda: "data parsed")
    scheduler.add_task("validate", lambda: "data validated")
    scheduler.add_task("transform", lambda: "data transformed")
    scheduler.add_task("load", lambda: "data loaded")
    scheduler.add_task("notify", lambda: "notification sent")
    scheduler.add_task("cleanup", lambda: "cleanup done")

    scheduler.add_dependency("parse_data", "fetch_data")
    scheduler.add_dependency("validate", "parse_data")
    scheduler.add_dependency("transform", "validate")
    scheduler.add_dependency("load", "transform")
    scheduler.add_dependency("notify", "load")
    scheduler.add_dependency("cleanup", "notify")
    scheduler.add_dependency("cleanup", "load")

    print("=== Validation ===")
    try:
        scheduler.validate()
        print("DAG is valid (no cycles)")
    except CycleError as e:
        print(f"Invalid: {e}")

    print("\n=== Execution Order ===")
    order = scheduler.get_execution_order()
    for i, task in enumerate(order, 1):
        print(f"  {i}. {task}")

    print("\n=== Parallel Groups ===")
    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups, 1):
        print(f"  Stage {i}: {sorted(group)}")

    print("\n=== Execution Results ===")
    results = scheduler.execute()
    for task_name, result in results.items():
        status = result["status"]
        value = result.get("result", result.get("error"))
        print(f"  {task_name}: [{status}] {value}")

    print("\n=== Cycle Detection Test ===")
    bad_scheduler = DAGScheduler()
    bad_scheduler.add_task("A", lambda: None)
    bad_scheduler.add_task("B", lambda: None)
    bad_scheduler.add_task("C", lambda: None)
    bad_scheduler.add_dependency("B", "A")
    bad_scheduler.add_dependency("C", "B")
    bad_scheduler.add_dependency("A", "C")
    try:
        bad_scheduler.validate()
    except CycleError as e:
        print(f"  Caught: {e}")
