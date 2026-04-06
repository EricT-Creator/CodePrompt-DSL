"""Event-Sourced Task Queue API — MC-BE-01 (H × RRC, S2 Implementer)"""

from __future__ import annotations

import asyncio
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─── Event Store ───

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
        return list(self._task_index.get(task_id, []))

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


# ─── Request / Response Models ───


class CreateTaskRequest(BaseModel):
    idempotency_key: str
    payload: dict[str, Any] = {}
    max_retries: int = 3


class CreateTaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class TaskStatusResponse(BaseModel):
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


# ─── Application ───

app = FastAPI(title="Event-Sourced Task Queue")

event_store = EventStore()
idempotency_map: dict[str, str] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()
task_meta: dict[str, dict[str, Any]] = {}
worker_task: asyncio.Task[None] | None = None

BASE_DELAY = 1.0
MAX_DELAY = 30.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_event(task_id: str, event_type: EventType, data: dict[str, Any] | None = None) -> Event:
    return Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=_now_iso(),
        data=data or {},
    )


# ─── Worker ───


async def _process_task(task_id: str) -> None:
    """Simulate processing a task."""
    event_store.append(_make_event(task_id, "task_started"))
    await asyncio.sleep(random.uniform(0.1, 0.5))

    if random.random() < 0.3:
        event_store.append(
            _make_event(task_id, "task_failed", {"error": "Simulated failure"})
        )
        state = event_store.reconstruct(task_id)
        if state is None:
            return
        max_retries = task_meta.get(task_id, {}).get("max_retries", 3)
        if state.retries < max_retries:
            retry_count = state.retries + 1
            event_store.append(
                _make_event(task_id, "task_retrying", {"retry_count": retry_count})
            )
            delay = min(BASE_DELAY * (2 ** state.retries) + random.uniform(0, 0.5), MAX_DELAY)
            asyncio.create_task(_schedule_retry(task_id, delay))
        else:
            event_store.append(_make_event(task_id, "task_exhausted"))
    else:
        event_store.append(
            _make_event(task_id, "task_completed", {"result": "success"})
        )


async def _schedule_retry(task_id: str, delay: float) -> None:
    await asyncio.sleep(delay)
    await task_queue.put(task_id)


async def _worker() -> None:
    while True:
        task_id = await task_queue.get()
        try:
            await _process_task(task_id)
        except Exception:
            pass
        finally:
            task_queue.task_done()


@app.on_event("startup")
async def startup() -> None:
    global worker_task
    worker_task = asyncio.create_task(_worker())


@app.on_event("shutdown")
async def shutdown() -> None:
    global worker_task
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


# ─── Endpoints ───


@app.post("/tasks", response_model=CreateTaskResponse)
async def create_task(req: CreateTaskRequest) -> CreateTaskResponse:
    if req.idempotency_key in idempotency_map:
        existing_id = idempotency_map[req.idempotency_key]
        state = event_store.reconstruct(existing_id)
        if state:
            return CreateTaskResponse(
                task_id=state.task_id,
                status=state.status,
                created_at=state.created_at,
            )

    task_id = str(uuid.uuid4())
    idempotency_map[req.idempotency_key] = task_id
    task_meta[task_id] = {"max_retries": req.max_retries}

    now = _now_iso()
    event_store.append(
        _make_event(
            task_id,
            "task_created",
            {"payload": req.payload, "max_retries": req.max_retries},
        )
    )
    await task_queue.put(task_id)

    return CreateTaskResponse(task_id=task_id, status="pending", created_at=now)


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str) -> TaskStatusResponse:
    state = event_store.reconstruct(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
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


@app.get("/tasks", response_model=list[TaskStatusResponse])
async def list_tasks(status: str | None = None) -> list[TaskStatusResponse]:
    results: list[TaskStatusResponse] = []
    for tid in event_store.all_task_ids():
        state = event_store.reconstruct(tid)
        if state is None:
            continue
        if status and state.status != status:
            continue
        results.append(
            TaskStatusResponse(
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
