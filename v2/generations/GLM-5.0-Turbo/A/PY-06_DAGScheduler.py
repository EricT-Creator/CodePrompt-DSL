from typing import Callable, Dict, List, Set, Optional


class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAGScheduler:
    """DAG task scheduler with dependency management and topological execution."""

    def __init__(self):
        self.tasks: Dict[str, Callable] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}

    def add_task(self, name: str, func: Callable) -> None:
        """Register a task with a name and executable function."""
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        self.tasks[name] = func
        self.dependencies.setdefault(name, set())
        self.dependents.setdefault(name, set())

    def add_dependency(self, task: str, depends_on: str) -> None:
        """Declare that `task` depends on `depends_on`."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' does not exist")
        if depends_on not in self.tasks:
            raise ValueError(f"Task '{depends_on}' does not exist")
        if task == depends_on:
            raise ValueError(f"Task cannot depend on itself")

        self.dependencies[task].add(depends_on)
        self.dependents[depends_on].add(task)

    def validate(self) -> None:
        """Validate the DAG has no circular dependencies. Raises CycleError if found."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in self.tasks}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for dep in self.dependencies.get(node, set()):
                if color[dep] == GRAY:
                    return True  # cycle found
                if color[dep] == WHITE:
                    if dfs(dep):
                        return True
            color[node] = BLACK
            return False

        for name in self.tasks:
            if color[name] == WHITE:
                if dfs(name):
                    raise CycleError("Circular dependency detected in the DAG")

    def get_execution_order(self) -> List[str]:
        """Return a topological sort of tasks respecting dependencies.

        Raises CycleError if the DAG contains cycles.
        """
        self.validate()

        in_degree: Dict[str, int] = {name: len(deps) for name, deps in self.dependencies.items()}
        queue = [name for name, degree in in_degree.items() if degree == 0]
        queue.sort()  # deterministic order
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for dependent in sorted(self.dependents.get(node, set())):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()

        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        """Return groups of tasks that can run in parallel.

        Each group contains tasks that have no unresolved dependencies
        within the same group. Tasks in group N depend only on tasks
        from groups 0..N-1.

        Raises CycleError if the DAG contains cycles.
        """
        self.validate()

        in_degree: Dict[str, int] = {name: len(deps) for name, deps in self.dependencies.items()}
        completed: Set[str] = set()
        groups: List[Set[str]] = []

        while len(completed) < len(self.tasks):
            # Find all tasks whose dependencies are fully satisfied
            ready = set()
            for name in self.tasks:
                if name not in completed and self.dependencies[name].issubset(completed):
                    ready.add(name)

            if not ready:
                remaining = set(self.tasks) - completed
                raise CycleError(
                    f"Cannot resolve remaining tasks: {remaining}. Possible cycle."
                )

            groups.append(ready)
            completed.update(ready)

        return groups

    def execute(self) -> Dict[str, object]:
        """Execute all tasks respecting dependencies.

        Tasks in the same parallel group are executed sequentially in sorted order.
        Use get_parallel_groups() and ThreadPoolExecutor for true parallel execution.

        Returns dict with execution order and results per task.

        Raises CycleError if the DAG contains cycles.
        """
        order = self.get_execution_order()
        results: Dict[str, object] = {}

        for task_name in order:
            try:
                result = self.tasks[task_name]()
                results[task_name] = {"status": "success", "result": result}
            except Exception as e:
                results[task_name] = {"status": "error", "error": str(e)}

        return {
            "execution_order": order,
            "results": results,
            "total": len(order),
            "succeeded": sum(1 for r in results.values() if r["status"] == "success"),
            "failed": sum(1 for r in results.values() if r["status"] == "error"),
        }


if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: "data fetched")
    scheduler.add_task("parse_data", lambda: "data parsed")
    scheduler.add_task("validate", lambda: "validated")
    scheduler.add_task("transform", lambda: "transformed")
    scheduler.add_task("load", lambda: "loaded")

    scheduler.add_dependency("parse_data", "fetch_data")
    scheduler.add_dependency("validate", "parse_data")
    scheduler.add_dependency("transform", "parse_data")
    scheduler.add_dependency("load", "validate")
    scheduler.add_dependency("load", "transform")

    print("Execution order:", scheduler.get_execution_order())
    print("Parallel groups:", [sorted(g) for g in scheduler.get_parallel_groups()])
    print("Execute result:", scheduler.execute())

    # Test cycle detection
    cycle_scheduler = DAGScheduler()
    cycle_scheduler.add_task("a", lambda: "a")
    cycle_scheduler.add_task("b", lambda: "b")
    cycle_scheduler.add_task("c", lambda: "c")
    cycle_scheduler.add_dependency("a", "b")
    cycle_scheduler.add_dependency("b", "c")
    cycle_scheduler.add_dependency("c", "a")
    try:
        cycle_scheduler.validate()
    except CycleError as e:
        print(f"Cycle detected (expected): {e}")
