# MC-PY-02: DAG Task Scheduler - Technical Design

## Overview

This document outlines the technical design for a DAG (Directed Acyclic Graph) task scheduler with topological sort, cycle detection, parallel grouping, and custom CycleError exception.

## 1. DAG Data Structure

### Graph Representation

```python
from typing import Dict, Set, List, Optional, Callable, Any
from dataclasses import dataclass

@dataclass
class Task:
    """Represents a single task in the DAG."""
    id: str
    name: str
    dependencies: Set[str]  # IDs of tasks this task depends on
    dependents: Set[str]    # IDs of tasks that depend on this task
    handler: Callable[[], Any]  # Task execution function
    
    def __init__(self, id: str, name: str, handler: Callable[[], Any]):
        self.id = id
        self.name = name
        self.handler = handler
        self.dependencies = set()
        self.dependents = set()


class DAGScheduler:
    """
    DAG-based task scheduler with topological ordering.
    
    Responsibilities:
    - Task registration and dependency management
    - Topological sort for execution order
    - Cycle detection with CycleError
    - Parallel grouping of independent tasks
    - Sequential execution with dependency resolution
    """
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._in_degree: Dict[str, int] = {}  # Number of incoming edges
```

### Dependency Management

```python
def add_task(
    self,
    task_id: str,
    name: str,
    handler: Callable[[], Any],
    dependencies: Optional[List[str]] = None
) -> None:
    """
    Add a task to the DAG.
    
    Args:
        task_id: Unique identifier for the task
        name: Human-readable task name
        handler: Function to execute when task runs
        dependencies: List of task IDs that must complete before this task
    """
    if task_id in self._tasks:
        raise ValueError(f"Task '{task_id}' already exists")
    
    task = Task(task_id, name, handler)
    self._tasks[task_id] = task
    self._in_degree[task_id] = 0
    
    # Add dependencies
    if dependencies:
        for dep_id in dependencies:
            if dep_id not in self._tasks:
                raise ValueError(f"Dependency '{dep_id}' not found")
            
            task.dependencies.add(dep_id)
            self._tasks[dep_id].dependents.add(task_id)
            self._in_degree[task_id] += 1
```

## 2. Topological Sort Algorithm

### Kahn's Algorithm Implementation

```python
def topological_sort(self) -> List[str]:
    """
    Perform topological sort using Kahn's algorithm.
    
    Returns:
        List of task IDs in execution order
    
    Raises:
        CycleError: If a cycle is detected in the graph
    """
    # Create copy of in-degree map
    in_degree = self._in_degree.copy()
    
    # Start with tasks that have no dependencies
    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    result = []
    
    while queue:
        # Process next task with no dependencies
        current = queue.pop(0)
        result.append(current)
        
        # Reduce in-degree for all dependents
        for dependent in self._tasks[current].dependents:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # Check for cycle
    if len(result) != len(self._tasks):
        raise CycleError("Cycle detected in task dependencies")
    
    return result
```

### Algorithm Walkthrough

```
Initial State:
  Tasks: A, B, C, D, E
  Dependencies: A -> B, A -> C, B -> D, C -> D, D -> E
  In-degree: A=0, B=1, C=1, D=2, E=1

Step 1: Queue=[A], Process A
  Result: [A]
  Reduce B.in_degree to 0, C.in_degree to 0
  Queue becomes [B, C]

Step 2: Queue=[B, C], Process B
  Result: [A, B]
  Reduce D.in_degree to 1
  Queue becomes [C]

Step 3: Queue=[C], Process C
  Result: [A, B, C]
  Reduce D.in_degree to 0
  Queue becomes [D]

Step 4: Queue=[D], Process D
  Result: [A, B, C, D]
  Reduce E.in_degree to 0
  Queue becomes [E]

Step 5: Queue=[E], Process E
  Result: [A, B, C, D, E]
  Queue empty, done
```

## 3. Cycle Detection Approach

### CycleError Exception

```python
class CycleError(Exception):
    """Raised when a cycle is detected in the task dependency graph."""
    
    def __init__(self, message: str, cycle_path: Optional[List[str]] = None):
        super().__init__(message)
        self.cycle_path = cycle_path
```

### DFS-Based Cycle Detection (Alternative)

```python
def _detect_cycle_dfs(self) -> Optional[List[str]]:
    """
    Detect cycle using DFS and return the cycle path if found.
    
    Returns:
        List of task IDs forming a cycle, or None if no cycle
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in self._tasks}
    parent = {}
    
    def dfs(node: str, path: List[str]) -> Optional[List[str]]:
        color[node] = GRAY
        
        for dependent in self._tasks[node].dependents:
            if color[dependent] == GRAY:
                # Found cycle - reconstruct path
                cycle_start = path.index(dependent)
                return path[cycle_start:] + [dependent]
            
            if color[dependent] == WHITE:
                result = dfs(dependent, path + [dependent])
                if result:
                    return result
        
        color[node] = BLACK
        return None
    
    for task_id in self._tasks:
        if color[task_id] == WHITE:
            cycle = dfs(task_id, [task_id])
            if cycle:
                return cycle
    
    return None
```

### Validation Before Execution

```python
def validate(self) -> None:
    """
    Validate the DAG has no cycles before execution.
    
    Raises:
        CycleError: If a cycle is detected
    """
    cycle = self._detect_cycle_dfs()
    if cycle:
        raise CycleError(
            f"Cycle detected: {' -> '.join(cycle)}",
            cycle_path=cycle
        )
```

## 4. Parallel Grouping Strategy

### Grouping Algorithm

```python
def get_parallel_groups(self) -> List[List[str]]:
    """
    Group tasks by execution level for parallel execution.
    
    Each group contains tasks that can run simultaneously
    (no dependencies within the group).
    
    Returns:
        List of task ID groups, where each group can run in parallel
    """
    in_degree = self._in_degree.copy()
    groups = []
    
    while in_degree:
        # Find all tasks with no remaining dependencies
        current_group = [
            tid for tid, deg in in_degree.items() if deg == 0
        ]
        
        if not current_group:
            # Should not happen if no cycles (validated before)
            raise CycleError("Cycle detected during grouping")
        
        groups.append(current_group)
        
        # Remove processed tasks and update in-degrees
        for tid in current_group:
            del in_degree[tid]
            for dependent in self._tasks[tid].dependents:
                if dependent in in_degree:
                    in_degree[dependent] -= 1
    
    return groups
```

### Grouping Example

```
Dependencies: A -> B, A -> C, B -> D, C -> D, D -> E

Group 1: [A]           (no dependencies)
Group 2: [B, C]        (both depend only on A)
Group 3: [D]           (depends on B and C)
Group 4: [E]           (depends on D)
```

### Execution with Groups

```python
def execute_parallel(self) -> Dict[str, Any]:
    """
    Execute tasks grouped by parallel levels.
    
    Returns:
        Dictionary mapping task_id to execution result
    """
    self.validate()
    groups = self.get_parallel_groups()
    results = {}
    
    for group in groups:
        # Execute all tasks in group (could be parallelized with threading)
        for task_id in group:
            task = self._tasks[task_id]
            try:
                results[task_id] = task.handler()
            except Exception as e:
                results[task_id] = e
                # Could implement error handling strategy here
    
    return results
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python 3.10+, standard library only** | No external dependencies; use typing, dataclasses |
| **No graph libraries** | Implement Kahn's algorithm from scratch for topological sort |
| **Class as main output** | `DAGScheduler` class encapsulates all functionality |
| **Full type annotations** | All public methods typed with Dict, Set, List, Callable, Any, Optional |
| **Custom CycleError** | Define `CycleError(Exception)` with cycle_path attribute |
| **Single Python file** | All classes (Task, DAGScheduler, CycleError) in one file |

## Summary

This design implements a DAG scheduler using Kahn's algorithm for topological sorting. The algorithm processes tasks level by level, starting with those having no dependencies. Cycle detection uses both the topological sort (incomplete result indicates cycle) and DFS for detailed cycle path reporting. Parallel grouping identifies tasks at the same dependency level that can execute simultaneously. The class-based design encapsulates graph state and provides clean APIs for task registration, validation, and execution.
