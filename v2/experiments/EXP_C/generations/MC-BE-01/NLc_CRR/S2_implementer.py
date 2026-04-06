from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Awaitable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ─── Event Store ───

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: str  # TaskSubmitted, TaskStarted, TaskCompleted, TaskFailed, TaskRetried
    payload: dict[str, Any]
    timestamp: str
    sequence_number: int


class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._index: dict[str, list[int]] = {}
        self._sequence_counters: dict[str, int] = {}

    def append(self, event: Event) -> None:
        self._events.append(event)
        if event.task_id not in self._index:
            self._index[event.task_id] = []
        self._index[event.task_id].append(len(self._events) - 1)

    def get_events_for_task(self, task_id: str) -> list[Event]:
        indices = self._index.get(task_id, [])
        return [self._events[i] for i in indices]

    def get_all_events(self) -> list[Event]:
        return self._events.copy()

    def next_sequence(self, task_id: str) -> int:
        seq = self._sequence_counters.get(task_id, 0) + 1
        self._sequence_counters[task_id] = seq
        return seq


# ─── Task Aggregate ───

@dataclass
class TaskAggregate:
    task_id: str
    idempotency_key: str
    task_type: str
    payload: dict[str, Any]
    status: str
    retry_count: int
    max_retries: int
    created_at: str
    updated_at: str


def reconstruct_task_state(events: list[Event]) -> TaskAggregate:
    if not events:
        raise ValueError("No events to reconstruct")

    first = events[0]
    task = TaskAggregate(
        task_id=first.task_id,
        idempotency_key=first.payload.get("idempotency_key", ""),
        task_type=first.payload.get("task_type", ""),
        payload=first.payload.get("payload", {}),
        status="pending",
        retry_count=0,
        max_retries=first.payload.get("max_retries", 3),
        created_at=first.timestamp,
        updated_at=first.timestamp,
    )

    for event in events[1:]:
        if event.event_type == "TaskStarted":
            task.status = "processing"
        elif event.event_type == "TaskCompleted":
            task.status = "completed"
        elif event.event_type == "TaskFailed":
            task.status = "failed"
        elif event.event_type == "TaskRetried":
            task.retry_count += 1
            task.status = "pending"
        task.updated_at = event.timestamp

    return task


# ─── Idempotency index ───

class IdempotencyIndex:
    def __init__(self) -> None:
        self._keys: dict[str, str] = {}  # idempotency_key -> task_id

    def has(self, key: str) -> bool:
        return key in self._keys

    def get_task_id(self, key: str) -> str | None:
        return self._keys.get(key)

    def register(self, key: str, task_id: str) -> None:
        self._keys[key] = task_id


# ─── Request / Response Models ───

class TaskSubmitRequest(BaseModel):
    task_type: str
    payload: dict[str, Any] = {}
    idempotency_key: str
    max_retries: int = 3


class TaskResponse(BaseModel):
    task_id: str
    status: str
    idempotency_key: str
    retry_count: int
    created_at: str
    updated_at: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    events: list[dict[str, Any]]
    current_state: dict[str, Any]


# ─── Task Handlers (simulated) ───

import random


async def default_handler(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.3:
        raise RuntimeError("Simulated task failure")
    return {"result": "success", "processed": payload}


HANDLERS: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    "default": default_handler,
}


# ─── Backoff ───

def calculate_backoff_delay(
    retry_count: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    delay = min(base_delay * (2 ** retry_count), max_delay)
    if jitter:
        delay = delay * (0.5 + random.random())
    return delay


# ─── Worker ───

class TaskWorker:
    def __init__(
        self,
        queue: asyncio.Queue[str],
        event_store: EventStore,
        idempotency_index: IdempotencyIndex,
        task_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]],
        max_concurrent: int = 3,
    ) -> None:
        self.queue = queue
        self.event_store = event_store
        self.idempotency_index = idempotency_index
        self.task_handlers = task_handlers
        self.max_concurrent = max_concurrent
        self._shutdown = False
        self._workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        self._workers = [
            asyncio.create_task(self._worker_loop())
            for _ in range(self.max_concurrent)
        ]

    async def stop(self) -> None:
        self._shutdown = True
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def _worker_loop(self) -> None:
        while not self._shutdown:
            try:
                task_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_task(task_id)
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue

    async def _process_task(self, task_id: str) -> None:
        events = self.event_store.get_events_for_task(task_id)
        if not events:
            return
        task = reconstruct_task_state(events)
        if task.status in ("completed", "failed"):
            return

        now = datetime.now(timezone.utc).isoformat()

        # Record TaskStarted
        self.event_store.append(Event(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type="TaskStarted",
            payload={},
            timestamp=now,
            sequence_number=self.event_store.next_sequence(task_id),
        ))

        handler = self.task_handlers.get(task.task_type, self.task_handlers.get("default"))
        if handler is None:
            self.event_store.append(Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="TaskFailed",
                payload={"error": f"No handler for task type: {task.task_type}"},
                timestamp=datetime.now(timezone.utc).isoformat(),
                sequence_number=self.event_store.next_sequence(task_id),
            ))
            return

        retry_count = 0
        max_retries = task.max_retries

        while retry_count <= max_retries:
            try:
                result = await handler(task.payload)
                self.event_store.append(Event(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="TaskCompleted",
                    payload={"result": result, "retry_count": retry_count},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    sequence_number=self.event_store.next_sequence(task_id),
                ))
                return
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    self.event_store.append(Event(
                        event_id=str(uuid.uuid4()),
                        task_id=task_id,
                        event_type="TaskFailed",
                        payload={"error": str(e), "final_retry": True},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        sequence_number=self.event_store.next_sequence(task_id),
                    ))
                    return
                self.event_store.append(Event(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="TaskRetried",
                    payload={"error": str(e), "retry_count": retry_count},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    sequence_number=self.event_store.next_sequence(task_id),
                ))
                delay = calculate_backoff_delay(retry_count)
                await asyncio.sleep(delay)


# ─── Global instances ───

event_store = EventStore()
idempotency_index = IdempotencyIndex()
task_queue: asyncio.Queue[str] = asyncio.Queue()

app = FastAPI(title="Event-Sourced Task Queue")


# ─── Lifecycle ───

@app.on_event("startup")
async def startup_event() -> None:
    worker = TaskWorker(
        queue=task_queue,
        event_store=event_store,
        idempotency_index=idempotency_index,
        task_handlers=HANDLERS,
        max_concurrent=3,
    )
    await worker.start()
    app.state.worker = worker


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if hasattr(app.state, "worker"):
        await app.state.worker.stop()


# ─── Endpoints ───

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskSubmitRequest) -> TaskResponse:
    # Idempotency check
    existing_task_id = idempotency_index.get_task_id(request.idempotency_key)
    if existing_task_id:
        events = event_store.get_events_for_task(existing_task_id)
        task = reconstruct_task_state(events)
        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            idempotency_key=task.idempotency_key,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    event = Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type="TaskSubmitted",
        payload={
            "task_type": request.task_type,
            "payload": request.payload,
            "idempotency_key": request.idempotency_key,
            "max_retries": request.max_retries,
        },
        timestamp=now,
        sequence_number=event_store.next_sequence(task_id),
    )
    event_store.append(event)
    idempotency_index.register(request.idempotency_key, task_id)

    await task_queue.put(task_id)

    return TaskResponse(
        task_id=task_id,
        status="pending",
        idempotency_key=request.idempotency_key,
        retry_count=0,
        created_at=now,
        updated_at=now,
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    events = event_store.get_events_for_task(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")

    task = reconstruct_task_state(events)
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        events=[asdict(e) for e in events],
        current_state={
            "task_type": task.task_type,
            "payload": task.payload,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
        },
    )


@app.post("/tasks/{task_id}/replay")
async def replay_task(task_id: str) -> dict[str, Any]:
    events = event_store.get_events_for_task(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")

    task = reconstruct_task_state(events)
    return {
        "task_id": task.task_id,
        "reconstructed_status": task.status,
        "event_count": len(events),
        "current_state": asdict(task),
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
