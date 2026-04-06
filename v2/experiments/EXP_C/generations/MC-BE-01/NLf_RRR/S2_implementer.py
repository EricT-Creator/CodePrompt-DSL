"""Event-Sourced Task Queue — FastAPI implementation."""

from __future__ import annotations

import asyncio
import math
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ─── Models ───────────────────────────────────────────────────


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


# ─── Event Store ──────────────────────────────────────────────


class Event:
    __slots__ = ("event_id", "task_id", "event_type", "timestamp", "data")

    def __init__(self, task_id: str, event_type: str, data: dict[str, Any]) -> None:
        self.event_id = str(uuid.uuid4())
        self.task_id = task_id
        self.event_type = event_type
        self.timestamp = datetime.now(timezone.utc)
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


event_store: list[Event] = []
task_event_index: dict[str, list[int]] = {}
idempotency_map: dict[str, str] = {}
task_configs: dict[str, dict[str, Any]] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()


def append_event(task_id: str, event_type: str, data: dict[str, Any]) -> Event:
    evt = Event(task_id, event_type, data)
    idx = len(event_store)
    event_store.append(evt)
    task_event_index.setdefault(task_id, []).append(idx)
    return evt


def derive_task_state(task_id: str) -> dict[str, Any]:
    indices = task_event_index.get(task_id, [])
    status = "unknown"
    payload: dict[str, Any] = {}
    created_at = ""
    retry_count = 0
    last_error: str | None = None

    for idx in indices:
        evt = event_store[idx]
        if evt.event_type == "TASK_CREATED":
            status = "pending"
            payload = evt.data.get("payload", {})
            created_at = evt.timestamp.isoformat()
        elif evt.event_type == "TASK_QUEUED":
            status = "queued"
        elif evt.event_type == "TASK_STARTED":
            status = "running"
        elif evt.event_type == "TASK_SUCCEEDED":
            status = "completed"
        elif evt.event_type == "TASK_FAILED":
            last_error = evt.data.get("error")
            retry_count = evt.data.get("attempt", retry_count)
        elif evt.event_type == "TASK_RETRY_SCHEDULED":
            status = "retrying"
        elif evt.event_type == "TASK_EXHAUSTED":
            status = "failed"

    return {
        "task_id": task_id,
        "status": status,
        "created_at": created_at,
        "payload": payload,
        "retry_count": retry_count,
        "last_error": last_error,
    }


# ─── Worker ───────────────────────────────────────────────────


async def worker() -> None:
    while True:
        task_id = await task_queue.get()
        cfg = task_configs.get(task_id, {})
        max_retries = cfg.get("max_retries", 3)
        backoff_base = cfg.get("backoff_base", 1.0)
        attempt = cfg.get("current_attempt", 1)

        append_event(task_id, "TASK_STARTED", {"attempt": attempt})

        # Simulate work
        await asyncio.sleep(random.uniform(0.1, 0.3))
        success = random.random() > 0.4

        if success:
            append_event(task_id, "TASK_SUCCEEDED", {"result": {"message": "done"}})
        else:
            error_msg = f"Simulated failure on attempt {attempt}"
            append_event(task_id, "TASK_FAILED", {"error": error_msg, "attempt": attempt})

            if attempt < max_retries:
                delay = min(backoff_base * (2 ** (attempt - 1)), 60.0)
                # Add jitter ±10%
                jitter = delay * random.uniform(-0.1, 0.1)
                delay = max(0, delay + jitter)
                append_event(task_id, "TASK_RETRY_SCHEDULED", {"next_attempt": attempt + 1, "delay": delay})
                task_configs[task_id]["current_attempt"] = attempt + 1
                await asyncio.sleep(delay)
                append_event(task_id, "TASK_QUEUED", {})
                await task_queue.put(task_id)
            else:
                append_event(task_id, "TASK_EXHAUSTED", {"total_attempts": attempt})

        task_queue.task_done()


# ─── App Lifecycle ────────────────────────────────────────────


worker_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    worker_task = asyncio.create_task(worker())
    yield
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Event-Sourced Task Queue", lifespan=lifespan)


# ─── Endpoints ────────────────────────────────────────────────


@app.post("/tasks", response_model=TaskResponse)
async def create_task(submission: TaskSubmission) -> TaskResponse:
    # Idempotency check
    if submission.idempotency_key in idempotency_map:
        existing_id = idempotency_map[submission.idempotency_key]
        state = derive_task_state(existing_id)
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

    state = derive_task_state(task_id)
    return TaskResponse(**state)


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    all_task_ids = list(task_event_index.keys())
    results = []
    for tid in all_task_ids:
        state = derive_task_state(tid)
        results.append(TaskResponse(**state))
    return results


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    state = derive_task_state(task_id)
    return TaskResponse(**state)


@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_task_events(task_id: str) -> list[EventResponse]:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    indices = task_event_index[task_id]
    events = []
    for idx in indices:
        evt = event_store[idx]
        events.append(EventResponse(**evt.to_dict()))
    return events


@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str) -> TaskResponse:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    state = derive_task_state(task_id)
    return TaskResponse(**state)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
