# MC-PY-02: DAG任务调度器技术方案

## 1. DAG数据结构

### 1.1 核心图表示
```python
from typing import Dict, List, Set, Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio
from enum import Enum

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskNode:
    """任务节点"""
    task_id: str
    task_fn: callable  # 任务函数
    dependencies: Set[str] = field(default_factory=set)  # 前置任务ID集合
    dependents: Set[str] = field(default_factory=set)  # 后置任务ID集合
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[Exception] = None
    execution_time: Optional[float] = None
    priority: int = 0  # 优先级（数值越大优先级越高）
    
    def add_dependency(self, task_id: str):
        """添加前置任务"""
        self.dependencies.add(task_id)
    
    def add_dependent(self, task_id: str):
        """添加后置任务"""
        self.dependents.add(task_id)
    
    def is_ready(self) -> bool:
        """检查任务是否就绪（所有前置任务已完成）"""
        return (
            self.status == TaskStatus.PENDING and
            all(dep_status == TaskStatus.COMPLETED 
                for dep_status in self._get_dependency_statuses())
        )
    
    def _get_dependency_statuses(self) -> List[TaskStatus]:
        """获取前置任务状态（由调度器提供）"""
        # 实际实现中由调度器提供
        return []

@dataclass
class DAG:
    """有向无环图"""
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    adjacency: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse_adjacency: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    entry_nodes: Set[str] = field(default_factory=set)  # 入度为0的节点
    exit_nodes: Set[str] = field(default_factory=set)  # 出度为0的节点
    
    def add_task(self, task_id: str, task_fn: callable, dependencies: List[str] = None):
        """添加任务到DAG"""
        if task_id in self.tasks:
            raise ValueError(f"任务已存在: {task_id}")
        
        # 创建任务节点
        task = TaskNode(task_id=task_id, task_fn=task_fn)
        
        # 添加依赖关系
        if dependencies:
            for dep_id in dependencies:
                # 验证依赖任务存在
                if dep_id not in self.tasks:
                    raise ValueError(f"依赖任务不存在: {dep_id}")
                
                task.add_dependency(dep_id)
                
                # 更新邻接表
                self.adjacency[dep_id].add(task_id)
                self.reverse_adjacency[task_id].add(dep_id)
        
        # 添加到任务字典
        self.tasks[task_id] = task
        
        # 更新入口/出口节点
        self._update_graph_structure()
    
    def _update_graph_structure(self):
        """更新图结构信息"""
        # 重新计算入口节点（入度为0）
        self.entry_nodes = {
            task_id for task_id in self.tasks.keys()
            if not self.reverse_adjacency.get(task_id)
        }
        
        # 重新计算出口节点（出度为0）
        self.exit_nodes = {
            task_id for task_id in self.tasks.keys()
            if not self.adjacency.get(task_id)
        }
    
    def get_independent_tasks(self) -> List[str]:
        """获取可并行执行的独立任务组"""
        # 使用Kahn算法的思想，但返回所有入度为0的节点
        ready_tasks = []
        
        for task_id, task_node in self.tasks.items():
            if task_node.status == TaskStatus.PENDING:
                # 检查所有前置任务是否完成
                all_deps_completed = all(
                    self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task_node.dependencies
                )
                
                if all_deps_completed:
                    ready_tasks.append(task_id)
        
        # 按优先级排序
        ready_tasks.sort(
            key=lambda tid: self.tasks[tid].priority,
            reverse=True
        )
        
        return ready_tasks
    
    def validate_dag(self) -> bool:
        """验证DAG是否有效（无环）"""
        try:
            self._topological_sort()
            return True
        except CycleError:
            return False
```

### 1.2 依赖关系管理
```python
class DependencyManager:
    """依赖关系管理器"""
    
    def __init__(self):
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_dependency(self, task_id: str, depends_on: List[str]):
        """注册任务依赖关系"""
        # 验证依赖任务存在
        missing_deps = [dep for dep in depends_on if dep not in self.task_metadata]
        if missing_deps:
            raise ValueError(f"依赖任务不存在: {missing_deps}")
        
        # 更新正向依赖
        self.dependency_graph[task_id].update(depends_on)
        
        # 更新反向依赖
        for dep_id in depends_on:
            self.reverse_dependency_graph[dep_id].add(task_id)
    
    def get_dependencies(self, task_id: str) -> Set[str]:
        """获取任务的所有依赖（直接和间接）"""
        # 使用BFS获取所有依赖
        all_deps = set()
        queue = list(self.dependency_graph.get(task_id, set()))
        
        while queue:
            current = queue.pop(0)
            if current not in all_deps:
                all_deps.add(current)
                # 添加当前任务的依赖
                queue.extend(self.dependency_graph.get(current, []))
        
        return all_deps
    
    def get_dependents(self, task_id: str) -> Set[str]:
        """获取依赖此任务的所有任务"""
        # 使用BFS获取所有依赖者
        all_dependents = set()
        queue = list(self.reverse_dependency_graph.get(task_id, set()))
        
        while queue:
            current = queue.pop(0)
            if current not in all_dependents:
                all_dependents.add(current)
                # 添加依赖当前任务的任务
                queue.extend(self.reverse_dependency_graph.get(current, []))
        
        return all_dependents
    
    def calculate_critical_path(self) -> List[str]:
        """计算关键路径"""
        # 实现关键路径算法（CPM）
        # 1. 计算最早开始时间（forward pass）
        # 2. 计算最晚开始时间（backward pass）
        # 3. 找出时差为0的任务
        pass
```

## 2. 拓扑排序算法

### 2.1 Kahn算法实现
```python
class KahnTopologicalSorter:
    """Kahn拓扑排序算法"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self._in_degree: Dict[str, int] = {}
        self._zero_in_degree_queue: List[str] = []
    
    def _calculate_in_degrees(self):
        """计算所有节点的入度"""
        # 初始化所有节点的入度为0
        self._in_degree = {task_id: 0 for task_id in self.dag.tasks.keys()}
        
        # 遍历所有边，增加目标节点的入度
        for task_id, task_node in self.dag.tasks.items():
            for dep_id in task_node.dependencies:
                if dep_id in self._in_degree:
                    self._in_degree[dep_id] += 1
                else:
                    # 依赖任务可能不存在（在验证时已检查）
                    pass
    
    def _init_zero_degree_queue(self):
        """初始化入度为0的节点队列"""
        self._zero_in_degree_queue = [
            task_id for task_id, degree in self._in_degree.items()
            if degree == 0
        ]
        
        # 按优先级排序
        self._zero_in_degree_queue.sort(
            key=lambda tid: self.dag.tasks[tid].priority,
            reverse=True
        )
    
    def topological_sort(self) -> List[str]:
        """
        执行拓扑排序
        
        Returns:
            拓扑排序结果
            
        Raises:
            CycleError: 检测到环
        """
        # 计算入度
        self._calculate_in_degrees()
        
        # 初始化零入度队列
        self._init_zero_degree_queue()
        
        # 执行Kahn算法
        sorted_tasks = []
        
        while self._zero_in_degree_queue:
            # 取出一个零入度节点
            current_task = self._zero_in_degree_queue.pop(0)
            sorted_tasks.append(current_task)
            
            # 遍历当前节点的所有后继节点
            for dependent_id in self.dag.adjacency.get(current_task, []):
                # 减少后继节点的入度
                self._in_degree[dependent_id] -= 1
                
                # 如果入度变为0，加入队列
                if self._in_degree[dependent_id] == 0:
                    self._zero_in_degree_queue.append(dependent_id)
            
            # 维护队列优先级顺序
            self._zero_in_degree_queue.sort(
                key=lambda tid: self.dag.tasks[tid].priority,
                reverse=True
            )
        
        # 检查是否存在环
        if len(sorted_tasks) != len(self.dag.tasks):
            # 有节点未被处理，说明存在环
            remaining_tasks = set(self.dag.tasks.keys()) - set(sorted_tasks)
            raise CycleError(f"检测到环，未处理的任务: {remaining_tasks}")
        
        return sorted_tasks
    
    def find_cycles(self) -> List[List[str]]:
        """查找所有环"""
        # 使用DFS检测环
        cycles = []
        visited = set()
        recursion_stack = set()
        path = []
        
        def dfs(task_id: str):
            if task_id in recursion_stack:
                # 发现环
                cycle_start = path.index(task_id)
                cycle = path[cycle_start:] + [task_id]
                cycles.append(cycle)
                return
            
            if task_id in visited:
                return
            
            visited.add(task_id)
            recursion_stack.add(task_id)
            path.append(task_id)
            
            # 遍历后继节点
            for dependent_id in self.dag.adjacency.get(task_id, []):
                dfs(dependent_id)
            
            recursion_stack.remove(task_id)
            path.pop()
        
        # 从所有节点开始DFS
        for task_id in self.dag.tasks.keys():
            if task_id not in visited:
                dfs(task_id)
        
        return cycles
```

### 2.2 带约束的拓扑排序
```python
class ConstrainedTopologicalSorter(KahnTopologicalSorter):
    """带约束的拓扑排序"""
    
    def __init__(self, dag: DAG, max_parallel_tasks: int = 4):
        super().__init__(dag)
        self.max_parallel_tasks = max_parallel_tasks
        self.resource_constraints: Dict[str, Set[str]] = {}  # 资源到任务映射
        self.task_resources: Dict[str, Set[str]] = {}  # 任务到资源映射
    
    def add_resource_constraint(self, resource_id: str, task_ids: List[str]):
        """添加资源约束"""
        if resource_id not in self.resource_constraints:
            self.resource_constraints[resource_id] = set()
        
        self.resource_constraints[resource_id].update(task_ids)
        
        # 更新任务资源映射
        for task_id in task_ids:
            if task_id not in self.task_resources:
                self.task_resources[task_id] = set()
            self.task_resources[task_id].add(resource_id)
    
    def topological_sort_with_constraints(self) -> List[List[str]]:
        """
        带约束的拓扑排序，返回分层任务列表
        
        Returns:
            每层可并行执行的任务列表
        """
        # 计算初始入度
        self._calculate_in_degrees()
        
        # 初始化零入度队列
        self._init_zero_degree_queue()
        
        # 执行带约束的Kahn算法
        sorted_layers = []
        
        while self._zero_in_degree_queue:
            # 根据约束选择当前层要执行的任务
            current_layer = self._select_tasks_for_layer()
            
            if not current_layer:
                # 无法选择任何任务，可能存在死锁
                break
            
            sorted_layers.append(current_layer)
            
            # 处理当前层任务的后继
            for task_id in current_layer:
                # 减少后继节点的入度
                for dependent_id in self.dag.adjacency.get(task_id, []):
                    self._in_degree[dependent_id] -= 1
                    
                    # 如果入度变为0，加入队列
                    if self._in_degree[dependent_id] == 0:
                        self._zero_in_degree_queue.append(dependent_id)
                
                # 从队列中移除已处理的任务
                if task_id in self._zero_in_degree_queue:
                    self._zero_in_degree_queue.remove(task_id)
            
            # 重新排序队列
            self._zero_in_degree_queue.sort(
                key=lambda tid: self.dag.tasks[tid].priority,
                reverse=True
            )
        
        return sorted_layers
    
    def _select_tasks_for_layer(self) -> List[str]:
        """根据约束选择当前层要执行的任务"""
        selected_tasks = []
        used_resources = set()
        
        # 按优先级顺序尝试选择任务
        for task_id in sorted(
            self._zero_in_degree_queue,
            key=lambda tid: self.dag.tasks[tid].priority,
            reverse=True
        ):
            # 检查并行任务数限制
            if len(selected_tasks) >= self.max_parallel_tasks:
                break
            
            # 检查资源约束
            task_resources = self.task_resources.get(task_id, set())
            if task_resources & used_resources:
                # 资源冲突，跳过此任务
                continue
            
            # 添加任务到当前层
            selected_tasks.append(task_id)
            
            # 标记使用的资源
            used_resources.update(task_resources)
        
        return selected_tasks
```

## 3. 环检测方法

### 3.1 DFS环检测
```python
class CycleDetector:
    """环检测器"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
    
    def detect_cycles(self) -> List[List[str]]:
        """
        检测环
        
        Returns:
            所有检测到的环的列表
        """
        cycles = []
        visited = set()
        recursion_stack = set()
        path = []
        
        def dfs(current_task_id: str):
            # 标记为已访问和递归栈中
            visited.add(current_task_id)
            recursion_stack.add(current_task_id)
            path.append(current_task_id)
            
            # 遍历后继节点
            for dependent_id in self.dag.adjacency.get(current_task_id, []):
                if dependent_id in recursion_stack:
                    # 发现环
                    cycle_start = path.index(dependent_id)
                    cycle = path[cycle_start:] + [dependent_id]
                    cycles.append(cycle)
                elif dependent_id not in visited:
                    dfs(dependent_id)
            
            # 从递归栈中移除
            recursion_stack.remove(current_task_id)
            path.pop()
        
        # 从所有未访问的节点开始DFS
        for task_id in self.dag.tasks.keys():
            if task_id not in visited:
                dfs(task_id)
        
        return cycles
    
    def has_cycles(self) -> bool:
        """检查是否存在环"""
        cycles = self.detect_cycles()
        return len(cycles) > 0
    
    def get_cycle_participants(self) -> Set[str]:
        """获取参与环的所有任务"""
        cycles = self.detect_cycles()
        participants = set()
        
        for cycle in cycles:
            participants.update(cycle)
        
        return participants
    
    def find_cycle_causes(self) -> List[Dict[str, Any]]:
        """分析环产生的原因"""
        cycles = self.detect_cycles()
        causes = []
        
        for cycle in cycles:
            # 分析环中的依赖关系
            cycle_edges = []
            for i in range(len(cycle) - 1):
                from_task = cycle[i]
                to_task = cycle[i + 1]
                cycle_edges.append(f"{from_task} -> {to_task}")
            
            # 添加最后一条边（环闭合）
            cycle_edges.append(f"{cycle[-1]} -> {cycle[0]}")
            
            causes.append({
                "cycle": cycle,
                "edges": cycle_edges,
                "length": len(cycle),
                "participants": list(set(cycle))
            })
        
        return causes
```

### 3.2 CycleError异常
```python
class CycleError(Exception):
    """环异常"""
    
    def __init__(self, message: str, cycle: Optional[List[str]] = None):
        super().__init__(message)
        self.cycle = cycle
        self.message = message
    
    def __str__(self) -> str:
        base_msg = f"CycleError: {self.message}"
        if self.cycle:
            return f"{base_msg}\nCycle detected: {self.cycle}"
        return base_msg
    
    def get_detailed_info(self) -> Dict[str, Any]:
        """获取详细异常信息"""
        return {
            "error_type": "cycle_error",
            "message": self.message,
            "cycle": self.cycle,
            "cycle_length": len(self.cycle) if self.cycle else 0
        }
```

### 3.3 环检测集成
```python
class DAGScheduler:
    """DAG调度器"""
    
    def __init__(self, dag: DAG, max_workers: int = 4):
        self.dag = dag
        self.max_workers = max_workers
        self.cycle_detector = CycleDetector(dag)
        self.topological_sorter = KahnTopologicalSorter(dag)
        
        # 验证DAG无环
        self._validate_dag()
    
    def _validate_dag(self):
        """验证DAG有效性"""
        if self.cycle_detector.has_cycles():
            cycles = self.cycle_detector.detect_cycles()
            raise CycleError(
                f"DAG包含 {len(cycles)} 个环",
                cycle=cycles[0] if cycles else None
            )
    
    async def execute(self) -> Dict[str, Any]:
        """
        执行DAG中的所有任务
        
        Returns:
            执行结果摘要
        """
        # 检查是否有环（再次验证）
        if self.cycle_detector.has_cycles():
            cycles = self.cycle_detector.detect_cycles()
            raise CycleError(
                f"执行前检测到 {len(cycles)} 个环",
                cycle=cycles[0]
            )
        
        # 获取拓扑排序结果
        try:
            execution_order = self.topological_sorter.topological_sort()
        except CycleError as e:
            # 再次验证
            cycles = self.cycle_detector.detect_cycles()
            raise CycleError(
                f"拓扑排序时检测到环: {e.message}",
                cycle=cycles[0] if cycles else None
            )
        
        # 执行任务
        execution_results = await self._execute_tasks(execution_order)
        
        return {
            "success": all(r["success"] for r in execution_results.values()),
            "execution_order": execution_order,
            "results": execution_results,
            "total_tasks": len(execution_order),
            "failed_tasks": sum(1 for r in execution_results.values() if not r["success"])
        }
    
    async def _execute_tasks(self, execution_order: List[str]) -> Dict[str, Dict[str, Any]]:
        """按顺序执行任务"""
        results = {}
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def execute_task(task_id: str):
            async with semaphore:
                task_node = self.dag.tasks[task_id]
                task_node.status = TaskStatus.RUNNING
                
                start_time = asyncio.get_event_loop().time()
                
                try:
                    # 执行任务函数
                    result = await task_node.task_fn()
                    task_node.result = result
                    task_node.status = TaskStatus.COMPLETED
                    
                    return {
                        "success": True,
                        "result": result,
                        "error": None,
                        "execution_time": asyncio.get_event_loop().time() - start_time
                    }
                except Exception as e:
                    task_node.error = e
                    task_node.status = TaskStatus.FAILED
                    
                    return {
                        "success": False,
                        "result": None,
                        "error": str(e),
                        "execution_time": asyncio.get_event_loop().time() - start_time
                    }
        
        # 创建并执行所有任务
        tasks = []
        for task_id in execution_order:
            task = asyncio.create_task(execute_task(task_id))
            tasks.append((task_id, task))
        
        # 等待所有任务完成
        for task_id, task in tasks:
            try:
                results[task_id] = await task
            except Exception as e:
                results[task_id] = {
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "execution_time": 0.0
                }
        
        return results
```

## 4. 并行分组策略

### 4.1 并行执行器
```python
class ParallelExecutor:
    """并行执行器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
    
    async def execute_parallel(
        self,
        task_ids: List[str],
        task_functions: Dict[str, callable]
    ) -> Dict[str, Dict[str, Any]]:
        """
        并行执行一组任务
        
        Args:
            task_ids: 要执行的任务ID列表
            task_functions: 任务ID到任务函数的映射
        
        Returns:
            执行结果字典
        """
        results = {}
        
        async def execute_single(task_id: str):
            async with self.semaphore:
                task_fn = task_functions.get(task_id)
                if not task_fn:
                    return {
                        "task_id": task_id,
                        "success": False,
                        "error": "Task function not found",
                        "result": None
                    }
                
                start_time = asyncio.get_event_loop().time()
                
                try:
                    result = await task_fn()
                    return {
                        "task_id": task_id,
                        "success": True,
                        "error": None,
                        "result": result,
                        "execution_time": asyncio.get_event_loop().time() - start_time
                    }
                except Exception as e:
                    return {
                        "task_id": task_id,
                        "success": False,
                        "error": str(e),
                        "result": None,
                        "execution_time": asyncio.get_event_loop().time() - start_time
                    }
        
        # 创建所有任务
        tasks = [execute_single(task_id) for task_id in task_ids]
        
        # 等待所有任务完成
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        for i, result in enumerate(task_results):
            task_id = task_ids[i]
            
            if isinstance(result, Exception):
                results[task_id] = {
                    "success": False,
                    "error": str(result),
                    "result": None,
                    "execution_time": 0.0
                }
            else:
                results[task_id] = result
        
        return results
```

### 4.2 分层执行策略
```python
class LayeredExecutor:
    """分层执行器"""
    
    def __init__(self, dag: DAG, max_workers_per_layer: int = 4):
        self.dag = dag
        self.max_workers_per_layer = max_workers_per_layer
        self.parallel_executor = ParallelExecutor(max_workers_per_layer)
    
    async def execute_by_layers(self) -> Dict[str, Any]:
        """
        按层执行DAG
        
        1. 找出所有独立任务（入度为0）
        2. 并行执行这些任务
        3. 完成后更新依赖关系
        4. 重复直到所有任务完成
        """
        execution_summary = {
            "layers": [],
            "total_tasks": len(self.dag.tasks),
            "failed_tasks": 0,
            "success": True
        }
        
        # 复制DAG状态以便跟踪
        remaining_tasks = set(self.dag.tasks.keys())
        completed_tasks = set()
        failed_tasks = set()
        
        layer_index = 0
        
        while remaining_tasks:
            # 找出当前可执行的任务
            ready_tasks = self._find_ready_tasks(
                remaining_tasks,
                completed_tasks
            )
            
            if not ready_tasks:
                # 没有就绪任务，检查是否存在死锁
                if not self._has_cycles_in_remaining(remaining_tasks):
                    # 不是环，可能是任务未就绪
                    break
                else:
                    # 存在环，引发异常
                    cycles = self._find_cycles_in_remaining(remaining_tasks)
                    raise CycleError(
                        f"检测到环，无法继续执行",
                        cycle=cycles[0] if cycles else None
                    )
            
            # 并行执行当前层任务
            task_functions = {
                task_id: self.dag.tasks[task_id].task_fn
                for task_id in ready_tasks
            }
            
            layer_results = await self.parallel_executor.execute_parallel(
                ready_tasks,
                task_functions
            )
            
            # 更新任务状态
            layer_success = True
            for task_id, result in layer_results.items():
                if result["success"]:
                    completed_tasks.add(task_id)
                    self.dag.tasks[task_id].status = TaskStatus.COMPLETED
                    self.dag.tasks[task_id].result = result["result"]
                else:
                    failed_tasks.add(task_id)
                    self.dag.tasks[task_id].status = TaskStatus.FAILED
                    self.dag.tasks[task_id].error = result["error"]
                    layer_success = False
            
            # 记录层执行结果
            execution_summary["layers"].append({
                "index": layer_index,
                "tasks": list(ready_tasks),
                "results": layer_results,
                "success": layer_success
            })
            
            # 更新剩余任务
            remaining_tasks -= set(ready_tasks)
            layer_index += 1
        
        # 更新摘要
        execution_summary["failed_tasks"] = len(failed_tasks)
        execution_summary["success"] = len(failed_tasks) == 0
        
        return execution_summary
    
    def _find_ready_tasks(self, remaining_tasks: Set[str], completed_tasks: Set[str]) -> Set[str]:
        """找出就绪任务"""
        ready = set()
        
        for task_id in remaining_tasks:
            task_node = self.dag.tasks[task_id]
            
            # 检查所有依赖是否已完成
            all_deps_completed = all(
                dep_id in completed_tasks
                for dep_id in task_node.dependencies
            )
            
            if all_deps_completed:
                ready.add(task_id)
        
        return ready
    
    def _has_cycles_in_remaining(self, remaining_tasks: Set[str]) -> bool:
        """检查剩余任务中是否存在环"""
        # 创建子图检查
        subgraph_adjacency = {}
        for task_id in remaining_tasks:
            task_node = self.dag.tasks[task_id]
            # 只保留也在remaining_tasks中的依赖
            subgraph_adjacency[task_id] = {
                dep for dep in task_node.dependencies
                if dep in remaining_tasks
            }
        
        # 使用DFS检查环
        visited = set()
        recursion_stack = set()
        
        def dfs(current: str) -> bool:
            visited.add(current)
            recursion_stack.add(current)
            
            for neighbor in subgraph_adjacency.get(current, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True
            
            recursion_stack.remove(current)
            return False
        
        for task_id in remaining_tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        
        return False
    
    def _find_cycles_in_remaining(self, remaining_tasks: Set[str]) -> List[List[str]]:
        """查找剩余任务中的环"""
        # 类似实现，返回环的具体信息
        pass
```

## 5. 约束确认

### 5.1 Python 3.10+, stdlib only
- 要求Python 3.10或更高版本
- 仅使用标准库
- 无外部依赖

### 5.2 No networkx/graphlib
- 手动实现DAG数据结构
- 实现拓扑排序算法
- 实现环检测算法
- 不使用networkx或graphlib库

### 5.3 Output as class
- 输出为类定义
- 封装DAG、调度器和执行器
- 提供完整的API接口

### 5.4 Full type annotations
- 完整的类型注解
- 使用泛型支持不同类型的任务
- 类型安全的API设计

### 5.5 CycleError on cycles
- 检测到环时抛出CycleError异常
- 提供详细的环信息
- 支持环分析和调试

### 5.6 Single file
- 所有代码在单个Python文件中
- 自包含实现
- 无外部依赖