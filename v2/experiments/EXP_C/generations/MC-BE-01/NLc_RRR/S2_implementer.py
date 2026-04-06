import asyncio
import time
import uuid
import random
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ---- Event Types ----

class EventType(str, Enum):
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    EXHAUSTED = "EXHAUSTED"


# ---- Data Models ----

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: float
    payload: dict


# ---- Event Store ----

event_store: dict[str, list[Event]] = {}
idempotency_index: dict[str, str] = {}


def append_event(task_id: str, event_type: EventType, payload: dict | None = None) -> Event:
    event = Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp=time.time(),
        payload=payload or {},
    )
    if task_id not in event_store:
        event_store[task_id] = []
    event_store[task_id].append(event)
    return event


def replay_task_state(task_id: str) -> dict[str, Any]:
    events = event_store.get(task_id, [])
    if not events:
        return {}

    state: dict[str, Any] = {
        "task_id": task_id,
        "idempotency_key": "",
        "status": "UNKNOWN",
        "retries": 0,
        "max_retries": 3,
        "result": None,
        "created_at": 0.0,
        "updated_at": 0.0,
    }

    for event in events:
        state["updated_at"] = event.timestamp

        if event.event_type == EventType.SUBMITTED:
            state["status"] = "SUBMITTED"
            state["created_at"] = event.timestamp
            state["idempotency_key"] = event.payload.get("idempotency_key", "")
            state["max_retries"] = event.payload.get("max_retries", 3)

        elif event.event_type == EventType.QUEUED:
            state["status"] = "QUEUED"

        elif event.event_type == EventType.PROCESSING:
            state["status"] = "PROCESSING"

        elif event.event_type == EventType.SUCCEEDED:
            state["status"] = "SUCCEEDED"
            state["result"] = event.payload.get("result")

        elif event.event_type == EventType.FAILED:
            state["status"] = "FAILED"
            state["result"] = event.payload.get("error")

        elif event.event_type == EventType.RETRY_SCHEDULED:
            state["status"] = "RETRY_SCHEDULED"
            state["retries"] = event.payload.get("retry_count", state["retries"] + 1)

        elif event.event_type == EventType.EXHAUSTED:
            state["status"] = "EXHAUSTED"

    return state


def retries_remaining(task_id: str) -> bool:
    state = replay_task_state(task_id)
    return state.get("retries", 0) < state.get("max_retries", 3)


def get_retry_count(task_id: str) -> int:
    events = event_store.get(task_id, [])
    count = 0
    for e in events:
        if e.event_type == EventType.RETRY_SCHEDULED:
            count += 1
    return count


# ---- Retry / Backoff ----

BASE_DELAY = 1.0
BACKOFF_MULTIPLIER = 2.0
MAX_DELAY = 30.0


def compute_backoff(retry_count: int) -> float:
    delay = min(BASE_DELAY * (BACKOFF_MULTIPLIER ** retry_count), MAX_DELAY)
    jitter = delay * 0.1 * (random.random() * 2 - 1)
    return delay + jitter


# ---- Task Execution (simulated) ----

async def execute_task(task_id: str) -> dict[str, Any]:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.3:
        raise RuntimeError(f"Simulated failure for task {task_id}")
    return {"message": f"Task {task_id} completed successfully", "value": random.randint(1, 100)}


# ---- Worker ----

task_queue: asyncio.Queue[str] = asyncio.Queue()


async def delayed_requeue(task_id: str, delay: float) -> None:
    await asyncio.sleep(delay)
    append_event(task_id, EventType.QUEUED)
    await task_queue.put(task_id)


async def worker() -> None:
    while True:
        task_id = await task_queue.get()
        append_event(task_id, EventType.PROCESSING)
        try:
            result = await execute_task(task_id)
            append_event(task_id, EventType.SUCCEEDED, {"result": result})
        except Exception as e:
            append_event(task_id, EventType.FAILED, {"error": str(e)})
            if retries_remaining(task_id):
                retry_count = get_retry_count(task_id) + 1
                delay = compute_backoff(retry_count - 1)
                append_event(task_id, EventType.RETRY_SCHEDULED, {
                    "retry_count": retry_count,
                    "delay": delay,
                })
                asyncio.create_task(delayed_requeue(task_id, delay))
            else:
                append_event(task_id, EventType.EXHAUSTED)
        finally:
            task_queue.task_done()


# ---- Request Models ----

class SubmitTaskRequest(BaseModel):
    idempotency_key: str
    description: str = ""
    max_retries: int = 3


# ---- FastAPI App ----

app = FastAPI(title="Event-Sourced Task Queue")


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(worker())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/tasks")
async def submit_task(request: SubmitTaskRequest) -> JSONResponse:
    if request.idempotency_key in idempotency_index:
        existing_task_id = idempotency_index[request.idempotency_key]
        state = replay_task_state(existing_task_id)
        return JSONResponse(content=state, status_code=200)

    task_id = str(uuid.uuid4())
    idempotency_index[request.idempotency_key] = task_id

    append_event(task_id, EventType.SUBMITTED, {
        "idempotency_key": request.idempotency_key,
        "description": request.description,
        "max_retries": request.max_retries,
    })
    append_event(task_id, EventType.QUEUED)
    await task_queue.put(task_id)

    state = replay_task_state(task_id)
    return JSONResponse(content=state, status_code=201)


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return replay_task_state(task_id)


@app.get("/tasks/{task_id}/events")
async def get_task_events(task_id: str) -> list[dict[str, Any]]:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        {
            "event_id": e.event_id,
            "task_id": e.task_id,
            "event_type": e.event_type.value,
            "timestamp": e.timestamp,
            "payload": e.payload,
        }
        for e in event_store[task_id]
    ]


@app.post("/tasks/{task_id}/replay")
async def replay_task(task_id: str) -> dict[str, Any]:
    if task_id not in event_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return replay_task_state(task_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
