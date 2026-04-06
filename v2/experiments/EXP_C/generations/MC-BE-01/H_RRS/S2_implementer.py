"""Event-Sourced Task Queue API — MC-BE-01 (H × RRS)"""
from __future__ import annotations

import asyncio
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─── Event types ───
EventType = Literal[
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "task_retrying",
    "task_exhausted",
]


@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: str
    data: dict[str, Any]


@dataclass
class TaskState:
    task_id: str
    status: str
    payload: dict[str, Any]
    retries: int
    max_retries: int
    events_count: int
    created_at: str
    updated_at: str


# ─── Append-only Event Store ───
class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._task_index: dict[str, list[Event]] = {}

    def append(self, event: Event) -> None:
        self._events.append(event)
        if event.task_id not in self._task_index:
            self._task_index[event.task_id] = []
        self._task_index[event.task_id].append(event)

    def get_events(self, task_id: str) -> list[Event]:
        return self._task_index.get(task_id, [])

    def reconstruct(self, task_id: str) -> TaskState | None:
        events = self.get_events(task_id)
        if not events:
            return None
        status = "unknown"
        payload: dict[str, Any] = {}
        retries = 0
        max_retries = 3
        created_at = ""
        updated_at = ""
        for ev in events:
            updated_at = ev.timestamp
            if ev.event_type == "task_created":
                status = "pending"
                payload = ev.data.get("payload", {})
                max_retries = ev.data.get("max_retries", 3)
                created_at = ev.timestamp
            elif ev.event_type == "task_started":
                status = "running"
            elif ev.event_type == "task_completed":
                status = "completed"
            elif ev.event_type == "task_failed":
                status = "failed"
            elif ev.event_type == "task_retrying":
                status = "pending"
                retries = ev.data.get("retry_count", retries + 1)
            elif ev.event_type == "task_exhausted":
                status = "exhausted"
        return TaskState(
            task_id=task_id,
            status=status,
            payload=payload,
            retries=retries,
            max_retries=max_retries,
            events_count=len(events),
            created_at=created_at,
            updated_at=updated_at,
        )

    def all_task_ids(self) -> list[str]:
        return list(self._task_index.keys())


# ─── Globals ───
event_store = EventStore()
idempotency_map: dict[str, str] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()

BASE_DELAY = 1.0
MAX_DELAY = 30.0


# ─── Helper ───
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(task_id: str, event_type: EventType, data: dict[str, Any] | None = None) -> Event:
    return Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=now_iso(),
        data=data or {},
    )


# ─── Pydantic models ───
class CreateTaskRequest(BaseModel):
    idempotency_key: str
    payload: dict[str, Any] = {}
    max_retries: int = 3


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class TaskDetailResponse(BaseModel):
    task_id: str
    status: str
    payload: dict[str, Any]
    retries: int
    events_count: int
    created_at: str
    updated_at: str


class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    data: dict[str, Any]


# ─── Worker ───
async def worker() -> None:
    while True:
        task_id = await task_queue.get()
        try:
            # Started
            event_store.append(make_event(task_id, "task_started"))
            # Simulate work
            await asyncio.sleep(random.uniform(0.1, 0.5))
            # Random success / failure
            if random.random() < 0.7:
                event_store.append(make_event(task_id, "task_completed"))
            else:
                state = event_store.reconstruct(task_id)
                if state is None:
                    continue
                event_store.append(make_event(task_id, "task_failed", {"error": "Random failure"}))
                if state.retries < state.max_retries:
                    retry_count = state.retries + 1
                    event_store.append(
                        make_event(task_id, "task_retrying", {"retry_count": retry_count})
                    )
                    delay = min(BASE_DELAY * (2 ** state.retries) + random.uniform(0, 0.5), MAX_DELAY)
                    asyncio.create_task(_delayed_enqueue(task_id, delay))
                else:
                    event_store.append(make_event(task_id, "task_exhausted"))
        except Exception:
            pass
        finally:
            task_queue.task_done()


async def _delayed_enqueue(task_id: str, delay: float) -> None:
    await asyncio.sleep(delay)
    await task_queue.put(task_id)


# ─── FastAPI App ───
app = FastAPI(title="Event-Sourced Task Queue")
worker_task: asyncio.Task[None] | None = None


@app.on_event("startup")
async def startup() -> None:
    global worker_task
    worker_task = asyncio.create_task(worker())


@app.on_event("shutdown")
async def shutdown() -> None:
    if worker_task:
        worker_task.cancel()


# ─── Routes ───
@app.post("/tasks", response_model=TaskResponse)
async def create_task(req: CreateTaskRequest) -> TaskResponse:
    # Idempotency check
    if req.idempotency_key in idempotency_map:
        existing_id = idempotency_map[req.idempotency_key]
        state = event_store.reconstruct(existing_id)
        if state:
            return TaskResponse(task_id=state.task_id, status=state.status, created_at=state.created_at)

    task_id = str(uuid.uuid4())
    idempotency_map[req.idempotency_key] = task_id

    event = make_event(
        task_id,
        "task_created",
        {"payload": req.payload, "max_retries": req.max_retries},
    )
    event_store.append(event)
    await task_queue.put(task_id)

    return TaskResponse(task_id=task_id, status="pending", created_at=event.timestamp)


@app.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str) -> TaskDetailResponse:
    state = event_store.reconstruct(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetailResponse(
        task_id=state.task_id,
        status=state.status,
        payload=state.payload,
        retries=state.retries,
        events_count=state.events_count,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_task_events(task_id: str) -> list[EventResponse]:
    events = event_store.get_events(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        EventResponse(
            event_id=e.event_id,
            task_id=e.task_id,
            event_type=e.event_type,
            timestamp=e.timestamp,
            data=e.data,
        )
        for e in events
    ]


@app.get("/tasks", response_model=list[TaskDetailResponse])
async def list_tasks(status: str | None = None) -> list[TaskDetailResponse]:
    results: list[TaskDetailResponse] = []
    for tid in event_store.all_task_ids():
        state = event_store.reconstruct(tid)
        if state is None:
            continue
        if status and state.status != status:
            continue
        results.append(
            TaskDetailResponse(
                task_id=state.task_id,
                status=state.status,
                payload=state.payload,
                retries=state.retries,
                events_count=state.events_count,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )
        )
    return results
