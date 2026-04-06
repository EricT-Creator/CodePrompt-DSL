"""MC-PY-02: DAG Task Scheduler — topological sort, cycle detection, parallel grouping"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ── Custom exception ────────────────────────────────────────────────

class CycleError(Exception):
    """Raised when a cycle is detected in the dependency graph."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = cycle_path
        super().__init__(f"Cycle detected: {' -> '.join(cycle_path)}")


# ── Task status ─────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Task node ───────────────────────────────────────────────────────

@dataclass
class TaskNode:
    name: str
    action: Callable[[], Any] | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)


# ── Execution plan ──────────────────────────────────────────────────

@dataclass
class ExecutionPlan:
    """Represents the computed execution order with parallel groups."""
    topological_order: list[str]
    parallel_groups: list[list[str]]
    total_tasks: int

    def __repr__(self) -> str:
        groups = " | ".join(str(g) for g in self.parallel_groups)
        return f"ExecutionPlan(tasks={self.total_tasks}, groups=[{groups}])"


# ── DAG Scheduler ───────────────────────────────────────────────────

class DAGScheduler:
    """Directed Acyclic Graph task scheduler with cycle detection and parallel grouping."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskNode] = {}

    # ── Graph construction ──────────────────────────────────────────

    def add_task(
        self,
        name: str,
        action: Callable[[], Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """Add a task node. Dependencies must already be added or will be auto-created."""
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already exists")

        deps = set(dependencies) if dependencies else set()
        node = TaskNode(name=name, action=action, dependencies=deps)
        self._tasks[name] = node

        # Auto-create placeholder nodes for unknown dependencies
        for dep_name in deps:
            if dep_name not in self._tasks:
                self._tasks[dep_name] = TaskNode(name=dep_name)
            self._tasks[dep_name].dependents.add(name)

    def add_dependency(self, task: str, depends_on: str) -> None:
        """Add a dependency edge: task depends on depends_on."""
        if task not in self._tasks:
            self._tasks[task] = TaskNode(name=task)
        if depends_on not in self._tasks:
            self._tasks[depends_on] = TaskNode(name=depends_on)
        self._tasks[task].dependencies.add(depends_on)
        self._tasks[depends_on].dependents.add(task)

    def remove_task(self, name: str) -> bool:
        if name not in self._tasks:
            return False
        node = self._tasks.pop(name)
        for dep in node.dependencies:
            if dep in self._tasks:
                self._tasks[dep].dependents.discard(name)
        for dep in node.dependents:
            if dep in self._tasks:
                self._tasks[dep].dependencies.discard(name)
        return True

    # ── Cycle detection (DFS) ───────────────────────────────────────

    def _detect_cycle(self) -> list[str] | None:
        """DFS-based cycle detection. Returns cycle path if found, else None."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {name: WHITE for name in self._tasks}
        parent: dict[str, str | None] = {name: None for name in self._tasks}

        def dfs(node: str) -> list[str] | None:
            color[node] = GRAY
            for neighbour in self._tasks[node].dependencies:
                if neighbour not in color:
                    continue
                if color[neighbour] == GRAY:
                    # Found cycle — reconstruct path
                    path = [neighbour, node]
                    cur = node
                    while parent[cur] is not None and parent[cur] != neighbour:
                        cur = parent[cur]  # type: ignore[assignment]
                        path.append(cur)
                    path.append(neighbour)
                    path.reverse()
                    return path
                if color[neighbour] == WHITE:
                    parent[neighbour] = node
                    result = dfs(neighbour)
                    if result is not None:
                        return result
            color[node] = BLACK
            return None

        for task_name in self._tasks:
            if color[task_name] == WHITE:
                cycle = dfs(task_name)
                if cycle is not None:
                    return cycle
        return None

    def validate(self) -> None:
        """Validate the graph. Raises CycleError if a cycle is found."""
        cycle = self._detect_cycle()
        if cycle is not None:
            raise CycleError(cycle)

    # ── Topological sort (Kahn's algorithm) ─────────────────────────

    def _topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = {name: len(node.dependencies) for name, node in self._tasks.items()}
        queue: deque[str] = deque(name for name, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for dependent in self._tasks[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._tasks):
            # Cycle exists — find and report it
            cycle = self._detect_cycle()
            raise CycleError(cycle or ["unknown"])

        return order

    # ── Parallel grouping ───────────────────────────────────────────

    def _compute_parallel_groups(self) -> list[list[str]]:
        """Group tasks into levels where each level can run in parallel."""
        if not self._tasks:
            return []

        in_degree: dict[str, int] = {name: len(node.dependencies) for name, node in self._tasks.items()}
        queue: deque[str] = deque(name for name, deg in in_degree.items() if deg == 0)
        groups: list[list[str]] = []

        while queue:
            current_level = list(queue)
            groups.append(current_level)
            next_queue: deque[str] = deque()

            for task_name in current_level:
                for dependent in self._tasks[task_name].dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)

            queue = next_queue

        return groups

    # ── Schedule ────────────────────────────────────────────────────

    def schedule(self) -> ExecutionPlan:
        """Validate, sort, and compute parallel groups."""
        self.validate()
        topo = self._topological_sort()
        groups = self._compute_parallel_groups()
        return ExecutionPlan(
            topological_order=topo,
            parallel_groups=groups,
            total_tasks=len(self._tasks),
        )

    # ── Execute ─────────────────────────────────────────────────────

    def execute(self) -> dict[str, Any]:
        """Execute tasks in topological order (sequential). Returns results dict."""
        plan = self.schedule()
        results: dict[str, Any] = {}

        for group in plan.parallel_groups:
            for task_name in group:
                node = self._tasks[task_name]
                node.status = TaskStatus.RUNNING
                try:
                    if node.action is not None:
                        node.result = node.action()
                    else:
                        node.result = None
                    node.status = TaskStatus.COMPLETED
                except Exception as e:
                    node.status = TaskStatus.FAILED
                    node.error = str(e)
                    node.result = None
                results[task_name] = {
                    "status": node.status.value,
                    "result": node.result,
                    "error": node.error,
                }

        return results

    # ── Inspection ──────────────────────────────────────────────────

    @property
    def tasks(self) -> list[str]:
        return list(self._tasks.keys())

    def get_dependencies(self, task: str) -> set[str]:
        if task not in self._tasks:
            raise KeyError(f"Task '{task}' not found")
        return set(self._tasks[task].dependencies)

    def get_dependents(self, task: str) -> set[str]:
        if task not in self._tasks:
            raise KeyError(f"Task '{task}' not found")
        return set(self._tasks[task].dependents)

    def __len__(self) -> int:
        return len(self._tasks)

    def __repr__(self) -> str:
        return f"DAGScheduler(tasks={len(self._tasks)})"


# ── Demo / self-test ────────────────────────────────────────────────

if __name__ == "__main__":
    scheduler = DAGScheduler()

    scheduler.add_task("fetch_data", action=lambda: "raw_data")
    scheduler.add_task("clean_data", action=lambda: "clean", dependencies=["fetch_data"])
    scheduler.add_task("validate", action=lambda: "valid", dependencies=["clean_data"])
    scheduler.add_task("transform_a", action=lambda: "a_out", dependencies=["validate"])
    scheduler.add_task("transform_b", action=lambda: "b_out", dependencies=["validate"])
    scheduler.add_task("merge", action=lambda: "merged", dependencies=["transform_a", "transform_b"])
    scheduler.add_task("export", action=lambda: "done", dependencies=["merge"])

    plan = scheduler.schedule()
    print(plan)
    print("Topological order:", plan.topological_order)
    print("Parallel groups:", plan.parallel_groups)

    results = scheduler.execute()
    for task, info in results.items():
        print(f"  {task}: {info}")

    # Cycle detection test
    try:
        s2 = DAGScheduler()
        s2.add_task("A", dependencies=["C"])
        s2.add_task("B", dependencies=["A"])
        s2.add_task("C", dependencies=["B"])
        s2.validate()
    except CycleError as e:
        print(f"\nCycle detected: {e}")
