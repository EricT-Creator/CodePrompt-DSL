from collections import defaultdict
from typing import Callable, Optional


class CycleError(Exception):
    def __init__(self, cycle: list):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


class DAGScheduler:
    """DAG-based task scheduler with dependency management.

    Supports adding tasks with dependencies, cycle detection,
    topological sort execution order, parallel group extraction, and execution.
    """

    def __init__(self):
        self.tasks: dict[str, Callable] = {}
        self.dependencies: dict[str, set[str]] = defaultdict(set)
        self.dependents: dict[str, set[str]] = defaultdict(set)

    def add_task(self, name: str, func: Callable) -> "DAGScheduler":
        """Add a task with a name and executable function."""
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        self.tasks[name] = func
        self.dependencies[name]  # ensure key exists
        return self

    def add_dependency(self, task: str, depends_on: str) -> "DAGScheduler":
        """Add a dependency: task depends on depends_on (depends_on must run first)."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' does not exist")
        if depends_on not in self.tasks:
            raise ValueError(f"Dependency task '{depends_on}' does not exist")
        if task == depends_on:
            raise CycleError([task])
        self.dependencies[task].add(depends_on)
        self.dependents[depends_on].add(task)
        return self

    def validate(self) -> bool:
        """Validate the DAG has no cycles. Raises CycleError if cycle found."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {task: WHITE for task in self.tasks}
        path: list[str] = []

        def dfs(node: str):
            color[node] = GRAY
            path.append(node)
            for dep in self.dependencies[node]:
                if color[dep] == GRAY:
                    cycle_start = path.index(dep)
                    raise CycleError(path[cycle_start:] + [dep])
                if color[dep] == WHITE:
                    dfs(dep)
            path.pop()
            color[node] = BLACK

        for task in self.tasks:
            if color[task] == WHITE:
                dfs(task)
        return True

    def get_execution_order(self) -> list[str]:
        """Return tasks in topological order (dependencies first).

        Raises CycleError if the DAG contains cycles.
        """
        self.validate()

        visited: set[str] = set()
        order: list[str] = []

        def visit(node: str):
            if node in visited:
                return
            visited.add(node)
            for dep in self.dependencies[node]:
                visit(dep)
            order.append(node)

        for task in self.tasks:
            visit(task)

        return order

    def get_parallel_groups(self) -> list[set[str]]:
        """Return sets of tasks that can run in parallel.

        Each set in the list represents a "wave" of tasks that can execute
        concurrently. Tasks in earlier waves must complete before later waves start.
        """
        self.validate()

        order = self.get_execution_order()
        completed: set[str] = set()
        groups: list[set[str]] = []

        remaining = set(order)
        while remaining:
            # Find tasks whose dependencies are all completed
            ready = set()
            for task in remaining:
                if self.dependencies[task].issubset(completed):
                    ready.add(task)

            if not ready:
                # Should not happen if validate() passed
                raise CycleError(list(remaining))

            groups.append(ready)
            completed.update(ready)
            remaining -= ready

        return groups

    def execute(self) -> dict:
        """Execute all tasks in topological order.

        Returns execution results including order, timing, and any errors.
        """
        import time

        order = self.get_execution_order()
        results = []

        for task_name in order:
            func = self.tasks[task_name]
            start = time.time()
            try:
                result = func()
                elapsed = time.time() - start
                results.append({
                    "task": task_name,
                    "status": "success",
                    "result": result,
                    "elapsed": round(elapsed, 4),
                })
            except Exception as e:
                elapsed = time.time() - start
                results.append({
                    "task": task_name,
                    "status": "error",
                    "error": str(e),
                    "elapsed": round(elapsed, 4),
                })

        return {
            "execution_order": order,
            "results": results,
            "total_tasks": len(order),
            "succeeded": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "error"),
        }


if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", lambda: f"Fetched {42} rows")
    scheduler.add_task("parse_data", lambda: f"Parsed successfully")
    scheduler.add_task("validate", lambda: f"Validation passed")
    scheduler.add_task("transform", lambda: f"Transformed to {3} columns")
    scheduler.add_task("load", lambda: f"Loaded into database")
    scheduler.add_task("notify", lambda: f"Notification sent")

    scheduler.add_dependency("parse_data", "fetch_data")
    scheduler.add_dependency("validate", "parse_data")
    scheduler.add_dependency("transform", "validate")
    scheduler.add_dependency("load", "transform")
    scheduler.add_dependency("notify", "load")

    print("=== Execution Order ===")
    for i, task in enumerate(scheduler.get_execution_order(), 1):
        print(f"  {i}. {task}")

    print("\n=== Parallel Groups ===")
    for i, group in enumerate(scheduler.get_parallel_groups(), 1):
        print(f"  Wave {i}: {', '.join(sorted(group))}")

    print("\n=== Execution ===")
    result = scheduler.execute()
    for r in result["results"]:
        icon = "✓" if r["status"] == "success" else "✗"
        print(f"  {icon} {r['task']}: {r.get('result', r.get('error'))} ({r['elapsed']}s)")
    print(f"\nTotal: {result['succeeded']}/{result['total_tasks']} succeeded")
