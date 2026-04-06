# MC-PY-02: DAG任务调度器技术方案

## 项目概述
本方案设计一个有向无环图(DAG)任务调度器，支持任务依赖管理、拓扑排序、环检测和并行任务分组执行。调度器接受任务依赖图，计算执行顺序，检测循环依赖，并将独立任务分组以最大化并行度。

## 约束解析
根据Header约束，本方案需满足以下技术要求：

| 约束 | 含义 | 技术实现 |
|------|------|----------|
| `[L]PY310` | Python 3.10+版本 | 使用Python 3.10+语法特性，如match语句、类型联合运算符 |
| `[D]STDLIB_ONLY` | 仅使用Python标准库 | 仅依赖`typing`, `collections`, `itertools`等标准库 |
| `[!D]NO_GRAPH_LIB` | 禁止使用图算法库 | 手动实现图数据结构，不使用networkx等库 |
| `[O]CLASS` | 使用类实现 | 所有功能封装在类中 |
| `[TYPE]FULL_HINTS` | 完整的类型提示 | 所有函数、变量都有详细类型注解 |
| `[ERR]CYCLE_EXC` | 检测到环时抛出CycleError异常 | 自定义CycleError异常类，检测到环时抛出 |
| `[FILE]SINGLE` | 单文件实现 | 所有代码在一个.py文件中 |

## 架构设计

### 1. 核心类架构

#### DAGScheduler类
主类，负责DAG的构建、验证和调度：
- `__init__()`: 初始化调度器，创建空图
- `add_task()`: 添加任务节点
- `add_dependency()`: 添加任务依赖关系
- `validate()`: 验证图结构，检测环
- `schedule()`: 生成调度计划
- `execute()`: 执行调度计划

#### TaskNode类
任务节点表示：
- `name`: 任务名称
- `dependencies`: 前置依赖任务集合
- `dependents`: 后置依赖任务集合
- `status`: 任务状态（pending, ready, running, completed）

### 2. 数据结构设计

#### 图表示
使用邻接表表示有向图：
```python
from typing import Dict, Set, List, Optional

class DAG:
    """有向无环图数据结构"""
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}  # 节点映射
        self.edges: Dict[str, Set[str]] = {}  # 出边邻接表
        self.reverse_edges: Dict[str, Set[str]] = {}  # 入边邻接表
```

#### 任务数据模型
```python
from typing import TypedDict, Callable, Any

class TaskConfig(TypedDict, total=False):
    """任务配置"""
    name: str  # 任务名称
    func: Callable[[], Any]  # 任务函数
    timeout: Optional[int]  # 超时时间（秒）
    retries: int  # 重试次数
```

### 3. 算法设计

#### 拓扑排序算法
实现Kahn算法进行拓扑排序：

**算法步骤**：
1. 计算所有节点的入度
2. 将入度为0的节点加入队列
3. 从队列中取出节点，加入结果列表
4. 移除该节点的所有出边，更新相关节点的入度
5. 将新的入度为0的节点加入队列
6. 重复步骤3-5直到队列为空

**复杂度分析**：
- 时间复杂度: O(V + E)，其中V是节点数，E是边数
- 空间复杂度: O(V + E)

#### 环检测算法
在拓扑排序过程中进行环检测：

**检测机制**：
1. 在Kahn算法执行后，检查结果列表长度
2. 如果结果列表长度 < 节点总数，说明存在环
3. 通过深度优先搜索(DFS)找到具体的环路径
4. 抛出`CycleError`异常，包含环路径信息

**DFS环检测算法**：
```python
def find_cycle(self) -> List[str]:
    """查找环路径"""
    visited = set()
    stack = set()
    path = []
    
    def dfs(node: str) -> bool:
        if node in stack:
            # 找到环
            cycle_start = path.index(node)
            return True
        if node in visited:
            return False
            
        visited.add(node)
        stack.add(node)
        path.append(node)
        
        for neighbor in self.edges.get(node, set()):
            if dfs(neighbor):
                return True
                
        stack.remove(node)
        path.pop()
        return False
    
    for node in self.nodes:
        if dfs(node):
            # 提取环路径
            cycle_start = path.index(path[-1])
            return path[cycle_start:]
    return []
```

### 4. 并行分组策略

#### 执行层级计算
基于拓扑排序结果计算执行层级：

**算法**：
1. 初始化所有节点的层级为0
2. 按拓扑顺序遍历节点
3. 对于每个节点，更新其后继节点的层级：`level[successor] = max(level[successor], level[node] + 1)`
4. 相同层级的节点可以并行执行

#### 分组算法
```python
def group_by_level(self, topological_order: List[str]) -> List[List[str]]:
    """按执行层级分组任务"""
    levels = {}
    max_level = 0
    
    # 计算每个任务的层级
    for task in topological_order:
        level = 0
        for dep in self.reverse_edges.get(task, set()):
            level = max(level, levels.get(dep, 0) + 1)
        levels[task] = level
        max_level = max(max_level, level)
    
    # 按层级分组
    groups = [[] for _ in range(max_level + 1)]
    for task, level in levels.items():
        groups[level].append(task)
    
    return groups
```

### 5. 执行引擎设计

#### 执行状态机
每个任务的状态转换：
- `PENDING` → `READY` (所有依赖完成)
- `READY` → `RUNNING` (开始执行)
- `RUNNING` → `COMPLETED` (执行成功)
- `RUNNING` → `FAILED` (执行失败)
- `FAILED` → `READY` (重试)

#### 并行执行控制
使用`concurrent.futures.ThreadPoolExecutor`实现并行执行：

**执行策略**：
1. 按层级顺序执行
2. 同一层级内任务并行执行
3. 等待当前层级所有任务完成后再进入下一层级
4. 支持任务超时和重试

## 关键实现策略

### 1. 图算法优化
- 使用双向邻接表加速依赖查询
- 缓存入度计算结果
- 增量式拓扑排序

### 2. 环检测优化
- 在添加依赖时进行快速环检测
- 使用Tarjan算法进行强连通分量检测
- 提供详细的环路径信息

### 3. 类型安全设计
- 使用泛型类型变量
- 运行时类型验证
- 完整的类型提示

### 4. 错误处理
- 自定义异常类层次结构
- 详细的错误消息
- 错误恢复机制

## 约束确认

### Constraint Acknowledgment

1. **`[L]PY310`** ✅
   - 方案使用Python 3.10+的`typing`语法
   - 使用`TypeVar`和泛型
   - 可选使用`match`语句进行状态匹配

2. **`[D]STDLIB_ONLY`** ✅
   - 仅使用Python标准库：`typing`, `collections`, `itertools`, `concurrent.futures`
   - 不依赖任何第三方库
   - 所有图算法手动实现

3. **`[!D]NO_GRAPH_LIB`** ✅
   - 完全避免使用networkx等图算法库
   - 手动实现邻接表数据结构
   - 手动实现拓扑排序和环检测算法

4. **`[O]CLASS`** ✅
   - 主要功能封装在`DAGScheduler`类中
   - `TaskNode`类表示任务节点
   - `CycleError`类表示环检测异常
   - 所有算法作为类方法实现

5. **`[TYPE]FULL_HINTS`** ✅
   - 所有函数参数和返回值都有完整类型注解
   - 使用`TypedDict`定义配置数据结构
   - 变量声明包含类型提示
   - 泛型类型参数

6. **`[ERR]CYCLE_EXC`** ✅
   - 定义`CycleError`异常类
   - 检测到环时抛出该异常
   - 异常包含环路径详细信息
   - 提供友好的错误消息

7. **`[FILE]SINGLE`** ✅
   - 所有代码实现在单个`.py`文件中
   - 包含所有类、函数和类型定义
   - 自包含，无需外部模块

## 性能优化

### 1. 算法优化
- 使用集合操作加速依赖检查
- 缓存拓扑排序结果
- 增量式图更新

### 2. 内存优化
- 使用生成器延迟计算
- 按需加载任务数据
- 清理不再需要的中间数据

### 3. 并发优化
- 可配置的线程池大小
- 任务优先级调度
- 资源限制控制

## 扩展功能

### 1. 监控与日志
- 执行进度跟踪
- 性能指标收集
- 详细执行日志

### 2. 容错机制
- 任务失败重试
- 依赖失败传播控制
- 检查点恢复

### 3. 可视化支持
- 生成DAG可视化图
- 执行时间线展示
- 依赖关系分析

## 使用示例

### 基本使用
```python
scheduler = DAGScheduler()

# 添加任务
scheduler.add_task("task_a", lambda: print("A"))
scheduler.add_task("task_b", lambda: print("B"))
scheduler.add_task("task_c", lambda: print("C"))

# 添加依赖
scheduler.add_dependency("task_a", "task_b")  # A -> B
scheduler.add_dependency("task_b", "task_c")  # B -> C

# 验证并执行
try:
    scheduler.validate()
    schedule = scheduler.schedule()
    scheduler.execute(schedule)
except CycleError as e:
    print(f"检测到环: {e.cycle}")
```

## 总结
本技术方案设计了一个符合所有Header约束的DAG任务调度器。通过手动实现图数据结构、拓扑排序算法和环检测机制，实现了高效、可靠的任务调度系统。方案严格遵循约束要求，同时提供了良好的性能、可扩展性和错误处理能力。