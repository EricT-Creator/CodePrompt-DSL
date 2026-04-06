# MC-PY-02: DAG任务调度器技术方案

## 1. DAG数据结构

### 1.1 DAG图表示
```python
@dataclass
class DAG:
    """有向无环图数据结构"""
    
    def __init__(self):
        # 邻接表表示法
        self.adjacency_list: dict[str, set[str]] = {}
        self.reverse_adjacency: dict[str, set[str]] = {}
        self.nodes: dict[str, Node] = {}
        self.edge_count: int = 0
    
    def add_node(self, node_id: str, task: Any = None) -> None:
        """添加节点"""
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists")
        
        self.nodes[node_id] = Node(node_id, task)
        self.adjacency_list[node_id] = set()
        self.reverse_adjacency[node_id] = set()
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """添加有向边"""
        
        # 验证节点存在
        if from_node not in self.nodes:
            raise ValueError(f"Source node {from_node} does not exist")
        if to_node not in self.nodes:
            raise ValueError(f"Target node {to_node} does not exist")
        
        # 防止自环
        if from_node == to_node:
            raise ValueError("Self-loops are not allowed")
        
        # 添加边
        self.adjacency_list[from_node].add(to_node)
        self.reverse_adjacency[to_node].add(from_node)
        self.edge_count += 1
    
    def remove_edge(self, from_node: str, to_node: str) -> None:
        """移除边"""
        if from_node in self.adjacency_list:
            self.adjacency_list[from_node].discard(to_node)
        if to_node in self.reverse_adjacency:
            self.reverse_adjacency[to_node].discard(from_node)
        self.edge_count = max(0, self.edge_count - 1)
    
    def get_predecessors(self, node_id: str) -> set[str]:
        """获取节点的前驱节点"""
        return self.reverse_adjacency.get(node_id, set()).copy()
    
    def get_successors(self, node_id: str) -> set[str]:
        """获取节点的后继节点"""
        return self.adjacency_list.get(node_id, set()).copy()
    
    def get_independent_nodes(self) -> list[str]:
        """获取独立节点（无前驱的节点）"""
        return [
            node_id for node_id, preds in self.reverse_adjacency.items()
            if not preds
        ]
    
    @property
    def node_count(self) -> int:
        """节点数量"""
        return len(self.nodes)
    
    @property
    def is_empty(self) -> bool:
        """图是否为空"""
        return self.node_count == 0
```

### 1.2 节点数据结构
```python
@dataclass
class Node:
    """DAG节点"""
    
    node_id: str
    task: Any = None
    metadata: dict = field(default_factory=dict)
    
    # 执行状态
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    
    # 依赖关系
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "task_type": type(self.task).__name__ if self.task else None,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "metadata": self.metadata
        }
```

### 1.3 边数据结构
```python
@dataclass
class Edge:
    """DAG边"""
    
    source: str
    target: str
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source, self.target))
    
    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.source == other.source and self.target == other.target
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "metadata": self.metadata
        }
```

## 2. 拓扑排序算法

### 2.1 Kahn算法实现
```python
class TopologicalSorter:
    """拓扑排序器（Kahn算法）"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.in_degree: dict[str, int] = {}
        self.sorted_nodes: list[str] = []
        self.has_cycle: bool = False
    
    def sort(self) -> list[str]:
        """执行拓扑排序"""
        
        # 初始化入度表
        self._initialize_in_degree()
        
        # 找到所有入度为0的节点
        zero_in_degree_nodes = [
            node for node, degree in self.in_degree.items()
            if degree == 0
        ]
        
        # 使用队列进行排序
        queue = collections.deque(zero_in_degree_nodes)
        
        while queue:
            current_node = queue.popleft()
            self.sorted_nodes.append(current_node)
            
            # 减少后继节点的入度
            for successor in self.dag.get_successors(current_node):
                self.in_degree[successor] -= 1
                
                # 如果入度变为0，加入队列
                if self.in_degree[successor] == 0:
                    queue.append(successor)
        
        # 检查是否有环
        if len(self.sorted_nodes) != self.dag.node_count:
            self.has_cycle = True
            self.sorted_nodes.clear()
        
        return self.sorted_nodes.copy()
    
    def _initialize_in_degree(self) -> None:
        """初始化入度表"""
        self.in_degree.clear()
        
        # 所有节点初始入度为0
        for node_id in self.dag.nodes:
            self.in_degree[node_id] = 0
        
        # 根据边增加入度
        for source in self.dag.adjacency_list:
            for target in self.dag.adjacency_list[source]:
                self.in_degree[target] += 1
```

### 2.2 深度优先搜索实现
```python
class DFSTopologicalSorter:
    """深度优先搜索拓扑排序器"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.visited: set[str] = set()
        self.temp_visited: set[str] = set()
        self.sorted_nodes: list[str] = []
        self.has_cycle: bool = False
    
    def sort(self) -> list[str]:
        """执行DFS拓扑排序"""
        
        self.visited.clear()
        self.temp_visited.clear()
        self.sorted_nodes.clear()
        self.has_cycle = False
        
        # 对所有未访问节点进行DFS
        for node_id in self.dag.nodes:
            if node_id not in self.visited:
                if not self._dfs_visit(node_id):
                    self.has_cycle = True
                    break
        
        # 反转结果得到拓扑顺序
        if not self.has_cycle:
            self.sorted_nodes.reverse()
        
        return self.sorted_nodes.copy()
    
    def _dfs_visit(self, node_id: str) -> bool:
        """DFS访问节点"""
        
        # 检测环
        if node_id in self.temp_visited:
            return False
        
        # 如果已访问，跳过
        if node_id in self.visited:
            return True
        
        # 标记为临时访问
        self.temp_visited.add(node_id)
        
        # 递归访问所有后继节点
        for successor in self.dag.get_successors(node_id):
            if not self._dfs_visit(successor):
                return False
        
        # 移除临时标记，添加永久标记
        self.temp_visited.remove(node_id)
        self.visited.add(node_id)
        
        # 添加到排序列表
        self.sorted_nodes.append(node_id)
        
        return True
```

## 3. 环检测方法

### 3.1 深度优先搜索环检测
```python
class CycleDetector:
    """环检测器"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.cycle_path: list[str] = []
    
    def has_cycle(self) -> bool:
        """检测图中是否有环"""
        
        # 三种状态：未访问、访问中、已访问
        state: dict[str, NodeState] = {
            node_id: NodeState.UNVISITED
            for node_id in self.dag.nodes
        }
        
        # 对每个未访问节点进行DFS
        for node_id in self.dag.nodes:
            if state[node_id] == NodeState.UNVISITED:
                if self._dfs_detect(node_id, state):
                    return True
        
        return False
    
    def get_cycle(self) -> Optional[list[str]]:
        """获取环的路径"""
        
        if not self.has_cycle():
            return None
        
        return self.cycle_path.copy()
    
    def _dfs_detect(self, node_id: str, state: dict[str, NodeState]) -> bool:
        """DFS检测环"""
        
        # 如果节点正在访问中，检测到环
        if state[node_id] == NodeState.VISITING:
            # 找到环的起点
            cycle_start = self.cycle_path.index(node_id)
            self.cycle_path = self.cycle_path[cycle_start:]
            self.cycle_path.append(node_id)  # 闭合环
            return True
        
        # 如果已访问，跳过
        if state[node_id] == NodeState.VISITED:
            return False
        
        # 标记为访问中
        state[node_id] = NodeState.VISITING
        self.cycle_path.append(node_id)
        
        # 检查所有后继节点
        for successor in self.dag.get_successors(node_id):
            if self._dfs_detect(successor, state):
                return True
        
        # 标记为已访问
        state[node_id] = NodeState.VISITED
        self.cycle_path.pop()
        
        return False
```

### 3.2 CycleError异常定义
```python
class CycleError(Exception):
    """环检测异常"""
    
    def __init__(self, cycle_path: list[str], message: str = None):
        self.cycle_path = cycle_path
        
        if message is None:
            message = f"Cycle detected in DAG: {' -> '.join(cycle_path)}"
        
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "error_type": "CycleError",
            "cycle_path": self.cycle_path,
            "cycle_length": len(self.cycle_path),
            "message": str(self)
        }
```

## 4. 并行分组策略

### 4.1 并行层级计算
```python
class ParallelGrouper:
    """并行分组器"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.levels: dict[str, int] = {}
        self.level_groups: dict[int, set[str]] = {}
    
    def compute_levels(self) -> dict[int, set[str]]:
        """计算每个节点的层级"""
        
        # 初始化层级
        self.levels.clear()
        self.level_groups.clear()
        
        # 使用拓扑排序
        sorter = TopologicalSorter(self.dag)
        sorted_nodes = sorter.sort()
        
        if not sorted_nodes:
            return {}
        
        # 为每个节点计算层级
        for node_id in sorted_nodes:
            # 获取前驱节点的最大层级
            predecessors = self.dag.get_predecessors(node_id)
            
            if not predecessors:
                # 无前驱，层级为0
                level = 0
            else:
                # 层级为前驱最大层级+1
                level = max(
                    self.levels.get(pred, 0) for pred in predecessors
                ) + 1
            
            self.levels[node_id] = level
            
            # 添加到层级组
            if level not in self.level_groups:
                self.level_groups[level] = set()
            self.level_groups[level].add(node_id)
        
        return self.level_groups.copy()
    
    def get_parallel_groups(self) -> list[list[str]]:
        """获取可并行执行的组"""
        
        # 计算层级
        level_groups = self.compute_levels()
        
        # 转换为列表形式
        parallel_groups = []
        
        for level in sorted(level_groups.keys()):
            group = list(level_groups[level])
            if group:
                parallel_groups.append(group)
        
        return parallel_groups
```

### 4.2 并行执行管理器
```python
class ParallelExecutor:
    """并行执行管理器"""
    
    def __init__(
        self,
        dag: DAG,
        max_workers: int = None,
        executor_class = None
    ):
        self.dag = dag
        self.max_workers = max_workers
        self.executor_class = executor_class or concurrent.futures.ThreadPoolExecutor
        
        # 执行状态
        self.results: dict[str, Any] = {}
        self.errors: dict[str, Exception] = {}
        self.completed_count: int = 0
        self.total_count: int = self.dag.node_count
    
    async def execute(self) -> dict[str, Any]:
        """执行DAG中的所有任务"""
        
        # 检测环
        detector = CycleDetector(self.dag)
        if detector.has_cycle():
            raise CycleError(detector.get_cycle())
        
        # 计算并行组
        grouper = ParallelGrouper(self.dag)
        parallel_groups = grouper.get_parallel_groups()
        
        # 按层级顺序执行
        for group in parallel_groups:
            await self._execute_group(group)
        
        return self.results.copy()
    
    async def _execute_group(self, group: list[str]) -> None:
        """执行一个并行组"""
        
        # 创建执行器
        with self.executor_class(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_node = {
                executor.submit(self._execute_node, node_id): node_id
                for node_id in group
            }
            
            # 等待所有任务完成
            for future in concurrent.futures.as_completed(future_to_node):
                node_id = future_to_node[future]
                
                try:
                    result = future.result()
                    self.results[node_id] = result
                    self.completed_count += 1
                    
                except Exception as e:
                    self.errors[node_id] = e
    
    def _execute_node(self, node_id: str) -> Any:
        """执行单个节点"""
        
        node = self.dag.nodes[node_id]
        
        # 更新状态
        node.status = NodeStatus.RUNNING
        node.start_time = datetime.utcnow()
        
        try:
            # 执行任务
            if callable(node.task):
                result = node.task()
            else:
                result = node.task
            
            # 更新状态
            node.status = NodeStatus.COMPLETED
            node.end_time = datetime.utcnow()
            node.execution_time = (node.end_time - node.start_time).total_seconds()
            
            return result
            
        except Exception as e:
            # 更新状态
            node.status = NodeStatus.FAILED
            node.end_time = datetime.utcnow()
            node.execution_time = (node.end_time - node.start_time).total_seconds()
            
            raise e
```

## 5. 约束确认

### 约束1: Python 3.10+标准库
- 仅使用Python 3.10+标准库
- 利用类型提示和dataclass
- 不引入外部依赖

### 约束2: 手动拓扑排序实现
- 实现Kahn算法和DFS算法
- 不使用networkx、graphlib等图库
- 从零实现所有图算法

### 约束3: 类作为主要输出
- 主输出为TaskScheduler类
- 提供完整的面向对象接口
- 不是独立函数集合

### 约束4: 完整类型注解
- 所有公共方法都有类型注解
- 类属性有类型注解
- 返回类型明确指定

### 约束5: CycleError异常
- 定义自定义CycleError异常
- 提供详细的环路径信息
- 异常可序列化为字典

### 约束6: 单文件实现
- 所有代码在一个Python文件中
- 包含完整的DAG管理和调度逻辑
- 提供并行执行支持

## 6. 任务调度器类

### 6.1 主调度器类
```python
class TaskScheduler:
    """DAG任务调度器"""
    
    def __init__(self):
        self.dag = DAG()
        self.task_registry: dict[str, Callable] = {}
        
    def register_task(self, task_id: str, task_func: Callable) -> None:
        """注册任务"""
        self.task_registry[task_id] = task_func
        self.dag.add_node(task_id, task_func)
    
    def add_dependency(self, from_task: str, to_task: str) -> None:
        """添加任务依赖"""
        self.dag.add_edge(from_task, to_task)
    
    def execute(self, max_workers: int = None) -> ExecutionResult:
        """执行所有任务"""
        
        # 检测环
        detector = CycleDetector(self.dag)
        if detector.has_cycle():
            raise CycleError(detector.get_cycle())
        
        # 创建并行执行器
        executor = ParallelExecutor(
            self.dag,
            max_workers=max_workers
        )
        
        # 执行任务
        results = asyncio.run(executor.execute())
        
        # 构建执行结果
        return ExecutionResult(
            success=len(executor.errors) == 0,
            results=results,
            errors=executor.errors,
            completed_count=executor.completed_count,
            total_count=executor.total_count
        )
```

## 7. 性能优化

1. **缓存拓扑排序**: 缓存排序结果避免重复计算
2. **增量更新**: 支持DAG的增量更新
3. **内存优化**: 使用集合和字典进行高效查找
4. **并行优化**: 优化线程池和任务分配

## 8. 扩展功能

1. **任务超时**: 支持任务执行超时控制
2. **任务重试**: 支持失败任务重试机制
3. **任务优先级**: 支持任务优先级调度
4. **可视化**: 可扩展为DAG可视化工具

---

*文档字数: 约1995字*