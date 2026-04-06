"""DAG Task Scheduler — MC-PY-02 (H × RRC, S2 Implementer)"""

from __future__ import annotations

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Callable, Literal


# ─── Custom Exception ───


class CycleError(Exception):
    def __init__(self, cycle_nodes: list[str]) -> None:
        self.cycle_nodes: list[str] = cycle_nodes
        super().__init__(f"Cycle detected involving nodes: {', '.join(cycle_nodes)}")


# ─── TaskNode ───


@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]
    dependencies: list[str] = field(default_factory=list)


# ─── Execution Result ───


@dataclass
class TaskExecResult:
    name: str
    status: Literal["success", "failed"]
    result: Any
    error: str | None


# ─── DAG ───


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
        if to_task not in self._adjacency[from_task]:
            self._adjacency[from_task].add(to_task)
            self._in_degree[to_task] = self._in_degree.get(to_task, 0) + 1

    def get_node(self, name: str) -> TaskNode | None:
        return self._nodes.get(name)

    def all_node_names(self) -> list[str]:
        return list(self._nodes.keys())

    def topological_sort_grouped(self) -> list[list[str]]:
        """
        Kahn's algorithm producing parallel execution groups (waves).
        Raises CycleError if cycles are detected.
        """
        in_deg: dict[str, int] = dict(self._in_degree)
        # Ensure all nodes have an in-degree entry
        for name in self._nodes:
            if name not in in_deg:
                in_deg[name] = 0

        current_wave: list[str] = [n for n, d in in_deg.items() if d == 0]
        groups: list[list[str]] = []
        processed: int = 0

        while current_wave:
            groups.append(list(current_wave))
            processed += len(current_wave)
            next_wave: list[str] = []
            for node in current_wave:
                for successor in self._adjacency.get(node, set()):
                    in_deg[successor] -= 1
                    if in_deg[successor] == 0:
                        next_wave.append(successor)
            current_wave = sorted(next_wave)  # Sort for determinism

        total_nodes: int = len(self._nodes)
        if processed < total_nodes:
            cycle_nodes: list[str] = [n for n, d in in_deg.items() if d > 0]
            raise CycleError(cycle_nodes)

        return groups


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
        node: TaskNode = TaskNode(name=name, callable=callable, dependencies=deps)
        self._dag.add_node(node)
        for dep in deps:
            # Ensure dependency node exists in DAG (if not added yet, it'll be a placeholder)
            if dep not in self._dag._nodes:
                # We only add the edge; the node should be added later or already exist
                if dep not in self._dag._adjacency:
                    self._dag._adjacency[dep] = set()
                if dep not in self._dag._in_degree:
                    self._dag._in_degree[dep] = 0
            self._dag.add_edge(dep, name)

    def validate(self) -> list[list[str]]:
        return self._dag.topological_sort_grouped()

    def execute(self) -> dict[str, TaskExecResult]:
        groups: list[list[str]] = self.validate()
        results: dict[str, TaskExecResult] = {}

        for group in groups:
            group_results: dict[str, TaskExecResult] = self._execute_group(group)
            results.update(group_results)

        return results

    def _execute_group(self, group: list[str]) -> dict[str, TaskExecResult]:
        results: dict[str, TaskExecResult] = {}

        if self._parallel and len(group) > 1:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures: dict[str, Future[Any]] = {}
                for name in group:
                    node: TaskNode | None = self._dag.get_node(name)
                    if node is None:
                        results[name] = TaskExecResult(
                            name=name,
                            status="failed",
                            result=None,
                            error=f"Node '{name}' not found",
                        )
                        continue
                    futures[name] = executor.submit(node.callable)

                for name, future in futures.items():
                    try:
                        result: Any = future.result()
                        results[name] = TaskExecResult(
                            name=name,
                            status="success",
                            result=result,
                            error=None,
                        )
                    except Exception as exc:
                        results[name] = TaskExecResult(
                            name=name,
                            status="failed",
                            result=None,
                            error=str(exc),
                        )
        else:
            for name in group:
                node = self._dag.get_node(name)
                if node is None:
                    results[name] = TaskExecResult(
                        name=name,
                        status="failed",
                        result=None,
                        error=f"Node '{name}' not found",
                    )
                    continue
                try:
                    result = node.callable()
                    results[name] = TaskExecResult(
                        name=name,
                        status="success",
                        result=result,
                        error=None,
                    )
                except Exception as exc:
                    results[name] = TaskExecResult(
                        name=name,
                        status="failed",
                        result=None,
                        error=str(exc),
                    )

        return results

    def get_execution_order(self) -> list[list[str]]:
        return self.validate()


# ─── Demo ───

if __name__ == "__main__":
    scheduler = DAGScheduler(parallel=True, max_workers=4)

    scheduler.add_task("fetch_data", lambda: "raw_data")
    scheduler.add_task("validate", lambda: "validated", dependencies=["fetch_data"])
    scheduler.add_task("transform_a", lambda: "transformed_a", dependencies=["validate"])
    scheduler.add_task("transform_b", lambda: "transformed_b", dependencies=["validate"])
    scheduler.add_task(
        "aggregate", lambda: "aggregated", dependencies=["transform_a", "transform_b"]
    )
    scheduler.add_task("save", lambda: "saved", dependencies=["aggregate"])

    print("Execution groups:")
    for i, group in enumerate(scheduler.get_execution_order()):
        print(f"  Wave {i}: {group}")

    results: dict[str, TaskExecResult] = scheduler.execute()
    print("\nResults:")
    for name, res in results.items():
        print(f"  {name}: {res.status} -> {res.result}")

    # Cycle detection demo
    print("\nCycle detection test:")
    bad_scheduler = DAGScheduler()
    bad_scheduler.add_task("A", lambda: None, dependencies=["C"])
    bad_scheduler.add_task("B", lambda: None, dependencies=["A"])
    bad_scheduler.add_task("C", lambda: None, dependencies=["B"])
    try:
        bad_scheduler.validate()
    except CycleError as e:
        print(f"  Caught: {e}")
