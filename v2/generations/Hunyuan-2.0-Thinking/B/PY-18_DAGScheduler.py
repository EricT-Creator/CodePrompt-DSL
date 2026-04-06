from typing import Callable, List, Dict, Set
from collections import defaultdict, deque

class DAGScheduler:
    def __init__(self):
        self.tasks: Dict[str, Callable] = {}
        self.dependencies: Dict[str, List[str]] = defaultdict(list)
        self.dependents: Dict[str, List[str]] = defaultdict(list)
    
    def add_task(self, name: str, fn: Callable, depends_on: List[str] = []):
        self.tasks[name] = fn
        self.dependencies[name] = depends_on.copy()
        for dep in depends_on:
            self.dependents[dep].append(name)
    
    def _detect_cycle(self) -> bool:
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.dependents[node]:
                if dfs(neighbor):
                    return True
                    
            rec_stack.remove(node)
            return False
        
        for task in self.tasks:
            if dfs(task):
                return True
        return False
    
    def run(self) -> Dict[str, any]:
        if self._detect_cycle():
            raise ValueError("Cycle detected in task dependencies")
        
        in_degree: Dict[str, int] = {}
        for task in self.tasks:
            in_degree[task] = len(self.dependencies[task])
        
        queue = deque([task for task in self.tasks if in_degree[task] == 0])
        result = {}
        execution_order = []
        
        while queue:
            task = queue.popleft()
            execution_order.append(task)
            result[task] = self.tasks[task]()
            
            for dependent in self.dependents[task]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return {
            "results": result,
            "execution_order": execution_order
        }

if __name__ == "__main__":
    def task_a():
        return "Task A result"
    def task_b():
        return "Task B result"
    def task_c():
        return "Task C result"
    
    scheduler = DAGScheduler()
    scheduler.add_task("A", task_a)
    scheduler.add_task("B", task_b, ["A"])
    scheduler.add_task("C", task_c, ["A"])
    
    result = scheduler.run()
    print(result)