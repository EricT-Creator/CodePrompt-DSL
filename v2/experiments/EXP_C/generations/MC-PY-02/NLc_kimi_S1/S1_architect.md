# MC-PY-02: DAG Task Scheduler - Technical Design Document

## 1. DAG Data Structure

### Graph Representation
```python
from dataclasses import dataclass, field
from typing import TypeVar, Generic

T = TypeVar('T')

@dataclass
class DAG(Generic[T]):
    """Directed Acyclic Graph for task scheduling."""
    
    # Adjacency list: node -> set of dependents (nodes that depend on it)
    _dependencies: dict[T, set[T]] = field(default_factory=dict)
    
    # Reverse adjacency: node -> set of dependencies (nodes it depends on)
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
        
        # from_node is a dependency of to_node
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
        
        # Remove from dependents' reverse deps
        for dependent in self._dependencies[node]:
            self._reverse_deps[dependent].discard(node)
        
        # Remove from dependencies' forward deps
        for dependency in self._reverse_deps[node]:
            self._dependencies[dependency].discard(node)
        
        del self._dependencies[node]
        del self._reverse_deps[node]
```

### Task Definition
```python
from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class Task:
    """A task with an ID and executable function."""
    task_id: str
    func: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    
    def execute(self) -> Any:
        """Execute the task function."""
        return self.func(*self.args, **self.kwargs)
```

## 2. Topological Sort Algorithm

### Kahn's Algorithm Implementation
```python
from collections import deque

def topological_sort(dag: DAG[T]) -> list[T]:
    """
    Perform topological sort using Kahn's algorithm.
    Returns nodes in execution order.
    Raises CycleError if cycle detected.
    """
    # Calculate in-degrees
    in_degree: dict[T, int] = {node: 0 for node in dag.get_nodes()}
    for node in dag.get_nodes():
        for dependent in dag.get_dependents(node):
            in_degree[dependent] += 1
    
    # Start with nodes having no dependencies
    queue: deque[T] = deque([
        node for node, degree in in_degree.items()
        if degree == 0
    ])
    
    result: list[T] = []
    visited_count = 0
    
    while queue:
        node = queue.popleft()
        result.append(node)
        visited_count += 1
        
        # Reduce in-degree of dependents
        for dependent in dag.get_dependents(node):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # Check for cycle
    if visited_count != len(dag.get_nodes()):
        raise CycleError("Graph contains a cycle")
    
    return result
```

### DFS-Based Alternative
```python
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
    
    # Reverse to get correct order
    result.reverse()
    return result
```

## 3. Cycle Detection Approach

### CycleError Exception
```python
class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    
    def __init__(self, message: str, cycle: list[Any] | None = None):
        super().__init__(message)
        self.cycle = cycle
```

### Cycle Detection with Path
```python
def find_cycle(dag: DAG[T]) -> list[T] | None:
    """Find and return a cycle if one exists."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[T, int] = {node: WHITE for node in dag.get_nodes()}
    parent: dict[T, T | None] = {node: None for node in dag.get_nodes()}
    
    def dfs(node: T, path: list[T]) -> list[T] | None:
        color[node] = GRAY
        
        for dependent in dag.get_dependents(node):
            if color[dependent] == GRAY:
                # Found cycle - reconstruct path
                cycle_start = path.index(dependent)
                return path[cycle_start:] + [dependent]
            
            if color[dependent] == WHITE:
                parent[dependent] = node
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
```

## 4. Parallel Grouping Strategy

### Independent Task Groups
```python
from typing import Iterator

def get_execution_groups(dag: DAG[T]) -> Iterator[list[T]]:
    """
    Group tasks into levels where each level can execute in parallel.
    Each group contains tasks with no remaining dependencies.
    """
    # Calculate in-degrees
    in_degree: dict[T, int] = {node: 0 for node in dag.get_nodes()}
    for node in dag.get_nodes():
        for dependent in dag.get_dependents(node):
            in_degree[dependent] += 1
    
    remaining = set(dag.get_nodes())
    
    while remaining:
        # Find all nodes with no remaining dependencies
        group = [
            node for node in remaining
            if in_degree[node] == 0
        ]
        
        if not group:
            raise CycleError("Cycle detected - no nodes with zero in-degree")
        
        yield group
        
        # Remove group from graph
        for node in group:
            remaining.remove(node)
            for dependent in dag.get_dependents(node):
                in_degree[dependent] -= 1
```

### Scheduler Class with Parallel Execution
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    result: Any
    error: Exception | None

class DAGScheduler:
    """Task scheduler for DAG execution."""
    
    def __init__(self, dag: DAG[str], tasks: dict[str, Task]):
        self.dag = dag
        self.tasks = tasks
        self.results: dict[str, ExecutionResult] = {}
    
    def execute_sequential(self) -> list[ExecutionResult]:
        """Execute tasks in topological order (sequential)."""
        order = topological_sort(self.dag)
        results = []
        
        for task_id in order:
            task = self.tasks[task_id]
            try:
                result = task.execute()
                results.append(ExecutionResult(task_id, True, result, None))
            except Exception as e:
                results.append(ExecutionResult(task_id, False, None, e))
        
        return results
    
    async def execute_parallel(self, max_workers: int = 4) -> list[ExecutionResult]:
        """Execute tasks in parallel groups."""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for group in get_execution_groups(self.dag):
                # Execute group in parallel
                futures = [
                    asyncio.get_event_loop().run_in_executor(
                        executor, self._execute_task, task_id
                    )
                    for task_id in group
                ]
                group_results = await asyncio.gather(*futures)
                results.extend(group_results)
        
        return results
    
    def _execute_task(self, task_id: str) -> ExecutionResult:
        """Execute a single task."""
        task = self.tasks[task_id]
        try:
            result = task.execute()
            return ExecutionResult(task_id, True, result, None)
        except Exception as e:
            return ExecutionResult(task_id, False, None, e)
```

## 5. Constraint Acknowledgment

### Python 3.10+, stdlib only
**Addressed by:** Only imports from Python standard library (typing, dataclasses, collections, asyncio, concurrent.futures). No external dependencies.

### No networkx/graphlib
**Addressed by:** DAG implemented using custom adjacency list with dictionaries and sets. No NetworkX, graphlib, or other graph libraries.

### Output as class
**Addressed by:** Main exports are `DAG` class and `DAGScheduler` class. All functionality encapsulated in class-based design.

### Full type annotations
**Addressed by:** Complete type hints on all functions, methods, and classes. Uses generics for type-safe DAG operations.

### CycleError on cycles
**Addressed by:** Custom `CycleError` exception defined and raised when cycle detected in topological sort or execution.

### Single file
**Addressed by:** Single Python file containing DAG class, Task class, DAGScheduler class, and all supporting functions.
