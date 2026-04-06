from typing import Any, Callable, Optional
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class CycleError(Exception):
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")

@dataclass
class TaskNode:
    name: str
    fn: Callable[[], Any]
    depends_on: list[str] = field(default_factory=list)
    result: Any = None
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class DAGScheduler:
    graph: dict[str, set[str]] = field(default_factory=dict)
    tasks: dict[str, TaskNode] = field(default_factory=dict)
    
    def add_task(self, name: str, fn: Callable[[], Any], depends_on: Optional[list[str]] = None) -> 'DAGScheduler':
        self.tasks[name] = TaskNode(name=name, fn=fn, depends_on=depends_on or [])
        self.graph[name] = set(depends_on or [])
        return self
    
    def validate(self) -> None:
        colors: dict[str, int] = {name: 0 for name in self.graph}
        
        def dfs(node: str, path: list[str]) -> None:
            colors[node] = 1
            for dep in self.graph.get(node, set()):
                if dep not in colors:
                    continue
                if colors[dep] == 1:
                    cycle_start = path.index(dep)
                    raise CycleError(path[cycle_start:] + [dep])
                if colors[dep] == 0:
                    dfs(dep, path + [dep])
            colors[node] = 2
        
        for node in self.graph:
            if colors[node] == 0:
                dfs(node, [node])
    
    def topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = {name: 0 for name in self.graph}
        for deps in self.graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 0
        
        for name, deps in self.graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0) + 1
        
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result: list[str] = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for name, deps in self.graph.items():
                if node in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        
        if len(result) != len(self.graph):
            unvisited = set(self.graph.keys()) - set(result)
            raise CycleError(list(unvisited))
        
        return result
    
    def parallel_groups(self) -> list[list[str]]:
        in_degree: dict[str, int] = {name: len(deps) for name, deps in self.graph.items()}
        remaining = set(self.graph.keys())
        groups: list[list[str]] = []
        
        while remaining:
            group = [name for name in remaining if in_degree[name] == 0]
            if not group:
                raise CycleError(list(remaining))
            groups.append(group)
            
            for node in group:
                remaining.remove(node)
                for name, deps in self.graph.items():
                    if node in deps and name in remaining:
                        in_degree[name] -= 1
        
        return groups
    
    def execute(self, max_workers: Optional[int] = None) -> dict[str, Any]:
        self.validate()
        groups = self.parallel_groups()
        
        for group in groups:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    name: executor.submit(self._run_task, name)
                    for name in group
                }
                for name, future in futures.items():
                    try:
                        future.result()
                    except Exception:
                        raise
        
        return {name: task.result for name, task in self.tasks.items()}
    
    def _run_task(self, name: str) -> Any:
        task = self.tasks[name]
        task.status = TaskStatus.RUNNING
        try:
            task.result = task.fn()
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.status = TaskStatus.FAILED
            raise e
        return task.result
