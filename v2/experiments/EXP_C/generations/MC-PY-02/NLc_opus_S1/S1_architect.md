# Technical Design Document — DAG Task Scheduler

## 1. Overview

A directed acyclic graph (DAG) task scheduler that accepts a task dependency graph, performs topological sorting, detects cycles (raising `CycleError`), groups independent tasks for parallel execution, and provides an `execute` method that runs tasks in the correct order.

## 2. DAG Data Structure

### Core Classes

#### `DAGScheduler`
- The main public class.
- Fields:
  - `graph: dict[str, set[str]]` — adjacency list mapping each task to its set of dependencies (predecessors).
  - `tasks: dict[str, TaskNode]` — maps task names to their `TaskNode` metadata.
- Methods:
  - `add_task(name, fn, depends_on)`: register a task with its callable and dependency list.
  - `validate()`: run cycle detection; raise `CycleError` if any cycle exists.
  - `topological_sort() -> list[str]`: return a valid execution order.
  - `parallel_groups() -> list[list[str]]`: return tasks grouped by execution level.
  - `execute()`: run all tasks in topological order, executing each parallel group together.

#### `TaskNode`
- Represents a single task in the graph.
- Fields: `name: str`, `fn: Callable[[], Any]`, `depends_on: list[str]`, `result: Any | None`, `status: TaskStatus`.

#### `TaskStatus` (Enum)
- Values: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.

#### `CycleError` (Exception)
- Raised when cycle detection finds a back edge.
- Contains the cycle path as a list of task names for diagnostic purposes: `cycle: list[str]`.

### Graph Representation
- Adjacency list using `dict[str, set[str]]` where keys are task names and values are sets of dependency task names.
- Reverse adjacency (dependents) can be derived but is not stored separately to keep the model simple.

## 3. Topological Sort Algorithm

### Kahn's Algorithm (BFS-based)

1. Compute `in_degree: dict[str, int]` for each task (count of dependencies).
2. Initialize a queue with all tasks where `in_degree == 0` (no dependencies).
3. While the queue is not empty:
   a. Dequeue a task, append to result list.
   b. For each dependent of that task, decrement its `in_degree`.
   c. If a dependent's `in_degree` reaches 0, enqueue it.
4. If the result list length < total tasks, a cycle exists → raise `CycleError`.

### Why Kahn's
- Naturally integrates with cycle detection (incomplete traversal = cycle).
- Produces a level-by-level ordering that maps directly to parallel grouping.
- No recursion, avoiding stack depth issues for large graphs.

## 4. Cycle Detection Approach

### Primary: Integrated with Kahn's
- After Kahn's algorithm completes, if `len(sorted_result) < len(all_tasks)`, then the remaining tasks form one or more cycles.
- The unvisited tasks can be inspected to reconstruct the cycle path.

### Secondary: DFS with Coloring (for detailed cycle path)
- Three colors: WHITE (unvisited), GRAY (in current path), BLACK (fully processed).
- Traverse from each WHITE node via DFS.
- If a GRAY node is encountered, a back edge exists → extract the cycle path from the recursion stack.
- This approach provides the exact cycle (list of task names forming the loop), which is stored in `CycleError.cycle`.

### Integration
- `validate()` runs the DFS coloring approach to detect cycles and provide a detailed error.
- `topological_sort()` uses Kahn's for the actual ordering and raises `CycleError` if ordering is incomplete.

## 5. Parallel Grouping Strategy

### Level-Based Grouping
Tasks at the same "depth" in the DAG (i.e., all their dependencies are in earlier levels) can execute in parallel.

### Algorithm
1. Run a modified Kahn's that processes one "wave" at a time:
   - All tasks with `in_degree == 0` form Level 0.
   - Remove them, update in-degrees; new `in_degree == 0` tasks form Level 1.
   - Repeat until all tasks are grouped.
2. Return `list[list[str]]` where each inner list is a parallel group.

### Example
```
A → C
B → C
C → D
```
Groups: `[[A, B], [C], [D]]` — A and B can run in parallel; C waits for both; D waits for C.

### Execution
- Within each group, tasks are independent and can be submitted concurrently.
- The `execute()` method processes groups sequentially: all tasks in group[i] complete before group[i+1] begins.
- Within a group, tasks run via `concurrent.futures.ThreadPoolExecutor` or simply sequentially if concurrency is not critical for the demo.

## 6. Execute Method

### Flow
```
validate()  # raise CycleError if cycles
groups = parallel_groups()
for group in groups:
    for task_name in group:
        task = tasks[task_name]
        task.status = RUNNING
        try:
            task.result = task.fn()
            task.status = COMPLETED
        except Exception:
            task.status = FAILED
            raise  # or continue with error handling policy
```

### Error Policy
- Default: fail-fast (abort on first task failure).
- Optional: continue and collect errors, returning a summary of which tasks succeeded/failed.

## 7. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python 3.10+, stdlib only** | All code uses only Python standard library. No third-party packages. |
| 2 | **No networkx/graphlib** | DAG representation, topological sort, and cycle detection are all implemented from scratch. Neither `networkx` nor `graphlib.TopologicalSorter` is used. |
| 3 | **Output as class** | The primary deliverable is the `DAGScheduler` class, instantiable and usable programmatically. |
| 4 | **Full type annotations** | Every function, method, parameter, and return value is type-annotated. |
| 5 | **CycleError on cycles** | A custom `CycleError` exception is raised with the cycle path when cycle detection finds a back edge. |
| 6 | **Single file** | All classes (`DAGScheduler`, `TaskNode`, `CycleError`, `TaskStatus`) reside in a single `.py` file. |
