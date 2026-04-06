from typing import Dict, List, Set, Callable, Any, Optional
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import time

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SchedulerError(Exception):
    """调度器基础异常"""
    pass

class CycleError(SchedulerError):
    """循环依赖异常"""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"发现循环依赖: {' -> '.join(cycle)}")

class TaskNotFoundError(SchedulerError):
    """任务不存在异常"""
    def __init__(self, task_name: str):
        super().__init__(f"任务不存在: {task_name}")

@dataclass
class Task:
    """任务定义"""
    name: str
    func: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class DAGScheduler:
    """DAG任务调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.tasks: Dict[str, Task] = {}
        self.execution_order: List[str] = []
        self.execution_log: List[Dict[str, Any]] = []
        self.visited: Set[str] = set()
        self.visiting: Set[str] = set()
        
    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        """
        注册任务
        
        Args:
            name: 任务名称
            func: 任务函数（无参数）
        
        Raises:
            ValueError: 如果任务已存在
        """
        if name in self.tasks:
            raise ValueError(f"任务已存在: {name}")
        
        self.tasks[name] = Task(
            name=name,
            func=func,
            dependencies=set(),
            dependents=set()
        )
    
    def add_dependency(self, task: str, dependency: str) -> None:
        """
        声明任务依赖关系
        
        Args:
            task: 任务名称
            dependency: 依赖的任务名称
        
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        if task not in self.tasks:
            raise TaskNotFoundError(task)
        
        if dependency not in self.tasks:
            raise TaskNotFoundError(dependency)
        
        # 添加依赖关系
        self.tasks[task].dependencies.add(dependency)
        self.tasks[dependency].dependents.add(task)
    
    def _detect_cycle_dfs(self, task_name: str, path: List[str]) -> None:
        """
        深度优先搜索检测循环依赖
        
        Args:
            task_name: 当前任务名称
            path: 当前路径
        
        Raises:
            CycleError: 如果发现循环依赖
        """
        if task_name in self.visiting:
            # 发现循环，构建循环路径
            cycle_start = path.index(task_name)
            cycle = path[cycle_start:] + [task_name]
            raise CycleError(cycle)
        
        if task_name in self.visited:
            return
        
        self.visiting.add(task_name)
        path.append(task_name)
        
        # 递归检查所有依赖
        for dep in self.tasks[task_name].dependencies:
            self._detect_cycle_dfs(dep, path)
        
        self.visiting.remove(task_name)
        path.pop()
        self.visited.add(task_name)
    
    def validate(self) -> None:
        """
        验证DAG，检测循环依赖
        
        Raises:
            CycleError: 如果发现循环依赖
        """
        self.visited.clear()
        self.visiting.clear()
        
        for task_name in self.tasks:
            if task_name not in self.visited:
                self._detect_cycle_dfs(task_name, [])
    
    def _topological_sort_kahn(self) -> List[str]:
        """
        Kahn算法进行拓扑排序
        
        Returns:
            List[str]: 拓扑排序结果
        """
        # 计算入度
        in_degree: Dict[str, int] = {name: 0 for name in self.tasks}
        
        for task in self.tasks.values():
            for dep in task.dependencies:
                in_degree[task.name] += 1
        
        # 初始化队列（入度为0的节点）
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            task_name = queue.popleft()
            result.append(task_name)
            
            # 减少依赖该任务的节点的入度
            for dependent in self.tasks[task_name].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # 检查是否所有节点都被处理
        if len(result) != len(self.tasks):
            # 有循环依赖，使用DFS找到循环
            self.validate()
        
        return result
    
    def get_execution_order(self) -> List[str]:
        """
        获取任务执行顺序（拓扑排序）
        
        Returns:
            List[str]: 任务执行顺序
        """
        self.validate()
        self.execution_order = self._topological_sort_kahn()
        return self.execution_order.copy()
    
    def get_parallel_groups(self) -> List[List[str]]:
        """
        获取可并行执行的任务组
        
        Returns:
            List[List[str]]: 每组任务可以并行执行
        """
        self.validate()
        
        # 使用Kahn算法变体计算并行组
        in_degree: Dict[str, int] = {name: 0 for name in self.tasks}
        
        for task in self.tasks.values():
            for dep in task.dependencies:
                in_degree[task.name] += 1
        
        parallel_groups = []
        
        while True:
            # 找到当前所有入度为0的节点
            current_group = [name for name, degree in in_degree.items() if degree == 0]
            
            if not current_group:
                break
            
            parallel_groups.append(sorted(current_group))
            
            # 处理当前组的节点
            for task_name in current_group:
                # 减少依赖该任务的节点的入度
                for dependent in self.tasks[task_name].dependents:
                    in_degree[dependent] -= 1
                
                # 标记为已处理
                in_degree[task_name] = -1
        
        return parallel_groups
    
    def _execute_task(self, task_name: str) -> Any:
        """
        执行单个任务
        
        Args:
            task_name: 任务名称
        
        Returns:
            Any: 任务执行结果
        """
        task = self.tasks[task_name]
        
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        try:
            result = task.func()
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            # 记录执行日志
            self.execution_log.append({
                "task": task_name,
                "status": "completed",
                "start_time": task.start_time,
                "end_time": task.end_time,
                "duration": task.end_time - task.start_time if task.end_time else None,
                "result": result
            })
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            
            # 记录错误日志
            self.execution_log.append({
                "task": task_name,
                "status": "failed",
                "start_time": task.start_time,
                "end_time": task.end_time,
                "duration": task.end_time - task.start_time if task.end_time else None,
                "error": str(e)
            })
            
            raise
            
        finally:
            task.end_time = time.time()
    
    def execute(self, parallel: bool = False, max_workers: int = 4) -> Dict[str, Any]:
        """
        执行所有任务
        
        Args:
            parallel: 是否并行执行
            max_workers: 最大并行工作数（如果parallel=True）
        
        Returns:
            Dict[str, Any]: 执行结果汇总
        """
        self.validate()
        
        # 获取执行顺序
        if not self.execution_order:
            self.execution_order = self.get_execution_order()
        
        # 重置任务状态
        for task in self.tasks.values():
            task.status = TaskStatus.PENDING
            task.result = None
            task.error = None
            task.start_time = None
            task.end_time = None
        
        self.execution_log.clear()
        start_time = time.time()
        
        if parallel:
            # 并行执行模式
            return self._execute_parallel(max_workers)
        else:
            # 顺序执行模式
            return self._execute_sequential()
    
    def _execute_sequential(self) -> Dict[str, Any]:
        """顺序执行所有任务"""
        results = {}
        failed_tasks = []
        
        for task_name in self.execution_order:
            try:
                result = self._execute_task(task_name)
                results[task_name] = result
            except Exception as e:
                failed_tasks.append({
                    "task": task_name,
                    "error": str(e)
                })
                
                # 如果任务失败，跳过依赖它的任务
                for dependent in list(self.tasks[task_name].dependents):
                    dependent_task = self.tasks[dependent]
                    dependent_task.status = TaskStatus.FAILED
                    dependent_task.error = Exception(f"依赖任务 {task_name} 失败")
        
        end_time = time.time()
        
        return {
            "total_tasks": len(self.tasks),
            "completed": len(results),
            "failed": len(failed_tasks),
            "total_duration": end_time - start_time,
            "results": results,
            "failed_tasks": failed_tasks,
            "execution_log": self.execution_log,
            "execution_order": self.execution_order
        }
    
    def _execute_parallel(self, max_workers: int) -> Dict[str, Any]:
        """并行执行所有任务"""
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor
        
        # 获取并行任务组
        parallel_groups = self.get_parallel_groups()
        results = {}
        failed_tasks = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for group in parallel_groups:
                # 为当前组的所有任务创建future
                future_to_task = {
                    executor.submit(self._execute_task, task_name): task_name
                    for task_name in group
                }
                
                # 等待当前组所有任务完成
                for future in concurrent.futures.as_completed(future_to_task):
                    task_name = future_to_task[future]
                    
                    try:
                        result = future.result()
                        results[task_name] = result
                    except Exception as e:
                        failed_tasks.append({
                            "task": task_name,
                            "error": str(e)
                        })
                        
                        # 标记依赖任务为失败
                        for dependent in list(self.tasks[task_name].dependents):
                            dependent_task = self.tasks[dependent]
                            dependent_task.status = TaskStatus.FAILED
                            dependent_task.error = Exception(f"依赖任务 {task_name} 失败")
        
        end_time = time.time()
        
        return {
            "total_tasks": len(self.tasks),
            "completed": len(results),
            "failed": len(failed_tasks),
            "total_duration": end_time - start_time,
            "parallel_groups": parallel_groups,
            "max_workers": max_workers,
            "results": results,
            "failed_tasks": failed_tasks,
            "execution_log": self.execution_log,
            "execution_order": self.execution_order
        }
    
    def get_task_status(self, task_name: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_name: 任务名称
        
        Returns:
            Dict[str, Any]: 任务状态信息
        
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        if task_name not in self.tasks:
            raise TaskNotFoundError(task_name)
        
        task = self.tasks[task_name]
        
        return {
            "name": task.name,
            "status": task.status.value,
            "dependencies": list(task.dependencies),
            "dependents": list(task.dependents),
            "result": task.result,
            "error": str(task.error) if task.error else None,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "duration": task.end_time - task.start_time if task.end_time and task.start_time else None
        }
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务状态
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有任务状态
        """
        return {
            task_name: self.get_task_status(task_name)
            for task_name in self.tasks
        }
    
    def visualize(self) -> str:
        """
        可视化DAG结构（简单文本格式）
        
        Returns:
            str: DAG的可视化表示
        """
        lines = []
        lines.append("DAG 结构:")
        lines.append("=" * 40)
        
        for task_name in self.get_execution_order():
            task = self.tasks[task_name]
            deps = ", ".join(sorted(task.dependencies)) if task.dependencies else "无"
            lines.append(f"{task_name}:")
            lines.append(f"  依赖: {deps}")
        
        lines.append("=" * 40)
        lines.append("并行执行组:")
        
        parallel_groups = self.get_parallel_groups()
        for i, group in enumerate(parallel_groups, 1):
            lines.append(f"  第{i}组: {', '.join(group)}")
        
        return "\n".join(lines)

# 示例用法
def example_task(name: str, duration: float = 0.1, should_fail: bool = False) -> Callable[[], str]:
    """创建示例任务"""
    def task():
        time.sleep(duration)
        if should_fail:
            raise ValueError(f"任务 {name} 故意失败")
        return f"任务 {name} 完成"
    return task

def main():
    """主函数：示例和测试"""
    
    # 创建调度器实例
    scheduler = DAGScheduler()
    
    # 添加任务
    tasks = [
        ("A", example_task("A", 0.2)),
        ("B", example_task("B", 0.1)),
        ("C", example_task("C", 0.3)),
        ("D", example_task("D", 0.1)),
        ("E", example_task("E", 0.2, should_fail=True)),
        ("F", example_task("F", 0.1)),
        ("G", example_task("G", 0.2)),
        ("H", example_task("H", 0.1)),
    ]
    
    for name, func in tasks:
        scheduler.add_task(name, func)
    
    # 添加依赖关系
    dependencies = [
        ("C", "A"),
        ("C", "B"),
        ("D", "C"),
        ("E", "C"),
        ("F", "D"),
        ("G", "D"),
        ("H", "F"),
        ("H", "G"),
    ]
    
    for task, dep in dependencies:
        scheduler.add_dependency(task, dep)
    
    print("DAG调度器示例")
    print("=" * 50)
    
    # 验证DAG
    try:
        scheduler.validate()
        print("✓ DAG验证通过，无循环依赖")
    except CycleError as e:
        print(f"✗ DAG验证失败: {e}")
        return
    
    # 获取执行顺序
    execution_order = scheduler.get_execution_order()
    print(f"\n任务执行顺序: {execution_order}")
    
    # 获取并行组
    parallel_groups = scheduler.get_parallel_groups()
    print(f"\n可并行执行组:")
    for i, group in enumerate(parallel_groups, 1):
        print(f"  第{i}组: {group}")
    
    # 可视化DAG
    print(f"\n{scheduler.visualize()}")
    
    # 顺序执行
    print("\n顺序执行测试:")
    print("-" * 30)
    
    seq_result = scheduler.execute(parallel=False)
    print(f"总耗时: {seq_result['total_duration']:.2f}秒")
    print(f"完成: {seq_result['completed']}, 失败: {seq_result['failed']}")
    
    if seq_result['failed_tasks']:
        print("失败任务:")
        for failed in seq_result['failed_tasks']:
            print(f"  - {failed['task']}: {failed['error']}")
    
    # 并行执行（如果系统支持）
    try:
        print("\n\n并行执行测试 (4线程):")
        print("-" * 30)
        
        par_result = scheduler.execute(parallel=True, max_workers=4)
        print(f"总耗时: {par_result['total_duration']:.2f}秒")
        print(f"完成: {par_result['completed']}, 失败: {par_result['failed']}")
        print(f"并行加速比: {seq_result['total_duration'] / par_result['total_duration']:.2f}x")
        
    except Exception as e:
        print(f"并行执行失败: {e}")
    
    # 显示任务状态
    print("\n\n最终任务状态:")
    print("-" * 30)
    
    all_status = scheduler.get_all_status()
    for task_name, status in all_status.items():
        print(f"{task_name}: {status['status']}")
        if status['duration']:
            print(f"  耗时: {status['duration']:.2f}秒")
        if status['result']:
            print(f"  结果: {status['result']}")
        if status['error']:
            print(f"  错误: {status['error']}")

# 测试循环依赖检测
def test_cycle_detection():
    """测试循环依赖检测"""
    print("\n\n循环依赖检测测试:")
    print("=" * 50)
    
    scheduler = DAGScheduler()
    
    # 添加任务
    scheduler.add_task("A", lambda: "A")
    scheduler.add_task("B", lambda: "B")
    scheduler.add_task("C", lambda: "C")
    
    # 创建循环依赖: A -> B -> C -> A
    scheduler.add_dependency("B", "A")
    scheduler.add_dependency("C", "B")
    
    try:
        # 此时应该没有循环
        scheduler.validate()
        print("✓ 无循环依赖时验证通过")
    except CycleError:
        print("✗ 错误：不应该检测到循环依赖")
    
    # 添加循环依赖
    scheduler.add_dependency("A", "C")  # 创建循环
    
    try:
        scheduler.validate()
        print("✗ 错误：应该检测到循环依赖")
    except CycleError as e:
        print(f"✓ 正确检测到循环依赖: {e}")

if __name__ == "__main__":
    main()
    test_cycle_detection()