from typing import Any, Callable, Dict, List, Optional, Set


class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAGScheduler:
    """Directed Acyclic Graph task scheduler.

    Supports adding tasks with dependencies, cycle detection,
    topological sorting, parallel group identification, and execution.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Callable] = {}
        self._dependencies: Dict[str, Set[str]] = {}

    def add_task(self, name: str, func: Callable) -> None:
        """Add a task with a name and callable."""
        self._tasks[name] = func
        if name not in self._dependencies:
            self._dependencies[name] = set()

    def add_dependency(self, task: str, depends_on: str) -> None:
        """Declare that `task` depends on `depends_on`."""
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' not found. Add it first with add_task().")
        if depends_on not in self._tasks:
            raise ValueError(f"Dependency '{depends_on}' not found. Add it first with add_task().")
        self._dependencies[task].add(depends_on)

    def validate(self) -> bool:
        """Validate the DAG has no cycles. Raises CycleError if a cycle exists."""
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
                    raise CycleError(f"Cycle detected: {' -> '.join(cycle)}")
                if dep not in visited:
                    dfs(dep)

            path.pop()
            in_stack.remove(node)

        for task_name in self._tasks:
            if task_name not in visited:
                dfs(task_name)

        return True

    def get_execution_order(self) -> List[str]:
        """Return a topological sort of tasks (dependencies first)."""
        self.validate()

        visited: Set[str] = set()
        order: List[str] = []

        def dfs(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            for dep in self._dependencies.get(node, set()):
                dfs(dep)
            order.append(node)

        for task_name in self._tasks:
            dfs(task_name)

        return order

    def get_parallel_groups(self) -> List[Set[str]]:
        """Return groups of tasks that can run in parallel (Kahn's algorithm)."""
        self.validate()

        in_degree: Dict[str, int] = {name: 0 for name in self._tasks}
        reverse_deps: Dict[str, Set[str]] = {name: set() for name in self._tasks}

        for task, deps in self._dependencies.items():
            in_degree[task] = len(deps)
            for dep in deps:
                reverse_deps[dep].add(task)

        groups: List[Set[str]] = []
        remaining = set(self._tasks.keys())

        while remaining:
            # Find all tasks with no unmet dependencies
            ready = {t for t in remaining if in_degree[t] == 0}
            if not ready:
                raise CycleError("Unexpected cycle detected during parallel grouping")

            groups.append(ready)
            remaining -= ready

            for task in ready:
                for dependent in reverse_deps.get(task, set()):
                    in_degree[dependent] -= 1

        return groups

    def execute(self) -> Dict[str, Any]:
        """Execute all tasks in dependency order. Returns dict of task -> result."""
        order = self.get_execution_order()
        results: Dict[str, Any] = {}

        for task_name in order:
            func = self._tasks[task_name]
            try:
                results[task_name] = func()
            except Exception as e:
                results[task_name] = f"ERROR: {e}"

        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: print("  Fetching data...") or "data")
    scheduler.add_task("parse_data", lambda: print("  Parsing data...") or "parsed")
    scheduler.add_task("validate", lambda: print("  Validating...") or "valid")
    scheduler.add_task("transform", lambda: print("  Transforming...") or "transformed")
    scheduler.add_task("save_db", lambda: print("  Saving to DB...") or "saved")
    scheduler.add_task("generate_report", lambda: print("  Generating report...") or "report")
    scheduler.add_task("notify", lambda: print("  Sending notification...") or "notified")

    scheduler.add_dependency("parse_data", "fetch_data")
    scheduler.add_dependency("validate", "parse_data")
    scheduler.add_dependency("transform", "validate")
    scheduler.add_dependency("save_db", "transform")
    scheduler.add_dependency("generate_report", "transform")
    scheduler.add_dependency("notify", "save_db")
    scheduler.add_dependency("notify", "generate_report")

    print("Validation:", scheduler.validate())
    print("\nExecution Order:", scheduler.get_execution_order())

    print("\nParallel Groups:")
    for i, group in enumerate(scheduler.get_parallel_groups()):
        print(f"  Group {i}: {group}")

    print("\nExecuting all tasks:")
    results = scheduler.execute()
    print("\nResults:", results)

    # Test cycle detection
    print("\n--- Cycle Detection Test ---")
    cyclic = DAGScheduler()
    cyclic.add_task("a", lambda: None)
    cyclic.add_task("b", lambda: None)
    cyclic.add_task("c", lambda: None)
    cyclic.add_dependency("a", "b")
    cyclic.add_dependency("b", "c")
    cyclic.add_dependency("c", "a")
    try:
        cyclic.validate()
    except CycleError as e:
        print(f"CycleError caught: {e}")
