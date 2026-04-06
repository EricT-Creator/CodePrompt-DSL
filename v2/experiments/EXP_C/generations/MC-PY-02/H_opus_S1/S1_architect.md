# Technical Design Document: DAG Task Scheduler

**Task**: MC-PY-02  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]PY310 [D]STDLIB_ONLY [!D]NO_GRAPH_LIB [O]CLASS [TYPE]FULL_HINTS [ERR]CYCLE_EXC [FILE]SINGLE`

---

## 1. DAG Data Structure

### Core Classes

```
DAGScheduler               (public API — add tasks, add edges, execute)
├── TaskNode               (represents a single task)
├── DAG                    (adjacency list graph + in-degree tracking)
└── CycleError             (custom exception for cycle detection)
```

### TaskNode

```python
@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]     # the work to execute
    dependencies: list[str]         # names of upstream tasks
```

### Adjacency List Representation

```python
class DAG:
    _adjacency: dict[str, set[str]]    # node → set of successors
    _in_degree: dict[str, int]         # node → count of incoming edges
    _nodes: dict[str, TaskNode]        # node name → TaskNode
```

**Why adjacency list?**
- O(1) edge lookup and insertion.
- Efficient in-degree tracking for topological sort (Kahn's algorithm).
- No external graph library needed.

### Edge Addition

```python
def add_edge(self, from_task: str, to_task: str) -> None:
    """Add a dependency: to_task depends on from_task."""
    self._adjacency[from_task].add(to_task)
    self._in_degree[to_task] += 1
```

---

## 2. Topological Sort Algorithm

### Kahn's Algorithm (BFS-based)

Chosen because it naturally produces parallel execution groups and integrates cycle detection.

### Steps

```
1. Initialize queue with all nodes where in_degree == 0
2. While queue is not empty:
     a. Dequeue node → add to sorted order
     b. For each successor of node:
          - Decrement successor's in_degree
          - If in_degree becomes 0 → enqueue successor
3. If sorted order length < total nodes → cycle exists → raise CycleError
```

### Parallel Grouping Integration

The algorithm is modified to process nodes **in waves** (levels) rather than one-by-one:

```
1. Initialize current_wave = [all nodes with in_degree == 0]
2. While current_wave is not empty:
     a. Record current_wave as a parallel group
     b. next_wave = []
     c. For each node in current_wave:
          - For each successor:
              Decrement in_degree
              If in_degree == 0 → add to next_wave
     d. current_wave = next_wave
3. Validate total processed == total nodes
```

Each "wave" contains nodes that can execute concurrently because all their dependencies are satisfied.

### Complexity

- Time: O(V + E) where V = nodes, E = edges.
- Space: O(V) for the queue and in-degree map.

---

## 3. Cycle Detection Approach

### Integrated with Topological Sort

Cycle detection is a **free byproduct** of Kahn's algorithm:

- After the algorithm completes, if `len(sorted_order) < len(all_nodes)`, then some nodes were never enqueued — meaning they are part of a cycle.
- The nodes in the cycle are those remaining with `in_degree > 0`.

### CycleError Exception

```python
class CycleError(Exception):
    def __init__(self, cycle_nodes: list[str]) -> None:
        self.cycle_nodes = cycle_nodes
        super().__init__(
            f"Cycle detected involving nodes: {', '.join(cycle_nodes)}"
        )
```

### Cycle Node Identification

After Kahn's algorithm, the unprocessed nodes (those still with in_degree > 0) are collected and passed to `CycleError`. This doesn't identify the exact cycle path, but it identifies all nodes participating in cycles — which is sufficient for debugging.

### When Detection Runs

- `validate()` — explicit validation before execution.
- `execute()` — implicitly calls `validate()` first. If a cycle exists, `CycleError` is raised before any task runs.

---

## 4. Parallel Grouping Strategy

### Execution Groups

The wave-based topological sort produces an ordered list of groups:

```python
groups: list[list[str]]
# Example:
# [["A", "B"],     # wave 0 — no dependencies
#  ["C", "D"],     # wave 1 — depend on A or B
#  ["E"]]          # wave 2 — depends on C and D
```

### Execution Model

```python
def execute(self) -> list[Any]:
    groups = self.topological_sort_grouped()
    results: dict[str, Any] = {}
    for group in groups:
        # Tasks within a group can run in parallel
        group_results = self._execute_group(group)
        results.update(group_results)
    return results
```

### Parallelism Options

The design supports two execution modes:

1. **Sequential within groups** (default): Tasks in a group are run one-by-one. Simpler, no threading overhead.
2. **Parallel within groups** (optional): Use `concurrent.futures.ThreadPoolExecutor` (stdlib) to run tasks in the same group concurrently.

The choice is configurable via a constructor parameter:

```python
scheduler = DAGScheduler(parallel=True, max_workers=4)
```

When `parallel=False`, the groups still provide a **valid topological order** — tasks in the same group can be interleaved in any order without violating dependencies.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Python 3.10+ | `[L]PY310` | Uses Python 3.10 features: `X \| Y` union types, `match` (if needed), structural pattern matching. |
| Stdlib only | `[D]STDLIB_ONLY` | Only `collections` (defaultdict, deque), `dataclasses`, `concurrent.futures`, `typing` from stdlib. |
| No graph library | `[!D]NO_GRAPH_LIB` | No networkx, igraph, or graph-tool. Adjacency list implemented from scratch. |
| Class-based output | `[O]CLASS` | `DAGScheduler`, `TaskNode`, `DAG`, `CycleError` are all classes. |
| Full type hints | `[TYPE]FULL_HINTS` | Every function signature, variable, and return type is annotated. |
| Cycle detection raises exception | `[ERR]CYCLE_EXC` | Custom `CycleError` exception with the list of cycle-participating nodes. |
| Single file | `[FILE]SINGLE` | All classes and logic in one `.py` file. |
