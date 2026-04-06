# MC-BE-01: Event-Sourced Task Queue - Technical Design

## Overview

This document outlines the technical design for a FastAPI event-sourced task queue with idempotent task submission, automatic retry with backoff, and event replay capabilities using asyncio.Queue.

## 1. API Endpoint Design

### Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Submit a new task with idempotency key |
| GET | `/tasks/{task_id}` | Query task status and history |
| GET | `/tasks/{task_id}/events` | Replay events for a task |
| GET | `/health` | Health check including queue status |

### Request/Response Schemas

```python
# POST /tasks
class TaskSubmitRequest(BaseModel):
    idempotency_key: str  # Client-generated UUID
    task_type: str
    payload: dict
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay in seconds

class TaskResponse(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime
    attempts: int
    result: Optional[dict] = None
    error: Optional[str] = None

# GET /tasks/{task_id}
class TaskStatusResponse(BaseModel):
    task_id: str
    current_status: str
    events: List[TaskEvent]
    attempt_count: int

# GET /tasks/{task_id}/events
class EventReplayResponse(BaseModel):
    task_id: str
    current_state: dict  # Derived from event replay
    event_log: List[TaskEvent]
```

## 2. Event Store Data Model

### Event Types

```python
class TaskEvent(BaseModel):
    event_id: str  # UUID
    task_id: str
    event_type: Literal[
        "TASK_SUBMITTED",
        "TASK_STARTED",
        "TASK_COMPLETED",
        "TASK_FAILED",
        "TASK_RETRY_SCHEDULED"
    ]
    timestamp: datetime
    payload: dict  # Event-specific data

# Event payload examples:
# TASK_SUBMITTED: {"idempotency_key": "...", "task_type": "...", "initial_payload": {...}}
# TASK_STARTED: {"worker_id": "...", "started_at": "..."}
# TASK_COMPLETED: {"result": {...}, "duration_ms": 123}
# TASK_FAILED: {"error": "...", "will_retry": true}
# TASK_RETRY_SCHEDULED: {"next_attempt_at": "...", "attempt_number": 2}
```

### Event Store Structure

```python
# In-memory append-only event store
class EventStore:
    def __init__(self):
        self._events: List[TaskEvent] = []  # Append-only list
        self._task_index: Dict[str, List[int]] = {}  # task_id -> event indices
    
    def append(self, event: TaskEvent) -> None:
        """Append event - never modify existing events."""
        index = len(self._events)
        self._events.append(event)
        self._task_index.setdefault(event.task_id, []).append(index)
    
    def get_events_for_task(self, task_id: str) -> List[TaskEvent]:
        """Retrieve all events for a task in chronological order."""
        indices = self._task_index.get(task_id, [])
        return [self._events[i] for i in indices]
    
    def replay_to_state(self, task_id: str) -> dict:
        """Derive current state by replaying all events."""
        events = self.get_events_for_task(task_id)
        state = {"status": "unknown", "attempts": 0}
        
        for event in events:
            if event.event_type == "TASK_SUBMITTED":
                state["status"] = "pending"
                state["task_type"] = event.payload["task_type"]
            elif event.event_type == "TASK_STARTED":
                state["status"] = "processing"
                state["attempts"] += 1
            elif event.event_type == "TASK_COMPLETED":
                state["status"] = "completed"
                state["result"] = event.payload["result"]
            elif event.event_type == "TASK_FAILED":
                if not event.payload.get("will_retry"):
                    state["status"] = "failed"
                state["last_error"] = event.payload["error"]
        
        return state
```

## 3. asyncio.Queue Worker Architecture

### Worker Pool Design

```python
class TaskWorker:
    def __init__(
        self,
        queue: asyncio.Queue,
        event_store: EventStore,
        worker_id: str
    ):
        self.queue = queue
        self.event_store = event_store
        self.worker_id = worker_id
        self.running = False
    
    async def start(self) -> None:
        self.running = True
        while self.running:
            try:
                task_id = await self.queue.get()
                await self.process_task(task_id)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
    
    async def process_task(self, task_id: str) -> None:
        # 1. Emit TASK_STARTED event
        # 2. Execute task handler
        # 3. On success: emit TASK_COMPLETED
        # 4. On failure: emit TASK_FAILED, schedule retry if needed
        pass
```

### Queue Lifecycle

```
Startup:
  1. Create asyncio.Queue()
  2. Spawn N worker tasks (asyncio.create_task)
  3. Workers begin awaiting queue.get()

Task Submission:
  1. Validate idempotency key
  2. Append TASK_SUBMITTED event
  3. Put task_id in queue
  4. Worker picks up task_id

Task Processing:
  1. Worker emits TASK_STARTED
  2. Execute handler
  3. Emit TASK_COMPLETED or TASK_FAILED
  4. If failed and retries remain, schedule retry
```

## 4. Retry and Backoff Strategy

### Exponential Backoff

```python
import asyncio
import random

async def schedule_retry(
    task_id: str,
    attempt_number: int,
    base_delay: float,
    queue: asyncio.Queue,
    event_store: EventStore
) -> None:
    """Schedule a task retry with exponential backoff + jitter."""
    # Exponential: 1s, 2s, 4s, 8s...
    delay = base_delay * (2 ** (attempt_number - 1))
    # Add jitter (±25%) to prevent thundering herd
    jitter = delay * 0.25 * (2 * random.random() - 1)
    actual_delay = delay + jitter
    
    await asyncio.sleep(actual_delay)
    
    # Emit retry scheduled event
    event_store.append(TaskEvent(
        event_id=str(uuid4()),
        task_id=task_id,
        event_type="TASK_RETRY_SCHEDULED",
        timestamp=datetime.utcnow(),
        payload={"next_attempt_at": datetime.utcnow().isoformat()}
    ))
    
    # Re-queue the task
    await queue.put(task_id)
```

### Retry Flow

```
Task Fails:
  ├─ Check attempt_count < max_retries
  │   ├─ Yes: Emit TASK_FAILED {will_retry: true}
  │   │        Calculate backoff delay
  │   │        Schedule retry via asyncio.sleep
  │   │        Re-queue task after delay
  │   └─ No:  Emit TASK_FAILED {will_retry: false}
  │           Task permanently failed
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python + FastAPI** | Use FastAPI framework with Pydantic models for request/response validation |
| **Standard library + FastAPI + uvicorn only** | No Celery, RQ, or other task queue libraries; asyncio.Queue for queue implementation |
| **asyncio.Queue for queue** | Implement worker pool using asyncio.Queue instead of external task queues |
| **Append-only event store** | EventStore uses List.append() only; no updates or deletes; state derived via replay |
| **Idempotent endpoints** | POST /tasks uses idempotency_key; duplicate submissions return existing task |
| **Output code only** | Design structured for direct implementation |

## Summary

This design implements an event-sourced task queue using only FastAPI and Python's standard library. The append-only event store provides complete audit history and enables state reconstruction via replay. asyncio.Queue powers the worker pool without external dependencies. Idempotency keys ensure safe retry semantics for task submission. Exponential backoff with jitter prevents cascading failures during recovery.
