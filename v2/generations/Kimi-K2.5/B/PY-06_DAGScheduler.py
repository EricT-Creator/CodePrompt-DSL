from typing import Dict, List, Set, Callable, Any, Optional
from collections import deque


class CycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class Task:
    """Represents a task in the DAG."""
    
    def __init__(self, name: str, func: Callable[[], Any]):
        self.name = name
        self.func = func
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()
    
    def __repr__(self):
        return f"Task({self.name})"


class DAGScheduler:
    """
    DAG scheduler with topological sort and parallel execution grouping.
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._execution_order: Optional[List[str]] = None
        self._parallel_groups: Optional[List[Set[str]]] = None
    
    def add_task(self, name: str, func: Callable[[], Any]) -> 'DAGScheduler':
        """
        Add a task to the scheduler.
        
        Args:
            name: Unique task name
            func: Function to execute
        
        Returns:
            Self for method chaining
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        
        self.tasks[name] = Task(name, func)
        # Invalidate cached results
        self._execution_order = None
        self._parallel_groups = None
        return self
    
    def add_dependency(self, task: str, depends_on: str) -> 'DAGScheduler':
        """
        Add a dependency between two tasks.
        
        Args:
            task: The task that depends on another
            depends_on: The task that must complete first
        
        Returns:
            Self for method chaining
        """
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' does not exist")
        if depends_on not in self.tasks:
            raise ValueError(f"Task '{depends_on}' does not exist")
        
        self.tasks[task].dependencies.add(depends_on)
        self.tasks[depends_on].dependents.add(task)
        # Invalidate cached results
        self._execution_order = None
        self._parallel_groups = None
        return self
    
    def validate(self) -> None:
        """
        Validate the DAG for cycles.
        
        Raises:
            CycleError: If a cycle is detected
        """
        # Use DFS to detect cycles
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in self.tasks}
        path = []
        
        def dfs(node: str) -> bool:
            color[node] = GRAY
            path.append(node)
            
            for neighbor in self.tasks[node].dependencies:
                if color[neighbor] == GRAY:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    raise CycleError(f"Cycle detected: {' -> '.join(cycle)}")
                if color[neighbor] == WHITE:
                    if dfs(neighbor):
                        return True
            
            path.pop()
            color[node] = BLACK
            return False
        
        for name in self.tasks:
            if color[name] == WHITE:
                dfs(name)
    
    def get_execution_order(self) -> List[str]:
        """
        Get the topological sort execution order.
        
        Returns:
            List of task names in execution order
        
        Raises:
            CycleError: If a cycle is detected
        """
        if self._execution_order is not None:
            return self._execution_order
        
        self.validate()
        
        # Kahn's algorithm for topological sort
        in_degree = {name: len(self.tasks[name].dependencies) for name in self.tasks}
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for dependent in self.tasks[node].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.tasks):
            raise CycleError("Cycle detected in DAG")
        
        self._execution_order = result
        return result
    
    def get_parallel_groups(self) -> List[Set[str]]:
        """
        Get groups of tasks that can be executed in parallel.
        
        Returns:
            List of sets, where each set contains tasks that can run in parallel
        """
        if self._parallel_groups is not None:
            return self._parallel_groups
        
        execution_order = self.get_execution_order()
        
        # Calculate levels for each task
        levels: Dict[str, int] = {}
        for task_name in execution_order:
            if not self.tasks[task_name].dependencies:
                levels[task_name] = 0
            else:
                levels[task_name] = max(
                    levels[dep] + 1
                    for dep in self.tasks[task_name].dependencies
                )
        
        # Group by level
        max_level = max(levels.values()) if levels else -1
        groups = []
        for level in range(max_level + 1):
            group = {name for name, lvl in levels.items() if lvl == level}
            if group:
                groups.append(group)
        
        self._parallel_groups = groups
        return groups
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute all tasks in dependency order.
        
        Returns:
            Dict mapping task names to their results
        """
        execution_order = self.get_execution_order()
        results: Dict[str, Any] = {}
        
        for task_name in execution_order:
            task = self.tasks[task_name]
            try:
                results[task_name] = task.func()
            except Exception as e:
                results[task_name] = e
                raise RuntimeError(f"Task '{task_name}' failed: {e}") from e
        
        return results
    
    def execute_parallel_groups(self) -> Dict[str, Any]:
        """
        Execute tasks by parallel groups.
        
        Returns:
            Dict mapping task names to their results
        """
        from concurrent.futures import ThreadPoolExecutor
        
        parallel_groups = self.get_parallel_groups()
        results: Dict[str, Any] = {}
        
        for group in parallel_groups:
            # Execute tasks in current group in parallel
            with ThreadPoolExecutor(max_workers=len(group)) as executor:
                futures = {
                    executor.submit(self.tasks[name].func): name
                    for name in group
                }
                
                for future in futures:
                    name = futures[future]
                    try:
                        results[name] = future.result()
                    except Exception as e:
                        results[name] = e
                        raise RuntimeError(f"Task '{name}' failed: {e}") from e
        
        return results
    
    def get_task_info(self) -> Dict[str, Dict]:
        """Get information about all tasks."""
        return {
            name: {
                "dependencies": list(task.dependencies),
                "dependents": list(task.dependents)
            }
            for name, task in self.tasks.items()
        }


def main():
    """Example usage of DAGScheduler."""
    
    # Create scheduler
    scheduler = DAGScheduler()
    
    # Add tasks
    scheduler.add_task("fetch_data", lambda: print("Fetching data...") or "data")
    scheduler.add_task("process_a", lambda: print("Processing A...") or "result_a")
    scheduler.add_task("process_b", lambda: print("Processing B...") or "result_b")
    scheduler.add_task("combine", lambda: print("Combining results...") or "combined")
    scheduler.add_task("save", lambda: print("Saving...") or "saved")
    
    # Add dependencies
    scheduler.add_dependency("process_a", "fetch_data")
    scheduler.add_dependency("process_b", "fetch_data")
    scheduler.add_dependency("combine", "process_a")
    scheduler.add_dependency("combine", "process_b")
    scheduler.add_dependency("save", "combine")
    
    # Validate
    print("Validating DAG...")
    scheduler.validate()
    print("✓ No cycles detected")
    
    # Get execution order
    print("\nExecution order:")
    order = scheduler.get_execution_order()
    for i, task in enumerate(order, 1):
        print(f"  {i}. {task}")
    
    # Get parallel groups
    print("\nParallel execution groups:")
    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups, 1):
        print(f"  Group {i}: {', '.join(group)}")
    
    # Execute
    print("\nExecuting tasks...")
    results = scheduler.execute()
    print("\nResults:")
    for task, result in results.items():
        print(f"  {task}: {result}")


if __name__ == "__main__":
    main()
