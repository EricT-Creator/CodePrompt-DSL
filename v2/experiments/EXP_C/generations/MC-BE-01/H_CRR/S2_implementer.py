"""
MC-BE-01: Event-Sourced Task Queue API
[L]Python [F]FastAPI [D]STDLIB+FASTAPI [!D]NO_CELERY [Q]ASYNCIO [STORE]APPEND_ONLY [API]IDEMPOTENT [OUT]CODE_ONLY
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ─── Event Types ──────────────────────────────────────────────────────────────

class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskState:
    task_id: str = ""
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    task_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    created_at: str = ""
    updated_at: str = ""
    error: str | None = None
    permanent_failure: bool = False


# ─── Append-Only Event Store ─────────────────────────────────────────────────

event_store: dict[str, list[Event]] = {}
idempotency_map: dict[str, str] = {}

# ─── Configuration ────────────────────────────────────────────────────────────

MAX_RETRIES = 3
BASE_DELAY = 1.0
BACKOFF_MULTIPLIER = 2
WORKER_COUNT = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(task_id: str, event_type: EventType, payload: dict[str, Any] | None = None) -> Event:
    event = Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=now_iso(),
        payload=payload or {},
    )
    if task_id not in event_store:
        event_store[task_id] = []
    event_store[task_id].append(event)
    return event


def reconstruct_state(task_id: str) -> TaskState:
    events = event_store.get(task_id, [])
    state = TaskState(task_id=task_id)

    for event in events:
        if event.event_type == EventType.TASK_CREATED:
            state.status = TaskStatusEnum.PENDING
            state.task_type = event.payload.get("task_type", "")
            state.payload = event.payload.get("payload", {})
            state.created_at = event.timestamp
            state.updated_at = event.timestamp
        elif event.event_type == EventType.TASK_STARTED:
            state.status = TaskStatusEnum.PROCESSING
            state.attempts += 1
            state.updated_at = event.timestamp
        elif event.event_type == EventType.TASK_COMPLETED:
            state.status = TaskStatusEnum.COMPLETED
            state.updated_at = event.timestamp
        elif event.event_type == EventType.TASK_FAILED:
            if event.payload.get("permanent"):
                state.status = TaskStatusEnum.FAILED
                state.permanent_failure = True
            else:
                state.status = TaskStatusEnum.FAILED
            state.error = event.payload.get("error")
            state.updated_at = event.timestamp
        elif event.event_type == EventType.TASK_RETRY_SCHEDULED:
            state.status = TaskStatusEnum.PENDING
            state.updated_at = event.timestamp

    return state


# ─── Request / Response Schemas ───────────────────────────────────────────────

class SubmitTaskRequest(BaseModel):
    idempotency_key: str
    task_type: str
    payload: dict[str, Any] = {}


class SubmitTaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    attempts: int
    created_at: str
    updated_at: str


class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    payload: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    workers: int
    queued_tasks: int


# ─── Worker ───────────────────────────────────────────────────────────────────

async def execute_task(task_id: str) -> None:
    """Simulate task execution. Randomly fail ~20% of the time."""
    await asyncio.sleep(0.5 + (hash(task_id) % 10) * 0.05)
    # Deterministic pseudo-random failure based on task_id hash
    if hash(task_id + str(reconstruct_state(task_id).attempts)) % 5 == 0:
        raise RuntimeError(f"Simulated failure for task {task_id}")


def calculate_delay(attempt: int) -> float:
    return BASE_DELAY * (BACKOFF_MULTIPLIER ** attempt)


async def schedule_retry(task_id: str, task_queue: asyncio.Queue[str]) -> None:
    state = reconstruct_state(task_id)
    if state.attempts >= MAX_RETRIES:
        append_event(task_id, EventType.TASK_FAILED, {"permanent": True, "error": "Max retries exceeded"})
        return

    delay = calculate_delay(state.attempts)
    await asyncio.sleep(delay)
    append_event(task_id, EventType.TASK_RETRY_SCHEDULED)
    await task_queue.put(task_id)


async def worker(task_queue: asyncio.Queue[str], worker_id: int) -> None:
    while True:
        task_id = await task_queue.get()
        append_event(task_id, EventType.TASK_STARTED, {"worker_id": worker_id})

        try:
            await execute_task(task_id)
            append_event(task_id, EventType.TASK_COMPLETED, {"worker_id": worker_id})
        except Exception as e:
            append_event(task_id, EventType.TASK_FAILED, {"error": str(e), "worker_id": worker_id})
            asyncio.create_task(schedule_retry(task_id, task_queue))

        task_queue.task_done()


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Event-Sourced Task Queue API")


@app.on_event("startup")
async def start_workers() -> None:
    app.state.task_queue: asyncio.Queue[str] = asyncio.Queue()
    app.state.workers = [
        asyncio.create_task(worker(app.state.task_queue, i))
        for i in range(WORKER_COUNT)
    ]


@app.on_event("shutdown")
async def stop_workers() -> None:
    for w in app.state.workers:
        w.cancel()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/tasks", status_code=201, response_model=SubmitTaskResponse)
async def submit_task(req: SubmitTaskRequest) -> SubmitTaskResponse:
    # Idempotency check
    if req.idempotency_key in idempotency_map:
        existing_id = idempotency_map[req.idempotency_key]
        existing_state = reconstruct_state(existing_id)
        raise HTTPException(
            status_code=409,
            detail={"error": "Task already exists", "task_id": existing_id},
        )

    task_id = str(uuid.uuid4())
    idempotency_map[req.idempotency_key] = task_id

    append_event(
        task_id,
        EventType.TASK_CREATED,
        {"task_type": req.task_type, "payload": req.payload, "idempotency_key": req.idempotency_key},
    )

    await app.state.task_queue.put(task_id)

    state = reconstruct_state(task_id)
    return SubmitTaskResponse(
        task_id=task_id,
        status=state.status.value,
        created_at=state.created_at,
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")

    state = reconstruct_state(task_id)
    return TaskStatusResponse(
        task_id=state.task_id,
        status=state.status.value,
        attempts=state.attempts,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_task_events(task_id: str) -> list[EventResponse]:
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


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        workers=WORKER_COUNT,
        queued_tasks=app.state.task_queue.qsize(),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
