# Technical Design Document: Event-Sourced Task Queue API

**Task**: MC-BE-01  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]Python [F]FastAPI [D]STDLIB+FASTAPI [!D]NO_CELERY [Q]ASYNCIO [STORE]APPEND_ONLY [API]IDEMPOTENT [OUT]CODE_ONLY`

---

## 1. API Endpoint Design

### Endpoints

| Method | Path | Description | Idempotency |
|--------|------|-------------|-------------|
| `POST` | `/tasks` | Submit a new task with an idempotency key | Yes — duplicate key returns existing task |
| `GET` | `/tasks/{task_id}` | Query current task status (reconstructed from events) | N/A (read-only) |
| `GET` | `/tasks/{task_id}/events` | Replay endpoint — return raw event log for a task | N/A (read-only) |
| `GET` | `/tasks` | List all tasks with optional status filter | N/A (read-only) |

### Request/Response Shapes

**POST /tasks**:
```
Request:  { "idempotency_key": str, "payload": dict, "max_retries": int (default 3) }
Response: { "task_id": str, "status": "pending", "created_at": str }
```

**GET /tasks/{task_id}**:
```
Response: { "task_id": str, "status": str, "payload": dict, "retries": int, "events_count": int, "created_at": str, "updated_at": str }
```

The `status` field is **never stored directly** — it is reconstructed by replaying the event log for that task.

### Idempotency Mechanism

- A `dict[str, str]` maps `idempotency_key → task_id`.
- On `POST /tasks`, check if the key already exists. If so, return the existing task (200) without creating a new one.
- This prevents duplicate task submission from network retries.

---

## 2. Event Store Data Model

### Event Types

```python
EventType = Literal[
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "task_retrying",
    "task_exhausted"    # max retries reached
]
```

### Event Structure

```python
@dataclass
class Event:
    event_id: str           # UUID
    task_id: str            # owning task
    event_type: EventType
    timestamp: str          # ISO 8601
    data: dict              # event-specific payload (error message, retry count, etc.)
```

### Append-Only Store

```python
class EventStore:
    _events: list[Event]                    # global ordered log
    _task_index: dict[str, list[Event]]     # per-task index for fast lookup

    def append(self, event: Event) -> None: ...
    def get_events(self, task_id: str) -> list[Event]: ...
    def reconstruct(self, task_id: str) -> TaskState: ...
```

**Append-only invariant**: The `_events` list is only ever appended to. No event is ever modified or deleted. This is the foundational event-sourcing guarantee.

### State Reconstruction

`reconstruct(task_id)` replays all events for a task in order and derives the current state:

```
task_created   → status=pending, retries=0
task_started   → status=running
task_completed → status=completed
task_failed    → status=failed (transient)
task_retrying  → status=pending, retries+=1
task_exhausted → status=exhausted (terminal)
```

---

## 3. asyncio.Queue Worker Architecture

### Components

```
FastAPI App
  ├── POST /tasks → creates event → enqueues task_id
  │
  └── Background Worker (started on app startup)
       └── while True:
             task_id = await queue.get()
             process(task_id)
```

### Worker Lifecycle

1. **Startup**: `@app.on_event("startup")` creates the `asyncio.Queue` and spawns the worker as an `asyncio.Task`.
2. **Processing loop**:
   - `task_id = await queue.get()` — blocks until a task is available.
   - Append `task_started` event.
   - Execute the task (simulated with `asyncio.sleep` + random success/failure).
   - On success: append `task_completed`.
   - On failure: append `task_failed`, then check retry count.
     - If retries < max_retries: append `task_retrying`, re-enqueue after backoff delay.
     - If retries >= max_retries: append `task_exhausted`.
3. **Shutdown**: `@app.on_event("shutdown")` cancels the worker task gracefully.

### Concurrency Model

- Single worker coroutine consuming from one `asyncio.Queue`.
- Could be extended to multiple workers via `asyncio.gather` on N worker coroutines sharing the same queue.
- No threading — pure asyncio concurrency.

---

## 4. Retry and Backoff Strategy

### Exponential Backoff with Jitter

```
delay = min(base_delay * (2 ** retry_count) + random_jitter, max_delay)
```

- `base_delay`: 1 second
- `max_delay`: 30 seconds
- `random_jitter`: `random.uniform(0, 0.5)` seconds

### Retry Flow

```
task_failed (retry_count=0) → wait 1s   → task_retrying → re-enqueue
task_failed (retry_count=1) → wait 2s   → task_retrying → re-enqueue
task_failed (retry_count=2) → wait 4s   → task_retrying → re-enqueue
task_failed (retry_count=3) → task_exhausted (terminal)
```

### Implementation

The backoff delay is implemented via `asyncio.sleep(delay)` before re-enqueueing. This does not block the worker — the worker moves on to the next queue item while the retry is scheduled via `asyncio.create_task`.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: Python | `[L]Python` | Entire implementation in Python 3.10+. |
| Framework: FastAPI | `[F]FastAPI` | All endpoints defined with FastAPI router, using Pydantic models for request/response validation. |
| Dependencies: stdlib + FastAPI only | `[D]STDLIB+FASTAPI` | Only `asyncio`, `uuid`, `datetime`, `random`, `dataclasses` from stdlib. FastAPI + Pydantic for API layer. No other packages. |
| No Celery | `[!D]NO_CELERY` | No Celery, no RQ, no Dramatiq. Task queue is pure `asyncio.Queue`. |
| Queue: asyncio | `[Q]ASYNCIO` | Worker consumes from `asyncio.Queue`. Retry scheduling via `asyncio.create_task` + `asyncio.sleep`. |
| Store: append-only | `[STORE]APPEND_ONLY` | `EventStore._events` is only appended to. No mutations, no deletions. State derived by replay. |
| API: idempotent | `[API]IDEMPOTENT` | `POST /tasks` uses `idempotency_key` to prevent duplicate creation. Duplicate key returns existing task. |
| Code only output | `[OUT]CODE_ONLY` | Final S2 deliverable will be pure code. |
