"""DAG Task Scheduler — MC-PY-02 (H × RRS)"""
from __future__ import annotations

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable


# ─── Custom exception ───
class CycleError(Exception):
    def __init__(self, cycle_nodes: list[str]) -> None:
        self.cycle_nodes: list[str] = cycle_nodes
        super().__init__(f"Cycle detected involving nodes: {', '.join(cycle_nodes)}")


# ─── Task Node ───
@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]
    dependencies: list[str] = field(default_factory=list)


# ─── DAG (adjacency list + in-degree tracking) ───
class DAG:
    def __init__(self) -> None:
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._in_degree: dict[str, int] = defaultdict(int)
        self._nodes: dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        self._nodes[node.name] = node
        if node.name not in self._in_degree:
            self._in_degree[node.name] = 0
        if node.name not in self._adjacency:
            self._adjacency[node.name] = set()

    def add_edge(self, from_task: str, to_task: str) -> None:
        """Add dependency: to_task depends on from_task."""
        if to_task not in self._adjacency[from_task]:
            self._adjacency[from_task].add(to_task)
            self._in_degree[to_task] = self._in_degree.get(to_task, 0) + 1

    def get_node(self, name: str) -> TaskNode | None:
        return self._nodes.get(name)

    def all_node_names(self) -> list[str]:
        return list(self._nodes.keys())

    def topological_sort_grouped(self) -> list[list[str]]:
        """Kahn's algorithm with wave-based grouping. Raises CycleError if cycle detected."""
        in_degree: dict[str, int] = dict(self._in_degree)
        # Ensure all nodes are tracked
        for name in self._nodes:
            if name not in in_degree:
                in_degree[name] = 0

        current_wave: list[str] = [n for n, d in in_degree.items() if d == 0]
        groups: list[list[str]] = []
        processed_count: int = 0

        while current_wave:
            groups.append(sorted(current_wave))
            processed_count += len(current_wave)
            next_wave: list[str] = []
            for node in current_wave:
                for successor in self._adjacency.get(node, set()):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        next_wave.append(successor)
            current_wave = next_wave

        total_nodes: int = len(self._nodes)
        if processed_count < total_nodes:
            cycle_nodes: list[str] = [n for n, d in in_degree.items() if d > 0]
            raise CycleError(cycle_nodes)

        return groups

    def validate(self) -> bool:
        """Validate the DAG has no cycles. Raises CycleError if cycle found."""
        self.topological_sort_grouped()
        return True


# ─── DAG Scheduler ───
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
        node = TaskNode(name=name, callable=callable, dependencies=deps)
        self._dag.add_node(node)
        for dep in deps:
            # Ensure dependency node exists in the adjacency structure
            if dep not in self._dag._nodes:
                # Placeholder — will be filled if user adds it later
                pass
            self._dag.add_edge(dep, name)

    def validate(self) -> bool:
        return self._dag.validate()

    def execute(self) -> dict[str, Any]:
        """Execute all tasks in topological order. Returns {task_name: result}."""
        groups: list[list[str]] = self._dag.topological_sort_grouped()
        results: dict[str, Any] = {}

        for group in groups:
            if self._parallel and len(group) > 1:
                group_results = self._execute_group_parallel(group)
            else:
                group_results = self._execute_group_sequential(group)
            results.update(group_results)

        return results

    def _execute_group_sequential(self, group: list[str]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name in group:
            node = self._dag.get_node(name)
            if node is None:
                continue
            results[name] = node.callable()
        return results

    def _execute_group_parallel(self, group: list[str]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            for name in group:
                node = self._dag.get_node(name)
                if node is None:
                    continue
                futures[executor.submit(node.callable)] = name
            for future in as_completed(futures):
                task_name = futures[future]
                results[task_name] = future.result()
        return results

    def get_execution_plan(self) -> list[list[str]]:
        """Return the execution groups without executing."""
        return self._dag.topological_sort_grouped()


# ─── Main guard ───
if __name__ == "__main__":
    scheduler = DAGScheduler(parallel=True, max_workers=4)

    scheduler.add_task("fetch_data", lambda: "raw_data", dependencies=[])
    scheduler.add_task("parse_data", lambda: "parsed", dependencies=["fetch_data"])
    scheduler.add_task("validate_data", lambda: "valid", dependencies=["fetch_data"])
    scheduler.add_task("transform", lambda: "transformed", dependencies=["parse_data", "validate_data"])
    scheduler.add_task("export_csv", lambda: "csv_done", dependencies=["transform"])
    scheduler.add_task("export_json", lambda: "json_done", dependencies=["transform"])
    scheduler.add_task("notify", lambda: "notified", dependencies=["export_csv", "export_json"])

    print("Execution plan:")
    for i, group in enumerate(scheduler.get_execution_plan()):
        print(f"  Wave {i}: {group}")

    results = scheduler.execute()
    print(f"\nResults: {results}")

    # Demonstrate cycle detection
    try:
        bad_scheduler = DAGScheduler()
        bad_scheduler.add_task("A", lambda: None, dependencies=["C"])
        bad_scheduler.add_task("B", lambda: None, dependencies=["A"])
        bad_scheduler.add_task("C", lambda: None, dependencies=["B"])
        bad_scheduler.validate()
    except CycleError as e:
        print(f"\nCycle detected: {e}")
