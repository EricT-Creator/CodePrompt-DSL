## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, HTTPException, status` and Python standard library modules.
- C2 (stdlib + fastapi only): PASS — Imports are limited to stdlib (`asyncio`, `random`, `uuid`, `contextlib`, `dataclasses`, `datetime`, `enum`, `typing`) plus `fastapi` and `pydantic` (bundled with fastapi). `uvicorn` imported only in `__main__`.
- C3 (asyncio.Queue, no Celery): PASS — `self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)` is the sole queuing mechanism; no Celery or RQ imported.
- C4 (Append-only event store): FAIL — The `retry_task` endpoint directly mutates `task.status`, `task.current_attempt`, `task.last_error` on the `TaskState` object without appending a corresponding event to the event store. The worker's `_worker` method also directly mutates `task.status`, `task.result`, etc. in addition to emitting events. The event store itself (`self.event_store.append(event)`) is append-only, but task state should be derived from events rather than independently mutated.
- C5 (Idempotent endpoints): FAIL — `POST /tasks/{task_id}/retry` lacks idempotency protection: repeated calls increment `current_attempt` and re-enqueue the task each time. `POST /tasks` is correctly idempotent via `idempotency_key`.
- C6 (Code only): PASS — File contains only executable code.

## Functionality Assessment (0-5)
Score: 4 — Comprehensive event-sourced task queue with worker pool, exponential backoff with jitter, event replay, metrics endpoint, and idempotent task creation. The retry endpoint and direct state mutation are minor functional gaps.

## Corrected Code
```py
"""
MC-BE-01: FastAPI Event-Sourced Task Queue
Engineering Constraints: Python + FastAPI. stdlib + fastapi + uvicorn only.
asyncio.Queue only, no Celery/RQ. Append-only list event store, no dict overwrite.
All endpoints idempotent. Code only.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel


# ── Domain Models ───────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"
    TASK_RETRY_STARTED = "task_retry_started"
    TASK_MANUAL_RETRY = "task_manual_retry"


@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: datetime
    sequence_number: int
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Request / Response Models ───────────────────────────────────────────


class TaskCreateRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any] = {}
    idempotency_key: str
    max_retries: int = 3
    initial_backoff_ms: int = 1000


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    updated_at: str
    current_attempt: int
    last_error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]
    sequence_number: int


class ReplayRequest(BaseModel):
    up_to_sequence: Optional[int] = None


class RetryRequest(BaseModel):
    idempotency_key: str


class MetricsResponse(BaseModel):
    total_tasks: int
    total_events: int
    tasks_by_status: Dict[str, int]
    queue_size: int
    workers_active: int


# ── Task State (derived from events) ────────────────────────────────────


@dataclass
class TaskState:
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    payload: Dict[str, Any]
    current_attempt: int = 1
    max_retries: int = 3
    initial_backoff_ms: int = 1000
    last_error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None


# ── Event Store & Queue System ──────────────────────────────────────────


class TaskQueueSystem:
    def __init__(self, max_workers: int = 5) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self.workers: List[asyncio.Task[None]] = []
        self.event_store: List[Event] = []
        self.idempotency_map: Dict[str, str] = {}
        self.retry_idempotency: Dict[str, bool] = {}
        self.max_workers = max_workers
        self._sequence_counter = 0
        self._running = False
        self._task_meta: Dict[str, Dict[str, Any]] = {}

    # ── Event helpers ────────────────────────────────────────────────

    def _next_seq(self) -> int:
        self._sequence_counter += 1
        return self._sequence_counter

    def emit_event(self, task_id: str, event_type: EventType, payload: Dict[str, Any]) -> Event:
        event = Event(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            sequence_number=self._next_seq(),
            payload=payload,
        )
        self.event_store.append(event)
        return event

    def get_events_for_task(self, task_id: str) -> List[Event]:
        return [e for e in self.event_store if e.task_id == task_id]

    # ── Rebuild state from events ────────────────────────────────────

    def rebuild_task_state(self, task_id: str, up_to_sequence: Optional[int] = None) -> Optional[TaskState]:
        events = self.get_events_for_task(task_id)
        if not events:
            return None

        if up_to_sequence is not None:
            events = [e for e in events if e.sequence_number <= up_to_sequence]

        task_state: Optional[TaskState] = None
        for evt in events:
            if evt.event_type == EventType.TASK_CREATED:
                meta = self._task_meta.get(task_id, {})
                task_state = TaskState(
                    task_id=task_id,
                    task_type=evt.payload.get("task_type", ""),
                    status=TaskStatus.PENDING,
                    created_at=evt.timestamp,
                    updated_at=evt.timestamp,
                    payload=evt.payload.get("payload", {}),
                    max_retries=meta.get("max_retries", 3),
                    initial_backoff_ms=meta.get("initial_backoff_ms", 1000),
                    idempotency_key=meta.get("idempotency_key"),
                )
            elif task_state is not None:
                if evt.event_type == EventType.TASK_STARTED:
                    task_state.status = TaskStatus.PROCESSING
                    task_state.current_attempt = evt.payload.get("attempt", task_state.current_attempt)
                    task_state.updated_at = evt.timestamp
                elif evt.event_type == EventType.TASK_COMPLETED:
                    task_state.status = TaskStatus.COMPLETED
                    task_state.result = evt.payload.get("result")
                    task_state.updated_at = evt.timestamp
                elif evt.event_type == EventType.TASK_FAILED:
                    task_state.status = TaskStatus.FAILED
                    task_state.last_error = evt.payload.get("error")
                    task_state.current_attempt = evt.payload.get("attempt", task_state.current_attempt)
                    task_state.updated_at = evt.timestamp
                elif evt.event_type == EventType.TASK_RETRY_SCHEDULED:
                    task_state.status = TaskStatus.RETRYING
                    task_state.updated_at = evt.timestamp
                elif evt.event_type == EventType.TASK_RETRY_STARTED:
                    task_state.status = TaskStatus.PROCESSING
                    task_state.current_attempt = evt.payload.get("attempt", task_state.current_attempt)
                    task_state.updated_at = evt.timestamp
                elif evt.event_type == EventType.TASK_MANUAL_RETRY:
                    task_state.status = TaskStatus.PENDING
                    task_state.current_attempt = evt.payload.get("attempt", task_state.current_attempt)
                    task_state.last_error = None
                    task_state.updated_at = evt.timestamp

        return task_state

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self.rebuild_task_state(task_id)

    # ── Task CRUD ────────────────────────────────────────────────────

    def create_task(self, req: TaskCreateRequest) -> TaskState:
        # Idempotency check
        if req.idempotency_key in self.idempotency_map:
            existing_id = self.idempotency_map[req.idempotency_key]
            state = self.rebuild_task_state(existing_id)
            if state:
                return state

        task_id = str(uuid.uuid4())
        self._task_meta[task_id] = {
            "max_retries": req.max_retries,
            "initial_backoff_ms": req.initial_backoff_ms,
            "idempotency_key": req.idempotency_key,
        }
        self.idempotency_map[req.idempotency_key] = task_id

        self.emit_event(task_id, EventType.TASK_CREATED, {"task_type": req.task_type, "payload": req.payload})
        return self.rebuild_task_state(task_id)  # type: ignore[return-value]

    # ── Backoff ──────────────────────────────────────────────────────

    @staticmethod
    def calculate_backoff(attempt: int, initial_backoff_ms: int) -> float:
        backoff_ms = initial_backoff_ms * (2 ** (attempt - 1))
        jitter = 1.0 + (random.random() * 0.5 - 0.25)
        backoff_ms *= jitter
        return min(backoff_ms, 30000) / 1000.0

    # ── Worker ───────────────────────────────────────────────────────

    async def _worker(self, worker_id: int) -> None:
        while self._running:
            try:
                task_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task = self.rebuild_task_state(task_id)
            if task is None:
                self.queue.task_done()
                continue

            self.emit_event(task_id, EventType.TASK_STARTED, {"worker_id": worker_id, "attempt": task.current_attempt})

            try:
                # Simulate work
                await asyncio.sleep(random.uniform(0.1, 0.5))
                if random.random() < 0.15:
                    raise RuntimeError("Simulated task failure")

                result = {"output": f"Processed {task.task_type}", "worker": worker_id}
                self.emit_event(task_id, EventType.TASK_COMPLETED, {"result": result})
            except Exception as exc:
                self.emit_event(task_id, EventType.TASK_FAILED, {"error": str(exc), "attempt": task.current_attempt})

                meta = self._task_meta.get(task_id, {})
                max_retries = meta.get("max_retries", 3)
                initial_backoff_ms = meta.get("initial_backoff_ms", 1000)

                if task.current_attempt < max_retries:
                    backoff = self.calculate_backoff(task.current_attempt, initial_backoff_ms)
                    self.emit_event(task_id, EventType.TASK_RETRY_SCHEDULED, {"backoff_seconds": backoff, "next_attempt": task.current_attempt + 1})

                    async def _retry(tid: str, delay: float, attempt: int) -> None:
                        await asyncio.sleep(delay)
                        current = self.rebuild_task_state(tid)
                        if current and current.status == TaskStatus.RETRYING:
                            self.emit_event(tid, EventType.TASK_RETRY_STARTED, {"attempt": attempt})
                            await self.queue.put(tid)

                    asyncio.create_task(_retry(task_id, backoff, task.current_attempt + 1))
            finally:
                self.queue.task_done()

    async def start(self) -> None:
        self._running = True
        for i in range(self.max_workers):
            self.workers.append(asyncio.create_task(self._worker(i)))

    async def stop(self) -> None:
        self._running = False
        for w in self.workers:
            w.cancel()
        self.workers.clear()


# ── App ─────────────────────────────────────────────────────────────────

system = TaskQueueSystem(max_workers=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await system.start()
    yield
    await system.stop()


app = FastAPI(title="Event-Sourced Task Queue", lifespan=lifespan)


def _task_to_response(t: TaskState) -> TaskResponse:
    return TaskResponse(
        task_id=t.task_id,
        status=t.status.value,
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
        current_attempt=t.current_attempt,
        last_error=t.last_error,
        result=t.result,
    )


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(req: TaskCreateRequest):
    task = system.create_task(req)
    if task.status == TaskStatus.PENDING:
        await system.queue.put(task.task_id)
    return _task_to_response(task)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = system.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@app.get("/tasks/{task_id}/events", response_model=List[EventResponse])
async def get_task_events(task_id: str):
    task = system.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    events = system.get_events_for_task(task_id)
    return [
        EventResponse(
            event_id=e.event_id,
            event_type=e.event_type.value,
            timestamp=e.timestamp.isoformat(),
            payload=e.payload,
            sequence_number=e.sequence_number,
        )
        for e in events
    ]


@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str, req: ReplayRequest):
    rebuilt = system.rebuild_task_state(task_id, req.up_to_sequence)
    if not rebuilt:
        raise HTTPException(status_code=404, detail="Task not found or no events")
    return _task_to_response(rebuilt)


@app.post("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str, req: RetryRequest):
    # Idempotency check for retry
    retry_key = f"retry:{task_id}:{req.idempotency_key}"
    if retry_key in system.retry_idempotency:
        task = system.get_task(task_id)
        if task:
            return _task_to_response(task)

    task = system.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in (TaskStatus.FAILED,):
        raise HTTPException(status_code=400, detail="Task is not in failed state")

    system.emit_event(task_id, EventType.TASK_MANUAL_RETRY, {"attempt": task.current_attempt + 1})
    system.retry_idempotency[retry_key] = True
    await system.queue.put(task_id)

    refreshed = system.get_task(task_id)
    return _task_to_response(refreshed)  # type: ignore[arg-type]


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    # Rebuild all task states from events
    task_ids = set()
    for e in system.event_store:
        task_ids.add(e.task_id)

    counts: Dict[str, int] = {}
    for tid in task_ids:
        state = system.rebuild_task_state(tid)
        if state:
            counts[state.status.value] = counts.get(state.status.value, 0) + 1

    return MetricsResponse(
        total_tasks=len(task_ids),
        total_events=len(system.event_store),
        tasks_by_status=counts,
        queue_size=system.queue.qsize(),
        workers_active=len([w for w in system.workers if not w.done()]),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```
