# MC-PY-02: DAG Task Scheduler — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. DAG Data Structure

### 1.1 Graph Representation

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Task:
    """A node in the DAG"""
    id: str
    name: str
    func: callable = field(compare=False)
    dependencies: set[str] = field(default_factory=set)

@dataclass
class DAG:
    """Directed Acyclic Graph of tasks"""
    tasks: dict[str, Task] = field(default_factory=dict)
    
    def add_task(self, task: Task) -> None:
        """Add a task to the DAG"""
        self.tasks[task.id] = task
    
    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add dependency edge: task_id depends_on another task"""
        if task_id in self.tasks:
            self.tasks[task_id].dependencies.add(depends_on)
```

### 1.2 Graph Construction Example

```python
# Build DAG
dag = DAG()
dag.add_task(Task("A", "Setup", setup_func))
dag.add_task(Task("B", "Process A", process_a, {"A"}))
dag.add_task(Task("C", "Process B", process_b, {"A"}))
dag.add_task(Task("D", "Finalize", finalize, {"B", "C"}))

# Graph:
#     A
#    / \
#   B   C
#    \ /
#     D
```

---

## 2. Topological Sort Algorithm

### 2.1 Kahn's Algorithm

```python
from collections import deque

def topological_sort(self) -> list[str]:
    """
    Kahn's algorithm for topological sorting.
    Returns task IDs in execution order.
    """
    # Calculate in-degrees
    in_degree = {tid: 0 for tid in self.tasks}
    for task in self.tasks.values():
        for dep in task.dependencies:
            if dep in in_degree:
                in_degree[task.id] += 1
    
    # Start with tasks that have no dependencies
    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    result = []
    
    while queue:
        current = queue.popleft()
        result.append(current)
        
        # Find tasks that depend on current
        for task in self.tasks.values():
            if current in task.dependencies:
                in_degree[task.id] -= 1
                if in_degree[task.id] == 0:
                    queue.append(task.id)
    
    # Check for cycle
    if len(result) != len(self.tasks):
        raise CycleError("Graph contains a cycle")
    
    return result
```

### 2.2 Alternative: DFS-Based

```python
def topological_sort_dfs(self) -> list[str]:
    """DFS-based topological sort"""
    visited = set()
    temp_mark = set()
    result = []
    
    def visit(task_id: str):
        if task_id in temp_mark:
            raise CycleError(f"Cycle detected at {task_id}")
        if task_id in visited:
            return
        
        temp_mark.add(task_id)
        task = self.tasks[task_id]
        for dep in task.dependencies:
            visit(dep)
        temp_mark.remove(task_id)
        visited.add(task_id)
        result.append(task_id)
    
    for task_id in self.tasks:
        if task_id not in visited:
            visit(task_id)
    
    return result
```

---

## 3. Cycle Detection Approach

### 3.1 CycleError Definition

```python
class CycleError(Exception):
    """Raised when a cycle is detected in the DAG"""
    pass
```

### 3.2 Detection During Sort

Cycle detection is integrated into topological sort:
- Kahn's: If result length < task count, there's a cycle
- DFS: If we encounter a temporarily marked node, there's a cycle

### 3.3 Standalone Cycle Check

```python
def has_cycle(self) -> bool:
    """Check if DAG contains a cycle without returning sort order"""
    try:
        self.topological_sort()
        return False
    except CycleError:
        return True
```

---

## 4. Parallel Grouping Strategy

### 4.1 Level-Based Grouping

```python
def get_parallel_groups(self) -> list[list[str]]:
    """
    Group tasks by execution level.
    Tasks in the same group can run in parallel.
    """
    # Get execution order
    order = self.topological_sort()
    
    # Calculate depth (longest path from root)
    depth = {tid: 0 for tid in self.tasks}
    for task_id in order:
        task = self.tasks[task_id]
        for dep in task.dependencies:
            depth[task_id] = max(depth[task_id], depth[dep] + 1)
    
    # Group by depth
    groups: dict[int, list[str]] = {}
    for task_id, d in depth.items():
        groups.setdefault(d, []).append(task_id)
    
    # Return groups in order
    return [groups[i] for i in sorted(groups.keys())]
```

### 4.2 Execution Groups Example

```
Level 0: [A]           # No dependencies
Level 1: [B, C]        # Depends on A
Level 2: [D]           # Depends on B and C

Groups: [[A], [B, C], [D]]
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]PY310` | Python 3.10+ features |
| `[D]STDLIB_ONLY` | No external dependencies |
| `[!D]NO_GRAPH_LIB` | No networkx; manual graph implementation |
| `[O]CLASS` | DAG and Task as dataclasses |
| `[TYPE]FULL_HINTS` | Full type annotations |
| `[ERR]CYCLE_EXC` | Custom CycleError exception |
| `[FILE]SINGLE` | Single file implementation |

---

## 6. Scheduler Class

```python
@dataclass
class Scheduler:
    dag: DAG
    
    def schedule(self) -> list[list[str]]:
        """Get parallel execution groups"""
        return self.dag.get_parallel_groups()
    
    def execute(self) -> dict[str, Any]:
        """Execute tasks in order, respecting dependencies"""
        order = self.dag.topological_sort()
        results = {}
        
        for task_id in order:
            task = self.dag.tasks[task_id]
            # Execute task
            result = task.func()
            results[task_id] = result
        
        return results
    
    def execute_parallel(self) -> dict[str, Any]:
        """Execute tasks by parallel groups"""
        groups = self.get_parallel_groups()
        results = {}
        
        for group in groups:
            # Tasks in group can run in parallel
            for task_id in group:
                task = self.dag.tasks[task_id]
                results[task_id] = task.func()
        
        return results
```

---

## 7. File Structure

```
MC-PY-02/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── scheduler.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
