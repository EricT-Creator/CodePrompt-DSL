"""Event-Sourced Task Queue API — MC-BE-01 (H × RRR)"""

from __future__ import annotations

import asyncio
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── Event Types ──
EventType = Literal[
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "task_retrying",
    "task_exhausted",
]

# ── Event ──
@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: str
    data: dict[str, Any]

# ── Task State (reconstructed) ──
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

# ── Event Store ──
class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._task_index: dict[str, list[Event]] = {}
        self._task_payloads: dict[str, dict[str, Any]] = {}
        self._task_max_retries: dict[str, int] = {}

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
        retries = 0
        created_at = events[0].timestamp
        updated_at = events[-1].timestamp

        for ev in events:
            if ev.event_type == "task_created":
                status = "pending"
            elif ev.event_type == "task_started":
                status = "running"
            elif ev.event_type == "task_completed":
                status = "completed"
            elif ev.event_type == "task_failed":
                status = "failed"
            elif ev.event_type == "task_retrying":
                status = "pending"
                retries += 1
            elif ev.event_type == "task_exhausted":
                status = "exhausted"

        return TaskState(
            task_id=task_id,
            status=status,
            payload=self._task_payloads.get(task_id, {}),
            retries=retries,
            max_retries=self._task_max_retries.get(task_id, 3),
            events_count=len(events),
            created_at=created_at,
            updated_at=updated_at,
        )

    def all_task_ids(self) -> list[str]:
        return list(self._task_index.keys())

# ── Pydantic Models ──
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
    max_retries: int
    events_count: int
    created_at: str
    updated_at: str

class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    data: dict[str, Any]

# ── Application ──
app = FastAPI(title="Event-Sourced Task Queue")
store = EventStore()
idempotency_map: dict[str, str] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()
worker_task: asyncio.Task[None] | None = None

# ── Helpers ──
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

# ── Worker ──
async def process_task(task_id: str) -> None:
    """Simulate task processing with random success/failure."""
    store.append(make_event(task_id, "task_started"))

    # Simulate work
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Random success (70%) or failure (30%)
    if random.random() < 0.7:
        store.append(make_event(task_id, "task_completed", {"result": "success"}))
    else:
        state = store.reconstruct(task_id)
        if state is None:
            return
        error_msg = f"Simulated failure at {now_iso()}"
        store.append(make_event(task_id, "task_failed", {"error": error_msg}))

        if state.retries < state.max_retries:
            store.append(make_event(task_id, "task_retrying", {"retry": state.retries + 1}))
            # Exponential backoff with jitter
            delay = min(1.0 * (2 ** state.retries) + random.uniform(0, 0.5), 30.0)
            asyncio.create_task(retry_after_delay(task_id, delay))
        else:
            store.append(make_event(task_id, "task_exhausted", {"total_retries": state.retries}))

async def retry_after_delay(task_id: str, delay: float) -> None:
    await asyncio.sleep(delay)
    await task_queue.put(task_id)

async def worker_loop() -> None:
    while True:
        task_id = await task_queue.get()
        try:
            await process_task(task_id)
        except Exception:
            pass
        finally:
            task_queue.task_done()

# ── Lifecycle ──
@app.on_event("startup")
async def startup() -> None:
    global worker_task
    worker_task = asyncio.create_task(worker_loop())

@app.on_event("shutdown")
async def shutdown() -> None:
    global worker_task
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

# ── Routes ──
@app.post("/tasks", response_model=TaskResponse)
async def create_task(req: CreateTaskRequest) -> TaskResponse:
    # Idempotency check
    if req.idempotency_key in idempotency_map:
        existing_id = idempotency_map[req.idempotency_key]
        state = store.reconstruct(existing_id)
        if state:
            return TaskResponse(
                task_id=state.task_id,
                status=state.status,
                created_at=state.created_at,
            )

    task_id = str(uuid.uuid4())
    idempotency_map[req.idempotency_key] = task_id
    store._task_payloads[task_id] = req.payload
    store._task_max_retries[task_id] = req.max_retries

    event = make_event(task_id, "task_created", {"payload": req.payload, "max_retries": req.max_retries})
    store.append(event)

    await task_queue.put(task_id)

    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=event.timestamp,
    )

@app.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str) -> TaskDetailResponse:
    state = store.reconstruct(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetailResponse(
        task_id=state.task_id,
        status=state.status,
        payload=state.payload,
        retries=state.retries,
        max_retries=state.max_retries,
        events_count=state.events_count,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )

@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_task_events(task_id: str) -> list[EventResponse]:
    events = store.get_events(task_id)
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
    for tid in store.all_task_ids():
        state = store.reconstruct(tid)
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
                max_retries=state.max_retries,
                events_count=state.events_count,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )
        )
    return results
