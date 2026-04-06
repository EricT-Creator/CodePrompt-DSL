from enum import Enum
from typing import Any, Callable, Optional, Dict, Set, List, Tuple
import concurrent.futures
from collections import deque


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CycleError(Exception):
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"DAG contains a cycle: {' -> '.join(cycle)}")


class TaskNode:
    def __init__(self, name: str, fn: Callable[[], Any], depends_on: List[str]):
        self.name: str = name
        self.fn: Callable[[], Any] = fn
        self.depends_on: List[str] = depends_on
        self.result: Optional[Any] = None
        self.status: TaskStatus = TaskStatus.PENDING


class DAGScheduler:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}
        self.tasks: Dict[str, TaskNode] = {}
        self._reverse_graph: Dict[str, Set[str]] = {}

    def add_task(self, name: str, fn: Callable[[], Any], depends_on: List[str]) -> None:
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        
        self.tasks[name] = TaskNode(name, fn, depends_on)
        self.graph[name] = set(depends_on)
        
        for dep in depends_on:
            if dep not in self._reverse_graph:
                self._reverse_graph[dep] = set()
            self._reverse_graph[dep].add(name)

    def _build_reverse_graph(self) -> Dict[str, Set[str]]:
        reverse: Dict[str, Set[str]] = {}
        for task_name, deps in self.graph.items():
            for dep in deps:
                if dep not in reverse:
                    reverse[dep] = set()
                reverse[dep].add(task_name)
        return reverse

    def _compute_in_degrees(self) -> Dict[str, int]:
        in_degree: Dict[str, int] = {task: 0 for task in self.tasks}
        for task_name, deps in self.graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        return in_degree

    def validate(self) -> None:
        self._detect_cycles_dfs()

    def _detect_cycles_dfs(self) -> None:
        color: Dict[str, int] = {task: 0 for task in self.tasks}  # 0=white, 1=gray, 2=black
        path_stack: List[str] = []
        
        def dfs(node: str) -> bool:
            if color[node] == 1:
                # Found a cycle, reconstruct from path_stack
                cycle_start = path_stack.index(node)
                cycle = path_stack[cycle_start:] + [node]
                raise CycleError(cycle)
            
            if color[node] == 2:
                return False
            
            color[node] = 1
            path_stack.append(node)
            
            for neighbor in self._reverse_graph.get(node, set()):
                dfs(neighbor)
            
            path_stack.pop()
            color[node] = 2
            return False
        
        for node in self.tasks:
            if color[node] == 0:
                try:
                    dfs(node)
                except CycleError:
                    raise

    def topological_sort(self) -> List[str]:
        in_degree = self._compute_in_degrees()
        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        result: List[str] = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in self._reverse_graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) < len(self.tasks):
            # There's a cycle, try to find and report it
            remaining = set(self.tasks.keys()) - set(result)
            for node in remaining:
                color: Dict[str, int] = {task: 0 for task in remaining}
                stack: List[Tuple[str, List[str]]] = [(node, [node])]
                
                while stack:
                    curr, path = stack.pop()
                    color[curr] = 1
                    
                    for neighbor in self._reverse_graph.get(curr, set()):
                        if neighbor in remaining:
                            if color[neighbor] == 1:
                                # Found a cycle
                                cycle_start = path.index(neighbor)
                                cycle = path[cycle_start:] + [neighbor]
                                raise CycleError(cycle)
                            elif color[neighbor] == 0:
                                stack.append((neighbor, path + [neighbor]))
        
        return result

    def parallel_groups(self) -> List[List[str]]:
        in_degree = self._compute_in_degrees()
        groups: List[List[str]] = []
        
        while any(deg >= 0 for deg in in_degree.values()):
            # Find all nodes with in_degree == 0
            current_group = [node for node, deg in in_degree.items() if deg == 0]
            
            if not current_group:
                # Cycle detected
                remaining = [node for node, deg in in_degree.items() if deg > 0]
                if remaining:
                    # Try to find a cycle for better error reporting
                    for node in remaining:
                        color: Dict[str, int] = {task: 0 for task in remaining}
                        stack: List[Tuple[str, List[str]]] = [(node, [node])]
                        
                        while stack:
                            curr, path = stack.pop()
                            color[curr] = 1
                            
                            for neighbor in self._reverse_graph.get(curr, set()):
                                if neighbor in remaining:
                                    if color[neighbor] == 1:
                                        cycle_start = path.index(neighbor)
                                        cycle = path[cycle_start:] + [neighbor]
                                        raise CycleError(cycle)
                                    elif color[neighbor] == 0:
                                        stack.append((neighbor, path + [neighbor]))
            
            groups.append(current_group)
            
            # Remove current group nodes and update in_degrees
            for node in current_group:
                in_degree[node] = -1  # Mark as processed
                for neighbor in self._reverse_graph.get(node, set()):
                    if neighbor in in_degree and in_degree[neighbor] > 0:
                        in_degree[neighbor] -= 1
        
        return groups

    def execute(self, fail_fast: bool = True) -> Dict[str, Any]:
        self.validate()
        groups = self.parallel_groups()
        results: Dict[str, Any] = {}
        
        for group in groups:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(group)) as executor:
                future_to_task = {}
                for task_name in group:
                    task = self.tasks[task_name]
                    task.status = TaskStatus.RUNNING
                    future = executor.submit(task.fn)
                    future_to_task[future] = (task_name, task)
                
                for future in concurrent.futures.as_completed(future_to_task):
                    task_name, task = future_to_task[future]
                    try:
                        task.result = future.result()
                        task.status = TaskStatus.COMPLETED
                        results[task_name] = task.result
                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        if fail_fast:
                            raise e
                        else:
                            results[task_name] = e
        
        return results