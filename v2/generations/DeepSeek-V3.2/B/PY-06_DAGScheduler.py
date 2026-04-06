from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field


class CycleError(Exception):
    """Exception raised when a cycle is detected in the DAG"""
    pass


@dataclass
class Task:
    """Represents a task in the DAG"""
    name: str
    func: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)


class DAGScheduler:
    """
    Directed Acyclic Graph (DAG) scheduler for task execution.
    
    Supports:
    - Adding tasks with dependencies
    - Validating DAG for cycles
    - Topological sorting for execution order
    - Finding parallel execution groups
    - Executing tasks in correct order
    """
    
    def __init__(self):
        """Initialize an empty DAG scheduler"""
        self.tasks: Dict[str, Task] = {}
        self.graph: Dict[str, Set[str]] = defaultdict(set)  # task -> dependents
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # task -> dependencies
    
    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        """
        Add a task to the DAG.
        
        Args:
            name: Unique identifier for the task
            func: Callable function to execute for this task
        
        Raises:
            ValueError: If task with same name already exists
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        
        self.tasks[name] = Task(name=name, func=func)
        self.graph[name] = set()  # Initialize empty dependents set
        self.reverse_graph[name] = set()  # Initialize empty dependencies set
    
    def add_dependency(self, task_name: str, depends_on: str) -> None:
        """
        Add a dependency between tasks.
        
        Args:
            task_name: Name of the dependent task
            depends_on: Name of the task that must complete first
        
        Raises:
            ValueError: If either task doesn't exist
        """
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")
        if depends_on not in self.tasks:
            raise ValueError(f"Task '{depends_on}' not found")
        
        # Add dependency
        self.tasks[task_name].dependencies.add(depends_on)
        self.graph[depends_on].add(task_name)  # depends_on -> task_name (edge direction)
        self.reverse_graph[task_name].add(depends_on)  # task_name -> depends_on (reverse)
    
    def _has_cycle_dfs(self, node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
        """
        Depth-first search to detect cycles.
        
        Returns:
            True if cycle detected, False otherwise
        """
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in self.graph[node]:
            if neighbor not in visited:
                if self._has_cycle_dfs(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    def validate(self) -> None:
        """
        Validate the DAG for cycles.
        
        Raises:
            CycleError: If a cycle is detected in the DAG
        """
        visited = set()
        rec_stack = set()
        
        for node in self.tasks:
            if node not in visited:
                if self._has_cycle_dfs(node, visited, rec_stack):
                    raise CycleError(f"Cycle detected in DAG involving task '{node}'")
    
    def _kahn_topological_sort(self) -> List[str]:
        """
        Perform Kahn's algorithm for topological sorting.
        
        Returns:
            List of task names in topological order
        """
        # Calculate in-degree for each node
        in_degree: Dict[str, int] = {}
        for task in self.tasks:
            in_degree[task] = len(self.reverse_graph[task])
        
        # Queue of nodes with no dependencies
        queue = deque([node for node in self.tasks if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # Remove this node's outgoing edges
            for dependent in self.graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check if we processed all nodes (should be true for DAG)
        if len(result) != len(self.tasks):
            raise CycleError("Graph has at least one cycle")
        
        return result
    
    def get_execution_order(self) -> List[str]:
        """
        Get topological execution order for tasks.
        
        Returns:
            List of task names in execution order
        
        Raises:
            CycleError: If a cycle is detected
        """
        self.validate()  # Ensure no cycles
        return self._kahn_topological_sort()
    
    def get_parallel_groups(self) -> List[Set[str]]:
        """
        Find groups of tasks that can be executed in parallel.
        
        Returns:
            List of sets, where each set contains tasks that can run in parallel
        
        Raises:
            CycleError: If a cycle is detected
        """
        self.validate()  # Ensure no cycles
        
        # Get topological order
        topological_order = self.get_execution_order()
        
        # Calculate levels (longest path from any source)
        level: Dict[str, int] = {}
        for node in topological_order:
            if self.reverse_graph[node]:  # Has dependencies
                # Level = max level of dependencies + 1
                level[node] = max(level[dep] for dep in self.reverse_graph[node]) + 1
            else:
                # No dependencies = level 0
                level[node] = 0
        
        # Group nodes by level
        groups_dict: Dict[int, Set[str]] = defaultdict(set)
        for node, lvl in level.items():
            groups_dict[lvl].add(node)
        
        # Convert to list of sets in level order
        parallel_groups = [groups_dict[lvl] for lvl in sorted(groups_dict.keys())]
        
        return parallel_groups
    
    def execute(self, max_workers: int = 1) -> Dict[str, Any]:
        """
        Execute all tasks in the correct order.
        
        Args:
            max_workers: Maximum number of parallel tasks (1 for sequential)
        
        Returns:
            Dictionary mapping task names to their results
        
        Raises:
            CycleError: If a cycle is detected
            Exception: If any task execution fails
        """
        import concurrent.futures
        import threading
        
        self.validate()  # Ensure no cycles
        
        # Get parallel groups
        parallel_groups = self.get_parallel_groups()
        results: Dict[str, Any] = {}
        results_lock = threading.Lock()
        
        for group in parallel_groups:
            if max_workers == 1 or len(group) == 1:
                # Sequential execution
                for task_name in sorted(group):
                    try:
                        result = self.tasks[task_name].func()
                        results[task_name] = result
                        print(f"✓ Executed task: {task_name}")
                    except Exception as e:
                        raise Exception(f"Task '{task_name}' failed: {str(e)}")
            else:
                # Parallel execution with ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(group))) as executor:
                    # Submit all tasks in this group
                    future_to_task = {
                        executor.submit(self.tasks[task_name].func): task_name
                        for task_name in group
                    }
                    
                    # Collect results as they complete
                    for future in concurrent.futures.as_completed(future_to_task):
                        task_name = future_to_task[future]
                        
                        try:
                            result = future.result()
                            with results_lock:
                                results[task_name] = result
                            print(f"✓ Executed task: {task_name}")
                        except Exception as e:
                            raise Exception(f"Task '{task_name}' failed: {str(e)}")
        
        return results
    
    def get_task_info(self, task_name: str) -> Dict[str, Any]:
        """
        Get information about a specific task.
        
        Args:
            task_name: Name of the task
        
        Returns:
            Dictionary with task information
        """
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")
        
        task = self.tasks[task_name]
        
        return {
            'name': task.name,
            'dependencies': sorted(task.dependencies),
            'dependents': sorted(self.graph[task_name]),
            'dependency_count': len(task.dependencies),
            'dependent_count': len(self.graph[task_name]),
        }
    
    def visualize(self) -> str:
        """
        Generate a simple text visualization of the DAG.
        
        Returns:
            String representation of the DAG
        """
        lines = []
        lines.append("DAG Visualization:")
        lines.append("=" * 40)
        
        # Get topological order
        try:
            order = self.get_execution_order()
            lines.append(f"Topological Order: {', '.join(order)}")
        except CycleError:
            lines.append("Topological Order: (Cycle detected!)")
        
        lines.append("")
        
        # List tasks with dependencies
        for task_name in sorted(self.tasks.keys()):
            task_info = self.get_task_info(task_name)
            lines.append(f"Task: {task_name}")
            
            if task_info['dependencies']:
                lines.append(f"  Depends on: {', '.join(task_info['dependencies'])}")
            else:
                lines.append("  No dependencies")
            
            if task_info['dependents']:
                lines.append(f"  Required by: {', '.join(task_info['dependents'])}")
            
            lines.append("")
        
        # Show parallel groups
        try:
            groups = self.get_parallel_groups()
            lines.append("Parallel Execution Groups:")
            for i, group in enumerate(groups):
                lines.append(f"  Group {i}: {', '.join(sorted(group))}")
        except CycleError:
            lines.append("Parallel Execution Groups: (Cycle detected!)")
        
        return "\n".join(lines)


# Example usage and testing
def example_task(name: str, duration: float = 0.1) -> Callable[[], str]:
    """Create example task functions"""
    def task():
        import time
        time.sleep(duration)
        return f"Result of {name}"
    return task


def main():
    """Example usage of DAGScheduler"""
    
    # Create scheduler
    scheduler = DAGScheduler()
    
    # Add tasks
    scheduler.add_task("A", example_task("A"))
    scheduler.add_task("B", example_task("B"))
    scheduler.add_task("C", example_task("C"))
    scheduler.add_task("D", example_task("D"))
    scheduler.add_task("E", example_task("E"))
    scheduler.add_task("F", example_task("F"))
    
    # Add dependencies
    scheduler.add_dependency("B", "A")  # B depends on A
    scheduler.add_dependency("C", "A")  # C depends on A
    scheduler.add_dependency("D", "B")  # D depends on B
    scheduler.add_dependency("D", "C")  # D depends on C
    scheduler.add_dependency("E", "C")  # E depends on C
    scheduler.add_dependency("F", "D")  # F depends on D
    scheduler.add_dependency("F", "E")  # F depends on E
    
    print("=== DAG Scheduler Example ===")
    print()
    
    # Validate DAG
    try:
        scheduler.validate()
        print("✓ DAG is valid (no cycles)")
    except CycleError as e:
        print(f"✗ {e}")
        return
    
    # Get execution order
    print("\n1. Execution Order:")
    order = scheduler.get_execution_order()
    for i, task in enumerate(order, 1):
        print(f"   {i}. {task}")
    
    # Get parallel groups
    print("\n2. Parallel Execution Groups:")
    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups, 1):
        print(f"   Group {i}: {', '.join(sorted(group))}")
    
    # Get task info
    print("\n3. Task Information:")
    for task_name in ["A", "D", "F"]:
        info = scheduler.get_task_info(task_name)
        print(f"   {task_name}: {info}")
    
    # Visualize DAG
    print("\n4. DAG Visualization:")
    print(scheduler.visualize())
    
    # Execute tasks
    print("\n5. Executing tasks (sequential):")
    results = scheduler.execute(max_workers=1)
    print(f"   Results: {results}")
    
    print("\n6. Executing tasks (parallel, max 2 workers):")
    results = scheduler.execute(max_workers=2)
    print(f"   Results: {results}")
    
    # Test cycle detection
    print("\n7. Testing cycle detection:")
    scheduler_with_cycle = DAGScheduler()
    scheduler_with_cycle.add_task("X", example_task("X"))
    scheduler_with_cycle.add_task("Y", example_task("Y"))
    scheduler_with_cycle.add_task("Z", example_task("Z"))
    
    # Create cycle: X -> Y -> Z -> X
    scheduler_with_cycle.add_dependency("Y", "X")
    scheduler_with_cycle.add_dependency("Z", "Y")
    scheduler_with_cycle.add_dependency("X", "Z")  # This creates a cycle!
    
    try:
        scheduler_with_cycle.validate()
        print("   (Should not reach here)")
    except CycleError as e:
        print(f"   ✓ Correctly detected cycle: {e}")


if __name__ == "__main__":
    main()