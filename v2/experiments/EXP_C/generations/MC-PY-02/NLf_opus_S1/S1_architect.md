# Technical Design Document — DAG Task Scheduler

## 1. Overview

This document describes the architecture for a DAG (Directed Acyclic Graph) task scheduler. The scheduler accepts a task dependency graph, performs topological sort, detects cycles (raising a custom `CycleError`), groups independent tasks for parallel execution, and provides an `execute` method that runs tasks in dependency order.

## 2. DAG Data Structure

### 2.1 Graph Representation

The DAG is represented using an adjacency list stored as a dictionary:

- **nodes**: `dict[str, TaskNode]` — Maps task names to their metadata.
- **edges**: `dict[str, set[str]]` — Maps each task to the set of tasks it depends on (incoming edges).
- **reverse_edges**: `dict[str, set[str]]` — Maps each task to the set of tasks that depend on it (outgoing edges). Used for efficient downstream traversal.

### 2.2 Interfaces

- **TaskNode**: `{ name: str; callable: Callable[[], Any]; dependencies: set[str] }`
- **ExecutionGroup**: `{ level: int; tasks: list[str] }` — A group of independent tasks that can run in parallel.
- **ExecutionResult**: `{ task: str; success: bool; result: Any; error: str | None; duration: float }`
- **SchedulerResult**: `{ order: list[str]; groups: list[ExecutionGroup]; results: list[ExecutionResult]; success: bool }`

### 2.3 TaskScheduler Class

The main class with the following public methods:

- `add_task(name: str, callable: Callable[[], Any], dependencies: list[str] | None = None) -> None`
- `remove_task(name: str) -> None`
- `topological_sort() -> list[str]`
- `detect_cycle() -> list[str] | None` — Returns the cycle path if found, else None.
- `parallel_groups() -> list[ExecutionGroup]`
- `execute() -> SchedulerResult`

## 3. Topological Sort Algorithm

### 3.1 Algorithm: Kahn's Algorithm (BFS-based)

Kahn's algorithm is chosen because it naturally produces parallel grouping (by levels) and integrates cycle detection.

### 3.2 Steps

1. Compute in-degree for each node: `in_degree[node] = len(edges[node])`.
2. Initialize a queue with all nodes having `in_degree == 0` (no dependencies).
3. While the queue is non-empty:
   a. Dequeue all current nodes (this forms one parallel group).
   b. For each dequeued node, decrement the in-degree of its dependents (via `reverse_edges`).
   c. If any dependent's in-degree drops to 0, add it to the next batch.
   d. Append dequeued nodes to the sorted order.
4. After the loop, if the sorted order contains fewer nodes than the total, a cycle exists.

### 3.3 Complexity

- Time: O(V + E) where V = number of tasks, E = number of dependency edges.
- Space: O(V) for in-degree tracking and queue.

## 4. Cycle Detection Approach

### 4.1 Primary Detection (Kahn's)

If Kahn's algorithm terminates with `len(sorted_order) < len(nodes)`, a cycle exists among the remaining nodes. At this point, raise `CycleError`.

### 4.2 Cycle Path Extraction (DFS)

To provide a useful error message with the actual cycle path:

1. Among the nodes not in `sorted_order`, perform a DFS.
2. Track visited nodes and the current recursion stack.
3. When a node is encountered that is already in the recursion stack, extract the cycle by backtracking from the current node to its first occurrence in the stack.
4. The cycle path is included in the `CycleError` exception message.

### 4.3 CycleError Exception

```
class CycleError(Exception):
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")
```

## 5. Parallel Grouping Strategy

### 5.1 Level-Based Grouping

Kahn's algorithm naturally produces levels:

- **Level 0**: All tasks with no dependencies (sources).
- **Level 1**: Tasks whose only dependencies are in Level 0.
- **Level N**: Tasks whose dependencies are all in levels < N.

### 5.2 Group Output

Each level becomes an `ExecutionGroup`:

```
groups = [
    ExecutionGroup(level=0, tasks=["A", "B"]),
    ExecutionGroup(level=1, tasks=["C", "D"]),
    ExecutionGroup(level=2, tasks=["E"]),
]
```

Tasks within the same group are independent and can be executed in parallel.

### 5.3 Execution Strategy

The `execute()` method processes groups sequentially (Level 0, then Level 1, etc.). Within each group, tasks can conceptually run in parallel. In a single-threaded context, they run sequentially within the group but the grouping information is preserved for systems that support parallelism.

## 6. Execute Method

### 6.1 Flow

1. Call `topological_sort()` (which also detects cycles and raises `CycleError` if found).
2. Obtain `parallel_groups()`.
3. For each group in order:
   a. For each task in the group:
      - Record start time.
      - Call `task.callable()` in a try/except.
      - Record end time and result (or error).
      - Append `ExecutionResult`.
4. Return `SchedulerResult` with the full order, groups, and per-task results.

### 6.2 Error Handling

A failing task does not stop execution of other tasks in the same group or subsequent groups (unless they depend on the failed task — that's a policy decision, documented as "fail-forward" by default).

## 7. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python 3.10+, standard library only | Only stdlib modules used: `typing`, `dataclasses`, `collections`, `time`. No external packages. |
| 2 | No networkx/graphlib; implement topological sort from scratch | Topological sort uses a hand-written Kahn's algorithm. Cycle detection uses custom DFS. Neither `networkx` nor `graphlib` is imported. |
| 3 | Main output must be a class | `TaskScheduler` is the primary class encapsulating all graph operations, sorting, grouping, and execution. |
| 4 | Full type annotations on all public methods | All public methods have parameter types, return types, and generic type annotations where applicable. |
| 5 | Raise CycleError when cycle detected | A custom `CycleError(Exception)` class is defined. It is raised during `topological_sort()` when Kahn's algorithm finds remaining nodes, with the cycle path extracted via DFS. |
| 6 | Single Python file | All classes (`TaskScheduler`, `CycleError`, dataclasses) are in one `.py` file. |
