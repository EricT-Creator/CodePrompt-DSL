from typing import Dict, List, Set, Callable, Any, Optional
from collections import deque
from dataclasses import dataclass, field


class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


@dataclass
class Task:
    name: str
    func: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)


class DAGScheduler:
    """A DAG scheduler that manages task dependencies and execution order."""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._dependents: Dict[str, Set[str]] = {}
    
    def add_task(self, name: str, func: Callable[[], Any]) -> 'DAGScheduler':
        """Add a task to the scheduler."""
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already exists")
        
        self._tasks[name] = Task(name=name, func=func)
        self._dependencies[name] = set()
        self._dependents[name] = set()
        return self
    
    def add_dependency(self, task: str, depends_on: str) -> 'DAGScheduler':
        """Add a dependency: task depends on depends_on."""
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' does not exist")
        if depends_on not in self._tasks:
            raise ValueError(f"Dependency '{depends_on}' does not exist")
        if task == depends_on:
            raise ValueError(f"Task '{task}' cannot depend on itself")
        
        self._dependencies[task].add(depends_on)
        self._dependents[depends_on].add(task)
        self._tasks[task].dependencies.add(depends_on)
        return self
    
    def validate(self) -> None:
        """Validate the DAG for cycles. Raises CycleError if a cycle is detected."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task in self._tasks:
            if task not in visited:
                if has_cycle(task):
                    raise CycleError(f"Cycle detected in DAG starting from task '{task}'")
    
    def get_execution_order(self) -> List[str]:
        """Get the topological sort of tasks."""
        self.validate()
        
        in_degree = {task: len(deps) for task, deps in self._dependencies.items()}
        queue = deque([task for task, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for dependent in self._dependents.get(current, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self._tasks):
            raise CycleError("Cycle detected during topological sort")
        
        return result
    
    def get_parallel_groups(self) -> List[Set[str]]:
        """Get groups of tasks that can be executed in parallel."""
        self.validate()
        
        in_degree = {task: len(deps) for task, deps in self._dependencies.items()}
        remaining = set(self._tasks.keys())
        groups = []
        
        while remaining:
            group = {task for task in remaining if in_degree[task] == 0}
            if not group:
                raise CycleError("Cycle detected while computing parallel groups")
            
            groups.append(group)
            remaining -= group
            
            for task in group:
                for dependent in self._dependents.get(task, set()):
                    in_degree[dependent] -= 1
        
        return groups
    
    def execute(self) -> Dict[str, Any]:
        """Execute all tasks in topological order."""
        execution_order = self.get_execution_order()
        results = {}
        
        for task_name in execution_order:
            task = self._tasks[task_name]
            try:
                results[task_name] = task.func()
            except Exception as e:
                results[task_name] = e
                raise RuntimeError(f"Task '{task_name}' failed: {e}") from e
        
        return results
    
    def get_task(self, name: str) -> Optional[Task]:
        """Get a task by name."""
        return self._tasks.get(name)
    
    def list_tasks(self) -> List[str]:
        """List all task names."""
        return list(self._tasks.keys())
    
    def get_dependencies(self, task: str) -> Set[str]:
        """Get direct dependencies of a task."""
        return self._dependencies.get(task, set()).copy()


def main():
    """Example usage of DAGScheduler."""
    scheduler = DAGScheduler()
    
    results_store = {}
    
    def task_a():
        print("Executing task A")
        results_store['A'] = "Result A"
        return "A done"
    
    def task_b():
        print("Executing task B")
        results_store['B'] = "Result B"
        return "B done"
    
    def task_c():
        print("Executing task C (depends on A)")
        results_store['C'] = f"Result C using {results_store.get('A')}"
        return "C done"
    
    def task_d():
        print("Executing task D (depends on B)")
        results_store['D'] = f"Result D using {results_store.get('B')}"
        return "D done"
    
    def task_e():
        print("Executing task E (depends on C and D)")
        results_store['E'] = f"Result E using {results_store.get('C')} and {results_store.get('D')}"
        return "E done"
    
    scheduler.add_task("A", task_a)
    scheduler.add_task("B", task_b)
    scheduler.add_task("C", task_c)
    scheduler.add_task("D", task_d)
    scheduler.add_task("E", task_e)
    
    scheduler.add_dependency("C", "A")
    scheduler.add_dependency("D", "B")
    scheduler.add_dependency("E", "C")
    scheduler.add_dependency("E", "D")
    
    print("Validating DAG...")
    scheduler.validate()
    print("✓ DAG is valid (no cycles)")
    
    print("\nExecution order:")
    order = scheduler.get_execution_order()
    print(f"  {' -> '.join(order)}")
    
    print("\nParallel execution groups:")
    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups):
        print(f"  Group {i+1}: {group}")
    
    print("\nExecuting tasks...")
    results = scheduler.execute()
    print("\nExecution results:")
    for task, result in results.items():
        print(f"  {task}: {result}")
    
    print("\n" + "="*50)
    print("Testing cycle detection...")
    
    cycle_scheduler = DAGScheduler()
    cycle_scheduler.add_task("X", lambda: "X")
    cycle_scheduler.add_task("Y", lambda: "Y")
    cycle_scheduler.add_task("Z", lambda: "Z")
    cycle_scheduler.add_dependency("Y", "X")
    cycle_scheduler.add_dependency("Z", "Y")
    cycle_scheduler.add_dependency("X", "Z")
    
    try:
        cycle_scheduler.validate()
    except CycleError as e:
        print(f"✓ Cycle detected as expected: {e}")


if __name__ == "__main__":
    main()
