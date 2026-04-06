import asyncio
import uuid
import time
import random
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ─── Event Types ──────────────────────────────────────────────────────────────

class EventType(str, Enum):
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    EXHAUSTED = "EXHAUSTED"


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: float
    payload: dict = field(default_factory=dict)


@dataclass
class DerivedTask:
    task_id: str
    idempotency_key: str
    status: str
    retries: int
    max_retries: int
    result: Any
    created_at: float
    updated_at: float


# ─── Request / Response Models ────────────────────────────────────────────────

class SubmitTaskRequest(BaseModel):
    idempotency_key: str
    payload: dict = {}
    max_retries: int = 3


class TaskResponse(BaseModel):
    task_id: str
    idempotency_key: str
    status: str
    retries: int
    max_retries: int
    result: Any = None
    created_at: float
    updated_at: float


class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: float
    payload: dict


# ─── Event Store ──────────────────────────────────────────────────────────────

event_store: dict[str, list[Event]] = {}
idempotency_index: dict[str, str] = {}
task_meta: dict[str, dict] = {}
task_queue: asyncio.Queue = asyncio.Queue()


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


def replay_events(task_id: str) -> DerivedTask:
    events = event_store.get(task_id, [])
    meta = task_meta.get(task_id, {})
    derived = DerivedTask(
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
        derived.updated_at = evt.timestamp
        if evt.event_type == EventType.SUBMITTED:
            derived.status = "SUBMITTED"
            derived.created_at = evt.timestamp
        elif evt.event_type == EventType.QUEUED:
            derived.status = "QUEUED"
        elif evt.event_type == EventType.PROCESSING:
            derived.status = "PROCESSING"
        elif evt.event_type == EventType.SUCCEEDED:
            derived.status = "SUCCEEDED"
            derived.result = evt.payload.get("result")
        elif evt.event_type == EventType.FAILED:
            derived.status = "FAILED"
            derived.result = evt.payload.get("error")
        elif evt.event_type == EventType.RETRY_SCHEDULED:
            derived.status = "RETRY_SCHEDULED"
            derived.retries += 1
        elif evt.event_type == EventType.EXHAUSTED:
            derived.status = "EXHAUSTED"
    return derived


# ─── Worker ───────────────────────────────────────────────────────────────────

BASE_DELAY = 1.0
BACKOFF_MULTIPLIER = 2.0
MAX_DELAY = 30.0
SUCCESS_RATE = 0.7


async def execute_task(task_id: str) -> dict:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < SUCCESS_RATE:
        return {"message": f"Task {task_id} completed successfully", "value": random.randint(1, 100)}
    raise RuntimeError(f"Simulated failure for task {task_id}")


def retries_remaining(task_id: str) -> bool:
    derived = replay_events(task_id)
    return derived.retries < derived.max_retries


async def delayed_requeue(task_id: str, delay: float) -> None:
    await asyncio.sleep(delay)
    await task_queue.put(task_id)


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
                derived = replay_events(task_id)
                retry_count = derived.retries
                delay = min(BASE_DELAY * (BACKOFF_MULTIPLIER ** retry_count), MAX_DELAY)
                jitter = delay * random.uniform(-0.1, 0.1)
                delay += jitter
                append_event(task_id, EventType.RETRY_SCHEDULED, {"delay": delay, "retry": retry_count + 1})
                asyncio.create_task(delayed_requeue(task_id, delay))
            else:
                append_event(task_id, EventType.EXHAUSTED)
        task_queue.task_done()


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Event-Sourced Task Queue")


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(worker())


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "queue_size": task_queue.qsize(), "total_tasks": len(task_meta)}


@app.post("/tasks", response_model=TaskResponse)
async def submit_task(req: SubmitTaskRequest) -> TaskResponse:
    if req.idempotency_key in idempotency_index:
        existing_id = idempotency_index[req.idempotency_key]
        derived = replay_events(existing_id)
        return TaskResponse(**asdict(derived))

    task_id = str(uuid.uuid4())
    idempotency_index[req.idempotency_key] = task_id
    task_meta[task_id] = {
        "idempotency_key": req.idempotency_key,
        "max_retries": req.max_retries,
        "payload": req.payload,
    }

    append_event(task_id, EventType.SUBMITTED, {"idempotency_key": req.idempotency_key, "payload": req.payload})
    append_event(task_id, EventType.QUEUED)
    await task_queue.put(task_id)

    derived = replay_events(task_id)
    return TaskResponse(**asdict(derived))


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    derived = replay_events(task_id)
    return TaskResponse(**asdict(derived))


@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_events(task_id: str) -> list[EventResponse]:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        EventResponse(
            event_id=e.event_id,
            task_id=e.task_id,
            event_type=e.event_type.value,
            timestamp=e.timestamp,
            payload=e.payload,
        )
        for e in event_store[task_id]
    ]


@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str) -> TaskResponse:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    derived = replay_events(task_id)
    return TaskResponse(**asdict(derived))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
