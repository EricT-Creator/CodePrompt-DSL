"""Event-Sourced Task Queue with FastAPI."""

from __future__ import annotations

import asyncio
import math
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ── Data Models ──────────────────────────────────────────────────────────────


class Event:
    __slots__ = ("event_id", "task_id", "event_type", "timestamp", "data")

    def __init__(self, task_id: str, event_type: str, data: dict[str, Any] | None = None) -> None:
        self.event_id: str = str(uuid.uuid4())
        self.task_id: str = task_id
        self.event_type: str = event_type
        self.timestamp: datetime = datetime.now(timezone.utc)
        self.data: dict[str, Any] = data or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# ── Global Stores ────────────────────────────────────────────────────────────

event_store: list[Event] = []
task_index: dict[str, list[int]] = {}
idempotency_map: dict[str, str] = {}
task_configs: dict[str, dict[str, Any]] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()


# ── Pydantic Models ──────────────────────────────────────────────────────────


class TaskSubmission(BaseModel):
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3
    backoff_base: float = 1.0


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    payload: dict[str, Any]
    retry_count: int
    last_error: str | None


class EventResponse(BaseModel):
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    data: dict[str, Any]


# ── Event Store Helpers ──────────────────────────────────────────────────────


def append_event(task_id: str, event_type: str, data: dict[str, Any] | None = None) -> Event:
    event = Event(task_id, event_type, data)
    idx = len(event_store)
    event_store.append(event)
    task_index.setdefault(task_id, []).append(idx)
    return event


def get_task_events(task_id: str) -> list[Event]:
    indices = task_index.get(task_id, [])
    return [event_store[i] for i in indices]


def derive_state(task_id: str) -> dict[str, Any]:
    events = get_task_events(task_id)
    if not events:
        raise KeyError(f"No events for task {task_id}")

    status = "pending"
    created_at = ""
    payload: dict[str, Any] = {}
    retry_count = 0
    last_error: str | None = None

    for ev in events:
        if ev.event_type == "TASK_CREATED":
            status = "pending"
            created_at = ev.timestamp.isoformat()
            payload = ev.data.get("payload", {})
        elif ev.event_type == "TASK_QUEUED":
            status = "queued"
        elif ev.event_type == "TASK_STARTED":
            status = "running"
        elif ev.event_type == "TASK_SUCCEEDED":
            status = "completed"
        elif ev.event_type == "TASK_FAILED":
            last_error = ev.data.get("error")
            retry_count = ev.data.get("attempt", retry_count)
        elif ev.event_type == "TASK_RETRY_SCHEDULED":
            status = "retrying"
        elif ev.event_type == "TASK_EXHAUSTED":
            status = "failed"

    return {
        "task_id": task_id,
        "status": status,
        "created_at": created_at,
        "payload": payload,
        "retry_count": retry_count,
        "last_error": last_error,
    }


# ── Worker ───────────────────────────────────────────────────────────────────


async def worker_loop() -> None:
    while True:
        task_id = await task_queue.get()
        config = task_configs.get(task_id, {})
        max_retries: int = config.get("max_retries", 3)
        backoff_base: float = config.get("backoff_base", 1.0)
        attempt: int = config.get("current_attempt", 1)

        append_event(task_id, "TASK_STARTED", {"attempt": attempt})

        # Simulate work: 60% success rate
        await asyncio.sleep(0.1)
        success = random.random() < 0.6

        if success:
            append_event(task_id, "TASK_SUCCEEDED", {"result": {"message": "Task completed"}})
        else:
            error_msg = f"Simulated failure on attempt {attempt}"
            append_event(task_id, "TASK_FAILED", {"error": error_msg, "attempt": attempt})

            if attempt < max_retries:
                delay = min(backoff_base * (2 ** (attempt - 1)), 60.0)
                # Add jitter ±10%
                jitter = delay * 0.1 * (random.random() * 2 - 1)
                delay += jitter
                append_event(task_id, "TASK_RETRY_SCHEDULED", {
                    "next_attempt": attempt + 1,
                    "delay": round(delay, 2),
                })
                task_configs[task_id]["current_attempt"] = attempt + 1
                await asyncio.sleep(delay)
                append_event(task_id, "TASK_QUEUED", {})
                await task_queue.put(task_id)
            else:
                append_event(task_id, "TASK_EXHAUSTED", {"total_attempts": attempt})

        task_queue.task_done()


# ── App Lifecycle ────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Event-Sourced Task Queue", lifespan=lifespan)


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/tasks", response_model=TaskResponse)
async def submit_task(submission: TaskSubmission) -> TaskResponse:
    # Idempotency check
    if submission.idempotency_key in idempotency_map:
        existing_id = idempotency_map[submission.idempotency_key]
        state = derive_state(existing_id)
        return TaskResponse(**state)

    task_id = str(uuid.uuid4())
    idempotency_map[submission.idempotency_key] = task_id

    task_configs[task_id] = {
        "max_retries": submission.max_retries,
        "backoff_base": submission.backoff_base,
        "current_attempt": 1,
    }

    append_event(task_id, "TASK_CREATED", {
        "payload": submission.payload,
        "max_retries": submission.max_retries,
        "backoff_base": submission.backoff_base,
    })
    append_event(task_id, "TASK_QUEUED", {})

    await task_queue.put(task_id)

    state = derive_state(task_id)
    return TaskResponse(**state)


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    all_task_ids = list(task_index.keys())
    results: list[TaskResponse] = []
    for tid in all_task_ids:
        state = derive_state(tid)
        results.append(TaskResponse(**state))
    return results


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    if task_id not in task_index:
        raise HTTPException(status_code=404, detail="Task not found")
    state = derive_state(task_id)
    return TaskResponse(**state)


@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_task_events_endpoint(task_id: str) -> list[EventResponse]:
    if task_id not in task_index:
        raise HTTPException(status_code=404, detail="Task not found")
    events = get_task_events(task_id)
    return [EventResponse(**e.to_dict()) for e in events]


@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str) -> TaskResponse:
    if task_id not in task_index:
        raise HTTPException(status_code=404, detail="Task not found")
    state = derive_state(task_id)
    return TaskResponse(**state)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
