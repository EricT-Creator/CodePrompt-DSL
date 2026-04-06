"""
MC-PY-02: DAG Task Scheduler
[L]PY310 [D]STDLIB_ONLY [!D]NO_GRAPH_LIB [O]CLASS [TYPE]FULL_HINTS [ERR]CYCLE_EXC [FILE]SINGLE
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable


# ─── Custom Exception ─────────────────────────────────────────────────────────

class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


# ─── Task Node ────────────────────────────────────────────────────────────────

@dataclass
class Task:
    """A node in the DAG."""
    id: str
    name: str
    func: Callable[[], Any] = field(default=lambda: None, compare=False, repr=False)
    dependencies: set[str] = field(default_factory=set)


# ─── DAG ──────────────────────────────────────────────────────────────────────

@dataclass
class DAG:
    """Directed Acyclic Graph of tasks."""
    tasks: dict[str, Task] = field(default_factory=dict)

    def add_task(self, task: Task) -> None:
        """Add a task to the DAG."""
        self.tasks[task.id] = task

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add dependency edge: task_id depends on depends_on."""
        if task_id not in self.tasks:
            raise KeyError(f"Task '{task_id}' not found in DAG")
        if depends_on not in self.tasks:
            raise KeyError(f"Dependency target '{depends_on}' not found in DAG")
        self.tasks[task_id].dependencies.add(depends_on)

    def topological_sort(self) -> list[str]:
        """
        Kahn's algorithm for topological sorting.
        Returns task IDs in execution order.
        Raises CycleError if a cycle is detected.
        """
        # Calculate in-degrees
        in_degree: dict[str, int] = {tid: 0 for tid in self.tasks}
        for task in self.tasks.values():
            for dep in task.dependencies:
                if dep in self.tasks:
                    # dep is depended upon by task.id,
                    # so in_degree of task.id should be incremented
                    pass
            # Actually: in_degree[task.id] = number of dependencies it has that exist in the DAG
            in_degree[task.id] = sum(1 for d in task.dependencies if d in self.tasks)

        # Start with tasks that have no dependencies
        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        result: list[str] = []

        while queue:
            current: str = queue.popleft()
            result.append(current)

            # Find tasks that depend on current (current is in their dependencies)
            for task in self.tasks.values():
                if current in task.dependencies:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)

        if len(result) != len(self.tasks):
            # Identify cycle participants
            remaining: list[str] = [tid for tid in self.tasks if tid not in result]
            raise CycleError(
                f"Graph contains a cycle involving tasks: {remaining}"
            )

        return result

    def topological_sort_dfs(self) -> list[str]:
        """DFS-based topological sort. Alternative algorithm."""
        visited: set[str] = set()
        temp_mark: set[str] = set()
        result: list[str] = []

        def visit(task_id: str) -> None:
            if task_id in temp_mark:
                raise CycleError(f"Cycle detected at task '{task_id}'")
            if task_id in visited:
                return

            temp_mark.add(task_id)
            task: Task = self.tasks[task_id]
            for dep in sorted(task.dependencies):
                if dep in self.tasks:
                    visit(dep)
            temp_mark.remove(task_id)
            visited.add(task_id)
            result.append(task_id)

        for task_id in sorted(self.tasks.keys()):
            if task_id not in visited:
                visit(task_id)

        return result

    def has_cycle(self) -> bool:
        """Check if DAG contains a cycle."""
        try:
            self.topological_sort()
            return False
        except CycleError:
            return True

    def get_parallel_groups(self) -> list[list[str]]:
        """
        Group tasks by execution level.
        Tasks in the same group can run in parallel.
        """
        order: list[str] = self.topological_sort()

        # Calculate depth (longest path from root)
        depth: dict[str, int] = {tid: 0 for tid in self.tasks}
        for task_id in order:
            task: Task = self.tasks[task_id]
            for dep in task.dependencies:
                if dep in depth:
                    depth[task_id] = max(depth[task_id], depth[dep] + 1)

        # Group by depth
        groups: dict[int, list[str]] = {}
        for task_id, d in depth.items():
            groups.setdefault(d, []).append(task_id)

        return [sorted(groups[i]) for i in sorted(groups.keys())]

    def get_dependents(self, task_id: str) -> set[str]:
        """Get all tasks that directly depend on the given task."""
        dependents: set[str] = set()
        for tid, task in self.tasks.items():
            if task_id in task.dependencies:
                dependents.add(tid)
        return dependents

    def get_all_ancestors(self, task_id: str) -> set[str]:
        """Get all transitive dependencies of a task."""
        ancestors: set[str] = set()
        stack: list[str] = list(self.tasks[task_id].dependencies)

        while stack:
            dep: str = stack.pop()
            if dep in ancestors or dep not in self.tasks:
                continue
            ancestors.add(dep)
            stack.extend(self.tasks[dep].dependencies)

        return ancestors


# ─── Scheduler ────────────────────────────────────────────────────────────────

@dataclass
class Scheduler:
    """Task scheduler that executes DAG tasks respecting dependencies."""
    dag: DAG

    def schedule(self) -> list[list[str]]:
        """Get parallel execution groups."""
        return self.dag.get_parallel_groups()

    def execute(self) -> dict[str, Any]:
        """Execute tasks sequentially in topological order."""
        order: list[str] = self.dag.topological_sort()
        results: dict[str, Any] = {}

        for task_id in order:
            task: Task = self.dag.tasks[task_id]
            try:
                result: Any = task.func()
                results[task_id] = {"status": "success", "result": result}
            except Exception as e:
                results[task_id] = {"status": "error", "error": str(e)}

        return results

    def execute_parallel(self) -> dict[str, Any]:
        """Execute tasks by parallel groups (simulated, single-threaded)."""
        groups: list[list[str]] = self.dag.get_parallel_groups()
        results: dict[str, Any] = {}

        for level, group in enumerate(groups):
            for task_id in group:
                task: Task = self.dag.tasks[task_id]
                try:
                    result: Any = task.func()
                    results[task_id] = {
                        "status": "success",
                        "result": result,
                        "level": level,
                    }
                except Exception as e:
                    results[task_id] = {
                        "status": "error",
                        "error": str(e),
                        "level": level,
                    }

        return results

    def dry_run(self) -> list[dict[str, Any]]:
        """Show execution plan without running tasks."""
        groups: list[list[str]] = self.dag.get_parallel_groups()
        plan: list[dict[str, Any]] = []

        for level, group in enumerate(groups):
            plan.append({
                "level": level,
                "tasks": [
                    {
                        "id": tid,
                        "name": self.dag.tasks[tid].name,
                        "dependencies": sorted(self.dag.tasks[tid].dependencies),
                    }
                    for tid in group
                ],
                "parallel": len(group) > 1,
            })

        return plan


# ─── Demo ─────────────────────────────────────────────────────────────────────

def main() -> None:
    dag = DAG()

    dag.add_task(Task("A", "Setup", lambda: "setup done"))
    dag.add_task(Task("B", "Process A", lambda: "processed A", {"A"}))
    dag.add_task(Task("C", "Process B", lambda: "processed B", {"A"}))
    dag.add_task(Task("D", "Finalize", lambda: "finalized", {"B", "C"}))

    scheduler = Scheduler(dag=dag)

    print("=== Execution Plan ===")
    for step in scheduler.dry_run():
        names: list[str] = [t["name"] for t in step["tasks"]]
        print(f"  Level {step['level']}: {names} (parallel={step['parallel']})")

    print("\n=== Parallel Groups ===")
    print(f"  {scheduler.schedule()}")

    print("\n=== Sequential Execution ===")
    results: dict[str, Any] = scheduler.execute()
    for tid, res in results.items():
        print(f"  {tid}: {res}")

    print("\n=== Cycle Detection ===")
    print(f"  Has cycle: {dag.has_cycle()}")

    # Test cycle detection
    cyclic_dag = DAG()
    cyclic_dag.add_task(Task("X", "X", dependencies={"Y"}))
    cyclic_dag.add_task(Task("Y", "Y", dependencies={"X"}))
    print(f"  Cyclic DAG has cycle: {cyclic_dag.has_cycle()}")

    try:
        cyclic_dag.topological_sort()
    except CycleError as e:
        print(f"  CycleError: {e}")


if __name__ == "__main__":
    main()
