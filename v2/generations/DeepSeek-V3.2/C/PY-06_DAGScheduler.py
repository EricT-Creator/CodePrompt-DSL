#!/usr/bin/env python3
"""
DAG（有向无环图）调度器 - 使用标准库实现
支持任务依赖、拓扑排序、并行执行组和任务执行
"""

from __future__ import annotations
import sys
import time
import threading
from typing import Dict, List, Set, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import inspect


# 枚举和异常
class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    READY = "ready"  # 依赖已完成
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class DAGError(Exception):
    """DAG基础异常"""
    pass


class CycleError(DAGError):
    """循环依赖错误"""
    pass


class TaskNotFoundError(DAGError):
    """任务未找到错误"""
    pass


# 数据类
@dataclass
class Task:
    """任务定义"""
    name: str
    func: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    
    # 状态字段
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保任务名是字符串
        if not isinstance(self.name, str):
            raise TypeError(f"任务名必须是字符串，实际类型: {type(self.name)}")
        
        # 验证函数
        if not callable(self.func):
            raise TypeError(f"任务函数必须可调用: {self.name}")
    
    @property
    def duration(self) -> Optional[float]:
        """任务持续时间（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "result": str(self.result) if self.result is not None else None,
            "error": str(self.error) if self.error else None,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents)
        }
    
    def execute(self) -> Any:
        """执行任务"""
        self.status = TaskStatus.RUNNING
        self.start_time = time.time()
        
        try:
            self.result = self.func()
            self.status = TaskStatus.SUCCESS
        except Exception as e:
            self.error = e
            self.status = TaskStatus.FAILED
            raise
        finally:
            self.end_time = time.time()
        
        return self.result


class DAGScheduler:
    """
    DAG调度器
    
    支持功能：
    - 添加任务和依赖
    - 检测循环依赖
    - 拓扑排序
    - 获取并行执行组
    - 执行任务（顺序或并行）
    """
    
    def __init__(self, name: str = "DAG调度器"):
        """
        初始化DAG调度器
        
        Args:
            name: DAG名称
        """
        self.name = name
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()
        self.execution_history: List[Dict[str, Any]] = []
        
        # 执行统计
        self.stats = {
            "total_tasks": 0,
            "executed_tasks": 0,
            "failed_tasks": 0,
            "successful_tasks": 0,
            "skipped_tasks": 0,
            "total_execution_time": 0.0,
            "start_time": None,
            "end_time": None
        }
    
    def add_task(self, name: str, func: Callable[[], Any]) -> None:
        """
        添加任务
        
        Args:
            name: 任务名称
            func: 任务函数（无参数）
        
        Raises:
            DAGError: 如果任务已存在
        """
        with self._lock:
            if name in self.tasks:
                raise DAGError(f"任务已存在: {name}")
            
            task = Task(name=name, func=func)
            self.tasks[name] = task
    
    def add_dependency(self, task_name: str, depends_on: str) -> None:
        """
        添加任务依赖
        
        Args:
            task_name: 依赖的任务
            depends_on: 被依赖的任务
        
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            if task_name not in self.tasks:
                raise TaskNotFoundError(f"任务未找到: {task_name}")
            if depends_on not in self.tasks:
                raise TaskNotFoundError(f"任务未找到: {depends_on}")
            
            # 添加依赖
            self.tasks[task_name].dependencies.add(depends_on)
            self.tasks[depends_on].dependents.add(task_name)
    
    def remove_task(self, name: str) -> None:
        """
        移除任务
        
        Args:
            name: 任务名称
        
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            if name not in self.tasks:
                raise TaskNotFoundError(f"任务未找到: {name}")
            
            task = self.tasks[name]
            
            # 从依赖任务中移除
            for dep_task_name in task.dependencies:
                self.tasks[dep_task_name].dependents.discard(name)
            
            # 从被依赖任务中移除
            for dep_task_name in task.dependents:
                self.tasks[dep_task_name].dependencies.discard(name)
            
            # 移除任务
            del self.tasks[name]
    
    def validate(self) -> None:
        """
        验证DAG，检测循环依赖
        
        Raises:
            CycleError: 如果检测到循环依赖
        """
        with self._lock:
            if not self.tasks:
                return
            
            # 使用DFS检测循环
            visited = set()
            recursion_stack = set()
            
            def dfs(task_name: str) -> None:
                if task_name in recursion_stack:
                    # 检测到循环
                    cycle = list(recursion_stack)
                    cycle.append(task_name)
                    raise CycleError(f"检测到循环依赖: {' -> '.join(cycle)}")
                
                if task_name in visited:
                    return
                
                visited.add(task_name)
                recursion_stack.add(task_name)
                
                for neighbor in self.tasks[task_name].dependents:
                    dfs(neighbor)
                
                recursion_stack.remove(task_name)
            
            # 对所有未访问的任务执行DFS
            for task_name in self.tasks:
                if task_name not in visited:
                    dfs(task_name)
    
    def get_execution_order(self) -> List[str]:
        """
        获取任务执行顺序（拓扑排序）
        
        Returns:
            List[str]: 按执行顺序排列的任务名列表
        
        Raises:
            CycleError: 如果检测到循环依赖
        """
        with self._lock:
            if not self.tasks:
                return []
            
            # 验证DAG
            self.validate()
            
            # Kahn算法进行拓扑排序
            in_degree: Dict[str, int] = {}
            for task_name, task in self.tasks.items():
                in_degree[task_name] = len(task.dependencies)
            
            # 入度为0的任务队列
            queue = deque([task_name for task_name, degree in in_degree.items() if degree == 0])
            result: List[str] = []
            
            while queue:
                task_name = queue.popleft()
                result.append(task_name)
                
                for dependent in self.tasks[task_name].dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            # 检查是否所有任务都被处理
            if len(result) != len(self.tasks):
                raise CycleError("DAG包含循环依赖，无法进行拓扑排序")
            
            return result
    
    def get_parallel_groups(self) -> List[List[str]]:
        """
        获取可以并行执行的任务组
        
        返回一个列表，每个元素是一组可以并行执行的任务名
        
        Returns:
            List[List[str]]: 并行任务组的列表
        """
        with self._lock:
            if not self.tasks:
                return []
            
            # 获取拓扑排序
            topological_order = self.get_execution_order()
            
            # 计算每个任务的最早开始时间
            earliest_start: Dict[str, int] = {}
            for task_name in topological_order:
                task = self.tasks[task_name]
                if not task.dependencies:
                    earliest_start[task_name] = 0
                else:
                    earliest_start[task_name] = max(
                        earliest_start[dep] + 1 
                        for dep in task.dependencies
                    )
            
            # 按照最早开始时间分组
            groups: Dict[int, List[str]] = defaultdict(list)
            for task_name in topological_order:
                groups[earliest_start[task_name]].append(task_name)
            
            # 转换为列表
            return [groups[level] for level in sorted(groups)]
    
    def _reset_task_statuses(self) -> None:
        """重置所有任务状态"""
        with self._lock:
            for task in self.tasks.values():
                task.status = TaskStatus.PENDING
                task.result = None
                task.error = None
                task.start_time = None
                task.end_time = None
    
    def _update_stats(self, start_time: float, end_time: float) -> None:
        """更新执行统计"""
        with self._lock:
            total_tasks = len(self.tasks)
            executed = sum(1 for t in self.tasks.values() if t.status != TaskStatus.PENDING)
            failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            success = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SUCCESS)
            skipped = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SKIPPED)
            
            total_time = sum(
                t.duration or 0 
                for t in self.tasks.values() 
                if t.start_time and t.end_time
            )
            
            self.stats = {
                "total_tasks": total_tasks,
                "executed_tasks": executed,
                "failed_tasks": failed,
                "successful_tasks": success,
                "skipped_tasks": skipped,
                "total_execution_time": total_time,
                "start_time": start_time,
                "end_time": end_time
            }
    
    def execute_sequential(self) -> Dict[str, Any]:
        """
        顺序执行任务
        
        Returns:
            Dict[str, Any]: 执行结果汇总
        
        Raises:
            CycleError: 如果检测到循环依赖
        """
        start_time = time.time()
        
        with self._lock:
            # 重置状态
            self._reset_task_statuses()
            
            # 获取执行顺序
            execution_order = self.get_execution_order()
            
            if not execution_order:
                return {
                    "success": True,
                    "message": "没有任务需要执行",
                    "total_tasks": 0,
                    "executed_tasks": 0
                }
            
            # 记录执行开始
            execution_id = f"exec_{int(start_time)}_{len(self.execution_history)}"
            execution_record = {
                "id": execution_id,
                "start_time": start_time,
                "order": execution_order,
                "tasks": {},
                "status": "running"
            }
            
            # 顺序执行
            results = {}
            successful_tasks = []
            failed_tasks = []
            
            for task_name in execution_order:
                task = self.tasks[task_name]
                
                try:
                    # 检查依赖是否成功
                    all_deps_success = True
                    for dep_name in task.dependencies:
                        dep_task = self.tasks[dep_name]
                        if dep_task.status != TaskStatus.SUCCESS:
                            all_deps_success = False
                            break
                    
                    if not all_deps_success:
                        task.status = TaskStatus.SKIPPED
                        execution_record["tasks"][task_name] = task.to_dict()
                        continue
                    
                    # 执行任务
                    result = task.execute()
                    results[task_name] = result
                    successful_tasks.append(task_name)
                    
                except Exception as e:
                    task.error = e
                    failed_tasks.append((task_name, str(e)))
                
                execution_record["tasks"][task_name] = task.to_dict()
            
            end_time = time.time()
            
            # 更新统计
            self._update_stats(start_time, end_time)
            
            # 完成执行记录
            execution_record["end_time"] = end_time
            execution_record["duration"] = end_time - start_time
            execution_record["results"] = results
            execution_record["successful_tasks"] = successful_tasks
            execution_record["failed_tasks"] = failed_tasks
            execution_record["status"] = "completed" if not failed_tasks else "failed"
            
            self.execution_history.append(execution_record)
            
            return {
                "success": not bool(failed_tasks),
                "total_tasks": len(execution_order),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "results": results,
                "execution_time": end_time - start_time,
                "execution_id": execution_id
            }
    
    def execute_parallel(self, max_workers: int = 4) -> Dict[str, Any]:
        """
        并行执行任务（使用线程池）
        
        Args:
            max_workers: 最大工作线程数
        
        Returns:
            Dict[str, Any]: 执行结果汇总
        
        Raises:
            CycleError: 如果检测到循环依赖
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        start_time = time.time()
        
        with self._lock:
            # 重置状态
            self._reset_task_statuses()
            
            # 获取任务组
            parallel_groups = self.get_parallel_groups()
            
            if not parallel_groups:
                return {
                    "success": True,
                    "message": "没有任务需要执行",
                    "total_tasks": 0,
                    "executed_tasks": 0
                }
            
            # 记录执行开始
            execution_id = f"exec_{int(start_time)}_{len(self.execution_history)}"
            execution_record = {
                "id": execution_id,
                "start_time": start_time,
                "parallel_groups": parallel_groups,
                "tasks": {},
                "status": "running"
            }
            
            # 并行执行
            results = {}
            successful_tasks = []
            failed_tasks = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {}
                
                for group in parallel_groups:
                    # 提交组内所有任务
                    for task_name in group:
                        task = self.tasks[task_name]
                        
                        # 检查依赖是否成功
                        all_deps_success = True
                        for dep_name in task.dependencies:
                            dep_task = self.tasks[dep_name]
                            if dep_task.status != TaskStatus.SUCCESS:
                                all_deps_success = False
                                break
                        
                        if not all_deps_success:
                            task.status = TaskStatus.SKIPPED
                            execution_record["tasks"][task_name] = task.to_dict()
                            continue
                        
                        # 提交任务执行
                        task.status = TaskStatus.RUNNING
                        task.start_time = time.time()
                        
                        future = executor.submit(task.execute)
                        
                        future_to_task[future] = (task_name, task)
                    
                    # 等待组内所有任务完成
                    for future in as_completed(future_to_task):
                        task_name, task = future_to_task[future]
                        
                        try:
                            result = future.result()
                            results[task_name] = result
                            successful_tasks.append(task_name)
                        except Exception as e:
                            task.error = e
                            task.status = TaskStatus.FAILED
                            failed_tasks.append((task_name, str(e)))
                        
                        task.end_time = time.time()
                        
                        execution_record["tasks"][task_name] = task.to_dict()
                    
                    future_to_task.clear()
            
            end_time = time.time()
            
            # 更新统计
            self._update_stats(start_time, end_time)
            
            # 完成执行记录
            execution_record["end_time"] = end_time
            execution_record["duration"] = end_time - start_time
            execution_record["results"] = results
            execution_record["successful_tasks"] = successful_tasks
            execution_record["failed_tasks"] = failed_tasks

            execution_record["status"] = "completed" if not failed_tasks else "failed"
            
            self.execution_history.append(execution_record)
            
            return {
                "success": not bool(failed_tasks),
                "total_tasks": sum(len(group) for group in parallel_groups),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "results": results,
                "execution_time": end_time - start_time,
                "execution_id": execution_id
            }
    
    def execute(self, parallel: bool = False, max_workers: int = 4) -> Dict[str, Any]:
        """
        执行任务（通用接口）
        
        Args:
            parallel: 是否并行执行
            max_workers: 并行执行时的工作线程数
        
        Returns:
            Dict[str, Any]: 执行结果汇总
        """
        if parallel:
            return self.execute_parallel(max_workers=max_workers)
        else:
            return self.execute_sequential()
    
    def get_task_status(self, task_name: str) -> Optional[TaskStatus]:
        """
        获取任务状态
        
        Args:
            task_name: 任务名称
        
        Returns:
            Optional[TaskStatus]: 任务状态，如果任务不存在则返回None
        """
        with self._lock:
            task = self.tasks.get(task_name)
            return task.status if task else None
    
    def get_task_result(self, task_name: str) -> Optional[Any]:
        """
        获取任务结果
        
        Args:
            task_name: 任务名称
        
        Returns:
            Optional[Any]: 任务结果，如果任务不存在或未执行则返回None
        """
        with self._lock:
            task = self.tasks.get(task_name)
            return task.result if task else None
    
    def get_task_dependencies(self, task_name: str) -> List[str]:
        """
        获取任务依赖
        
        Args:
            task_name: 任务名称
        
        Returns:
            List[str]: 任务依赖列表
        
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            if task_name not in self.tasks:
                raise TaskNotFoundError(f"任务未找到: {task_name}")
            
            return list(self.tasks[task_name].dependencies)
    
    def get_task_dependents(self, task_name: str) -> List[str]:
        """
        获取依赖该任务的任务
        
        Args:
            task_name: 任务名称
        
        Returns:
            List[str]: 依赖该任务的任务列表
        
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            if task_name not in self.tasks:
                raise TaskNotFoundError(f"任务未找到: {task_name}")
            
            return list(self.tasks[task_name].dependents)
    
    def visualize(self) -> str:
        """
        可视化DAG结构
        
        Returns:
            str: 文本形式的DAG可视化
        """
        with self._lock:
            if not self.tasks:
                return "DAG为空"
            
            lines = []
            lines.append(f"{self.name}")
            lines.append("=" * 60)
            
            # 任务列表
            lines.append("任务列表:")
            for task_name, task in sorted(self.tasks.items()):
                lines.append(f"  [{task.status.value.upper():7}] {task_name}")
            
            lines.append("")
            
            # 依赖关系
            lines.append("依赖关系:")
            for task_name, task in sorted(self.tasks.items()):
                if task.dependencies:
                    deps_str = ", ".join(sorted(task.dependencies))
                    lines.append(f"  {task_name} <- {deps_str}")
            
            lines.append("")
            
            # 执行顺序
            try:
                order = self.get_execution_order()
                lines.append(f"执行顺序 ({len(order)} 个任务):")
                lines.append("  " + " -> ".join(order))
            except CycleError as e:
                lines.append(f"执行顺序: 循环依赖错误 - {e}")
            
            lines.append("")
            
            # 并行组
            try:
                groups = self.get_parallel_groups()
                lines.append(f"并行执行组 ({len(groups)} 个层级):")
                for i, group in enumerate(groups, 1):
                    group_str = ", ".join(sorted(group))
                    lines.append(f"  层级 {i}: {{{group_str}}}")
            except CycleError as e:
                lines.append(f"并行执行组: 循环依赖错误 - {e}")
            
            lines.append("=" * 60)
            
            return "\n".join(lines)
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            return self.stats.copy()
    
    def clear(self) -> None:
        """清除所有任务和历史记录"""
        with self._lock:
            self.tasks.clear()
            self.execution_history.clear()
            self.stats = {
                "total_tasks": 0,
                "executed_tasks": 0,
                "failed_tasks": 0,
                "successful_tasks": 0,
                "skipped_tasks": 0,
                "total_execution_time": 0.0,
                "start_time": None,
                "end_time": None
            }


# 使用示例和测试
def example_usage():
    """使用示例"""
    
    # 创建任务函数
    def task_1():
        print("执行任务1")
        time.sleep(0.5)
        return "任务1结果"
    
    def task_2():
        print("执行任务2")
        time.sleep(0.3)
        return "任务2结果"
    
    def task_3():
        print("执行任务3")
        time.sleep(0.7)
        return "任务3结果"
    
    def task_4():
        print("执行任务4")
        time.sleep(0.2)
        return "任务4结果"
    
    def task_5():
        print("执行任务5")
        time.sleep(0.4)
        return "任务5结果"
    
    # 创建DAG调度器
    dag = DAGScheduler(name="示例DAG")
    
    # 添加任务
    dag.add_task("task_1", task_1)
    dag.add_task("task_2", task_2)
    dag.add_task("task_3", task_3)
    dag.add_task("task_4", task_4)
    dag.add_task("task_5", task_5)
    
    # 添加依赖关系
    # task_3 依赖 task_1 和 task_2
    dag.add_dependency("task_3", "task_1")
    dag.add_dependency("task_3", "task_2")
    
    # task_4 依赖 task_3
    dag.add_dependency("task_4", "task_3")
    
    # task_5 依赖 task_2
    dag.add_dependency("task_5", "task_2")
    
    print("=" * 60)
    print("DAG结构可视化:")
    print("=" * 60)
    print(dag.visualize())
    
    print("\n" + "=" * 60)
    print("顺序执行:")
    print("=" * 60)
    sequential_result = dag.execute_sequential()
    print(f"执行结果: {sequential_result['success']}")
    print(f"成功任务: {len(sequential_result['successful_tasks'])}")
    print(f"失败任务: {len(sequential_result['failed_tasks'])}")
    print(f"执行时间: {sequential_result['execution_time']:.2f}秒")
    
    print("\n" + "=" * 60)
    print("并行执行 (2个工作线程):")
    print("=" * 60)
    parallel_result = dag.execute_parallel(max_workers=2)
    print(f"执行结果: {parallel_result['success']}")
    print(f"成功任务: {len(parallel_result['successful_tasks'])}")
    print(f"失败任务: {len(parallel_result['failed_tasks'])}")
    print(f"执行时间: {parallel_result['execution_time']:.2f}秒")
    
    print("\n" + "=" * 60)
    print("统计信息:")
    print("=" * 60)
    stats = dag.get_stats_summary()
    for key, value in stats.items():
        if value is not None:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试循环依赖检测:")
    print("=" * 60)
    
    # 创建一个有循环依赖的DAG
    dag_cycle = DAGScheduler(name="循环DAG测试")
    
    dag_cycle.add_task("A", lambda: None)
    dag_cycle.add_task("B", lambda: None)
    dag_cycle.add_task("C", lambda: None)
    
    # 添加依赖: A -> B -> C -> A (循环)
    dag_cycle.add_dependency("B", "A")
    dag_cycle.add_dependency("C", "B")
    
    try:
        # 尝试添加循环依赖
        dag_cycle.add_dependency("A", "C")
        print("添加依赖成功 (不应该发生)")
    except Exception as e:
        print(f"添加依赖时捕获异常: {type(e).__name__}: {e}")
    
    try:
        # 验证应该检测到循环
        dag_cycle.validate()
        print("验证通过 (不应该发生)")
    except CycleError as e:
        print(f"成功检测到循环依赖: {e}")
    except Exception as e:
        print(f"验证时捕获异常: {type(e).__name__}: {e}")


# 命令行接口
def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DAG调度器 - 有向无环图任务调度工具"
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="运行使用示例"
    )
    parser.add_argument(
        "--test-cycle",
        action="store_true",
        help="测试循环依赖检测"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="可视化示例DAG结构"
    )
    
    args = parser.parse_args()
    
    if args.example:
        example_usage()
    elif args.test_cycle:
        # 测试循环依赖检测
        dag = DAGScheduler(name="循环依赖测试")
        
        dag.add_task("A", lambda: None)
        dag.add_task("B", lambda: None)
        dag.add_task("C", lambda: None)
        
        dag.add_dependency("B", "A")
        dag.add_dependency("C", "B")
        dag.add_dependency("A", "C")  # 这应该创建循环
        
        try:
            dag.validate()
            print("错误: 应该检测到循环依赖!")
        except CycleError as e:
            print(f"成功检测到循环依赖: {e}")
    elif args.visualize:
        # 可视化示例DAG
        dag = DAGScheduler(name="可视化示例")
        
        def create_task_func(name):
            def task():
                return f"{name}执行完成"
            return task
        
        tasks = ["A", "B", "C", "D", "E", "F"]
        for task_name in tasks:
            dag.add_task(task_name, create_task_func(task_name))
        
        # 添加依赖关系
        dependencies = [
            ("C", "A"),
            ("C", "B"),
            ("D", "C"),
            ("E", "B"),
            ("F", "D"),
            ("F", "E")
        ]
        
        for dependent, dependency in dependencies:
            dag.add_dependency(dependent, dependency)
        
        print(dag.visualize())
    else:
        print("请指定一个选项:")
        print("  --example     运行使用示例")
        print("  --test-cycle  测试循环依赖检测")
        print("  --visualize   可视化示例DAG结构")


if __name__ == "__main__":
    main()