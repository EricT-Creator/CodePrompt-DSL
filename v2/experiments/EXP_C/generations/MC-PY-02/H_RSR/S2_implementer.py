"""
DAG Task Scheduler with Topological Sort and Cycle Detection

This module implements a directed acyclic graph (DAG) task scheduler
with Kahn's algorithm for topological sorting and integrated cycle detection.
"""

import time
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set, Optional, Tuple
import traceback

# ============================================================================
# Custom Exceptions
# ============================================================================

class CycleError(Exception):
    """Exception raised when a cycle is detected in the DAG."""
    
    def __init__(self, cycle_nodes: List[str]) -> None:
        self.cycle_nodes = cycle_nodes
        super().__init__(f"Cycle detected involving nodes: {', '.join(cycle_nodes)}")

class TaskError(Exception):
    """Exception raised when a task execution fails."""
    
    def __init__(self, task_name: str, error: str) -> None:
        self.task_name = task_name
        self.error = error
        super().__init__(f"Task '{task_name}' failed: {error}")

# ============================================================================
# Core Data Structures
# ============================================================================

@dataclass
class TaskNode:
    """Represents a single task in the DAG."""
    name: str
    callable: Callable[[], Any]
    dependencies: List[str] = field(default_factory=list)

@dataclass
class TaskResult:
    """Result of a task execution."""
    task_name: str
    status: str  # "success", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    traceback: Optional[str] = None

@dataclass
class ExecutionResult:
    """Result of a complete DAG execution."""
    success: bool
    task_results: Dict[str, TaskResult]
    execution_groups: List[List[str]]
    total_duration_seconds: float = 0.0
    
    def get_successful_tasks(self) -> List[str]:
        """Get names of successfully executed tasks."""
        return [
            task_name for task_name, result in self.task_results.items()
            if result.status == "success"
        ]
    
    def get_failed_tasks(self) -> List[str]:
        """Get names of failed tasks."""
        return [
            task_name for task_name, result in self.task_results.items()
            if result.status == "failed"
        ]

# ============================================================================
# DAG Class (Graph Representation)
# ============================================================================

class DAG:
    """Directed acyclic graph representation using adjacency list."""
    
    def __init__(self) -> None:
        # Node name -> TaskNode
        self._nodes: Dict[str, TaskNode] = {}
        
        # Adjacency list: node -> set of successors
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        
        # In-degree: node -> count of incoming edges
        self._in_degree: Dict[str, int] = defaultdict(int)
    
    def add_node(self, task: TaskNode) -> None:
        """Add a task node to the DAG."""
        if task.name in self._nodes:
            raise ValueError(f"Task '{task.name}' already exists")
        
        self._nodes[task.name] = task
        self._adjacency[task.name] = set()
        self._in_degree[task.name] = 0
    
    def add_edge(self, from_task: str, to_task: str) -> None:
        """Add a dependency edge: to_task depends on from_task."""
        if from_task not in self._nodes:
            raise ValueError(f"Source task '{from_task}' not found")
        if to_task not in self._nodes:
            raise ValueError(f"Target task '{to_task}' not found")
        
        # Avoid duplicate edges
        if to_task not in self._adjacency[from_task]:
            self._adjacency[from_task].add(to_task)
            self._in_degree[to_task] += 1
    
    def get_nodes(self) -> Dict[str, TaskNode]:
        """Get all nodes in the DAG."""
        return self._nodes.copy()
    
    def get_dependencies(self, task_name: str) -> Set[str]:
        """Get dependencies for a task (predecessors)."""
        return {
            pred for pred, succs in self._adjacency.items()
            if task_name in succs
        }
    
    def get_dependents(self, task_name: str) -> Set[str]:
        """Get dependents of a task (successors)."""
        return self._adjacency[task_name].copy()
    
    def has_cycle(self) -> bool:
        """Check if the DAG has a cycle using Kahn's algorithm."""
        # Make copies to avoid modifying original data
        in_degree = self._in_degree.copy()
        adjacency = {k: v.copy() for k, v in self._adjacency.items()}
        
        # Find nodes with no incoming edges
        queue = deque([node for node in self._nodes if in_degree[node] == 0])
        visited_count = 0
        
        while queue:
            node = queue.popleft()
            visited_count += 1
            
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return visited_count != len(self._nodes)
    
    def topological_sort_grouped(self) -> List[List[str]]:
        """
        Perform topological sort returning groups of tasks that can run in parallel.
        
        Returns groups of task names, where tasks in the same group have no
        dependencies on each other and can be executed concurrently.
        
        Raises CycleError if a cycle is detected.
        """
        # Make copies to avoid modifying original data
        in_degree = self._in_degree.copy()
        adjacency = {k: v.copy() for k, v in self._adjacency.items()}
        
        # Find initial nodes with no dependencies
        current_wave = [node for node in self._nodes if in_degree[node] == 0]
        groups: List[List[str]] = []
        
        while current_wave:
            # Add current wave as a parallel group
            groups.append(current_wave.copy())
            next_wave = []
            
            # Process all nodes in current wave
            for node in current_wave:
                for neighbor in adjacency[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_wave.append(neighbor)
            
            current_wave = next_wave
        
        # Check for cycles
        processed_count = sum(len(group) for group in groups)
        if processed_count != len(self._nodes):
            # Find nodes that are part of a cycle
            cycle_nodes = [node for node in self._nodes if in_degree[node] > 0]
            raise CycleError(cycle_nodes)
        
        return groups

# ============================================================================
# DAG Scheduler
# ============================================================================

class DAGScheduler:
    """Main scheduler class for executing DAG tasks."""
    
    def __init__(self, parallel: bool = False, max_workers: int = 4) -> None:
        """
        Initialize the DAG scheduler.
        
        Args:
            parallel: Whether to execute tasks within each group in parallel
            max_workers: Maximum number of threads for parallel execution
        """
        self.dag = DAG()
        self.parallel = parallel
        self.max_workers = max_workers if parallel else 1
        self._task_registry: Dict[str, TaskNode] = {}
    
    def add_task(self, name: str, task_func: Callable[[], Any], dependencies: Optional[List[str]] = None) -> None:
        """
        Add a task to the scheduler.
        
        Args:
            name: Unique name for the task
            task_func: Callable that executes the task
            dependencies: List of task names that must complete before this task
        """
        task = TaskNode(
            name=name,
            callable=task_func,
            dependencies=dependencies or []
        )
        
        self._task_registry[name] = task
        self.dag.add_node(task)
    
    def _build_dependencies(self) -> None:
        """Build dependency edges from task dependencies."""
        for task_name, task in self._task_registry.items():
            for dep_name in task.dependencies:
                if dep_name not in self._task_registry:
                    raise ValueError(f"Dependency '{dep_name}' not found for task '{task_name}'")
                self.dag.add_edge(dep_name, task_name)
    
    def validate(self) -> None:
        """Validate the DAG and check for cycles."""
        self._build_dependencies()
        
        if self.dag.has_cycle():
            # Get cycle nodes for error reporting
            try:
                groups = self.dag.topological_sort_grouped()
                return  # No cycle
            except CycleError as e:
                raise e
    
    def execute(self) -> ExecutionResult:
        """
        Execute all tasks in the DAG according to dependencies.
        
        Returns:
            ExecutionResult containing task results and execution metadata
        """
        start_time = time.time()
        
        # Build dependencies and validate DAG
        self._build_dependencies()
        
        # Get execution groups (parallelizable sets of tasks)
        try:
            groups = self.dag.topological_sort_grouped()
        except CycleError as e:
            # Re-raise with more context
            raise e
        
        # Initialize results dictionary
        task_results: Dict[str, TaskResult] = {}
        
        # Execute groups sequentially, tasks within groups can be parallel
        for group_idx, group in enumerate(groups):
            group_start_time = time.time()
            
            if self.parallel and len(group) > 1:
                # Execute tasks in parallel
                group_results = self._execute_group_parallel(group)
            else:
                # Execute tasks sequentially
                group_results = self._execute_group_sequential(group)
            
            # Update overall results
            task_results.update(group_results)
            
            # Check for failures - optionally stop execution
            failed_tasks = [
                task_name for task_name, result in group_results.items()
                if result.status == "failed"
            ]
            
            if failed_tasks and self._should_stop_on_failure():
                # Stop execution if any task failed
                break
        
        total_duration = time.time() - start_time
        
        # Determine overall success
        success = all(
            result.status == "success"
            for result in task_results.values()
        )
        
        return ExecutionResult(
            success=success,
            task_results=task_results,
            execution_groups=groups,
            total_duration_seconds=total_duration
        )
    
    def _execute_group_sequential(self, task_names: List[str]) -> Dict[str, TaskResult]:
        """Execute tasks in a group sequentially."""
        results: Dict[str, TaskResult] = {}
        
        for task_name in task_names:
            start_time = time.time()
            task = self._task_registry[task_name]
            
            try:
                # Execute task
                task_result = task.callable()
                duration = time.time() - start_time
                
                results[task_name] = TaskResult(
                    task_name=task_name,
                    status="success",
                    result=task_result,
                    duration_seconds=duration
                )
                
            except Exception as e:
                duration = time.time() - start_time
                tb = traceback.format_exc()
                
                results[task_name] = TaskResult(
                    task_name=task_name,
                    status="failed",
                    error=str(e),
                    duration_seconds=duration,
                    traceback=tb
                )
        
        return results
    
    def _execute_group_parallel(self, task_names: List[str]) -> Dict[str, TaskResult]:
        """Execute tasks in a group in parallel using ThreadPoolExecutor."""
        results: Dict[str, TaskResult] = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks to executor
            future_to_task = {
                executor.submit(self._execute_single_task, task_name): task_name
                for task_name in task_names
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task_name = future_to_task[future]
                try:
                    task_result = future.result()
                    results[task_name] = task_result
                except Exception as e:
                    # This shouldn't happen since _execute_single_task catches exceptions
                    results[task_name] = TaskResult(
                        task_name=task_name,
                        status="failed",
                        error=f"Unexpected error: {e}",
                        duration_seconds=0.0,
                        traceback=traceback.format_exc()
                    )
        
        return results
    
    def _execute_single_task(self, task_name: str) -> TaskResult:
        """Execute a single task and return its result."""
        start_time = time.time()
        task = self._task_registry[task_name]
        
        try:
            # Execute task
            task_result = task.callable()
            duration = time.time() - start_time
            
            return TaskResult(
                task_name=task_name,
                status="success",
                result=task_result,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            tb = traceback.format_exc()
            
            return TaskResult(
                task_name=task_name,
                status="failed",
                error=str(e),
                duration_seconds=duration,
                traceback=tb
            )
    
    def _should_stop_on_failure(self) -> bool:
        """Determine whether to stop execution when a task fails."""
        # Default behavior: continue despite failures
        # Override this method for different failure handling strategies
        return False
    
    def clear(self) -> None:
        """Clear all tasks and reset the scheduler."""
        self.dag = DAG()
        self._task_registry.clear()

# ============================================================================
# Example Tasks and Demonstration
# ============================================================================

def example_task_a() -> str:
    """Example task A."""
    time.sleep(0.1)  # Simulate work
    return "Task A completed"

def example_task_b() -> str:
    """Example task B."""
    time.sleep(0.2)  # Simulate work
    return "Task B completed"

def example_task_c() -> str:
    """Example task C (depends on A and B)."""
    time.sleep(0.3)  # Simulate work
    return "Task C completed"

def example_task_d() -> str:
    """Example task D (depends on A)."""
    time.sleep(0.15)  # Simulate work
    return "Task D completed"

def example_task_e() -> str:
    """Example task E (depends on C and D)."""
    time.sleep(0.25)  # Simulate work
    return "Task E completed"

def failing_task() -> str:
    """Example task that always fails."""
    time.sleep(0.05)
    raise ValueError("This task is designed to fail")

def demonstrate_scheduler() -> None:
    """Demonstrate the DAG scheduler with example tasks."""
    
    print("=== DAG Task Scheduler Demonstration ===\n")
    
    # Test 1: Basic DAG without cycles
    print("Test 1: Basic DAG execution")
    scheduler = DAGScheduler(parallel=False)
    
    scheduler.add_task("A", example_task_a)
    scheduler.add_task("B", example_task_b)
    scheduler.add_task("C", example_task_c, dependencies=["A", "B"])
    scheduler.add_task("D", example_task_d, dependencies=["A"])
    scheduler.add_task("E", example_task_e, dependencies=["C", "D"])
    
    try:
        scheduler.validate()
        print("  DAG validation: PASSED (no cycles)")
    except CycleError as e:
        print(f"  DAG validation: FAILED - {e}")
        return
    
    result = scheduler.execute()
    
    print(f"  Execution successful: {result.success}")
    print(f"  Total duration: {result.total_duration_seconds:.2f} seconds")
    print(f"  Execution groups: {result.execution_groups}")
    
    for task_name, task_result in result.task_results.items():
        status_symbol = "✓" if task_result.status == "success" else "✗"
        print(f"    {status_symbol} {task_name}: {task_result.status} ({task_result.duration_seconds:.2f}s)")
    
    print()
    
    # Test 2: Parallel execution
    print("Test 2: Parallel execution")
    parallel_scheduler = DAGScheduler(parallel=True, max_workers=3)
    
    parallel_scheduler.add_task("A", example_task_a)
    parallel_scheduler.add_task("B", example_task_b)
    parallel_scheduler.add_task("C", example_task_c, dependencies=["A", "B"])
    parallel_scheduler.add_task("D", example_task_d, dependencies=["A"])
    parallel_scheduler.add_task("E", example_task_e, dependencies=["C", "D"])
    
    parallel_result = parallel_scheduler.execute()
    
    print(f"  Parallel execution successful: {parallel_result.success}")
    print(f"  Parallel total duration: {parallel_result.total_duration_seconds:.2f} seconds")
    
    print()
    
    # Test 3: Cycle detection
    print("Test 3: Cycle detection")
    cycle_scheduler = DAGScheduler()
    
    cycle_scheduler.add_task("X", lambda: "X")
    cycle_scheduler.add_task("Y", lambda: "Y", dependencies=["X"])
    cycle_scheduler.add_task("Z", lambda: "Z", dependencies=["Y"])
    # Create a cycle: X -> Y -> Z -> X
    # This is done by adding X as a dependency of Z
    cycle_scheduler._task_registry["X"].dependencies.append("Z")
    
    try:
        cycle_scheduler.validate()
        print("  Cycle detection: FAILED (should have detected cycle)")
    except CycleError as e:
        print(f"  Cycle detection: PASSED - {e}")
    
    print()
    
    # Test 4: Task with failure
    print("Test 4: Task with failure")
    failure_scheduler = DAGScheduler()
    
    failure_scheduler.add_task("F1", example_task_a)
    failure_scheduler.add_task("F2", failing_task, dependencies=["F1"])
    failure_scheduler.add_task("F3", example_task_b, dependencies=["F2"])
    
    failure_result = failure_scheduler.execute()
    
    print(f"  Execution successful: {failure_result.success}")
    print(f"  Failed tasks: {failure_result.get_failed_tasks()}")
    
    for task_name in failure_result.get_failed_tasks():
        result = failure_result.task_results[task_name]
        print(f"    {task_name} error: {result.error}")

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    demonstrate_scheduler()