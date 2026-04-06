# MC-BE-01: FastAPI事件溯源任务队列技术方案

## 1. API端点设计

### 1.1 RESTful端点
```
POST /tasks - 提交新任务（带幂等性键）
GET /tasks/{task_id} - 查询任务状态
GET /tasks/{task_id}/events - 获取任务事件日志
POST /tasks/{task_id}/replay - 重放事件重建状态
POST /tasks/{task_id}/retry - 手动重试失败任务
GET /metrics - 系统指标端点
```

### 1.2 请求/响应模型
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class TaskCreateRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    idempotency_key: str
    max_retries: int = 3
    initial_backoff_ms: int = 1000

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    events: list["EventResponse"]
    current_attempt: int
    last_error: Optional[str]

class EventResponse(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]
    sequence_number: int

class ReplayRequest(BaseModel):
    up_to_sequence: Optional[int] = None
    up_to_timestamp: Optional[datetime] = None
```

### 1.3 幂等性实现
- **幂等性键**: 客户端提供的唯一标识符
- **键映射**: 存储`idempotency_key → task_id`映射
- **请求去重**: 相同键的请求返回已有任务
- **过期清理**: 定期清理旧的幂等性映射

## 2. 事件存储数据模型

### 2.1 核心数据结构
```python
from typing import List, TypedDict
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: str  # 'task_created', 'task_started', 'task_completed', 'task_failed'
    timestamp: datetime
    sequence_number: int
    payload: dict
    metadata: dict = field(default_factory=dict)

@dataclass
class TaskState:
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    current_attempt: int = 1
    max_retries: int = 3
    last_error: Optional[str] = None
    events: List[Event] = field(default_factory=list)
    
    # 派生字段（通过事件重放计算）
    result: Optional[dict] = None
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

### 2.2 存储策略
- **仅追加列表**: 事件按顺序追加，永不修改或删除
- **内存存储**: 使用Python列表存储事件和任务状态
- **序列化**: 事件和状态使用字典序列化存储
- **索引优化**: 维护任务ID到事件列表的映射

### 2.3 事件模式
```python
class EventTypes:
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"
    TASK_RETRY_STARTED = "task_retry_started"
    TASK_CANCELLED = "task_cancelled"
```

## 3. asyncio.Queue工作者架构

### 3.1 队列系统设计
```python
import asyncio
from typing import Dict, Set
from contextlib import asynccontextmanager

class TaskQueueSystem:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1000)
        self.workers: Set[asyncio.Task] = set()
        self.task_registry: Dict[str, TaskState] = {}
        self.event_store: List[Event] = []
        self.idempotency_map: Dict[str, str] = {}  # key -> task_id
        self.max_workers = 5
```

### 3.2 工作者生命周期
```
工作者启动 → 监听队列 → 获取任务 → 
处理任务 → 发送事件 → 更新状态 → 
返回队列监听（循环）
```

### 3.3 任务处理流程
```python
async def worker_process(self, worker_id: int):
    """单个工作者处理循环"""
    while True:
        try:
            # 从队列获取任务
            task_state = await self.queue.get()
            
            # 发送任务开始事件
            await self.emit_event(
                task_state.task_id,
                EventTypes.TASK_STARTED,
                {"worker_id": worker_id}
            )
            
            # 执行任务逻辑
            result = await self.execute_task(task_state)
            
            # 发送任务完成事件
            await self.emit_event(
                task_state.task_id,
                EventTypes.TASK_COMPLETED,
                {"result": result}
            )
            
        except Exception as e:
            # 发送失败事件
            await self.emit_event(
                task_state.task_id,
                EventTypes.TASK_FAILED,
                {"error": str(e), "attempt": task_state.current_attempt}
            )
            
            # 重试逻辑
            if task_state.current_attempt < task_state.max_retries:
                await self.schedule_retry(task_state)
        finally:
            self.queue.task_done()
```

## 4. 重试和退避策略

### 4.1 退避算法
```python
def calculate_backoff(self, attempt: int, initial_backoff_ms: int) -> float:
    """
    指数退避算法
    attempt: 当前尝试次数
    initial_backoff_ms: 初始退避时间（毫秒）
    """
    # 指数退避：backoff = initial * 2^(attempt-1)
    backoff_ms = initial_backoff_ms * (2 ** (attempt - 1))
    
    # 添加随机抖动（±25%）
    jitter_factor = 1 + (random.random() * 0.5 - 0.25)
    backoff_ms *= jitter_factor
    
    # 限制最大退避时间（30秒）
    max_backoff_ms = 30000
    return min(backoff_ms, max_backoff_ms) / 1000.0  # 转换为秒
```

### 4.2 重试策略实现
- **立即重试**: 第一次失败后立即重试（可选）
- **指数退避**: 后续重试使用指数退避
- **最大重试**: 可配置的最大重试次数
- **失败处理**: 达到最大重试后标记为永久失败

### 4.3 状态恢复
- **事件重放**: 通过重放事件重建任务状态
- **检查点**: 定期保存状态快照加速恢复
- **一致性保证**: 确保事件顺序和状态一致性

## 5. 约束确认

### 5.1 Python + FastAPI
- 使用FastAPI构建RESTful API
- Python 3.10+类型注解
- Pydantic数据验证

### 5.2 stdlib + fastapi + uvicorn only
- 仅使用标准库
- FastAPI作为Web框架
- Uvicorn作为ASGI服务器
- 不引入额外依赖

### 5.3 asyncio.Queue only, no Celery/RQ
- 使用asyncio.Queue实现任务队列
- 原生异步任务处理
- 不依赖外部队列系统

### 5.4 Append-only list event store, no dict overwrite
- 事件仅追加到列表
- 不可变事件存储
- 不覆盖现有数据

### 5.5 All endpoints idempotent
- 所有端点实现幂等性
- 幂等性键支持
- 重复请求处理

### 5.6 Code only
- 纯代码实现
- 无外部配置文件
- 自包含系统设计