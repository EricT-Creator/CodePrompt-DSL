from typing import Callable, Any, Optional, List, Dict, Set
from dataclasses import dataclass
from collections import deque
import time


@dataclass
class ExecutionGroup:
    """Group of independent tasks that can run in parallel."""
    level: int
    tasks: List[str]


@dataclass
class ExecutionResult:
    """Result of a single task execution."""
    task: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class SchedulerResult:
    """Aggregate result of scheduler execution."""
    order: List[str]
    groups: List[ExecutionGroup]
    results: List[ExecutionResult]
    success: bool


class CycleError(Exception):
    """Exception raised when a cycle is detected in the dependency graph."""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


class TaskScheduler:
    """DAG task scheduler with topological sort and cycle detection."""
    
    def __init__(self) -> None:
        """Initialize an empty scheduler."""
        self.nodes: Dict[str, Callable[[], Any]] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.reverse_deps: Dict[str, Set[str]] = {}
    
    def add_task(self, name: str, callable: Callable[[], Any], dependencies: Optional[List[str]] = None) -> None:
        """Add a task with optional dependencies."""
        if name in self.nodes:
            raise ValueError(f"Task '{name}' already exists")
        
        self.nodes[name] = callable
        self.dependencies[name] = set(dependencies or [])
        
        for dep in self.dependencies[name]:
            if dep not in self.reverse_deps:
                self.reverse_deps[dep] = set()
            self.reverse_deps[dep].add(name)
        
        if name not in self.reverse_deps:
            self.reverse_deps[name] = set()
    
    def remove_task(self, name: str) -> None:
        """Remove a task and its dependencies."""
        if name not in self.nodes:
            raise ValueError(f"Task '{name}' does not exist")
        
        del self.nodes[name]
        
        for dep in self.dependencies[name]:
            if dep in self.reverse_deps:
                self.reverse_deps[dep].discard(name)
        
        for dependent in self.reverse_deps[name]:
            self.dependencies[dependent].discard(name)
        
        del self.dependencies[name]
        del self.reverse_deps[name]
    
    def topological_sort(self) -> List[str]:
        """Perform topological sort using Kahn's algorithm."""
        in_degree: Dict[str, int] = {}
        for node in self.nodes:
            in_degree[node] = len(self.dependencies[node])
        
        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        sorted_order: List[str] = []
        
        while queue:
            level_nodes = list(queue)
            queue.clear()
            
            for node in level_nodes:
                sorted_order.append(node)
                
                for dependent in self.reverse_deps[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        if len(sorted_order) < len(self.nodes):
            cycle = self._find_cycle(sorted_order)
            raise CycleError(cycle)
        
        return sorted_order
    
    def _find_cycle(self, sorted_nodes: List[str]) -> List[str]:
        """Find a cycle in the remaining nodes."""
        remaining = set(self.nodes.keys()) - set(sorted_nodes)
        if not remaining:
            return []
        
        visited: Set[str] = set()
        stack: List[str] = []
        node_to_visit = next(iter(remaining))
        
        def dfs(current: str, path: List[str]) -> Optional[List[str]]:
            if current in visited:
                return None
            if current in path:
                idx = path.index(current)
                return path[idx:]
            
            visited.add(current)
            path.append(current)
            
            for dependent in self.reverse_deps.get(current, set()):
                if dependent in remaining:
                    result = dfs(dependent, path)
                    if result:
                        return result
            
            path.pop()
            return None
        
        cycle = dfs(node_to_visit, [])
        return cycle or []
    
    def parallel_groups(self) -> List[ExecutionGroup]:
        """Group tasks by parallel execution level."""
        try:
            order = self.topological_sort()
        except CycleError:
            return []
        
        groups: List[ExecutionGroup] = []
        current_level: List[str] = []
        processed: Set[str] = set()
        
        for task in order:
            if not self.dependencies[task].intersection(current_level) and not any(task in self.dependencies[dep] for dep in current_level):
                current_level.append(task)
            else:
                if current_level:
                    groups.append(ExecutionGroup(level=len(groups), tasks=current_level.copy()))
                    processed.update(current_level)
                    current_level = [task]
        
        if current_level:
            groups.append(ExecutionGroup(level=len(groups), tasks=current_level.copy()))
        
        return groups
    
    def execute(self) -> SchedulerResult:
        """Execute tasks in dependency order."""
        try:
            order = self.topological_sort()
            groups = self.parallel_groups()
        except CycleError as e:
            return SchedulerResult(
                order=[],
                groups=[],
                results=[],
                success=False
            )
        
        results: List[ExecutionResult] = []
        all_success = True
        
        for group in groups:
            for task in group.tasks:
                start_time = time.time()
                try:
                    task_result = self.nodes[task]()
                    end_time = time.time()
                    results.append(ExecutionResult(
                        task=task,
                        success=True,
                        result=task_result,
                        duration=end_time - start_time
                    ))
                except Exception as e:
                    end_time = time.time()
                    results.append(ExecutionResult(
                        task=task,
                        success=False,
                        error=str(e),
                        duration=end_time - start_time
                    ))
                    all_success = False
        
        return SchedulerResult(
            order=order,
            groups=groups,
            results=results,
            success=all_success
        )