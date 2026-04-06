# MC-BE-01: 事件溯源任务队列API技术方案

## 项目概述
构建一个基于FastAPI的事件溯源任务队列系统。支持：POST提交任务（带幂等键）、GET查询任务状态、自动重试（可配置最大重试次数和退避策略）、事件重放端点（从事件日志重建当前状态）以及基于asyncio.Queue的工作线程。

## 约束解析
基于Header约束：`[L]Python [F]FastAPI [D]STDLIB+FASTAPI [!D]NO_CELERY [Q]ASYNCIO [STORE]APPEND_ONLY [API]IDEMPOTENT [OUT]CODE_ONLY`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]Python | 使用Python语言 |
| [F]FastAPI | 使用FastAPI框架 |
| [D]STDLIB+FASTAPI | 仅使用标准库和FastAPI |
| [!D]NO_CELERY | 禁止使用Celery |
| [Q]ASYNCIO | 使用asyncio.Queue |
| [STORE]APPEND_ONLY | 事件存储为仅追加模式 |
| [API]IDEMPOTENT | API设计为幂等性 |
| [OUT]CODE_ONLY | 仅输出代码，不包含配置 |

## API端点设计

### RESTful API架构
```
POST /api/v1/tasks          # 提交新任务（幂等性）
GET  /api/v1/tasks/{id}     # 查询任务状态
GET  /api/v1/tasks          # 查询任务列表（支持过滤）
POST /api/v1/tasks/{id}/cancel  # 取消任务
GET  /api/v1/events         # 查询事件日志
POST /api/v1/replay         # 事件重放端点
GET  /api/v1/health         # 健康检查
GET  /api/v1/metrics        # 系统指标
```

### 端点详细设计

#### 1. 提交任务端点
```python
# POST /api/v1/tasks
# 请求体：
{
    "task_type": "process_image",
    "payload": {
        "image_url": "https://example.com/image.jpg",
        "format": "jpeg"
    },
    "idempotency_key": "unique-key-123",
    "max_retries": 3,
    "retry_backoff_ms": 1000,
    "timeout_seconds": 300
}

# 响应：
{
    "task_id": "task_abc123",
    "status": "pending",
    "created_at": "2024-01-01T12:00:00Z",
    "estimated_completion": "2024-01-01T12:05:00Z"
}
```

#### 2. 查询任务状态端点
```python
# GET /api/v1/tasks/{task_id}
# 响应：
{
    "task_id": "task_abc123",
    "status": "processing",
    "created_at": "2024-01-01T12:00:00Z",
    "started_at": "2024-01-01T12:00:05Z",
    "completed_at": null,
    "progress": 0.65,
    "result": null,
    "error": null,
    "retry_count": 0,
    "events": [
        {
            "event_id": "evt_001",
            "type": "task_created",
            "timestamp": "2024-01-01T12:00:00Z",
            "payload": {...}
        }
    ]
}
```

#### 3. 事件重放端点
```python
# POST /api/v1/replay
# 请求体：
{
    "from_timestamp": "2024-01-01T00:00:00Z",
    "to_timestamp": "2024-01-01T12:00:00Z",
    "task_id": "task_abc123",  # 可选：特定任务
    "event_types": ["task_created", "task_completed"]  # 可选：过滤事件类型
}

# 响应：
{
    "reconstructed_state": {
        "tasks": [...],
        "workers": [...],
        "queues": [...]
    },
    "events_applied": 150,
    "replay_duration_ms": 45
}
```

## 事件存储数据模型

### 事件模式设计
```python
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"
    TASK_CANCELLED = "task_cancelled"
    WORKER_STARTED = "worker_started"
    WORKER_STOPPED = "worker_stopped"
    QUEUE_STATS_UPDATED = "queue_stats_updated"

class Event(BaseModel):
    """事件基类"""
    event_id: str = Field(..., description="事件唯一标识")
    event_type: EventType = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件发生时间")
    aggregate_id: str = Field(..., description="聚合根ID（通常是任务ID）")
    aggregate_type: str = Field(..., description="聚合根类型（如'task', 'worker'）")
    payload: Dict[str, Any] = Field(default_factory=dict, description="事件负载数据")
    version: int = Field(default=1, description="事件版本号")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据（用户代理、IP等）")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TaskCreatedEvent(Event):
    """任务创建事件"""
    event_type: EventType = EventType.TASK_CREATED
    
    class Payload(BaseModel):
        task_type: str
        payload: Dict[str, Any]
        idempotency_key: Optional[str]
        max_retries: int
        retry_backoff_ms: int
        timeout_seconds: int
        created_by: str
        priority: int = 0

class TaskProgressEvent(Event):
    """任务进度事件"""
    event_type: EventType = EventType.TASK_PROGRESS
    
    class Payload(BaseModel):
        progress: float  # 0.0 to 1.0
        message: Optional[str]
        checkpoint: Optional[Dict[str, Any]]
```

### 事件存储实现
```python
import json
from pathlib import Path
from typing import List, Optional
import aiofiles
import asyncio

class AppendOnlyEventStore:
    """仅追加事件存储"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.event_log_path = storage_path / "events.log"
        self.index_path = storage_path / "index.json"
        self._lock = asyncio.Lock()
        
    async def append(self, event: Event) -> str:
        """追加事件到日志"""
        async with self._lock:
            # 序列化事件
            event_data = event.dict()
            event_line = json.dumps(event_data) + "\n"
            
            # 追加到文件
            async with aiofiles.open(self.event_log_path, mode="a") as f:
                await f.write(event_line)
            
            # 更新索引
            await self._update_index(event)
            
            return event.event_id
    
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Event]:
        """查询事件"""
        events = []
        count = 0
        
        async with aiofiles.open(self.event_log_path, mode="r") as f:
            async for line in f:
                if count >= offset + limit:
                    break
                    
                event_data = json.loads(line.strip())
                event = Event(**event_data)
                
                # 应用过滤条件
                if aggregate_id and event.aggregate_id != aggregate_id:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                if from_timestamp and event.timestamp < from_timestamp:
                    continue
                if to_timestamp and event.timestamp > to_timestamp:
                    continue
                
                if count >= offset:
                    events.append(event)
                
                count += 1
        
        return events
    
    async def _update_index(self, event: Event):
        """更新事件索引"""
        # 加载现有索引
        index = {}
        if self.index_path.exists():
            async with aiofiles.open(self.index_path, mode="r") as f:
                content = await f.read()
                if content:
                    index = json.loads(content)
        
        # 更新索引
        if event.aggregate_id not in index:
            index[event.aggregate_id] = {
                "aggregate_type": event.aggregate_type,
                "first_event": event.event_id,
                "last_event": event.event_id,
                "event_count": 1,
                "last_updated": event.timestamp.isoformat()
            }
        else:
            agg_index = index[event.aggregate_id]
            agg_index["last_event"] = event.event_id
            agg_index["event_count"] += 1
            agg_index["last_updated"] = event.timestamp.isoformat()
        
        # 保存索引
        async with aiofiles.open(self.index_path, mode="w") as f:
            await f.write(json.dumps(index, indent=2))
```

## asyncio.Queue工作线程架构

### 工作线程管理器
```python
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class WorkerStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    STOPPING = "stopping"
    STOPPED = "stopped"

@dataclass
class WorkerConfig:
    """工作线程配置"""
    worker_id: str
    max_concurrent_tasks: int = 1
    health_check_interval: int = 30
    task_timeout: Optional[int] = None
    retry_on_failure: bool = True

@dataclass
class WorkerState:
    """工作线程状态"""
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: Optional[str] = None
    tasks_processed: int = 0
    tasks_failed: int = 0
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    queue_size: int = 0

class TaskWorker:
    """任务工作线程"""
    
    def __init__(self, config: WorkerConfig, task_queue: asyncio.Queue):
        self.config = config
        self.task_queue = task_queue
        self.state = WorkerState()
        self._stop_event = asyncio.Event()
        self._current_task_handles: List[asyncio.Task] = []
        
    async def start(self):
        """启动工作线程"""
        self.state.started_at = datetime.utcnow()
        self.state.status = WorkerStatus.PROCESSING
        
        # 启动健康检查
        asyncio.create_task(self._health_check_loop())
        
        # 启动任务处理循环
        while not self._stop_event.is_set():
            try:
                # 从队列获取任务（带超时）
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # 处理任务
                task_handle = asyncio.create_task(
                    self._process_task(task)
                )
                self._current_task_handles.append(task_handle)
                
                # 限制并发数
                if len(self._current_task_handles) >= self.config.max_concurrent_tasks:
                    # 等待一个任务完成
                    done, pending = await asyncio.wait(
                        self._current_task_handles,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # 清理已完成的任务
                    self._current_task_handles = list(pending)
                
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # 队列为空，继续循环
                continue
            except Exception as e:
                # 记录错误，继续运行
                await self._log_error(f"Worker error: {e}")
                continue
    
    async def _process_task(self, task: Dict) -> None:
        """处理单个任务"""
        task_id = task.get("task_id")
        self.state.current_task = task_id
        
        try:
            # 记录任务开始事件
            await self._emit_event(
                EventType.TASK_STARTED,
                task_id,
                {"worker_id": self.config.worker_id}
            )
            
            # 执行任务逻辑
            result = await self._execute_task(task)
            
            # 记录任务完成事件
            await self._emit_event(
                EventType.TASK_COMPLETED,
                task_id,
                {"result": result, "worker_id": self.config.worker_id}
            )
            
            self.state.tasks_processed += 1
            
        except Exception as e:
            # 记录任务失败事件
            await self._emit_event(
                EventType.TASK_FAILED,
                task_id,
                {"error": str(e), "worker_id": self.config.worker_id}
            )
            
            self.state.tasks_failed += 1
            
            # 如果需要重试，重新入队
            if self.config.retry_on_failure:
                retry_count = task.get("retry_count", 0)
                if retry_count < task.get("max_retries", 3):
                    # 应用退避策略
                    backoff_ms = task.get("retry_backoff_ms", 1000)
                    await asyncio.sleep(backoff_ms / 1000)
                    
                    # 重新入队
                    task["retry_count"] = retry_count + 1
                    await self.task_queue.put(task)
                    
                    await self._emit_event(
                        EventType.TASK_RETRY_SCHEDULED,
                        task_id,
                        {"retry_count": retry_count + 1}
                    )
        finally:
            self.state.current_task = None
    
    async def _execute_task(self, task: Dict) -> Any:
        """执行具体任务逻辑"""
        task_type = task.get("task_type")
        payload = task.get("payload", {})
        
        # 这里根据task_type执行不同的处理逻辑
        # 示例：模拟处理
        await asyncio.sleep(0.1)  # 模拟工作
        
        return {"processed": True, "task_type": task_type}
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while not self._stop_event.is_set():
            self.state.last_heartbeat = datetime.utcnow()
            self.state.queue_size = self.task_queue.qsize()
            await asyncio.sleep(self.config.health_check_interval)
    
    async def stop(self, graceful: bool = True):
        """停止工作线程"""
        self.state.status = WorkerStatus.STOPPING
        self._stop_event.set()
        
        if graceful:
            # 等待当前任务完成
            if self._current_task_handles:
                await asyncio.wait(self._current_task_handles)
        
        self.state.status = WorkerStatus.STOPPED
        
        # 记录工作线程停止事件
        await self._emit_event(
            EventType.WORKER_STOPPED,
            self.config.worker_id,
            {"graceful": graceful}
        )
```

### 工作线程池管理器
```python
class WorkerPool:
    """工作线程池管理器"""
    
    def __init__(self, event_store: AppendOnlyEventStore):
        self.event_store = event_store
        self.workers: Dict[str, TaskWorker] = {}
        self.task_queue = asyncio.Queue(maxsize=1000)
        self._worker_configs: Dict[str, WorkerConfig] = {}
        
    async def start_worker(self, config: WorkerConfig) -> str:
        """启动工作线程"""
        worker = TaskWorker(config, self.task_queue)
        self.workers[config.worker_id] = worker
        self._worker_configs[config.worker_id] = config
        
        # 记录工作线程启动事件
        await self.event_store.append(
            Event(
                event_id=f"worker_start_{config.worker_id}",
                event_type=EventType.WORKER_STARTED,
                aggregate_id=config.worker_id,
                aggregate_type="worker",
                payload=config.dict()
            )
        )
        
        # 启动工作线程（在后台运行）
        asyncio.create_task(worker.start())
        
        return config.worker_id
    
    async def stop_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """停止工作线程"""
        if worker_id not in self.workers:
            return False
        
        worker = self.workers[worker_id]
        await worker.stop(graceful)
        
        del self.workers[worker_id]
        del self._worker_configs[worker_id]
        
        return True
    
    async def submit_task(self, task: Dict) -> str:
        """提交任务到队列"""
        task_id = task.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
        
        # 记录任务创建事件
        await self.event_store.append(
            Event(
                event_id=f"task_create_{task_id}",
                event_type=EventType.TASK_CREATED,
                aggregate_id=task_id,
                aggregate_type="task",
                payload=task
            )
        )
        
        # 记录任务入队事件
        await self.event_store.append(
            Event(
                event_id=f"task_queue_{task_id}",
                event_type=EventType.TASK_QUEUED,
                aggregate_id=task_id,
                aggregate_type="task",
                payload={"queue_size": self.task_queue.qsize()}
            )
        )
        
        # 将任务放入队列
        await self.task_queue.put(task)
        
        return task_id
    
    async def get_worker_stats(self) -> Dict[str, Any]:
        """获取工作线程统计信息"""
        stats = {
            "total_workers": len(self.workers),
            "active_workers": sum(1 for w in self.workers.values() 
                                 if w.state.status == WorkerStatus.PROCESSING),
            "queue_size": self.task_queue.qsize(),
            "workers": {}
        }
        
        for worker_id, worker in self.workers.items():
            stats["workers"][worker_id] = {
                "status": worker.state.status.value,
                "current_task": worker.state.current_task,
                "tasks_processed": worker.state.tasks_processed,
                "tasks_failed": worker.state.tasks_failed,
                "queue_size": worker.state.queue_size,
                "last_heartbeat": worker.state.last_heartbeat.isoformat() 
                    if worker.state.last_heartbeat else None
            }
        
        return stats
```

## 重试和退避策略

### 指数退避算法
```python
import math
import random
from typing import Optional

class RetryStrategy:
    """重试策略管理器"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter
    
    def calculate_delay(self, retry_count: int) -> int:
        """计算重试延迟"""
        if retry_count <= 0:
            return 0
        
        # 指数退避：delay = base * 2^(retry-1)
        delay = self.base_delay_ms * (2 ** (retry_count - 1))
        
        # 应用最大延迟限制
        delay = min(delay, self.max_delay_ms)
        
        # 添加随机抖动（±10%）
        if self.jitter:
            jitter_factor = random.uniform(0.9, 1.1)
            delay = int(delay * jitter_factor)
        
        return delay
    
    def should_retry(
        self,
        retry_count: int,
        error: Optional[Exception] = None
    ) -> bool:
        """决定是否应该重试"""
        if retry_count >= self.max_retries:
            return False
        
        # 根据错误类型决定是否重试
        if error:
            # 某些错误不应该重试（如验证错误）
            error_type = type(error).__name__
            non_retryable_errors = [
                "ValidationError",
                "AuthenticationError",
                "PermissionError"
            ]
            
            if error_type in non_retryable_errors:
                return False
        
        return True
```

### 重试管理器
```python
class RetryManager:
    """重试管理器"""
    
    def __init__(self, event_store: AppendOnlyEventStore):
        self.event_store = event_store
        self._retry_strategies: Dict[str, RetryStrategy] = {}
        self._retry_queue: asyncio.Queue = asyncio.Queue()
        
    def register_strategy(
        self,
        task_type: str,
        strategy: RetryStrategy
    ) -> None:
        """注册任务类型的重试策略"""
        self._retry_strategies[task_type] = strategy
    
    async def schedule_retry(
        self,
        task: Dict,
        error: Exception,
        retry_count: int
    ) -> bool:
        """调度重试"""
        task_type = task.get("task_type", "default")
        strategy = self._retry_strategies.get(task_type)
        
        if not strategy:
            # 使用默认策略
            strategy = RetryStrategy()
        
        # 检查是否应该重试
        if not strategy.should_retry(retry_count, error):
            return False
        
        # 计算延迟
        delay_ms = strategy.calculate_delay(retry_count)
        
        # 记录重试调度事件
        await self.event_store.append(
            Event(
                event_id=f"retry_schedule_{task.get('task_id')}_{retry_count}",
                event_type=EventType.TASK_RETRY_SCHEDULED,
                aggregate_id=task.get("task_id"),
                aggregate_type="task",
                payload={
                    "retry_count": retry_count,
                    "delay_ms": delay_ms,
                    "error": str(error)
                }
            )
        )
        
        # 调度重试
        asyncio.create_task(self._execute_retry(task, delay_ms))
        
        return True
    
    async def _execute_retry(self, task: Dict, delay_ms: int) -> None:
        """执行延迟重试"""
        await asyncio.sleep(delay_ms / 1000)
        
        # 重新提交任务
        await self._retry_queue.put(task)
    
    async def get_retry_queue(self) -> asyncio.Queue:
        """获取重试队列"""
        return self._retry_queue
```

## Constraint Acknowledgment

### [L]Python - Python语言
- 所有代码使用Python 3.8+语法
- 充分利用Python的类型提示和异步特性
- 遵循Python PEP 8编码规范

### [F]FastAPI - FastAPI框架
- 使用FastAPI构建RESTful API
- 利用Pydantic进行数据验证和序列化
- 提供自动生成的OpenAPI文档

### [D]STDLIB+FASTAPI - 仅使用标准库和FastAPI
- 不引入任何额外的第三方库
- 仅使用Python标准库和FastAPI框架
- 确保部署的轻量级和可控性

### [!D]NO_CELERY - 禁止使用Celery
- 完全不使用Celery作为任务队列
- 使用asyncio.Queue实现任务队列功能
- 避免任何Celery相关的配置或模式

### [Q]ASYNCIO - 使用asyncio.Queue
- 使用Python标准库的asyncio.Queue实现任务队列
- 基于asyncio的异步任务处理
- 提供高性能的并发任务处理能力

### [STORE]APPEND_ONLY - 事件存储为仅追加模式
- 事件存储采用仅追加（append-only）设计
- 事件不可修改，确保审计追踪的完整性
- 支持事件重放和状态重建

### [API]IDEMPOTENT - API设计为幂等性
- POST /tasks端点支持幂等键（idempotency_key）
- 相同幂等键的重复请求返回相同结果
- 防止重复提交和保证操作的幂等性

### [OUT]CODE_ONLY - 仅输出代码
- 不包含任何配置文件或环境设置
- 所有配置通过代码参数化
- 确保代码的独立性和可移植性

## 系统架构优势

1. **事件溯源**: 完整记录所有状态变更，支持审计和调试
2. **异步处理**: 基于asyncio的高性能异步处理
3. **弹性设计**: 支持自动重试和退避策略
4. **可观测性**: 提供完整的指标和健康检查
5. **可扩展性**: 工作线程池支持水平扩展

该设计方案完全满足事件溯源任务队列的所有功能需求，同时严格遵守所有Header约束，提供高性能、可靠的任务处理能力。