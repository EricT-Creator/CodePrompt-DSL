from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn


# ── Event types ─────────────────────────────────────────────────────────

class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"
    TASK_CANCELLED = "task_cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class Event:
    event_id: str
    event_type: EventType
    task_id: str
    timestamp: str
    data: dict[str, Any]
    version: int

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "version": self.version,
        }


# ── Event Store (append-only) ──────────────────────────────────────────

class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._index: dict[str, list[Event]] = {}

    def append(self, event: Event) -> None:
        self._events.append(event)
        self._index.setdefault(event.task_id, []).append(event)

    def get_events_by_task(self, task_id: str) -> list[Event]:
        return list(self._index.get(task_id, []))

    def replay(self, from_event_id: str | None = None, limit: int = 100, task_id: str | None = None) -> list[Event]:
        source = self._index.get(task_id, []) if task_id else self._events
        start = 0
        if from_event_id:
            for i, e in enumerate(source):
                if e.event_id == from_event_id:
                    start = i
                    break
        return source[start: start + limit]

    def get_current_state(self, task_id: str) -> dict[str, Any]:
        events = self.get_events_by_task(task_id)
        state: dict[str, Any] = {"status": TaskStatus.PENDING.value, "retry_count": 0}
        for ev in events:
            if ev.event_type == EventType.TASK_CREATED:
                state.update({"status": TaskStatus.PENDING.value, "name": ev.data.get("name"), "payload": ev.data.get("payload"), "created_at": ev.timestamp})
            elif ev.event_type == EventType.TASK_STARTED:
                state["status"] = TaskStatus.RUNNING.value
                state["started_at"] = ev.timestamp
            elif ev.event_type == EventType.TASK_COMPLETED:
                state["status"] = TaskStatus.COMPLETED.value
                state["result"] = ev.data.get("result")
                state["completed_at"] = ev.timestamp
            elif ev.event_type == EventType.TASK_FAILED:
                state["status"] = TaskStatus.FAILED.value
                state["error"] = ev.data.get("error")
            elif ev.event_type == EventType.TASK_RETRY_SCHEDULED:
                state["status"] = TaskStatus.RETRYING.value
                state["retry_count"] = ev.data.get("retry_count", state["retry_count"] + 1)
            elif ev.event_type == EventType.TASK_CANCELLED:
                state["status"] = TaskStatus.CANCELLED.value
        return state


# ── Idempotency registry ───────────────────────────────────────────────

class IdempotencyStore:
    def __init__(self) -> None:
        self._map: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._map.get(key)

    def set(self, key: str, task_id: str) -> None:
        self._map[key] = task_id


# ── Worker Manager ──────────────────────────────────────────────────────

class WorkerManager:
    def __init__(self, event_store: EventStore, num_workers: int = 3, max_retries: int = 3, backoff_ms: int = 1000) -> None:
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
        self.event_store = event_store
        self.num_workers = num_workers
        self.max_retries = max_retries
        self.backoff_ms = backoff_ms
        self._workers: list[asyncio.Task[None]] = []
        self._running = False

    async def start(self) -> None:
        self._running = True
        for i in range(self.num_workers):
            self._workers.append(asyncio.create_task(self._loop(f"w-{i}")))

    async def stop(self) -> None:
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    def _emit(self, etype: EventType, task_id: str, data: dict) -> Event:
        existing = self.event_store.get_events_by_task(task_id)
        ev = Event(
            event_id=str(uuid.uuid4()),
            event_type=etype,
            task_id=task_id,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
            version=len(existing) + 1,
        )
        self.event_store.append(ev)
        return ev

    async def _loop(self, wid: str) -> None:
        while self._running:
            try:
                item = await self.queue.get()
                await self._process(item, wid)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                self.queue.task_done()

    async def _process(self, item: dict, wid: str) -> None:
        task_id = item["task_id"]
        retry_count = item.get("retry_count", 0)
        self._emit(EventType.TASK_STARTED, task_id, {"worker_id": wid})
        try:
            await asyncio.sleep(random.uniform(0.1, 0.5))
            if random.random() < 0.15:
                raise RuntimeError("Simulated transient error")
            result = {"message": f"Task {task_id} done by {wid}"}
            self._emit(EventType.TASK_COMPLETED, task_id, {"result": result})
        except Exception as exc:
            if retry_count < self.max_retries:
                backoff = (self.backoff_ms / 1000) * (2 ** retry_count) * random.uniform(0.8, 1.2)
                self._emit(EventType.TASK_RETRY_SCHEDULED, task_id, {"retry_count": retry_count + 1, "backoff_seconds": backoff})
                asyncio.create_task(self._delayed_requeue(item, retry_count + 1, backoff))
            else:
                self._emit(EventType.TASK_FAILED, task_id, {"error": str(exc), "final_failure": True, "retry_count": retry_count})

    async def _delayed_requeue(self, item: dict, retry_count: int, delay: float) -> None:
        await asyncio.sleep(delay)
        await self.queue.put({**item, "retry_count": retry_count})

    @property
    def stats(self) -> dict:
        return {"queue_size": self.queue.qsize(), "workers": self.num_workers, "running": self._running}


# ── Pydantic models ────────────────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    name: str
    payload: dict = {}
    idempotency_key: str
    max_retries: int = 3
    retry_backoff_ms: int = 1000


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


# ── Application ─────────────────────────────────────────────────────────

app = FastAPI(title="Event-Sourced Task Queue")
event_store = EventStore()
idempotency = IdempotencyStore()
worker_mgr = WorkerManager(event_store)


@app.on_event("startup")
async def startup() -> None:
    await worker_mgr.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    await worker_mgr.stop()


@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(req: TaskCreateRequest) -> TaskResponse:
    existing_id = idempotency.get(req.idempotency_key)
    if existing_id:
        state = event_store.get_current_state(existing_id)
        return TaskResponse(task_id=existing_id, status=state.get("status", "pending"), created_at=state.get("created_at", ""))

    task_id = str(uuid.uuid4())
    idempotency.set(req.idempotency_key, task_id)
    now = datetime.utcnow().isoformat()
    ev = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TASK_CREATED,
        task_id=task_id,
        timestamp=now,
        data={"name": req.name, "payload": req.payload, "idempotency_key": req.idempotency_key},
        version=1,
    )
    event_store.append(ev)
    await worker_mgr.queue.put({"task_id": task_id, "retry_count": 0})
    return TaskResponse(task_id=task_id, status=TaskStatus.PENDING.value, created_at=now)


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    events = event_store.get_events_by_task(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    state = event_store.get_current_state(task_id)
    return {"task_id": task_id, "current_state": state, "events": [e.to_dict() for e in events]}


@app.delete("/tasks/{task_id}", status_code=204)
async def cancel_task(task_id: str) -> None:
    events = event_store.get_events_by_task(task_id)
    if not events:
        return
    state = event_store.get_current_state(task_id)
    if state.get("status") in (TaskStatus.CANCELLED.value, TaskStatus.COMPLETED.value):
        return
    ev = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TASK_CANCELLED,
        task_id=task_id,
        timestamp=datetime.utcnow().isoformat(),
        data={},
        version=len(events) + 1,
    )
    event_store.append(ev)


@app.get("/events/replay")
async def replay_events(
    from_event_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    task_id: str | None = Query(None),
) -> dict:
    events = event_store.replay(from_event_id=from_event_id, limit=limit, task_id=task_id)
    rebuilt: dict[str, Any] = {}
    for ev in events:
        rebuilt[ev.task_id] = event_store.get_current_state(ev.task_id)
    return {"events": [e.to_dict() for e in events], "rebuilt_states": rebuilt}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "queue": worker_mgr.stats, "total_events": len(event_store._events)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
