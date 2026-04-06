"""Event-Sourced Task Queue with FastAPI."""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ── Models ───────────────────────────────────────────────────────────────────


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


# ── Event Store ──────────────────────────────────────────────────────────────


class Event:
    __slots__ = ("event_id", "task_id", "event_type", "timestamp", "data")

    def __init__(
        self,
        task_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
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


event_store: list[Event] = []
task_event_index: dict[str, list[int]] = {}
idempotency_map: dict[str, str] = {}

task_configs: dict[str, dict[str, Any]] = {}

task_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


def append_event(event: Event) -> None:
    idx = len(event_store)
    event_store.append(event)
    task_event_index.setdefault(event.task_id, []).append(idx)


def get_task_events(task_id: str) -> list[Event]:
    indices = task_event_index.get(task_id, [])
    return [event_store[i] for i in indices]


def derive_task_state(task_id: str) -> dict[str, Any]:
    events = get_task_events(task_id)
    state: dict[str, Any] = {
        "task_id": task_id,
        "status": "unknown",
        "created_at": "",
        "payload": {},
        "retry_count": 0,
        "last_error": None,
        "max_retries": 3,
        "backoff_base": 1.0,
    }

    for ev in events:
        if ev.event_type == "TASK_CREATED":
            state["status"] = "pending"
            state["created_at"] = ev.timestamp.isoformat()
            state["payload"] = ev.data.get("payload", {})
            state["max_retries"] = ev.data.get("max_retries", 3)
            state["backoff_base"] = ev.data.get("backoff_base", 1.0)
        elif ev.event_type == "TASK_QUEUED":
            state["status"] = "queued"
        elif ev.event_type == "TASK_STARTED":
            state["status"] = "running"
        elif ev.event_type == "TASK_SUCCEEDED":
            state["status"] = "completed"
        elif ev.event_type == "TASK_FAILED":
            state["status"] = "failed"
            state["retry_count"] = ev.data.get("attempt", 0)
            state["last_error"] = ev.data.get("error", "")
        elif ev.event_type == "TASK_RETRY_SCHEDULED":
            state["status"] = "retrying"
            state["retry_count"] = ev.data.get("next_attempt", 0) - 1
        elif ev.event_type == "TASK_EXHAUSTED":
            state["status"] = "failed"
            state["retry_count"] = ev.data.get("total_attempts", 0)

    return state


# ── Worker ───────────────────────────────────────────────────────────────────


async def simulate_task_work() -> dict[str, Any]:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.4:
        raise RuntimeError("Simulated task failure")
    return {"result": "success", "value": random.randint(1, 100)}


async def worker_loop() -> None:
    while True:
        task_info = await task_queue.get()
        task_id: str = task_info["task_id"]
        attempt: int = task_info.get("attempt", 1)

        append_event(Event(task_id, "TASK_STARTED", {"attempt": attempt}))

        try:
            result = await simulate_task_work()
            append_event(Event(task_id, "TASK_SUCCEEDED", {"result": result}))
        except Exception as exc:
            append_event(
                Event(
                    task_id,
                    "TASK_FAILED",
                    {"error": str(exc), "attempt": attempt},
                )
            )

            cfg = task_configs.get(task_id, {})
            max_retries: int = cfg.get("max_retries", 3)
            backoff_base: float = cfg.get("backoff_base", 1.0)

            if attempt < max_retries:
                delay = min(backoff_base * (2 ** (attempt - 1)), 60.0)
                jitter = delay * random.uniform(-0.1, 0.1)
                delay = max(0, delay + jitter)

                append_event(
                    Event(
                        task_id,
                        "TASK_RETRY_SCHEDULED",
                        {"next_attempt": attempt + 1, "delay": delay},
                    )
                )
                await asyncio.sleep(delay)
                await task_queue.put(
                    {"task_id": task_id, "attempt": attempt + 1}
                )
            else:
                append_event(
                    Event(
                        task_id,
                        "TASK_EXHAUSTED",
                        {"total_attempts": attempt},
                    )
                )
        finally:
            task_queue.task_done()


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Event-Sourced Task Queue")

worker_task: asyncio.Task[None] | None = None


@app.on_event("startup")
async def startup() -> None:
    global worker_task
    worker_task = asyncio.create_task(worker_loop())


@app.on_event("shutdown")
async def shutdown() -> None:
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/tasks", response_model=TaskResponse)
async def submit_task(submission: TaskSubmission) -> TaskResponse:
    existing_task_id = idempotency_map.get(submission.idempotency_key)
    if existing_task_id is not None:
        state = derive_task_state(existing_task_id)
        return TaskResponse(
            task_id=state["task_id"],
            status=state["status"],
            created_at=state["created_at"],
            payload=state["payload"],
            retry_count=state["retry_count"],
            last_error=state["last_error"],
        )

    task_id = str(uuid.uuid4())
    idempotency_map[submission.idempotency_key] = task_id

    task_configs[task_id] = {
        "max_retries": submission.max_retries,
        "backoff_base": submission.backoff_base,
    }

    append_event(
        Event(
            task_id,
            "TASK_CREATED",
            {
                "payload": submission.payload,
                "max_retries": submission.max_retries,
                "backoff_base": submission.backoff_base,
            },
        )
    )

    append_event(Event(task_id, "TASK_QUEUED"))
    await task_queue.put({"task_id": task_id, "attempt": 1})

    state = derive_task_state(task_id)
    return TaskResponse(
        task_id=state["task_id"],
        status=state["status"],
        created_at=state["created_at"],
        payload=state["payload"],
        retry_count=state["retry_count"],
        last_error=state["last_error"],
    )


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    seen: set[str] = set()
    results: list[TaskResponse] = []
    for ev in event_store:
        if ev.task_id not in seen and ev.event_type == "TASK_CREATED":
            seen.add(ev.task_id)
            state = derive_task_state(ev.task_id)
            results.append(
                TaskResponse(
                    task_id=state["task_id"],
                    status=state["status"],
                    created_at=state["created_at"],
                    payload=state["payload"],
                    retry_count=state["retry_count"],
                    last_error=state["last_error"],
                )
            )
    return results


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    state = derive_task_state(task_id)
    return TaskResponse(
        task_id=state["task_id"],
        status=state["status"],
        created_at=state["created_at"],
        payload=state["payload"],
        retry_count=state["retry_count"],
        last_error=state["last_error"],
    )


@app.get("/tasks/{task_id}/events", response_model=list[EventResponse])
async def get_task_events_endpoint(task_id: str) -> list[EventResponse]:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    events = get_task_events(task_id)
    return [
        EventResponse(
            event_id=ev.event_id,
            task_id=ev.task_id,
            event_type=ev.event_type,
            timestamp=ev.timestamp.isoformat(),
            data=ev.data,
        )
        for ev in events
    ]


@app.post("/tasks/{task_id}/replay", response_model=TaskResponse)
async def replay_task(task_id: str) -> TaskResponse:
    if task_id not in task_event_index:
        raise HTTPException(status_code=404, detail="Task not found")
    state = derive_task_state(task_id)
    return TaskResponse(
        task_id=state["task_id"],
        status=state["status"],
        created_at=state["created_at"],
        payload=state["payload"],
        retry_count=state["retry_count"],
        last_error=state["last_error"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
