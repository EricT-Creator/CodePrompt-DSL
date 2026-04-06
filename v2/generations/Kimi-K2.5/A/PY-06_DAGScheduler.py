from typing import Dict, List, Set, Callable, Any
from collections import defaultdict, deque


class CycleError(Exception):
    """Raised when a circular dependency is detected."""
    pass


class DAGScheduler:
    def __init__(self):
        self.tasks: Dict[str, Callable] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)
        self.results: Dict[str, Any] = {}

    def add_task(self, name: str, func: Callable) -> None:
        """Register a task with a name and function."""
        self.tasks[name] = func

    def add_dependency(self, task: str, depends_on: str) -> None:
        """Declare that 'task' depends on 'depends_on'."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' not found. Add it first with add_task.")
        if depends_on not in self.tasks:
            raise ValueError(f"Dependency '{depends_on}' not found. Add it first with add_task.")
        
        self.dependencies[task].add(depends_on)
        self.dependents[depends_on].add(task)

    def validate(self) -> None:
        """Detect circular dependencies and raise CycleError if found."""
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in self.dependencies.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in recursion_stack:
                    cycle_start = path.index(neighbor) if neighbor in path else len(path)
                    cycle = path[cycle_start:] + [neighbor]
                    raise CycleError(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            recursion_stack.remove(node)
        
        for task in self.tasks:
            if task not in visited:
                dfs(task, [task])

    def get_execution_order(self) -> List[str]:
        """Return a topological sort of tasks."""
        self.validate()
        
        in_degree = {task: 0 for task in self.tasks}
        for task, deps in self.dependencies.items():
            in_degree[task] = len(deps)
        
        queue = deque([task for task, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            task = queue.popleft()
            result.append(task)
            
            for dependent in self.dependents.get(task, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.tasks):
            raise CycleError("Circular dependency detected during topological sort")
        
        return result

    def get_parallel_groups(self) -> List[Set[str]]:
        """Return list of sets where tasks in each set can run in parallel."""
        self.validate()
        
        in_degree = {task: 0 for task in self.tasks}
        for task, deps in self.dependencies.items():
            in_degree[task] = len(deps)
        
        groups = []
        remaining = set(self.tasks.keys())
        
        while remaining:
            current_group = set()
            for task in list(remaining):
                deps_satisfied = all(dep not in remaining for dep in self.dependencies.get(task, set()))
                if deps_satisfied:
                    current_group.add(task)
            
            if not current_group:
                raise CycleError("Unable to resolve dependencies")
            
            groups.append(current_group)
            remaining -= current_group
        
        return groups

    def execute(self) -> Dict[str, Any]:
        """Run all tasks respecting dependencies."""
        order = self.get_execution_order()
        self.results = {}
        
        for task_name in order:
            func = self.tasks[task_name]
            # Get results of dependencies as arguments
            dep_results = {
                dep: self.results[dep]
                for dep in self.dependencies.get(task_name, set())
            }
            
            try:
                if dep_results:
                    result = func(**dep_results)
                else:
                    result = func()
                self.results[task_name] = result
            except Exception as e:
                raise RuntimeError(f"Task '{task_name}' failed: {str(e)}")
        
        return self.results


if __name__ == "__main__":
    # Example usage
    scheduler = DAGScheduler()
    
    # Define tasks
    def task_a():
        print("Running task A")
        return "result_a"
    
    def task_b():
        print("Running task B")
        return "result_b"
    
    def task_c(result_a=None):
        print(f"Running task C with {result_a}")
        return f"result_c ({result_a})"
    
    def task_d(result_b=None, result_c=None):
        print(f"Running task D with {result_b}, {result_c}")
        return f"result_d ({result_b}, {result_c})"
    
    # Register tasks
    scheduler.add_task("A", task_a)
    scheduler.add_task("B", task_b)
    scheduler.add_task("C", task_c)
    scheduler.add_task("D", task_d)
    
    # Define dependencies: C depends on A, D depends on B and C
    scheduler.add_dependency("C", "A")
    scheduler.add_dependency("D", "B")
    scheduler.add_dependency("D", "C")
    
    # Validate
    try:
        scheduler.validate()
        print("✓ No circular dependencies")
    except CycleError as e:
        print(f"✗ {e}")
    
    # Get execution order
    order = scheduler.get_execution_order()
    print(f"Execution order: {order}")
    
    # Get parallel groups
    groups = scheduler.get_parallel_groups()
    print(f"Parallel groups: {[list(g) for g in groups]}")
    
    # Execute
    print("\nExecuting tasks:")
    results = scheduler.execute()
    print(f"\nResults: {results}")
    
    # Test cycle detection
    print("\n--- Testing Cycle Detection ---")
    scheduler2 = DAGScheduler()
    scheduler2.add_task("X", lambda: "x")
    scheduler2.add_task("Y", lambda: "y")
    scheduler2.add_task("Z", lambda: "z")
    scheduler2.add_dependency("X", "Y")
    scheduler2.add_dependency("Y", "Z")
    scheduler2.add_dependency("Z", "X")  # Creates cycle
    
    try:
        scheduler2.validate()
    except CycleError as e:
        print(f"✓ Correctly detected: {e}")
