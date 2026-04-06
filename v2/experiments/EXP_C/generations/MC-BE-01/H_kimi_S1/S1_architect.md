# MC-BE-01: Event-Sourced Task Queue API — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. API Endpoint Design

### 1.1 Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Submit new task (idempotent) |
| GET | `/tasks/{task_id}` | Query task status |
| GET | `/tasks/{task_id}/events` | Replay event log |
| GET | `/health` | Worker health check |

### 1.2 Request/Response Schemas

**Submit Task**:
```python
# Request
{
    "idempotency_key": "uuid-string",
    "task_type": "email_send",
    "payload": {...}
}

# Response 201
{
    "task_id": "task-uuid",
    "status": "pending",
    "created_at": "2026-04-01T10:00:00Z"
}

# Response 409 (duplicate idempotency key)
{
    "error": "Task already exists",
    "task_id": "existing-task-uuid"
}
```

**Query Status**:
```python
# Response 200
{
    "task_id": "task-uuid",
    "status": "completed",  # pending | processing | completed | failed
    "attempts": 2,
    "created_at": "...",
    "updated_at": "..."
}
```

---

## 2. Event Store Data Model

### 2.1 Event Types

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any

class EventType(Enum):
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY_SCHEDULED = "task_retry_scheduled"

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: EventType
    timestamp: datetime
    payload: dict[str, Any]
```

### 2.2 Append-Only Store

**Storage Strategy**:
- Events never deleted or modified
- New events appended to task's event stream
- Current state derived by replaying events

**In-Memory Structure**:
```python
event_store: dict[str, list[Event]] = {}  # task_id -> events
idempotency_map: dict[str, str] = {}       # idempotency_key -> task_id
```

### 2.3 State Reconstruction

```python
def reconstruct_state(task_id: str) -> TaskState:
    events = event_store.get(task_id, [])
    state = TaskState()
    
    for event in events:
        state = apply_event(state, event)
    
    return state
```

---

## 3. asyncio.Queue Worker Architecture

### 3.1 Worker Components

```
FastAPI App
├── Task Queue (asyncio.Queue)
├── Worker Pool (N concurrent workers)
└── Event Store (in-memory)
```

### 3.2 Worker Lifecycle

```python
async def worker(queue: asyncio.Queue, worker_id: int):
    while True:
        task_id = await queue.get()
        
        # Record start
        append_event(task_id, EventType.TASK_STARTED)
        
        try:
            # Execute task
            await execute_task(task_id)
            
            # Record success
            append_event(task_id, EventType.TASK_COMPLETED)
        except Exception as e:
            # Record failure
            append_event(task_id, EventType.TASK_FAILED, {"error": str(e)})
            
            # Schedule retry
            await schedule_retry(task_id)
        
        queue.task_done()
```

### 3.3 Startup/Shutdown

```python
@app.on_event("startup")
async def start_workers():
    app.state.task_queue = asyncio.Queue()
    app.state.workers = [
        asyncio.create_task(worker(app.state.task_queue, i))
        for i in range(WORKER_COUNT)
    ]

@app.on_event("shutdown")
async def stop_workers():
    for w in app.state.workers:
        w.cancel()
```

---

## 4. Retry and Backoff Strategy

### 4.1 Configuration

```python
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds
BACKOFF_MULTIPLIER = 2
```

### 4.2 Exponential Backoff

```python
def calculate_delay(attempt: int) -> float:
    return BASE_DELAY * (BACKOFF_MULTIPLIER ** attempt)

# Attempt 1: 1s delay
# Attempt 2: 2s delay
# Attempt 3: 4s delay
```

### 4.3 Retry Flow

```python
async def schedule_retry(task_id: str):
    state = reconstruct_state(task_id)
    
    if state.attempts >= MAX_RETRIES:
        # Mark as permanently failed
        append_event(task_id, EventType.TASK_FAILED, {"permanent": True})
        return
    
    delay = calculate_delay(state.attempts)
    
    # Schedule async retry
    asyncio.create_task(retry_after_delay(task_id, delay))

async def retry_after_delay(task_id: str, delay: float):
    await asyncio.sleep(delay)
    append_event(task_id, EventType.TASK_RETRY_SCHEDULED)
    await app.state.task_queue.put(task_id)
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]Python` | Python 3.10+ with type hints |
| `[F]FastAPI` | FastAPI framework for HTTP endpoints |
| `[D]STDLIB+FASTAPI` | Only standard library + FastAPI |
| `[!D]NO_CELERY` | asyncio.Queue instead of Celery |
| `[Q]ASYNCIO` | Native asyncio for concurrency |
| `[STORE]APPEND_ONLY` | Events appended, never modified |
| `[API]IDEMPOTENT` | Idempotency key deduplication |
| `[OUT]CODE_ONLY` | Output will be code only |

---

## 6. File Structure

```
MC-BE-01/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── main.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
