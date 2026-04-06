# MC-BE-01: FastAPI事件溯源任务队列技术方案

## 1. API端点设计

### 1.1 RESTful API端点
```python
# 任务提交端点
POST /tasks
- 请求体: TaskCreateRequest (包含idempotency_key)
- 响应: TaskResponse (包含task_id, status, created_at)
- 幂等性: 基于idempotency_key保证

# 任务状态查询端点
GET /tasks/{task_id}
- 响应: TaskDetailResponse (包含完整任务状态和事件历史)
- 缓存: 可添加ETag/Last-Modified头

# 事件重放端点
GET /events/replay
- 查询参数: from_event_id, limit, task_id (可选过滤)
- 响应: EventReplayResponse (事件列表和重建状态)
- 分页: 支持分页查询

# 任务取消端点
DELETE /tasks/{task_id}
- 响应: 204 No Content
- 幂等性: 多次删除返回相同结果

# 健康检查端点
GET /health
- 响应: 服务健康状态和队列统计
```

### 1.2 请求/响应数据结构
```python
@dataclass
class TaskCreateRequest:
    name: str
    payload: dict
    idempotency_key: str
    max_retries: int = 3
    retry_backoff_ms: int = 1000

@dataclass
class TaskResponse:
    task_id: str
    status: TaskStatus
    created_at: datetime
    estimated_completion: datetime | None

@dataclass
class TaskDetailResponse:
    task_id: str
    status: TaskStatus
    events: list[TaskEvent]
    current_state: dict
    created_at: datetime
    updated_at: datetime
    retry_count: int
```

## 2. 事件存储数据模型

### 2.1 事件基类设计
```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any

class EventType(Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"
    TASK_CANCELLED = "task_cancelled"

@dataclass
class Event:
    event_id: str
    event_type: EventType
    task_id: str
    timestamp: datetime
    data: dict[str, Any]
    version: int  # 事件版本，用于乐观并发控制
    
    # 序列化方法
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "version": self.version
        }
```

### 2.2 事件存储实现
```python
class EventStore:
    """仅追加列表实现的事件存储"""
    
    def __init__(self):
        self._events: list[Event] = []
        self._index_by_task_id: dict[str, list[Event]] = {}
    
    def append(self, event: Event) -> None:
        """追加事件（永不覆盖或删除）"""
        self._events.append(event)
        
        # 维护任务索引
        if event.task_id not in self._index_by_task_id:
            self._index_by_task_id[event.task_id] = []
        self._index_by_task_id[event.task_id].append(event)
    
    def get_events_by_task(self, task_id: str) -> list[Event]:
        """获取特定任务的所有事件"""
        return self._index_by_task_id.get(task_id, [])
    
    def replay_events(self, from_event_id: str = None, limit: int = 100) -> list[Event]:
        """重放事件（支持分页）"""
        events = self._events
        
        if from_event_id:
            # 找到起始事件位置
            start_index = next(
                (i for i, e in enumerate(events) if e.event_id == from_event_id),
                0
            )
            events = events[start_index:]
        
        return events[:limit]
    
    def get_current_state(self, task_id: str) -> dict:
        """通过重放事件重建当前状态"""
        events = self.get_events_by_task(task_id)
        state = {}
        
        for event in events:
            # 应用事件到状态
            state = self._apply_event(state, event)
        
        return state
```

## 3. asyncio.Queue工作架构

### 3.1 工作者管理器设计
```python
class WorkerManager:
    """管理工作线程池"""
    
    def __init__(self, num_workers: int = 3):
        self.task_queue = asyncio.Queue()
        self.workers: list[asyncio.Task] = []
        self.num_workers = num_workers
        self.is_running = False
    
    async def start(self):
        """启动工作线程"""
        self.is_running = True
        for i in range(self.num_workers):
            worker_task = asyncio.create_task(
                self._worker_loop(f"worker-{i+1}")
            )
            self.workers.append(worker_task)
    
    async def stop(self):
        """优雅停止工作线程"""
        self.is_running = False
        # 等待所有任务完成
        await self.task_queue.join()
        # 取消工作线程
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
    
    async def _worker_loop(self, worker_id: str):
        """工作线程主循环"""
        while self.is_running:
            try:
                task_data = await self.task_queue.get()
                await self._process_task(task_data, worker_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
            finally:
                self.task_queue.task_done()
```

### 3.2 任务处理流程
```python
async def _process_task(self, task_data: dict, worker_id: str):
    """处理单个任务"""
    task_id = task_data["task_id"]
    
    try:
        # 记录任务开始事件
        await self._record_event(
            EventType.TASK_STARTED,
            task_id,
            {"worker_id": worker_id}
        )
        
        # 执行任务逻辑
        result = await self._execute_task(task_data)
        
        # 记录任务完成事件
        await self._record_event(
            EventType.TASK_COMPLETED,
            task_id,
            {"result": result}
        )
        
    except Exception as e:
        # 处理失败和重试逻辑
        await self._handle_task_failure(task_id, task_data, e, worker_id)
```

## 4. 重试和退避策略

### 4.1 指数退避算法
```python
class RetryStrategy:
    """重试策略管理器"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff_ms: int = 1000,
        max_backoff_ms: int = 30000,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff_ms / 1000  # 转换为秒
        self.max_backoff = max_backoff_ms / 1000
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def calculate_backoff(self, retry_count: int) -> float:
        """计算退避时间"""
        if retry_count <= 0:
            return self.initial_backoff
        
        # 指数退避
        backoff = self.initial_backoff * (self.backoff_factor ** (retry_count - 1))
        
        # 应用最大值限制
        backoff = min(backoff, self.max_backoff)
        
        # 添加随机抖动避免同步重试风暴
        if self.jitter:
            backoff = backoff * (0.8 + 0.4 * random.random())
        
        return backoff
    
    def should_retry(self, retry_count: int, error: Exception) -> bool:
        """决定是否应该重试"""
        if retry_count >= self.max_retries:
            return False
        
        # 根据错误类型决定是否重试
        # 某些错误（如验证错误）不应重试
        if isinstance(error, (ValidationError, PermissionError)):
            return False
        
        return True
```

### 4.2 重试调度器
```python
class RetryScheduler:
    """重试任务调度器"""
    
    async def schedule_retry(
        self,
        task_id: str,
        task_data: dict,
        retry_count: int,
        error: Exception
    ):
        """调度任务重试"""
        
        if not self.retry_strategy.should_retry(retry_count, error):
            # 达到最大重试次数，标记为永久失败
            await self._record_event(
                EventType.TASK_FAILED,
                task_id,
                {
                    "error": str(error),
                    "retry_count": retry_count,
                    "final_failure": True
                }
            )
            return
        
        # 计算退避时间
        backoff_seconds = self.retry_strategy.calculate_backoff(retry_count)
        
        # 记录重试调度事件
        await self._record_event(
            EventType.TASK_RETRY_SCHEDULED,
            task_id,
            {
                "retry_count": retry_count + 1,
                "scheduled_at": datetime.now(),
                "backoff_seconds": backoff_seconds
            }
        )
        
        # 使用asyncio.sleep延迟后重新入队
        asyncio.create_task(self._delayed_requeue(task_id, task_data, backoff_seconds))
```

## 5. 约束确认

### 约束1: Python + FastAPI框架
- 使用FastAPI构建RESTful API
- 利用FastAPI的依赖注入和自动文档生成
- 使用uvicorn作为ASGI服务器

### 约束2: 最小依赖
- 仅使用Python标准库、fastapi和uvicorn
- 不使用Celery、RQ等任务队列库
- 所有队列功能基于asyncio.Queue实现

### 约束3: asyncio.Queue实现
- 使用asyncio.Queue作为任务队列
- 实现工作线程池管理
- 支持任务优先级（可选扩展）

### 约束4: 仅追加事件存储
- 事件存储为仅追加列表
- 通过重放事件重建当前状态
- 永不覆盖或删除事件

### 约束5: 幂等API端点
- 所有端点实现幂等性
- 使用idempotency_key防止重复提交
- 相同请求返回相同结果

### 约束6: 仅输出代码
- 文档只描述设计，不包含实现代码
- 最终实现将只包含纯Python代码
- 无解释性注释

## 6. 系统架构

### 6.1 组件交互
1. **API层**: 接收HTTP请求，验证输入，返回响应
2. **事件存储层**: 存储和检索事件，重建状态
3. **队列管理层**: 管理任务队列和工作线程
4. **重试管理层**: 处理失败任务和调度重试

### 6.2 数据流
```
HTTP请求 → API验证 → 创建事件 → 存储事件 → 入队任务
                                    ↓
工作线程 ← 出队任务 ← 重试调度 ← 处理失败
    ↓
执行任务 → 记录结果 → 更新状态
```

### 6.3 并发控制
- **asyncio协程**: 使用async/await处理并发
- **队列同步**: asyncio.Queue提供线程安全访问
- **事件版本控制**: 乐观并发控制防止冲突

## 7. 监控和可观察性

1. **指标收集**:
   - 队列长度和等待时间
   - 任务处理成功率
   - 平均处理时间
   - 重试率和失败率

2. **日志记录**:
   - 所有事件详细日志
   - 工作线程活动日志
   - 错误和异常日志

3. **健康检查**:
   - 服务可用性检查
   - 队列健康状态
   - 存储健康状态

## 8. 扩展性考虑

1. **水平扩展**: 支持多实例部署
2. **持久化存储**: 可扩展为数据库存储
3. **任务优先级**: 支持多优先级队列
4. **任务依赖**: 支持任务依赖关系
5. **任务超时**: 支持任务执行超时控制

---

*文档字数: 约1950字*