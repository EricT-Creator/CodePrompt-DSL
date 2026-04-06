import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


class CycleError(Exception):
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


@dataclass
class TaskNode:
    name: str
    callable: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)


@dataclass
class ExecutionGroup:
    level: int
    tasks: List[str]


@dataclass
class ExecutionResult:
    task: str
    success: bool
    result: Any
    error: Optional[str]
    duration: float


@dataclass
class SchedulerResult:
    order: List[str]
    groups: List[ExecutionGroup]
    results: List[ExecutionResult]
    success: bool


class TaskScheduler:
    def __init__(self) -> None:
        self._nodes: Dict[str, TaskNode] = {}
        self._edges: Dict[str, Set[str]] = {}
        self._reverse_edges: Dict[str, Set[str]] = {}
    
    def add_task(self, name: str, callable: Callable[[], Any], dependencies: Optional[List[str]] = None) -> None:
        self._nodes[name] = TaskNode(name=name, callable=callable, dependencies=set(dependencies or []))
        self._edges[name] = set(dependencies or [])
        if name not in self._reverse_edges:
            self._reverse_edges[name] = set()
        for dep in (dependencies or []):
            if dep not in self._reverse_edges:
                self._reverse_edges[dep] = set()
            self._reverse_edges[dep].add(name)
    
    def remove_task(self, name: str) -> None:
        if name in self._nodes:
            del self._nodes[name]
        if name in self._edges:
            del self._edges[name]
        if name in self._reverse_edges:
            for dependent in self._reverse_edges[name]:
                if dependent in self._edges:
                    self._edges[dependent].discard(name)
            del self._reverse_edges[name]
        for deps in self._edges.values():
            deps.discard(name)
    
    def detect_cycle(self) -> Optional[List[str]]:
        try:
            self.topological_sort()
            return None
        except CycleError as e:
            return e.cycle
    
    def topological_sort(self) -> List[str]:
        in_degree: Dict[str, int] = {node: len(self._edges.get(node, set())) for node in self._nodes}
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result: List[str] = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            for dependent in self._reverse_edges.get(current, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self._nodes):
            remaining = set(self._nodes.keys()) - set(result)
            cycle = self._extract_cycle(list(remaining))
            raise CycleError(cycle)
        
        return result
    
    def _extract_cycle(self, remaining: List[str]) -> List[str]:
        visited: Set[str] = set()
        rec_stack: List[str] = []
        
        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.append(node)
            for dep in self._edges.get(node, set()):
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result
                elif dep in rec_stack:
                    cycle_start = rec_stack.index(dep)
                    return rec_stack[cycle_start:] + [dep]
            rec_stack.pop()
            return None
        
        for node in remaining:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle
        return remaining[:2] + [remaining[0]] if len(remaining) >= 2 else remaining
    
    def parallel_groups(self) -> List[ExecutionGroup]:
        in_degree: Dict[str, int] = {node: len(self._edges.get(node, set())) for node in self._nodes}
        current_level: List[str] = [node for node, degree in in_degree.items() if degree == 0]
        groups: List[ExecutionGroup] = []
        level = 0
        
        while current_level:
            groups.append(ExecutionGroup(level=level, tasks=current_level.copy()))
            next_level: List[str] = []
            for node in current_level:
                for dependent in self._reverse_edges.get(node, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_level.append(dependent)
            current_level = next_level
            level += 1
        
        return groups
    
    def execute(self) -> SchedulerResult:
        try:
            order = self.topological_sort()
        except CycleError:
            return SchedulerResult(order=[], groups=[], results=[], success=False)
        
        groups = self.parallel_groups()
        results: List[ExecutionResult] = []
        
        for group in groups:
            for task_name in group.tasks:
                if task_name not in self._nodes:
                    continue
                node = self._nodes[task_name]
                start = time.time()
                try:
                    result = node.callable()
                    duration = time.time() - start
                    results.append(ExecutionResult(task=task_name, success=True, result=result, error=None, duration=duration))
                except Exception as e:
                    duration = time.time() - start
                    results.append(ExecutionResult(task=task_name, success=False, result=None, error=str(e), duration=duration))
        
        return SchedulerResult(order=order, groups=groups, results=results, success=all(r.success for r in results))


if __name__ == "__main__":
    scheduler = TaskScheduler()
    scheduler.add_task("A", lambda: print("Task A"))
    scheduler.add_task("B", lambda: print("Task B"), ["A"])
    result = scheduler.execute()
    print(result)
