from __future__ import annotations

import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Iterator, TypeVar


T = TypeVar("T")


# ─── CycleError ───

class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""

    def __init__(self, message: str, cycle: list[Any] | None = None) -> None:
        super().__init__(message)
        self.cycle: list[Any] | None = cycle


# ─── DAG ───

@dataclass
class DAG(Generic[T]):
    """Directed Acyclic Graph for task scheduling."""

    _dependencies: dict[T, set[T]] = field(default_factory=dict)
    _reverse_deps: dict[T, set[T]] = field(default_factory=dict)

    def add_node(self, node: T) -> None:
        """Add a node to the graph."""
        if node not in self._dependencies:
            self._dependencies[node] = set()
            self._reverse_deps[node] = set()

    def add_edge(self, from_node: T, to_node: T) -> None:
        """Add edge: from_node must complete before to_node."""
        self.add_node(from_node)
        self.add_node(to_node)
        self._dependencies[from_node].add(to_node)
        self._reverse_deps[to_node].add(from_node)

    def get_dependencies(self, node: T) -> set[T]:
        """Get all nodes that node depends on."""
        return self._reverse_deps.get(node, set()).copy()

    def get_dependents(self, node: T) -> set[T]:
        """Get all nodes that depend on node."""
        return self._dependencies.get(node, set()).copy()

    def get_nodes(self) -> set[T]:
        """Get all nodes in the graph."""
        return set(self._dependencies.keys())

    def remove_node(self, node: T) -> None:
        """Remove a node and all its edges."""
        if node not in self._dependencies:
            return
        for dependent in self._dependencies[node]:
            self._reverse_deps[dependent].discard(node)
        for dependency in self._reverse_deps[node]:
            self._dependencies[dependency].discard(node)
        del self._dependencies[node]
        del self._reverse_deps[node]

    def node_count(self) -> int:
        """Return number of nodes."""
        return len(self._dependencies)

    def edge_count(self) -> int:
        """Return number of edges."""
        return sum(len(deps) for deps in self._dependencies.values())


# ─── Task ───

@dataclass
class Task:
    """A task with an ID and executable function."""
    task_id: str
    func: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)

    def execute(self) -> Any:
        """Execute the task function."""
        return self.func(*self.args, **self.kwargs)


# ─── Execution Result ───

@dataclass
class ExecutionResult:
    """Result of a single task execution."""
    task_id: str
    success: bool
    result: Any
    error: Exception | None


# ─── Topological Sort (Kahn's Algorithm) ───

def topological_sort(dag: DAG[T]) -> list[T]:
    """
    Perform topological sort using Kahn's algorithm.
    Returns nodes in execution order.
    Raises CycleError if cycle detected.
    """
    nodes = dag.get_nodes()
    in_degree: dict[T, int] = {node: 0 for node in nodes}

    for node in nodes:
        for dependent in dag.get_dependents(node):
            in_degree[dependent] += 1

    queue: deque[T] = deque(
        node for node, degree in in_degree.items() if degree == 0
    )

    result: list[T] = []
    visited_count: int = 0

    while queue:
        node = queue.popleft()
        result.append(node)
        visited_count += 1

        for dependent in dag.get_dependents(node):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if visited_count != len(nodes):
        raise CycleError("Graph contains a cycle")

    return result


# ─── Topological Sort (DFS) ───

def topological_sort_dfs(dag: DAG[T]) -> list[T]:
    """
    Perform topological sort using DFS.
    Raises CycleError if cycle detected.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[T, int] = {node: WHITE for node in dag.get_nodes()}
    result: list[T] = []

    def dfs(node: T) -> None:
        color[node] = GRAY
        for dependent in dag.get_dependents(node):
            if color[dependent] == GRAY:
                raise CycleError(f"Cycle detected involving node {dependent}")
            if color[dependent] == WHITE:
                dfs(dependent)
        color[node] = BLACK
        result.append(node)

    for node in dag.get_nodes():
        if color[node] == WHITE:
            dfs(node)

    result.reverse()
    return result


# ─── Cycle Detection ───

def find_cycle(dag: DAG[T]) -> list[T] | None:
    """Find and return a cycle if one exists."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[T, int] = {node: WHITE for node in dag.get_nodes()}

    def dfs(node: T, path: list[T]) -> list[T] | None:
        color[node] = GRAY
        for dependent in dag.get_dependents(node):
            if color[dependent] == GRAY:
                cycle_start = path.index(dependent)
                return path[cycle_start:] + [dependent]
            if color[dependent] == WHITE:
                result = dfs(dependent, path + [dependent])
                if result:
                    return result
        color[node] = BLACK
        return None

    for node in dag.get_nodes():
        if color[node] == WHITE:
            cycle = dfs(node, [node])
            if cycle:
                return cycle
    return None


# ─── Parallel Grouping ───

def get_execution_groups(dag: DAG[T]) -> Iterator[list[T]]:
    """
    Group tasks into levels where each level can execute in parallel.
    Each group contains tasks with no remaining dependencies.
    """
    nodes = dag.get_nodes()
    in_degree: dict[T, int] = {node: 0 for node in nodes}
    for node in nodes:
        for dependent in dag.get_dependents(node):
            in_degree[dependent] += 1

    remaining: set[T] = set(nodes)

    while remaining:
        group: list[T] = [
            node for node in remaining if in_degree[node] == 0
        ]

        if not group:
            raise CycleError("Cycle detected - no nodes with zero in-degree")

        yield group

        for node in group:
            remaining.remove(node)
            for dependent in dag.get_dependents(node):
                in_degree[dependent] -= 1


# ─── DAG Scheduler ───

class DAGScheduler:
    """Task scheduler for DAG execution."""

    def __init__(self, dag: DAG[str], tasks: dict[str, Task]) -> None:
        self.dag: DAG[str] = dag
        self.tasks: dict[str, Task] = tasks
        self.results: dict[str, ExecutionResult] = {}

    def execute_sequential(self) -> list[ExecutionResult]:
        """Execute tasks in topological order (sequential)."""
        order = topological_sort(self.dag)
        results: list[ExecutionResult] = []

        for task_id in order:
            task = self.tasks[task_id]
            try:
                result = task.execute()
                er = ExecutionResult(task_id, True, result, None)
            except Exception as e:
                er = ExecutionResult(task_id, False, None, e)
            results.append(er)
            self.results[task_id] = er

        return results

    async def execute_parallel(self, max_workers: int = 4) -> list[ExecutionResult]:
        """Execute tasks in parallel groups."""
        results: list[ExecutionResult] = []
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for group in get_execution_groups(self.dag):
                futures = [
                    loop.run_in_executor(executor, self._execute_task, task_id)
                    for task_id in group
                ]
                group_results = await asyncio.gather(*futures)
                for er in group_results:
                    results.append(er)
                    self.results[er.task_id] = er

        return results

    def _execute_task(self, task_id: str) -> ExecutionResult:
        """Execute a single task."""
        task = self.tasks[task_id]
        try:
            result = task.execute()
            return ExecutionResult(task_id, True, result, None)
        except Exception as e:
            return ExecutionResult(task_id, False, None, e)

    def get_result(self, task_id: str) -> ExecutionResult | None:
        """Get execution result for a specific task."""
        return self.results.get(task_id)

    def get_execution_order(self) -> list[str]:
        """Get the topological execution order."""
        return topological_sort(self.dag)

    def get_parallel_groups(self) -> list[list[str]]:
        """Get parallel execution groups."""
        return list(get_execution_groups(self.dag))

    def validate(self) -> bool:
        """Validate that DAG has no cycles and all tasks exist."""
        try:
            order = topological_sort(self.dag)
            for task_id in order:
                if task_id not in self.tasks:
                    return False
            return True
        except CycleError:
            return False


# ─── Demo / Main ───

if __name__ == "__main__":
    # Create DAG
    dag: DAG[str] = DAG()

    # Define tasks
    def fetch_data() -> str:
        return "raw_data"

    def parse_data() -> str:
        return "parsed"

    def validate_data() -> str:
        return "validated"

    def transform_a() -> str:
        return "transformed_a"

    def transform_b() -> str:
        return "transformed_b"

    def merge_results() -> str:
        return "merged"

    def save_output() -> str:
        return "saved"

    tasks: dict[str, Task] = {
        "fetch": Task("fetch", fetch_data),
        "parse": Task("parse", parse_data),
        "validate": Task("validate", validate_data),
        "transform_a": Task("transform_a", transform_a),
        "transform_b": Task("transform_b", transform_b),
        "merge": Task("merge", merge_results),
        "save": Task("save", save_output),
    }

    # Build dependency graph
    dag.add_edge("fetch", "parse")
    dag.add_edge("parse", "validate")
    dag.add_edge("validate", "transform_a")
    dag.add_edge("validate", "transform_b")
    dag.add_edge("transform_a", "merge")
    dag.add_edge("transform_b", "merge")
    dag.add_edge("merge", "save")

    # Validate
    scheduler = DAGScheduler(dag, tasks)
    print("Valid:", scheduler.validate())
    print("Order:", scheduler.get_execution_order())
    print("Groups:", scheduler.get_parallel_groups())

    # Execute sequentially
    results = scheduler.execute_sequential()
    for r in results:
        print(f"  {r.task_id}: success={r.success}, result={r.result}")

    # Test cycle detection
    cyclic_dag: DAG[str] = DAG()
    cyclic_dag.add_edge("A", "B")
    cyclic_dag.add_edge("B", "C")
    cyclic_dag.add_edge("C", "A")

    cycle = find_cycle(cyclic_dag)
    print(f"Cycle found: {cycle}")

    try:
        topological_sort(cyclic_dag)
    except CycleError as e:
        print(f"CycleError: {e}")
