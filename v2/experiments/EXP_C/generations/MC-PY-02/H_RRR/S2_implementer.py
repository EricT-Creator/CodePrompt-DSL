"""DAG Task Scheduler — MC-PY-02 (H × RRR)"""

from __future__ import annotations

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Callable

# ── Custom Exception ──
class CycleError(Exception):
    def __init__(self, cycle_nodes: list[str]) -> None:
        self.cycle_nodes: list[str] = cycle_nodes
        super().__init__(
            f"Cycle detected involving nodes: {', '.join(cycle_nodes)}"
        )

# ── Task Node ──
@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]
    dependencies: list[str] = field(default_factory=list)

# ── Execution Result ──
@dataclass
class TaskResult:
    name: str
    status: str  # "success" or "failed"
    result: Any = None
    error: str | None = None

# ── DAG Graph ──
class DAG:
    def __init__(self) -> None:
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._in_degree: dict[str, int] = defaultdict(int)
        self._nodes: dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        self._nodes[node.name] = node
        if node.name not in self._adjacency:
            self._adjacency[node.name] = set()
        if node.name not in self._in_degree:
            self._in_degree[node.name] = 0

    def add_edge(self, from_task: str, to_task: str) -> None:
        """Add a dependency: to_task depends on from_task."""
        if to_task not in self._adjacency[from_task]:
            self._adjacency[from_task].add(to_task)
            self._in_degree[to_task] = self._in_degree.get(to_task, 0) + 1

    def get_node(self, name: str) -> TaskNode | None:
        return self._nodes.get(name)

    def all_node_names(self) -> list[str]:
        return list(self._nodes.keys())

    def topological_sort_grouped(self) -> list[list[str]]:
        """
        Kahn's algorithm with wave-based grouping.
        Returns list of parallel groups.
        Raises CycleError if cycle detected.
        """
        # Work on a copy of in-degree
        in_deg: dict[str, int] = dict(self._in_degree)
        all_names: set[str] = set(self._nodes.keys())

        # Ensure all nodes have an in-degree entry
        for name in all_names:
            if name not in in_deg:
                in_deg[name] = 0

        # Initial wave: nodes with in-degree 0
        current_wave: list[str] = [n for n in all_names if in_deg[n] == 0]
        groups: list[list[str]] = []
        processed_count: int = 0

        while current_wave:
            groups.append(sorted(current_wave))  # sort for determinism
            next_wave: list[str] = []

            for node in current_wave:
                processed_count += 1
                for successor in self._adjacency.get(node, set()):
                    in_deg[successor] -= 1
                    if in_deg[successor] == 0:
                        next_wave.append(successor)

            current_wave = next_wave

        # Cycle detection
        if processed_count < len(all_names):
            cycle_nodes: list[str] = [
                n for n in all_names if in_deg.get(n, 0) > 0
            ]
            raise CycleError(sorted(cycle_nodes))

        return groups

# ── DAG Scheduler ──
class DAGScheduler:
    def __init__(self, parallel: bool = False, max_workers: int = 4) -> None:
        self._dag: DAG = DAG()
        self._parallel: bool = parallel
        self._max_workers: int = max_workers

    def add_task(
        self,
        name: str,
        callable: Callable[[], Any],
        dependencies: list[str] | None = None,
    ) -> None:
        deps: list[str] = dependencies or []
        node: TaskNode = TaskNode(name=name, callable=callable, dependencies=deps)
        self._dag.add_node(node)

        # Add edges for dependencies
        for dep in deps:
            # Ensure dependency node exists (at least as a placeholder)
            if dep not in self._dag._nodes:
                raise ValueError(f"Dependency '{dep}' not found for task '{name}'")
            self._dag.add_edge(dep, name)

    def validate(self) -> list[list[str]]:
        """Validate the DAG (check for cycles). Returns execution groups."""
        return self._dag.topological_sort_grouped()

    def execute(self) -> dict[str, TaskResult]:
        """Execute all tasks in topological order. Returns results per task."""
        groups: list[list[str]] = self.validate()
        results: dict[str, TaskResult] = {}

        for group in groups:
            group_results: dict[str, TaskResult] = self._execute_group(group)
            results.update(group_results)

        return results

    def _execute_group(self, group: list[str]) -> dict[str, TaskResult]:
        """Execute a group of independent tasks."""
        results: dict[str, TaskResult] = {}

        if self._parallel and len(group) > 1:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures: dict[str, Future[Any]] = {}
                for name in group:
                    node: TaskNode | None = self._dag.get_node(name)
                    if node is None:
                        continue
                    futures[name] = executor.submit(node.callable)

                for name, future in futures.items():
                    try:
                        result: Any = future.result()
                        results[name] = TaskResult(
                            name=name, status="success", result=result
                        )
                    except Exception as exc:
                        results[name] = TaskResult(
                            name=name, status="failed", error=str(exc)
                        )
        else:
            for name in group:
                node = self._dag.get_node(name)
                if node is None:
                    continue
                try:
                    result = node.callable()
                    results[name] = TaskResult(
                        name=name, status="success", result=result
                    )
                except Exception as exc:
                    results[name] = TaskResult(
                        name=name, status="failed", error=str(exc)
                    )

        return results

    def get_execution_plan(self) -> list[list[str]]:
        """Return the execution plan as grouped task names."""
        return self.validate()


# ── Main (demo) ──
if __name__ == "__main__":
    scheduler = DAGScheduler(parallel=True, max_workers=4)

    # Define tasks
    scheduler.add_task("fetch_data", lambda: {"rows": 100})
    scheduler.add_task("fetch_config", lambda: {"timeout": 30})
    scheduler.add_task(
        "process",
        lambda: "processed",
        dependencies=["fetch_data", "fetch_config"],
    )
    scheduler.add_task("validate", lambda: "validated", dependencies=["process"])
    scheduler.add_task("save", lambda: "saved", dependencies=["validate"])
    scheduler.add_task("notify", lambda: "notified", dependencies=["validate"])

    # Show plan
    plan: list[list[str]] = scheduler.get_execution_plan()
    print("Execution plan:")
    for i, group in enumerate(plan):
        print(f"  Wave {i}: {group}")

    # Execute
    results: dict[str, TaskResult] = scheduler.execute()
    print("\nResults:")
    for name, result in results.items():
        print(f"  {name}: {result.status} -> {result.result}")

    # Test cycle detection
    print("\nCycle detection test:")
    try:
        bad_scheduler = DAGScheduler()
        bad_scheduler.add_task("A", lambda: None)
        bad_scheduler.add_task("B", lambda: None, dependencies=["A"])
        bad_scheduler.add_task("C", lambda: None, dependencies=["B"])
        # Manually add cycle edge C -> A
        bad_scheduler._dag.add_edge("C", "A")
        bad_scheduler.validate()
    except CycleError as e:
        print(f"  Caught: {e}")
        print(f"  Cycle nodes: {e.cycle_nodes}")
