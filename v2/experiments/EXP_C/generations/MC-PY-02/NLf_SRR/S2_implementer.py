from __future__ import annotations

import collections
import concurrent.futures
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# ── Exceptions ──────────────────────────────────────────────────────────

class CycleError(Exception):
    def __init__(self, cycle_path: list[str], message: str | None = None) -> None:
        self.cycle_path = cycle_path
        if message is None:
            message = f"Cycle detected: {' -> '.join(cycle_path)}"
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {"error_type": "CycleError", "cycle_path": self.cycle_path, "cycle_length": len(self.cycle_path), "message": str(self)}


# ── Node status ─────────────────────────────────────────────────────────

class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Data classes ────────────────────────────────────────────────────────

@dataclass
class Node:
    node_id: str
    task: Any = None
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str = ""
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "status": self.status.value, "execution_time": round(self.execution_time, 4), "error": self.error}


@dataclass
class ExecutionResult:
    success: bool
    results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "completed": self.completed_count,
            "total": self.total_count,
            "order": self.order,
            "parallel_groups": self.parallel_groups,
            "errors": self.errors,
        }


# ── DAG ─────────────────────────────────────────────────────────────────

class DAG:
    def __init__(self) -> None:
        self._adj: dict[str, set[str]] = {}
        self._rev: dict[str, set[str]] = {}
        self._nodes: dict[str, Node] = {}

    # ── Node management ─────────────────────────────────────────────────

    def add_node(self, node_id: str, task: Any = None) -> None:
        if node_id in self._nodes:
            raise ValueError(f"Node '{node_id}' already exists")
        self._nodes[node_id] = Node(node_id=node_id, task=task)
        self._adj.setdefault(node_id, set())
        self._rev.setdefault(node_id, set())

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._nodes:
            raise ValueError(f"Source node '{src}' does not exist")
        if dst not in self._nodes:
            raise ValueError(f"Target node '{dst}' does not exist")
        if src == dst:
            raise ValueError("Self-loops not allowed")
        self._adj[src].add(dst)
        self._rev[dst].add(src)

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def predecessors(self, node_id: str) -> set[str]:
        return set(self._rev.get(node_id, set()))

    def successors(self, node_id: str) -> set[str]:
        return set(self._adj.get(node_id, set()))

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    @property
    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())


# ── Topological Sort (Kahn's algorithm) ────────────────────────────────

def topological_sort(dag: DAG) -> list[str]:
    in_deg: dict[str, int] = {nid: 0 for nid in dag.node_ids}
    for nid in dag.node_ids:
        for succ in dag.successors(nid):
            in_deg[succ] += 1

    queue: collections.deque[str] = collections.deque(nid for nid, d in in_deg.items() if d == 0)
    result: list[str] = []

    while queue:
        nid = queue.popleft()
        result.append(nid)
        for succ in dag.successors(nid):
            in_deg[succ] -= 1
            if in_deg[succ] == 0:
                queue.append(succ)

    if len(result) != dag.node_count:
        cycle = _find_cycle(dag)
        raise CycleError(cycle)

    return result


# ── Cycle detection (DFS) ──────────────────────────────────────────────

def _find_cycle(dag: DAG) -> list[str]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in dag.node_ids}
    parent: dict[str, str | None] = {nid: None for nid in dag.node_ids}

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        for v in dag.successors(u):
            if color[v] == GRAY:
                path = [v, u]
                cur = u
                while cur != v:
                    cur = parent[cur]  # type: ignore
                    if cur is None:
                        break
                    path.append(cur)
                path.reverse()
                path.append(path[0])
                return path
            if color[v] == WHITE:
                parent[v] = u
                found = dfs(v)
                if found:
                    return found
        color[u] = BLACK
        return None

    for nid in dag.node_ids:
        if color[nid] == WHITE:
            found = dfs(nid)
            if found:
                return found
    return []


# ── Parallel grouping ──────────────────────────────────────────────────

def compute_parallel_groups(dag: DAG) -> list[list[str]]:
    order = topological_sort(dag)
    level: dict[str, int] = {}
    for nid in order:
        preds = dag.predecessors(nid)
        if not preds:
            level[nid] = 0
        else:
            level[nid] = max(level.get(p, 0) for p in preds) + 1

    groups_map: dict[int, list[str]] = {}
    for nid, lv in level.items():
        groups_map.setdefault(lv, []).append(nid)

    return [groups_map[k] for k in sorted(groups_map)]


# ── TaskScheduler ───────────────────────────────────────────────────────

class TaskScheduler:
    def __init__(self) -> None:
        self._dag: DAG = DAG()

    # ── Task registration ───────────────────────────────────────────────

    def register_task(self, task_id: str, task_func: Callable[[], Any] | None = None) -> None:
        self._dag.add_node(task_id, task_func)

    def add_dependency(self, upstream: str, downstream: str) -> None:
        self._dag.add_edge(upstream, downstream)

    # ── Queries ─────────────────────────────────────────────────────────

    def topological_order(self) -> list[str]:
        return topological_sort(self._dag)

    def parallel_groups(self) -> list[list[str]]:
        return compute_parallel_groups(self._dag)

    def has_cycle(self) -> bool:
        try:
            topological_sort(self._dag)
            return False
        except CycleError:
            return True

    # ── Execution ───────────────────────────────────────────────────────

    def execute(self, max_workers: int | None = None) -> ExecutionResult:
        groups = self.parallel_groups()
        order: list[str] = []
        results: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for group in groups:
            if max_workers and max_workers > 1 and len(group) > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                    futures = {pool.submit(self._run_node, nid): nid for nid in group}
                    for fut in concurrent.futures.as_completed(futures):
                        nid = futures[fut]
                        order.append(nid)
                        try:
                            results[nid] = fut.result()
                        except Exception as exc:
                            errors[nid] = str(exc)
            else:
                for nid in group:
                    order.append(nid)
                    try:
                        results[nid] = self._run_node(nid)
                    except Exception as exc:
                        errors[nid] = str(exc)

        return ExecutionResult(
            success=len(errors) == 0,
            results=results,
            errors=errors,
            order=order,
            parallel_groups=[list(g) for g in groups],
            completed_count=len(results),
            total_count=self._dag.node_count,
        )

    def _run_node(self, node_id: str) -> Any:
        node = self._dag.get_node(node_id)
        if node is None:
            raise ValueError(f"Unknown node: {node_id}")
        node.status = NodeStatus.RUNNING
        start = time.perf_counter()
        try:
            if callable(node.task):
                result = node.task()
            else:
                result = node.task
            node.status = NodeStatus.COMPLETED
            node.result = result
            node.execution_time = time.perf_counter() - start
            return result
        except Exception as exc:
            node.status = NodeStatus.FAILED
            node.error = str(exc)
            node.execution_time = time.perf_counter() - start
            raise


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    s = TaskScheduler()
    s.register_task("A", lambda: "result_A")
    s.register_task("B", lambda: "result_B")
    s.register_task("C", lambda: "result_C")
    s.register_task("D", lambda: "result_D")
    s.add_dependency("A", "C")
    s.add_dependency("B", "C")
    s.add_dependency("C", "D")

    print("Order:", s.topological_order())
    print("Groups:", s.parallel_groups())
    result = s.execute()
    print("Result:", result.to_dict())
