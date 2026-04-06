from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import time

# Custom exceptions
class CycleError(Exception):
    """Raised when a circular dependency is detected in the DAG."""
    pass

class TaskError(Exception):
    """Raised when a task execution fails."""
    pass

# Data classes
@dataclass
class Task:
    name: str
    func: Callable
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    result: Any = None
    error: Optional[Exception] = None
    executed: bool = False
    
    def __repr__(self):
        return f"Task(name='{self.name}', deps={sorted(self.dependencies)}, executed={self.executed})"

@dataclass
class ExecutionResult:
    task_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

class DAGScheduler:
    """
    Directed Acyclic Graph (DAG) task scheduler.
    
    This class implements a DAG scheduler that can:
    1. Add tasks with dependencies
    2. Detect circular dependencies
    3. Provide topological execution order
    4. Identify parallel execution groups
    5. Execute tasks respecting dependencies
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._validated = False
        self._execution_order: List[str] = []
        self._parallel_groups: List[Set[str]] = []
    
    def add_task(self, name: str, func: Callable) -> None:
        """
        Add a task to the scheduler.
        
        Args:
            name: Unique name for the task
            func: Callable to execute for this task
            
        Raises:
            ValueError: If task name already exists
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
        
        self.tasks[name] = Task(name=name, func=func)
        self._validated = False
    
    def add_dependency(self, task_name: str, depends_on: str) -> None:
        """
        Add a dependency between tasks.
        
        Args:
            task_name: Name of the task that depends on another
            depends_on: Name of the task that must execute first
            
        Raises:
            KeyError: If either task doesn't exist
        """
        if task_name not in self.tasks:
            raise KeyError(f"Task '{task_name}' not found")
        if depends_on not in self.tasks:
            raise KeyError(f"Task '{depends_on}' not found")
        
        task = self.tasks[task_name]
        dependency = self.tasks[depends_on]
        
        task.dependencies.add(depends_on)
        dependency.dependents.add(task_name)
        
        self._validated = False
    
    def validate(self) -> None:
        """
        Validate the DAG and detect circular dependencies.
        
        Raises:
            CycleError: If a circular dependency is detected
        """
        # Reset validation state
        self._validated = False
        
        # Use Kahn's algorithm to detect cycles
        # Calculate indegree for each task
        indegree: Dict[str, int] = {name: 0 for name in self.tasks}
        for task in self.tasks.values():
            indegree[task.name] = len(task.dependencies)
        
        # Find tasks with no dependencies
        queue = deque([name for name, degree in indegree.items() if degree == 0])
        topological_order = []
        
        while queue:
            current = queue.popleft()
            topological_order.append(current)
            
            # Reduce indegree of dependents
            for dependent in self.tasks[current].dependents:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for cycles
        if len(topological_order) != len(self.tasks):
            # Find the cycle
            cycle = self._find_cycle()
            raise CycleError(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        self._execution_order = topological_order
        self._compute_parallel_groups()
        self._validated = True
    
    def _find_cycle(self) -> List[str]:
        """Find a cycle in the graph using DFS."""
        visited = set()
        path = []
        cycle = []
        
        def dfs(node: str) -> bool:
            nonlocal cycle
            
            if node in visited:
                return False
            
            visited.add(node)
            path.append(node)
            
            for dependent in self.tasks[node].dependents:
                if dependent in path:
                    # Found a cycle
                    start_idx = path.index(dependent)
                    cycle = path[start_idx:] + [dependent]
                    return True
                if dfs(dependent):
                    return True
            
            path.pop()
            return False
        
        for task_name in self.tasks:
            if dfs(task_name):
                break
        
        return cycle if cycle else ["unknown cycle"]
    
    def _compute_parallel_groups(self) -> None:
        """Compute groups of tasks that can run in parallel."""
        if not self._execution_order:
            return
        
        # Create a mapping of task -> level (longest path to that task)
        levels: Dict[str, int] = {}
        
        for task_name in self._execution_order:
            task = self.tasks[task_name]
            if not task.dependencies:
                levels[task_name] = 0
            else:
                levels[task_name] = max(levels[dep] for dep in task.dependencies) + 1
        
        # Group tasks by level
        max_level = max(levels.values()) if levels else 0
        parallel_groups = []
        
        for level in range(max_level + 1):
            group = {name for name, lvl in levels.items() if lvl == level}
            if group:
                parallel_groups.append(group)
        
        self._parallel_groups = parallel_groups
    
    def get_execution_order(self) -> List[str]:
        """
        Get the topological execution order.
        
        Returns:
            List of task names in execution order
            
        Raises:
            CycleError: If the graph has cycles (call validate() first)
        """
        if not self._validated:
            self.validate()
        
        return self._execution_order.copy()
    
    def get_parallel_groups(self) -> List[Set[str]]:
        """
        Get groups of tasks that can run in parallel.
        
        Returns:
            List of sets, where each set contains tasks that can run in parallel
            
        Raises:
            CycleError: If the graph has cycles (call validate() first)
        """
        if not self._validated:
            self.validate()
        
        return [group.copy() for group in self._parallel_groups]
    
    def execute(self, max_workers: Optional[int] = None) -> Dict[str, ExecutionResult]:
        """
        Execute all tasks respecting dependencies.
        
        Args:
            max_workers: Maximum number of parallel tasks (None for sequential)
            
        Returns:
            Dictionary mapping task names to execution results
            
        Raises:
            CycleError: If the graph has cycles
        """
        if not self._validated:
            self.validate()
        
        # Reset task states
        for task in self.tasks.values():
            task.executed = False
            task.result = None
            task.error = None
        
        results: Dict[str, ExecutionResult] = {}
        
        if max_workers is None or max_workers <= 1:
            # Sequential execution
            return self._execute_sequential(results)
        else:
            # Parallel execution
            return self._execute_parallel(results, max_workers)
    
    def _execute_sequential(self, results: Dict[str, ExecutionResult]) -> Dict[str, ExecutionResult]:
        """Execute tasks sequentially."""
        execution_order = self.get_execution_order()
        
        for task_name in execution_order:
            result = self._execute_task(task_name)
            results[task_name] = result
            
            # If task failed, we can still try to execute independent tasks
            # but mark this task's dependents as failed
            if not result.success:
                self._mark_dependents_failed(task_name, results)
        
        return results
    
    def _execute_parallel(self, results: Dict[str, ExecutionResult], max_workers: int) -> Dict[str, ExecutionResult]:
        """Execute tasks in parallel using simple thread pool simulation."""
        import threading
        from queue import Queue
        
        execution_order = self.get_execution_order()
        parallel_groups = self.get_parallel_groups()
        
        # Create a queue for tasks ready to execute
        ready_queue = Queue()
        
        # Track task states
        task_states = {
            name: {
                'completed': False,
                'failed': False,
                'dependencies': set(self.tasks[name].dependencies),
                'dependents': set(self.tasks[name].dependents)
            }
            for name in self.tasks
        }
        
        # Worker function
        def worker():
            while True:
                try:
                    task_name = ready_queue.get(timeout=0.1)
                except:
                    break
                
                if task_states[task_name]['failed']:
                    ready_queue.task_done()
                    continue
                
                result = self._execute_task(task_name)
                results[task_name] = result
                
                # Update task state
                task_states[task_name]['completed'] = True
                task_states[task_name]['failed'] = not result.success
                
                # Mark dependents of failed tasks as failed
                if not result.success:
                    for dependent in task_states[task_name]['dependents']:
                        task_states[dependent]['failed'] = True
                
                # Check which dependents are now ready
                for dependent in task_states[task_name]['dependents']:
                    task_states[dependent]['dependencies'].discard(task_name)
                    if not task_states[dependent]['dependencies'] and not task_states[dependent]['failed']:
                        ready_queue.put(dependent)
                
                ready_queue.task_done()
        
        # Start with tasks that have no dependencies
        for task_name in execution_order:
            if not self.tasks[task_name].dependencies:
                ready_queue.put(task_name)
        
        # Start worker threads
        threads = []
        for _ in range(min(max_workers, len(self.tasks))):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        # Wait for all tasks to complete
        ready_queue.join()
        
        # Stop workers
        for thread in threads:
            thread.join()
        
        return results
    
    def _execute_task(self, task_name: str) -> ExecutionResult:
        """Execute a single task."""
        task = self.tasks[task_name]
        start_time = time.time()
        
        try:
            # Check if all dependencies succeeded
            for dep_name in task.dependencies:
                dep_task = self.tasks[dep_name]
                if dep_task.error is not None:
                    raise TaskError(f"Dependency '{dep_name}' failed: {dep_task.error}")
            
            # Execute the task
            result = task.func()
            
            end_time = time.time()
            
            # Update task
            task.executed = True
            task.result = result
            task.error = None
            
            return ExecutionResult(
                task_name=task_name,
                success=True,
                result=result,
                duration_seconds=end_time - start_time,
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            end_time = time.time()
            
            # Update task
            task.executed = True
            task.error = e
            
            return ExecutionResult(
                task_name=task_name,
                success=False,
                error=str(e),
                duration_seconds=end_time - start_time,
                start_time=start_time,
                end_time=end_time
            )
    
    def _mark_dependents_failed(self, failed_task: str, results: Dict[str, ExecutionResult]) -> None:
        """Mark all dependents of a failed task as failed."""
        visited = set()
        stack = [failed_task]
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            
            visited.add(current)
            
            for dependent in self.tasks[current].dependents:
                if dependent not in results:
                    # Create a failed result for this dependent
                    results[dependent] = ExecutionResult(
                        task_name=dependent,
                        success=False,
                        error=f"Skipped due to failed dependency: {current}"
                    )
                
                stack.append(dependent)
    
    def visualize(self) -> str:
        """
        Create a simple text visualization of the DAG.
        
        Returns:
            String representation of the DAG
        """
        lines = []
        lines.append("=" * 60)
        lines.append("DAG SCHEDULER VISUALIZATION")
        lines.append("=" * 60)
        lines.append(f"Total tasks: {len(self.tasks)}")
        lines.append("")
        
        # Show tasks
        lines.append("TASKS:")
        for task_name in sorted(self.tasks.keys()):
            task = self.tasks[task_name]
            deps = sorted(task.dependencies)
            lines.append(f"  {task_name}")
            if deps:
                lines.append(f"    depends on: {', '.join(deps)}")
            lines.append("")
        
        # Show execution order if validated
        if self._validated:
            lines.append("EXECUTION ORDER:")
            lines.append("  " + " -> ".join(self._execution_order))
            lines.append("")
            
            lines.append("PARALLEL EXECUTION GROUPS:")
            for i, group in enumerate(self._parallel_groups):
                lines.append(f"  Group {i + 1}: {', '.join(sorted(group))}")
        
        lines.append("=" * 60)
        return "\n".join(lines)

# Example usage and testing
def example_task(name: str, duration: float = 0.1, fail: bool = False):
    """Example task function for testing."""
    def task():
        time.sleep(duration)
        if fail:
            raise ValueError(f"Task '{name}' intentionally failed")
        return f"Result of {name}"
    return task

def main():
    """Example usage of the DAGScheduler."""
    print("DAG Scheduler Example")
    print("=" * 60)
    
    # Create scheduler
    scheduler = DAGScheduler()
    
    # Add tasks
    tasks = [
        ("A", example_task("A", 0.2)),
        ("B", example_task("B", 0.1)),
        ("C", example_task("C", 0.3)),
        ("D", example_task("D", 0.1)),
        ("E", example_task("E", 0.2)),
        ("F", example_task("F", 0.1, fail=True)),  # This task will fail
        ("G", example_task("G", 0.1)),
    ]
    
    for name, func in tasks:
        scheduler.add_task(name, func)
    
    # Add dependencies
    dependencies = [
        ("C", "A"),  # C depends on A
        ("C", "B"),  # C depends on B
        ("D", "C"),  # D depends on C
        ("E", "C"),  # E depends on C
        ("F", "D"),  # F depends on D
        ("G", "E"),  # G depends on E
    ]
    
    for task, depends_on in dependencies:
        scheduler.add_dependency(task, depends_on)
    
    # Visualize the DAG
    print(scheduler.visualize())
    
    # Validate and get execution order
    try:
        scheduler.validate()
        print("✓ DAG is valid (no cycles)")
        
        execution_order = scheduler.get_execution_order()
        print(f"Execution order: {execution_order}")
        
        parallel_groups = scheduler.get_parallel_groups()
        print("Parallel groups:")
        for i, group in enumerate(parallel_groups):
            print(f"  Group {i + 1}: {group}")
        
    except CycleError as e:
        print(f"✗ {e}")
        return
    
    # Execute tasks sequentially
    print("\n" + "=" * 60)
    print("SEQUENTIAL EXECUTION")
    print("=" * 60)
    
    start_time = time.time()
    results = scheduler.execute(max_workers=1)
    total_time = time.time() - start_time
    
    print(f"Total execution time: {total_time:.2f}s")
    print("\nResults:")
    
    success_count = 0
    for task_name, result in results.items():
        status = "✓" if result.success else "✗"
        print(f"  {status} {task_name}: {result.duration_seconds:.2f}s")
        if not result.success:
            print(f"     Error: {result.error}")
        success_count += 1 if result.success else 0
    
    print(f"\nSuccess rate: {success_count}/{len(tasks)}")
    
    # Execute tasks in parallel
    print("\n" + "=" * 60)
    print("PARALLEL EXECUTION (max 2 workers)")
    print("=" * 60)
    
    # Reset scheduler
    scheduler = DAGScheduler()
    for name, func in tasks:
        scheduler.add_task(name, func)
    for task, depends_on in dependencies:
        scheduler.add_dependency(task, depends_on)
    
    start_time = time.time()
    results = scheduler.execute(max_workers=2)
    total_time = time.time() - start_time
    
    print(f"Total execution time: {total_time:.2f}s")
    print("\nResults:")
    
    success_count = 0
    for task_name, result in results.items():
        status = "✓" if result.success else "✗"
        print(f"  {status} {task_name}: {result.duration_seconds:.2f}s")
        if not result.success:
            print(f"     Error: {result.error}")
        success_count += 1 if result.success else 0
    
    print(f"\nSuccess rate: {success_count}/{len(tasks)}")
    
    # Test cycle detection
    print("\n" + "=" * 60)
    print("CYCLE DETECTION TEST")
    print("=" * 60)
    
    cyclic_scheduler = DAGScheduler()
    cyclic_scheduler.add_task("X", example_task("X"))
    cyclic_scheduler.add_task("Y", example_task("Y"))
    cyclic_scheduler.add_task("Z", example_task("Z"))
    
    # Create a cycle: X -> Y -> Z -> X
    cyclic_scheduler.add_dependency("Y", "X")
    cyclic_scheduler.add_dependency("Z", "Y")
    
    try:
        cyclic_scheduler.add_dependency("X", "Z")  # This creates a cycle
        cyclic_scheduler.validate()
        print("✗ Cycle not detected (unexpected)")
    except CycleError as e:
        print(f"✓ Cycle correctly detected: {e}")

if __name__ == "__main__":
    main()