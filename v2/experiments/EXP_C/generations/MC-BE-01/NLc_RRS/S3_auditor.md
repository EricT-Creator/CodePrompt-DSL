# MC-BE-01 代码审查报告

## Constraint Review
- C1 (Python + FastAPI): PASS — 使用Python和FastAPI框架创建API应用
- C2 (stdlib + fastapi only): FAIL — 使用了pydantic库（用于数据验证），虽然pydantic是FastAPI的推荐依赖，但严格来说超出了"stdlib + fastapi + uvicorn only"的约束
- C3 (asyncio.Queue, no Celery): PASS — 使用asyncio.Queue实现任务队列，没有使用Celery或RQ
- C4 (Append-only event store): PASS — 事件存储使用字典列表，只通过append_event函数添加，没有覆盖操作
- C5 (Idempotent endpoints): PASS — /tasks端点通过idempotency_key实现幂等性，相同key返回现有任务
- C6 (Code only): PASS — 只有Python代码，没有外部配置文件或资源

## Functionality Assessment (0-5)
Score: 4 — 代码实现了完整的事件溯源任务队列系统，功能包括：任务提交、异步执行、失败重试（指数退避）、事件存储与回放、幂等性保证、健康检查。代码结构清晰，事件溯源模式实现正确。扣分点：使用了pydantic，不符合"stdlib only"的严格约束。

## Corrected Code
由于C2约束失败（要求stdlib + fastapi only，但使用了pydantic），需要移除pydantic依赖。以下是修正后的代码：

```py
import asyncio
import uuid
import time
import random
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any

from fastapi import FastAPI, HTTPException


# ── Event Types ──

class EventType(str, Enum):
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    EXHAUSTED = "EXHAUSTED"


@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: float
    payload: dict


# ── Request / Response Models (using dataclasses instead of pydantic) ──

@dataclass
class TaskSubmission:
    idempotency_key: str
    description: str = ""
    max_retries: int = 3


@dataclass
class TaskResponse:
    task_id: str
    idempotency_key: str
    status: str
    retries: int
    max_retries: int
    result: Any
    created_at: float
    updated_at: float


# ── Event Store ──

event_store: dict[str, list[Event]] = {}
idempotency_index: dict[str, str] = {}
task_meta: dict[str, dict] = {}

# ── Retry Config ──

BASE_DELAY = 1.0
BACKOFF_MULTIPLIER = 2.0
MAX_DELAY = 30.0


def append_event(task_id: str, event_type: EventType, payload: dict | None = None) -> Event:
    evt = Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=time.time(),
        payload=payload or {},
    )
    if task_id not in event_store:
        event_store[task_id] = []
    event_store[task_id].append(evt)
    return evt


def replay_task(task_id: str) -> TaskResponse:
    events = event_store.get(task_id, [])
    meta = task_meta.get(task_id, {})

    state = TaskResponse(
        task_id=task_id,
        idempotency_key=meta.get("idempotency_key", ""),
        status="UNKNOWN",
        retries=0,
        max_retries=meta.get("max_retries", 3),
        result=None,
        created_at=0.0,
        updated_at=0.0,
    )

    for evt in events:
        state.updated_at = evt.timestamp

        if evt.event_type == EventType.SUBMITTED:
            state.status = "SUBMITTED"
            state.created_at = evt.timestamp
        elif evt.event_type == EventType.QUEUED:
            state.status = "QUEUED"
        elif evt.event_type == EventType.PROCESSING:
            state.status = "PROCESSING"
        elif evt.event_type == EventType.SUCCEEDED:
            state.status = "SUCCEEDED"
            state.result = evt.payload.get("result")
        elif evt.event_type == EventType.FAILED:
            state.status = "FAILED"
            state.result = evt.payload.get("error")
        elif evt.event_type == EventType.RETRY_SCHEDULED:
            state.status = "RETRY_SCHEDULED"
            state.retries += 1
        elif evt.event_type == EventType.EXHAUSTED:
            state.status = "EXHAUSTED"

    return state


def retries_remaining(task_id: str) -> bool:
    events = event_store.get(task_id, [])
    meta = task_meta.get(task_id, {})
    max_retries = meta.get("max_retries", 3)
    retry_count = sum(1 for e in events if e.event_type == EventType.RETRY_SCHEDULED)
    return retry_count < max_retries


def get_retry_count(task_id: str) -> int:
    events = event_store.get(task_id, [])
    return sum(1 for e in events if e.event_type == EventType.RETRY_SCHEDULED)


# ── Task Execution ──

async def execute_task(task_id: str) -> dict:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.3:
        raise RuntimeError(f"Simulated failure for task {task_id}")
    return {"message": f"Task {task_id} completed successfully", "value": random.randint(1, 100)}


# ── App ──

app = FastAPI(title="Event-Sourced Task Queue")

task_queue: asyncio.Queue[str] = asyncio.Queue()


async def delayed_requeue(task_id: str, delay: float) -> None:
    jitter = delay * random.uniform(-0.1, 0.1)
    await asyncio.sleep(delay + jitter)
    await task_queue.put(task_id)
    append_event(task_id, EventType.QUEUED)


async def worker() -> None:
    while True:
        task_id = await task_queue.get()
        append_event(task_id, EventType.PROCESSING)
        try:
            result = await execute_task(task_id)
            append_event(task_id, EventType.SUCCEEDED, {"result": result})
        except Exception as e:
            append_event(task_id, EventType.FAILED, {"error": str(e)})
            if retries_remaining(task_id):
                retry_count = get_retry_count(task_id)
                delay = min(BASE_DELAY * (BACKOFF_MULTIPLIER ** retry_count), MAX_DELAY)
                append_event(task_id, EventType.RETRY_SCHEDULED, {"delay": delay, "retry": retry_count + 1})
                asyncio.create_task(delayed_requeue(task_id, delay))
            else:
                append_event(task_id, EventType.EXHAUSTED)
        task_queue.task_done()


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(worker())


# ── Endpoints ──

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(body: TaskSubmission) -> TaskResponse:
    if body.idempotency_key in idempotency_index:
        existing_id = idempotency_index[body.idempotency_key]
        return replay_task(existing_id)

    task_id = str(uuid.uuid4())
    idempotency_index[body.idempotency_key] = task_id
    task_meta[task_id] = {
        "idempotency_key": body.idempotency_key,
        "max_retries": body.max_retries,
        "description": body.description,
    }

    append_event(task_id, EventType.SUBMITTED, {"description": body.description})
    await task_queue.put(task_id)
    append_event(task_id, EventType.QUEUED)

    return replay_task(task_id)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return replay_task(task_id)


@app.get("/tasks/{task_id}/events")
async def get_task_events(task_id: str) -> list[dict]:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return [asdict(e) for e in event_store[task_id]]


@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task_endpoint(task_id: str) -> TaskResponse:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return replay_task(task_id)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "queue_size": task_queue.qsize(), "total_tasks": len(event_store)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```