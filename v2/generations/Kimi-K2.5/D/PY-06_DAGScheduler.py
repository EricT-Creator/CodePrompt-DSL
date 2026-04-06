from typing import Dict, List, Set, Callable, Any
from collections import deque

class CycleError(Exception):
    pass

class DAGScheduler:
    def __init__(self):
        self.tasks: Dict[str, Callable[[], Any]] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}
    
    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        self.tasks[name] = func
        self.dependencies[name] = set()
        self.dependents[name] = set()
    
    def add_dependency(self, task: str, dependency: str) -> None:
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' does not exist")
        if dependency not in self.tasks:
            raise ValueError(f"Dependency '{dependency}' does not exist")
        if task == dependency:
            raise ValueError("Task cannot depend on itself")
        
        self.dependencies[task].add(dependency)
        self.dependents[dependency].add(task)
    
    def validate(self) -> None:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task in self.tasks:
            if task not in visited:
                if has_cycle(task):
                    raise CycleError("Cycle detected in task dependencies")
    
    def get_execution_order(self) -> List[str]:
        self.validate()
        
        in_degree: Dict[str, int] = {task: 0 for task in self.tasks}
        for task, deps in self.dependencies.items():
            in_degree[task] = len(deps)
        
        queue: deque = deque([task for task, degree in in_degree.items() if degree == 0])
        result: List[str] = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for dependent in self.dependents.get(current, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.tasks):
            raise CycleError("Cycle detected in task dependencies")
        
        return result
    
    def get_parallel_groups(self) -> List[List[str]]:
        self.validate()
        
        in_degree: Dict[str, int] = {task: 0 for task in self.tasks}
        for task, deps in self.dependencies.items():
            in_degree[task] = len(deps)
        
        groups: List[List[str]] = []
        remaining = set(self.tasks.keys())
        
        while remaining:
            current_group: List[str] = []
            for task in list(remaining):
                deps_satisfied = all(dep not in remaining for dep in self.dependencies[task])
                if deps_satisfied:
                    current_group.append(task)
            
            if not current_group:
                raise CycleError("Cycle detected in task dependencies")
            
            groups.append(current_group)
            for task in current_group:
                remaining.remove(task)
        
        return groups
    
    def execute(self) -> Dict[str, Any]:
        execution_order = self.get_execution_order()
        results: Dict[str, Any] = {}
        
        for task_name in execution_order:
            task_func = self.tasks[task_name]
            try:
                results[task_name] = task_func()
            except Exception as e:
                results[task_name] = e
                raise RuntimeError(f"Task '{task_name}' failed: {e}") from e
        
        return results


if __name__ == "__main__":
    scheduler = DAGScheduler()
    
    scheduler.add_task("A", lambda: print("Executing A") or "A_result")
    scheduler.add_task("B", lambda: print("Executing B") or "B_result")
    scheduler.add_task("C", lambda: print("Executing C") or "C_result")
    scheduler.add_task("D", lambda: print("Executing D") or "D_result")
    
    scheduler.add_dependency("C", "A")
    scheduler.add_dependency("C", "B")
    scheduler.add_dependency("D", "C")
    
    print("执行顺序:", scheduler.get_execution_order())
    print("并行组:", scheduler.get_parallel_groups())
    print("\n执行任务:")
    results = scheduler.execute()
    print("\n结果:", results)
