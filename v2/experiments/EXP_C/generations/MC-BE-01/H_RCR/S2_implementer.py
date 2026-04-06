from __future__ import annotations
import asyncio
import uuid
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

EventType = Literal[
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "task_retrying",
    "task_exhausted"
]


@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: str
    data: Dict[str, Any]


@dataclass
class TaskState:
    task_id: str
    status: str
    payload: Dict[str, Any]
    retries: int
    max_retries: int
    created_at: str
    updated_at: str


class EventStore:
    def __init__(self) -> None:
        self._events: List[Event] = []
        self._task_index: Dict[str, List[Event]] = {}
        self._idempotency_map: Dict[str, str] = {}

    def append(self, event: Event) -> None:
        self._events.append(event)
        if event.task_id not in self._task_index:
            self._task_index[event.task_id] = []
        self._task_index[event.task_id].append(event)

    def get_events(self, task_id: str) -> List[Event]:
        return self._task_index.get(task_id, []).copy()

    def reconstruct(self, task_id: str) -> Optional[TaskState]:
        events = self.get_events(task_id)
        if not events:
            return None

        payload: Dict[str, Any] = {}
        max_retries = 3
        retries = 0
        status = "pending"
        created_at = events[0].timestamp
        updated_at = events[0].timestamp

        for event in events:
            updated_at = event.timestamp
            if event.event_type == "task_created":
                payload = event.data.get("payload", {})
                max_retries = event.data.get("max_retries", 3)
                status = "pending"
            elif event.event_type == "task_started":
                status = "running"
            elif event.event_type == "task_completed":
                status = "completed"
            elif event.event_type == "task_failed":
                status = "failed"
            elif event.event_type == "task_retrying":
                status = "pending"
                retries = event.data.get("retry_count", retries)
            elif event.event_type == "task_exhausted":
                status = "exhausted"

        return TaskState(
            task_id=task_id,
            status=status,
            payload=payload,
            retries=retries,
            max_retries=max_retries,
            created_at=created_at,
            updated_at=updated_at
        )

    def check_idempotency(self, idempotency_key: str) -> Optional[str]:
        return self._idempotency_map.get(idempotency_key)

    def store_idempotency(self, idempotency_key: str, task_id: str) -> None:
        self._idempotency_map[idempotency_key] = task_id


class TaskQueue:
    def __init__(self, event_store: EventStore) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._event_store = event_store
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start(self) -> None:
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        self._shutdown = True
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, task_id: str) -> None:
        await self._queue.put(task_id)

    async def _worker_loop(self) -> None:
        while not self._shutdown:
            try:
                task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_task(task_id)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _process_task(self, task_id: str) -> None:
        state = self._event_store.reconstruct(task_id)
        if not state or state.status != "pending":
            return

        self._event_store.append(Event(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type="task_started",
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={}
        ))

        await asyncio.sleep(0.1 + random.random() * 0.4)

        success = random.random() > 0.3

        if success:
            self._event_store.append(Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_completed",
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={}
            ))
        else:
            self._event_store.append(Event(
                event_id=str(uuid.uuid4()),
                task_id=task_id,
                event_type="task_failed",
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={"error": "Simulated failure"}
            ))

            new_state = self._event_store.reconstruct(task_id)
            if new_state and new_state.retries < new_state.max_retries:
                retry_count = new_state.retries + 1
                self._event_store.append(Event(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="task_retrying",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={"retry_count": retry_count}
                ))

                delay = min(1.0 * (2 ** retry_count) + random.uniform(0, 0.5), 30.0)
                asyncio.create_task(self._schedule_retry(task_id, delay))
            else:
                self._event_store.append(Event(
                    event_id=str(uuid.uuid4()),
                    task_id=task_id,
                    event_type="task_exhausted",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={}
                ))

    async def _schedule_retry(self, task_id: str, delay: float) -> None:
        await asyncio.sleep(delay)
        if not self._shutdown:
            await self.enqueue(task_id)


class CreateTaskRequest(BaseModel):
    idempotency_key: str
    payload: Dict[str, Any]
    max_retries: int = 3


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class TaskDetailResponse(BaseModel):
    task_id: str
    status: str
    payload: Dict[str, Any]
    retries: int
    events_count: int
    created_at: str
    updated_at: str


class EventResponse(BaseModel):
    event_id: str
    event_type: EventType
    timestamp: str
    data: Dict[str, Any]


class TaskListResponse(BaseModel):
    tasks: List[TaskDetailResponse]
    total: int


app = FastAPI(title="Event-Sourced Task Queue API")
event_store = EventStore()
task_queue = TaskQueue(event_store)


@app.on_event("startup")
async def startup() -> None:
    await task_queue.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    await task_queue.stop()


@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest) -> TaskResponse:
    existing_task_id = event_store.check_idempotency(request.idempotency_key)
    if existing_task_id:
        state = event_store.reconstruct(existing_task_id)
        if state:
            return TaskResponse(
                task_id=state.task_id,
                status=state.status,
                created_at=state.created_at
            )

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    event_store.store_idempotency(request.idempotency_key, task_id)

    event_store.append(Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type="task_created",
        timestamp=now,
        data={
            "payload": request.payload,
            "max_retries": request.max_retries,
            "idempotency_key": request.idempotency_key
        }
    ))

    await task_queue.enqueue(task_id)

    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=now
    )


@app.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str) -> TaskDetailResponse:
    state = event_store.reconstruct(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")

    events = event_store.get_events(task_id)

    return TaskDetailResponse(
        task_id=state.task_id,
        status=state.status,
        payload=state.payload,
        retries=state.retries,
        events_count=len(events),
        created_at=state.created_at,
        updated_at=state.updated_at
    )


@app.get("/tasks/{task_id}/events", response_model=List[EventResponse])
async def get_task_events(task_id: str) -> List[EventResponse]:
    events = event_store.get_events(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")

    return [
        EventResponse(
            event_id=e.event_id,
            event_type=e.event_type,
            timestamp=e.timestamp,
            data=e.data
        )
        for e in events
    ]


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(status: Optional[str] = None) -> TaskListResponse:
    all_tasks: List[TaskDetailResponse] = []

    for task_id in event_store._task_index.keys():
        state = event_store.reconstruct(task_id)
        if state:
            if status is None or state.status == status:
                events = event_store.get_events(task_id)
                all_tasks.append(TaskDetailResponse(
                    task_id=state.task_id,
                    status=state.status,
                    payload=state.payload,
                    retries=state.retries,
                    events_count=len(events),
                    created_at=state.created_at,
                    updated_at=state.updated_at
                ))

    return TaskListResponse(tasks=all_tasks, total=len(all_tasks))
