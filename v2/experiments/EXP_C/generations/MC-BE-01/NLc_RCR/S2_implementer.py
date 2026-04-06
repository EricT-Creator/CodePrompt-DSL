import asyncio
import uuid
import time
import random
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

app = FastAPI()

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
    payload: dict = field(default_factory=dict)

@dataclass
class Task:
    task_id: str
    idempotency_key: str
    status: str
    retries: int
    max_retries: int
    result: Any = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

class TaskSubmitRequest(BaseModel):
    payload: dict
    idempotency_key: str
    max_retries: int = 3

class TaskResponse(BaseModel):
    task_id: str
    status: str
    retries: int
    max_retries: int
    result: Any = None
    created_at: float
    updated_at: float

event_store: dict[str, list[Event]] = {}
idempotency_index: dict[str, str] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()

BASE_DELAY = 1.0
BACKOFF_MULTIPLIER = 2.0
MAX_DELAY = 30.0

async def execute_task(task_id: str) -> Any:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.3:
        raise Exception("Simulated task failure")
    return {"result": f"Task {task_id} completed successfully"}

def append_event(task_id: str, event_type: EventType, **payload) -> Event:
    event = Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=time.time(),
        payload=payload
    )
    if task_id not in event_store:
        event_store[task_id] = []
    event_store[task_id].append(event)
    return event

def derive_task_state(task_id: str) -> Optional[Task]:
    if task_id not in event_store:
        return None
    events = event_store[task_id]
    task: Optional[Task] = None
    for event in events:
        if event.event_type == EventType.SUBMITTED:
            task = Task(
                task_id=event.task_id,
                idempotency_key=event.payload.get("idempotency_key", ""),
                status="submitted",
                retries=0,
                max_retries=event.payload.get("max_retries", 3),
                created_at=event.timestamp,
                updated_at=event.timestamp
            )
        elif task:
            if event.event_type == EventType.QUEUED:
                task.status = "queued"
            elif event.event_type == EventType.PROCESSING:
                task.status = "processing"
            elif event.event_type == EventType.SUCCEEDED:
                task.status = "succeeded"
                task.result = event.payload.get("result")
            elif event.event_type == EventType.FAILED:
                task.status = "failed"
            elif event.event_type == EventType.RETRY_SCHEDULED:
                task.retries += 1
                task.status = "retry_scheduled"
            elif event.event_type == EventType.EXHAUSTED:
                task.status = "exhausted"
            task.updated_at = event.timestamp
    return task

def retries_remaining(task_id: str) -> int:
    task = derive_task_state(task_id)
    if not task:
        return 0
    return max(0, task.max_retries - task.retries)

async def delayed_requeue(task_id: str, delay: float):
    await asyncio.sleep(delay)
    await task_queue.put(task_id)
    append_event(task_id, EventType.QUEUED)

async def worker():
    while True:
        task_id = await task_queue.get()
        append_event(task_id, EventType.PROCESSING)
        try:
            result = await execute_task(task_id)
            append_event(task_id, EventType.SUCCEEDED, result=result)
        except Exception as e:
            append_event(task_id, EventType.FAILED, error=str(e))
            if retries_remaining(task_id) > 0:
                retry_count = derive_task_state(task_id).retries if derive_task_state(task_id) else 0
                delay = min(BASE_DELAY * (BACKOFF_MULTIPLIER ** retry_count), MAX_DELAY)
                jitter = delay * (0.9 + random.random() * 0.2)
                append_event(task_id, EventType.RETRY_SCHEDULED, delay=jitter)
                asyncio.create_task(delayed_requeue(task_id, jitter))
            else:
                append_event(task_id, EventType.EXHAUSTED)
        task_queue.task_done()

@app.on_event("startup")
async def startup():
    asyncio.create_task(worker())

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskSubmitRequest):
    if request.idempotency_key in idempotency_index:
        task_id = idempotency_index[request.idempotency_key]
        task = derive_task_state(task_id)
        if task:
            return TaskResponse(
                task_id=task.task_id,
                status=task.status,
                retries=task.retries,
                max_retries=task.max_retries,
                result=task.result,
                created_at=task.created_at,
                updated_at=task.updated_at
            )
    
    task_id = str(uuid.uuid4())
    idempotency_index[request.idempotency_key] = task_id
    append_event(task_id, EventType.SUBMITTED, 
                 idempotency_key=request.idempotency_key, 
                 max_retries=request.max_retries,
                 payload=request.payload)
    await task_queue.put(task_id)
    append_event(task_id, EventType.QUEUED)
    
    task = derive_task_state(task_id)
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        retries=task.retries,
        max_retries=task.max_retries,
        result=task.result,
        created_at=task.created_at,
        updated_at=task.updated_at
    )

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = derive_task_state(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        retries=task.retries,
        max_retries=task.max_retries,
        result=task.result,
        created_at=task.created_at,
        updated_at=task.updated_at
    )

@app.get("/tasks/{task_id}/events")
async def get_task_events(task_id: str):
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        {
            "event_id": e.event_id,
            "task_id": e.task_id,
            "event_type": e.event_type,
            "timestamp": e.timestamp,
            "payload": e.payload
        }
        for e in event_store[task_id]
    ]

@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str):
    task = derive_task_state(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        retries=task.retries,
        max_retries=task.max_retries,
        result=task.result,
        created_at=task.created_at,
        updated_at=task.updated_at
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
