"""DAG Task Scheduler — topological sort, cycle detection, parallel grouping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

# ─── Exceptions ───────────────────────────────────────────────────────────────

class CycleError(Exception):
    """Raised when a cycle is detected in the task dependency graph."""

    def __init__(self, message: str, cycle_path: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.cycle_path = cycle_path


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None


@dataclass
class ScheduleResult:
    """Result of running the full schedule."""
    execution_order: List[str]
    parallel_groups: List[List[str]]
    results: Dict[str, TaskResult]
    success: bool


# ─── Task ─────────────────────────────────────────────────────────────────────

class Task:
    """Represents a single task in the DAG."""

    def __init__(self, task_id: str, name: str, handler: Callable[[], Any]) -> None:
        self.id: str = task_id
        self.name: str = name
        self.handler: Callable[[], Any] = handler
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, name={self.name!r}, deps={self.dependencies})"


# ─── DAG Scheduler ────────────────────────────────────────────────────────────

class DAGScheduler:
    """
    DAG-based task scheduler with topological ordering.

    Supports:
    - Task registration with dependencies
    - Topological sort (Kahn's algorithm)
    - Cycle detection (DFS with path tracking)
    - Parallel grouping of independent tasks
    - Sequential execution with error handling
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._in_degree: Dict[str, int] = {}

    def add_task(
        self,
        task_id: str,
        name: str,
        handler: Callable[[], Any],
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """
        Add a task to the DAG.

        Args:
            task_id: Unique identifier for the task.
            name: Human-readable name.
            handler: Callable to execute when task runs.
            dependencies: List of task IDs that must complete first.

        Raises:
            ValueError: If task_id already exists or a dependency is not found.
        """
        if task_id in self._tasks:
            raise ValueError(f"Task '{task_id}' already exists")

        task = Task(task_id, name, handler)
        self._tasks[task_id] = task
        self._in_degree[task_id] = 0

        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self._tasks:
                    raise ValueError(f"Dependency '{dep_id}' not found. Add it before '{task_id}'.")

                task.dependencies.add(dep_id)
                self._tasks[dep_id].dependents.add(task_id)
                self._in_degree[task_id] += 1

    def remove_task(self, task_id: str) -> None:
        """
        Remove a task from the DAG.

        Args:
            task_id: The task to remove.

        Raises:
            ValueError: If the task doesn't exist or has dependents.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")

        task = self._tasks[task_id]
        if task.dependents:
            raise ValueError(
                f"Cannot remove '{task_id}': other tasks depend on it: {task.dependents}"
            )

        # Remove from dependency lists
        for dep_id in task.dependencies:
            if dep_id in self._tasks:
                self._tasks[dep_id].dependents.discard(task_id)

        del self._tasks[task_id]
        del self._in_degree[task_id]

    def validate(self) -> None:
        """
        Validate the DAG has no cycles.

        Raises:
            CycleError: If a cycle is detected.
        """
        cycle = self._detect_cycle_dfs()
        if cycle:
            raise CycleError(
                f"Cycle detected: {' -> '.join(cycle)}",
                cycle_path=cycle,
            )

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm.

        Returns:
            List of task IDs in valid execution order.

        Raises:
            CycleError: If a cycle prevents complete ordering.
        """
        in_degree = self._in_degree.copy()
        queue: List[str] = [tid for tid, deg in in_degree.items() if deg == 0]
        queue.sort()  # Deterministic ordering
        result: List[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for dependent in sorted(self._tasks[current].dependents):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
            queue.sort()

        if len(result) != len(self._tasks):
            # Find cycle for error message
            remaining = set(self._tasks.keys()) - set(result)
            raise CycleError(
                f"Cycle detected involving tasks: {remaining}",
                cycle_path=list(remaining),
            )

        return result

    def get_parallel_groups(self) -> List[List[str]]:
        """
        Group tasks by execution level for parallel execution.

        Each group contains tasks with no mutual dependencies.

        Returns:
            List of groups, each group is a list of task IDs.

        Raises:
            CycleError: If a cycle is detected.
        """
        in_degree = self._in_degree.copy()
        groups: List[List[str]] = []

        remaining = set(in_degree.keys())

        while remaining:
            current_group = sorted(
                tid for tid in remaining if in_degree[tid] == 0
            )

            if not current_group:
                raise CycleError(
                    f"Cycle detected during grouping, remaining: {remaining}",
                    cycle_path=list(remaining),
                )

            groups.append(current_group)

            for tid in current_group:
                remaining.discard(tid)
                for dependent in self._tasks[tid].dependents:
                    if dependent in remaining:
                        in_degree[dependent] -= 1

        return groups

    def execute(self) -> ScheduleResult:
        """
        Execute all tasks in topological order.

        Returns:
            ScheduleResult with execution details.
        """
        self.validate()
        order = self.topological_sort()
        groups = self.get_parallel_groups()
        results: Dict[str, TaskResult] = {}
        all_success = True

        for task_id in order:
            task = self._tasks[task_id]
            try:
                result = task.handler()
                results[task_id] = TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                )
            except Exception as e:
                all_success = False
                results[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                )

        return ScheduleResult(
            execution_order=order,
            parallel_groups=groups,
            results=results,
            success=all_success,
        )

    def execute_parallel(self) -> ScheduleResult:
        """
        Execute tasks grouped by parallel level.

        Within each group, tasks are independent and could run in parallel.
        This implementation runs them sequentially within each group.

        Returns:
            ScheduleResult with execution details.
        """
        self.validate()
        groups = self.get_parallel_groups()
        order: List[str] = []
        results: Dict[str, TaskResult] = {}
        all_success = True

        for group in groups:
            for task_id in group:
                order.append(task_id)
                task = self._tasks[task_id]
                try:
                    result = task.handler()
                    results[task_id] = TaskResult(
                        task_id=task_id,
                        success=True,
                        result=result,
                    )
                except Exception as e:
                    all_success = False
                    results[task_id] = TaskResult(
                        task_id=task_id,
                        success=False,
                        error=str(e),
                    )

        return ScheduleResult(
            execution_order=order,
            parallel_groups=groups,
            results=results,
            success=all_success,
        )

    def get_task_ids(self) -> List[str]:
        """Return all task IDs."""
        return list(self._tasks.keys())

    def get_dependencies(self, task_id: str) -> Set[str]:
        """Return dependencies of a task."""
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")
        return self._tasks[task_id].dependencies.copy()

    def get_dependents(self, task_id: str) -> Set[str]:
        """Return tasks that depend on the given task."""
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")
        return self._tasks[task_id].dependents.copy()

    # ─── Private: Cycle Detection ─────────────────────────────────────────

    def _detect_cycle_dfs(self) -> Optional[List[str]]:
        """
        Detect cycle using DFS with coloring.

        Returns:
            List of task IDs forming a cycle, or None if no cycle.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {tid: WHITE for tid in self._tasks}

        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            color[node] = GRAY

            for dependent in sorted(self._tasks[node].dependents):
                if color[dependent] == GRAY:
                    cycle_start = path.index(dependent) if dependent in path else 0
                    return path[cycle_start:] + [dependent]

                if color[dependent] == WHITE:
                    result = dfs(dependent, path + [dependent])
                    if result:
                        return result

            color[node] = BLACK
            return None

        for task_id in sorted(self._tasks.keys()):
            if color[task_id] == WHITE:
                cycle = dfs(task_id, [task_id])
                if cycle:
                    return cycle

        return None


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", "Fetch Data", lambda: {"rows": 100})
    scheduler.add_task("clean_data", "Clean Data", lambda: {"rows": 95}, dependencies=["fetch_data"])
    scheduler.add_task("validate", "Validate", lambda: {"valid": True}, dependencies=["fetch_data"])
    scheduler.add_task("transform", "Transform", lambda: {"transformed": True}, dependencies=["clean_data", "validate"])
    scheduler.add_task("load", "Load to DB", lambda: {"loaded": True}, dependencies=["transform"])

    print("Topological order:", scheduler.topological_sort())
    print("Parallel groups:", scheduler.get_parallel_groups())

    result = scheduler.execute()
    print(f"\nExecution success: {result.success}")
    print(f"Order: {result.execution_order}")
    for tid, tr in result.results.items():
        print(f"  {tid}: {'✓' if tr.success else '✗'} {tr.result or tr.error}")
