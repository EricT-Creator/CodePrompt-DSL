"""MC-BE-01: Event-Sourced Task Queue API — FastAPI + asyncio.Queue + Append-Only Store"""
from __future__ import annotations

import asyncio
import json
import math
import random
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# ── Event types ─────────────────────────────────────────────────────

class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"
    TASK_CANCELLED = "task_cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Pydantic models ─────────────────────────────────────────────────

class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    aggregate_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1


class TaskSubmitRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    max_retries: int = 3
    retry_backoff_ms: int = 1000
    timeout_seconds: int = 300


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    idempotency_key: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    events: List[Dict[str, Any]] = Field(default_factory=list)


class ReplayRequest(BaseModel):
    from_timestamp: Optional[str] = None
    to_timestamp: Optional[str] = None
    task_id: Optional[str] = None
    event_types: Optional[List[str]] = None


class ReplayResponse(BaseModel):
    reconstructed_state: Dict[str, Any]
    events_applied: int
    replay_duration_ms: float


# ── Append-Only Event Store (in-memory) ─────────────────────────────

class AppendOnlyEventStore:
    def __init__(self) -> None:
        self._events: List[Event] = []
        self._lock = asyncio.Lock()
        self._index_by_aggregate: Dict[str, List[int]] = {}

    async def append(self, event: Event) -> str:
        async with self._lock:
            idx = len(self._events)
            self._events.append(event)
            self._index_by_aggregate.setdefault(event.aggregate_id, []).append(idx)
        return event.event_id

    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
        limit: int = 500,
    ) -> List[Event]:
        if aggregate_id and aggregate_id in self._index_by_aggregate:
            indices = self._index_by_aggregate[aggregate_id]
            candidates = [self._events[i] for i in indices]
        else:
            candidates = list(self._events)

        results: List[Event] = []
        for ev in candidates:
            if event_types and ev.event_type.value not in event_types:
                continue
            if from_ts and ev.timestamp < from_ts:
                continue
            if to_ts and ev.timestamp > to_ts:
                continue
            results.append(ev)
            if len(results) >= limit:
                break
        return results

    async def all_events(self) -> List[Event]:
        return list(self._events)


# ── Retry strategy ──────────────────────────────────────────────────

class RetryStrategy:
    def __init__(self, max_retries: int = 3, base_delay_ms: int = 1000, max_delay_ms: int = 30000) -> None:
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms

    def calculate_delay(self, retry_count: int) -> float:
        delay = self.base_delay_ms * (2 ** (retry_count - 1))
        delay = min(delay, self.max_delay_ms)
        jitter = random.uniform(0.9, 1.1)
        return delay * jitter / 1000.0

    def should_retry(self, retry_count: int) -> bool:
        return retry_count < self.max_retries


# ── Task state materialization ──────────────────────────────────────

def materialize_task(events: List[Event]) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "task_id": "",
        "status": TaskStatus.PENDING.value,
        "created_at": None,
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "retry_count": 0,
    }
    for ev in events:
        state["task_id"] = ev.aggregate_id
        if ev.event_type == EventType.TASK_CREATED:
            state["status"] = TaskStatus.PENDING.value
            state["created_at"] = ev.timestamp
        elif ev.event_type == EventType.TASK_QUEUED:
            state["status"] = TaskStatus.QUEUED.value
        elif ev.event_type == EventType.TASK_STARTED:
            state["status"] = TaskStatus.PROCESSING.value
            state["started_at"] = ev.timestamp
        elif ev.event_type == EventType.TASK_COMPLETED:
            state["status"] = TaskStatus.COMPLETED.value
            state["completed_at"] = ev.timestamp
            state["result"] = ev.payload.get("result")
        elif ev.event_type == EventType.TASK_FAILED:
            state["error"] = ev.payload.get("error")
        elif ev.event_type == EventType.TASK_RETRY_SCHEDULED:
            state["retry_count"] = ev.payload.get("retry_count", state["retry_count"] + 1)
            state["status"] = TaskStatus.QUEUED.value
        elif ev.event_type == EventType.TASK_CANCELLED:
            state["status"] = TaskStatus.CANCELLED.value
    return state


# ── Worker ──────────────────────────────────────────────────────────

class TaskWorker:
    def __init__(self, worker_id: str, queue: asyncio.Queue, store: AppendOnlyEventStore) -> None:  # type: ignore[type-arg]
        self.worker_id = worker_id
        self.queue = queue
        self.store = store
        self._running = True

    async def run(self) -> None:
        while self._running:
            try:
                task_data: Dict[str, Any] = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task_id = task_data["task_id"]
            retry = RetryStrategy(
                max_retries=task_data.get("max_retries", 3),
                base_delay_ms=task_data.get("retry_backoff_ms", 1000),
            )

            await self.store.append(Event(
                event_type=EventType.TASK_STARTED,
                aggregate_id=task_id,
                payload={"worker_id": self.worker_id},
            ))

            try:
                # Simulate work
                await asyncio.sleep(random.uniform(0.05, 0.2))
                # Random failure for demonstration
                if random.random() < 0.1:
                    raise RuntimeError("Simulated task failure")

                result = {"processed": True, "task_type": task_data.get("task_type")}
                await self.store.append(Event(
                    event_type=EventType.TASK_COMPLETED,
                    aggregate_id=task_id,
                    payload={"result": result, "worker_id": self.worker_id},
                ))
            except Exception as exc:
                await self.store.append(Event(
                    event_type=EventType.TASK_FAILED,
                    aggregate_id=task_id,
                    payload={"error": str(exc), "worker_id": self.worker_id},
                ))
                current_retry = task_data.get("retry_count", 0) + 1
                if retry.should_retry(current_retry):
                    delay = retry.calculate_delay(current_retry)
                    await self.store.append(Event(
                        event_type=EventType.TASK_RETRY_SCHEDULED,
                        aggregate_id=task_id,
                        payload={"retry_count": current_retry, "delay_s": delay},
                    ))
                    await asyncio.sleep(delay)
                    task_data["retry_count"] = current_retry
                    await self.queue.put(task_data)

            self.queue.task_done()

    def stop(self) -> None:
        self._running = False


# ── Application ─────────────────────────────────────────────────────

app = FastAPI(title="Event-Sourced Task Queue API")

event_store = AppendOnlyEventStore()
task_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)  # type: ignore[type-arg]
idempotency_cache: Dict[str, str] = {}
workers: List[TaskWorker] = []


@app.on_event("startup")
async def startup() -> None:
    for i in range(2):
        w = TaskWorker(f"worker_{i}", task_queue, event_store)
        workers.append(w)
        asyncio.create_task(w.run())


@app.on_event("shutdown")
async def shutdown() -> None:
    for w in workers:
        w.stop()


# ── Endpoints ───────────────────────────────────────────────────────

@app.post("/api/v1/tasks", response_model=TaskSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_task(req: TaskSubmitRequest) -> TaskSubmitResponse:
    # Idempotency check
    if req.idempotency_key and req.idempotency_key in idempotency_cache:
        existing_id = idempotency_cache[req.idempotency_key]
        events = await event_store.get_events(aggregate_id=existing_id)
        st = materialize_task(events)
        return TaskSubmitResponse(task_id=existing_id, status=st["status"], created_at=st.get("created_at", ""), idempotency_key=req.idempotency_key)

    task_id = f"task_{uuid.uuid4().hex[:8]}"

    if req.idempotency_key:
        idempotency_cache[req.idempotency_key] = task_id

    ts = datetime.now(timezone.utc).isoformat()

    await event_store.append(Event(
        event_type=EventType.TASK_CREATED,
        aggregate_id=task_id,
        payload={
            "task_type": req.task_type,
            "payload": req.payload,
            "idempotency_key": req.idempotency_key,
            "max_retries": req.max_retries,
            "retry_backoff_ms": req.retry_backoff_ms,
            "timeout_seconds": req.timeout_seconds,
        },
    ))

    task_data = {
        "task_id": task_id,
        "task_type": req.task_type,
        "payload": req.payload,
        "max_retries": req.max_retries,
        "retry_backoff_ms": req.retry_backoff_ms,
        "timeout_seconds": req.timeout_seconds,
        "retry_count": 0,
    }

    await event_store.append(Event(event_type=EventType.TASK_QUEUED, aggregate_id=task_id, payload={"queue_size": task_queue.qsize()}))
    await task_queue.put(task_data)

    return TaskSubmitResponse(task_id=task_id, status=TaskStatus.QUEUED.value, created_at=ts, idempotency_key=req.idempotency_key)


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    events = await event_store.get_events(aggregate_id=task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    st = materialize_task(events)
    return TaskStatusResponse(
        task_id=task_id,
        status=st["status"],
        created_at=st.get("created_at"),
        started_at=st.get("started_at"),
        completed_at=st.get("completed_at"),
        result=st.get("result"),
        error=st.get("error"),
        retry_count=st.get("retry_count", 0),
        events=[ev.dict() for ev in events],
    )


@app.get("/api/v1/tasks")
async def list_tasks(status_filter: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    all_events = await event_store.all_events()
    task_events: Dict[str, List[Event]] = {}
    for ev in all_events:
        task_events.setdefault(ev.aggregate_id, []).append(ev)

    tasks = []
    for tid, evts in task_events.items():
        if not any(e.event_type == EventType.TASK_CREATED for e in evts):
            continue
        st = materialize_task(evts)
        if status_filter and st["status"] != status_filter:
            continue
        tasks.append(st)
        if len(tasks) >= limit:
            break

    return {"tasks": tasks, "total": len(tasks)}


@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> Dict[str, str]:
    events = await event_store.get_events(aggregate_id=task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    await event_store.append(Event(event_type=EventType.TASK_CANCELLED, aggregate_id=task_id))
    return {"message": f"Task {task_id} cancelled"}


@app.get("/api/v1/events")
async def get_events(
    aggregate_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    types = [event_type] if event_type else None
    events = await event_store.get_events(aggregate_id=aggregate_id, event_types=types, limit=limit)
    return {"events": [ev.dict() for ev in events], "count": len(events)}


@app.post("/api/v1/replay", response_model=ReplayResponse)
async def replay_events(req: ReplayRequest) -> ReplayResponse:
    start = time.monotonic()

    events = await event_store.get_events(
        aggregate_id=req.task_id,
        event_types=req.event_types,
        from_ts=req.from_timestamp,
        to_ts=req.to_timestamp,
        limit=10000,
    )

    task_states: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        task_states.setdefault(ev.aggregate_id, [])
        task_states[ev.aggregate_id].append(ev)  # type: ignore[union-attr]

    reconstructed: Dict[str, Any] = {}
    for tid, evts in task_states.items():
        reconstructed[tid] = materialize_task(evts)  # type: ignore[arg-type]

    elapsed = (time.monotonic() - start) * 1000

    return ReplayResponse(
        reconstructed_state={"tasks": reconstructed},
        events_applied=len(events),
        replay_duration_ms=round(elapsed, 2),
    )


@app.get("/api/v1/health")
async def health() -> Dict[str, Any]:
    return {"status": "healthy", "workers": len(workers), "queue_size": task_queue.qsize()}


@app.get("/api/v1/metrics")
async def metrics() -> Dict[str, Any]:
    all_events = await event_store.all_events()
    type_counts: Dict[str, int] = {}
    for ev in all_events:
        type_counts[ev.event_type.value] = type_counts.get(ev.event_type.value, 0) + 1
    return {
        "total_events": len(all_events),
        "event_type_counts": type_counts,
        "queue_size": task_queue.qsize(),
        "workers_active": len(workers),
    }
