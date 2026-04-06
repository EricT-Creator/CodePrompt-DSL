"""Event-Sourced Task Queue with FastAPI, asyncio.Queue, idempotent endpoints, and event replay."""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─── Models ───────────────────────────────────────────────────────────────────

class TaskSubmitRequest(BaseModel):
    idempotency_key: str
    task_type: str
    payload: dict
    max_retries: int = 3
    retry_delay: float = 1.0


class TaskEvent(BaseModel):
    event_id: str
    task_id: str
    event_type: Literal[
        "TASK_SUBMITTED",
        "TASK_STARTED",
        "TASK_COMPLETED",
        "TASK_FAILED",
        "TASK_RETRY_SCHEDULED",
    ]
    timestamp: str
    payload: dict


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    attempts: int
    result: Optional[dict] = None
    error: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    current_status: str
    events: List[TaskEvent]
    attempt_count: int


class EventReplayResponse(BaseModel):
    task_id: str
    current_state: dict
    event_log: List[TaskEvent]


class HealthResponse(BaseModel):
    status: str
    queue_size: int
    total_tasks: int
    active_workers: int


# ─── Event Store (Append-Only) ────────────────────────────────────────────────

class EventStore:
    def __init__(self) -> None:
        self._events: List[TaskEvent] = []
        self._task_index: Dict[str, List[int]] = {}

    def append(self, event: TaskEvent) -> None:
        index = len(self._events)
        self._events.append(event)
        self._task_index.setdefault(event.task_id, []).append(index)

    def get_events_for_task(self, task_id: str) -> List[TaskEvent]:
        indices = self._task_index.get(task_id, [])
        return [self._events[i] for i in indices]

    def replay_to_state(self, task_id: str) -> dict:
        events = self.get_events_for_task(task_id)
        state: Dict[str, Any] = {
            "status": "unknown",
            "attempts": 0,
            "task_type": None,
            "result": None,
            "last_error": None,
            "created_at": None,
        }
        for event in events:
            if event.event_type == "TASK_SUBMITTED":
                state["status"] = "pending"
                state["task_type"] = event.payload.get("task_type")
                state["created_at"] = event.timestamp
            elif event.event_type == "TASK_STARTED":
                state["status"] = "processing"
                state["attempts"] += 1
            elif event.event_type == "TASK_COMPLETED":
                state["status"] = "completed"
                state["result"] = event.payload.get("result")
            elif event.event_type == "TASK_FAILED":
                if not event.payload.get("will_retry"):
                    state["status"] = "failed"
                state["last_error"] = event.payload.get("error")
            elif event.event_type == "TASK_RETRY_SCHEDULED":
                state["status"] = "pending"
        return state

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def total_tasks(self) -> int:
        return len(self._task_index)


# ─── Task Registry (for idempotency + metadata) ──────────────────────────────

class TaskRegistry:
    def __init__(self) -> None:
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> task_id
        self._task_meta: Dict[str, dict] = {}  # task_id -> {max_retries, retry_delay, task_type}

    def has_idempotency_key(self, key: str) -> bool:
        return key in self._idempotency_map

    def get_task_id_by_key(self, key: str) -> str:
        return self._idempotency_map[key]

    def register(self, idempotency_key: str, task_id: str, meta: dict) -> None:
        self._idempotency_map[idempotency_key] = task_id
        self._task_meta[task_id] = meta

    def get_meta(self, task_id: str) -> dict:
        return self._task_meta.get(task_id, {})


# ─── Task Handlers (simulated work) ──────────────────────────────────────────

async def execute_task(task_type: str, payload: dict) -> dict:
    """Simulate task execution. Randomly fails ~30% of the time for demo."""
    await asyncio.sleep(0.1 + random.random() * 0.3)
    if random.random() < 0.3:
        raise RuntimeError(f"Simulated failure for task type '{task_type}'")
    return {"processed": True, "task_type": task_type, "items": len(payload)}


# ─── Worker ───────────────────────────────────────────────────────────────────

class TaskWorker:
    def __init__(
        self,
        queue: asyncio.Queue[str],
        event_store: EventStore,
        registry: TaskRegistry,
        worker_id: str,
    ) -> None:
        self.queue = queue
        self.event_store = event_store
        self.registry = registry
        self.worker_id = worker_id
        self.running = False

    async def start(self) -> None:
        self.running = True
        while self.running:
            try:
                task_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            await self._process(task_id)
            self.queue.task_done()

    async def _process(self, task_id: str) -> None:
        meta = self.registry.get_meta(task_id)
        state = self.event_store.replay_to_state(task_id)

        # Emit TASK_STARTED
        self.event_store.append(
            TaskEvent(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="TASK_STARTED",
                timestamp=datetime.utcnow().isoformat(),
                payload={"worker_id": self.worker_id},
            )
        )

        try:
            result = await execute_task(
                meta.get("task_type", "unknown"),
                meta.get("payload", {}),
            )
            self.event_store.append(
                TaskEvent(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="TASK_COMPLETED",
                    timestamp=datetime.utcnow().isoformat(),
                    payload={"result": result},
                )
            )
        except Exception as exc:
            current_state = self.event_store.replay_to_state(task_id)
            attempts = current_state["attempts"]
            max_retries = meta.get("max_retries", 3)
            will_retry = attempts < max_retries

            self.event_store.append(
                TaskEvent(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="TASK_FAILED",
                    timestamp=datetime.utcnow().isoformat(),
                    payload={"error": str(exc), "will_retry": will_retry},
                )
            )

            if will_retry:
                asyncio.create_task(
                    self._schedule_retry(task_id, attempts, meta.get("retry_delay", 1.0))
                )

    async def _schedule_retry(self, task_id: str, attempt: int, base_delay: float) -> None:
        delay = base_delay * (2 ** (attempt - 1))
        jitter = delay * 0.25 * (2 * random.random() - 1)
        actual_delay = max(0.1, delay + jitter)

        await asyncio.sleep(actual_delay)

        self.event_store.append(
            TaskEvent(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="TASK_RETRY_SCHEDULED",
                timestamp=datetime.utcnow().isoformat(),
                payload={"attempt_number": attempt + 1},
            )
        )

        await self.queue.put(task_id)


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(title="Event-Sourced Task Queue")

event_store = EventStore()
task_registry = TaskRegistry()
task_queue: asyncio.Queue[str] = asyncio.Queue()

NUM_WORKERS = 3
workers: List[TaskWorker] = []
worker_tasks: List[asyncio.Task[None]] = []


@app.on_event("startup")
async def startup() -> None:
    for i in range(NUM_WORKERS):
        worker = TaskWorker(task_queue, event_store, task_registry, f"worker-{i}")
        workers.append(worker)
        t = asyncio.create_task(worker.start())
        worker_tasks.append(t)


@app.on_event("shutdown")
async def shutdown() -> None:
    for w in workers:
        w.running = False
    for t in worker_tasks:
        t.cancel()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskSubmitRequest) -> TaskResponse:
    # Idempotency check
    if task_registry.has_idempotency_key(request.idempotency_key):
        existing_id = task_registry.get_task_id_by_key(request.idempotency_key)
        state = event_store.replay_to_state(existing_id)
        return TaskResponse(
            task_id=existing_id,
            status=state["status"],
            created_at=state.get("created_at", ""),
            attempts=state["attempts"],
            result=state.get("result"),
            error=state.get("last_error"),
        )

    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    task_registry.register(
        request.idempotency_key,
        task_id,
        {
            "task_type": request.task_type,
            "payload": request.payload,
            "max_retries": request.max_retries,
            "retry_delay": request.retry_delay,
        },
    )

    event_store.append(
        TaskEvent(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type="TASK_SUBMITTED",
            timestamp=now,
            payload={
                "idempotency_key": request.idempotency_key,
                "task_type": request.task_type,
                "initial_payload": request.payload,
            },
        )
    )

    await task_queue.put(task_id)

    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=now,
        attempts=0,
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    events = event_store.get_events_for_task(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")

    state = event_store.replay_to_state(task_id)
    return TaskStatusResponse(
        task_id=task_id,
        current_status=state["status"],
        events=events,
        attempt_count=state["attempts"],
    )


@app.get("/tasks/{task_id}/events", response_model=EventReplayResponse)
async def replay_events(task_id: str) -> EventReplayResponse:
    events = event_store.get_events_for_task(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")

    state = event_store.replay_to_state(task_id)
    return EventReplayResponse(
        task_id=task_id,
        current_state=state,
        event_log=events,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        queue_size=task_queue.qsize(),
        total_tasks=event_store.total_tasks,
        active_workers=len([w for w in workers if w.running]),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
