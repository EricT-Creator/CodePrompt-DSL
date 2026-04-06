# MC-BE-01 Code Review Report (NLc_RRC)

## Constraint Review

- C1 (Python + FastAPI): PASS — Uses Python with FastAPI framework (line 1693)
- C2 (stdlib + fastapi only): FAIL — Uses `pydantic` (line 1694) which is a third-party package
- C3 (asyncio.Queue, no Celery): PASS — Uses `asyncio.Queue` (line 1764), no Celery/RQ used
- C4 (Append-only event store): FAIL — Event store is a dict `event_store: dict[str, list[Event]]` (line 1761), not a single append-only list. Events are stored per task in separate lists.
- C5 (Idempotent endpoints): PASS — POST /tasks uses `idempotency_key` and `idempotency_index` to ensure idempotency (lines 1881-1884)
- C6 (Code only): PASS — Output contains code only, no explanation text

## Functionality Assessment (0-5)
Score: 3 — The code implements event-sourced task queue with asyncio.Queue and idempotent endpoints. However, it violates C2 by using pydantic, and more critically violates C4: the event store is a dictionary mapping task_id to event lists, not a single append-only list as required.

## Corrected Code

```py
import asyncio
import uuid
import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException


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


# ─── Event Store ──────────────────────────────────────────────────────────────

# Single append-only list for all events
event_store: list[Event] = []
task_event_index: dict[str, list[int]] = {}  # Maps task_id to indices in event_store
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
    idx = len(event_store)
    event_store.append(evt)
    task_event_index.setdefault(task_id, []).append(idx)
    return evt


def get_task_events(task_id: str) -> list[Event]:
    indices = task_event_index.get(task_id, [])
    return [event_store[i] for i in indices]


def replay_events(task_id: str) -> DerivedTask:
    events = get_task_events(task_id)
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


@app.post("/tasks")
async def submit_task(request: dict) -> dict:
    idempotency_key = request.get("idempotency_key", "")
    payload = request.get("payload", {})
    max_retries = request.get("max_retries", 3)
    
    if idempotency_key in idempotency_index:
        existing_id = idempotency_index[idempotency_key]
        derived = replay_events(existing_id)
        return {
            "task_id": derived.task_id,
            "idempotency_key": derived.idempotency_key,
            "status": derived.status,
            "retries": derived.retries,
            "max_retries": derived.max_retries,
            "result": derived.result,
            "created_at": derived.created_at,
            "updated_at": derived.updated_at,
        }

    task_id = str(uuid.uuid4())
    idempotency_index[idempotency_key] = task_id
    task_meta[task_id] = {
        "idempotency_key": idempotency_key,
        "max_retries": max_retries,
        "payload": payload,
    }

    append_event(task_id, EventType.SUBMITTED, {"idempotency_key": idempotency_key, "payload": payload})
    append_event(task_id, EventType.QUEUED)
    await task_queue.put(task_id)

    derived = replay_events(task_id)
    return {
        "task_id": derived.task_id,
        "idempotency_key": derived.idempotency_key,
        "status": derived.status,
        "retries": derived.retries,
        "max_retries": derived.max_retries,
        "result": derived.result,
        "created_at": derived.created_at,
        "updated_at": derived.updated_at,
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    derived = replay_events(task_id)
    return {
        "task_id": derived.task_id,
        "idempotency_key": derived.idempotency_key,
        "status": derived.status,
        "retries": derived.retries,
        "max_retries": derived.max_retries,
        "result": derived.result,
        "created_at": derived.created_at,
        "updated_at": derived.updated_at,
    }


@app.get("/tasks/{task_id}/events")
async def get_events(task_id: str) -> list[dict]:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    events = get_task_events(task_id)
    return [
        {
            "event_id": e.event_id,
            "task_id": e.task_id,
            "event_type": e.event_type.value,
            "timestamp": e.timestamp,
            "payload": e.payload,
        }
        for e in events
    ]


@app.post("/tasks/{task_id}/replay")
async def replay_task(task_id: str) -> dict:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    derived = replay_events(task_id)
    return {
        "task_id": derived.task_id,
        "idempotency_key": derived.idempotency_key,
        "status": derived.status,
        "retries": derived.retries,
        "max_retries": derived.max_retries,
        "result": derived.result,
        "created_at": derived.created_at,
        "updated_at": derived.updated_at,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
