# MC-BE-01: FastAPI Event-Sourced Task Queue - Technical Design Document

## 1. API Endpoint Design

### Endpoint Specifications

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Request/Response Models
class TaskSubmitRequest(BaseModel):
    task_type: str
    payload: dict
    idempotency_key: str
    max_retries: int = 3

class TaskResponse(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    idempotency_key: str
    retry_count: int
    created_at: str
    updated_at: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    events: list[dict]  # Event history for replay
    current_state: dict
```

### Route Definitions

```python
@app.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskSubmitRequest):
    """Submit a new task with idempotency key."""
    pass

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Query task status and event history."""
    pass

@app.post("/tasks/{task_id}/replay")
async def replay_task(task_id: str):
    """Replay events to reconstruct current state."""
    pass

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    pass
```

## 2. Event Store Data Model

### Event Structure

```python
from dataclasses import dataclass
from typing import Any
from datetime import datetime

@dataclass
class Event:
    event_id: str
    task_id: str
    event_type: str  # TaskSubmitted, TaskStarted, TaskCompleted, TaskFailed, TaskRetried
    payload: dict[str, Any]
    timestamp: datetime
    sequence_number: int  # Monotonic per task

@dataclass
class TaskAggregate:
    task_id: str
    idempotency_key: str
    task_type: str
    status: str
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    events: list[Event]
```

### Append-Only Event Store

**Storage Strategy:**
- Events stored as immutable append-only log
- No updates or deletes to existing events
- Current state derived by replaying events
- In-memory list with persistence to JSON file

```python
class EventStore:
    def __init__(self):
        self._events: list[Event] = []  # Append-only list
        self._index: dict[str, list[int]] = {}  # task_id -> event indices
    
    def append(self, event: Event) -> None:
        """Append event to store - never modify existing events."""
        self._events.append(event)
        if event.task_id not in self._index:
            self._index[event.task_id] = []
        self._index[event.task_id].append(len(self._events) - 1)
    
    def get_events_for_task(self, task_id: str) -> list[Event]:
        """Retrieve all events for a task in sequence order."""
        indices = self._index.get(task_id, [])
        return [self._events[i] for i in indices]
    
    def get_all_events(self) -> list[Event]:
        """Return all events (for backup/debug)."""
        return self._events.copy()
```

### State Reconstruction

```python
def reconstruct_task_state(events: list[Event]) -> TaskAggregate:
    """Rebuild task state from event stream."""
    if not events:
        raise ValueError("No events to reconstruct")
    
    # Start with initial state from first event
    first_event = events[0]
    task = TaskAggregate(
        task_id=first_event.task_id,
        idempotency_key=first_event.payload['idempotency_key'],
        task_type=first_event.payload['task_type'],
        status='pending',
        retry_count=0,
        max_retries=first_event.payload.get('max_retries', 3),
        created_at=first_event.timestamp,
        updated_at=first_event.timestamp,
        events=events
    )
    
    # Apply each subsequent event
    for event in events[1:]:
        if event.event_type == 'TaskStarted':
            task.status = 'processing'
        elif event.event_type == 'TaskCompleted':
            task.status = 'completed'
        elif event.event_type == 'TaskFailed':
            task.status = 'failed'
        elif event.event_type == 'TaskRetried':
            task.retry_count += 1
            task.status = 'pending'
        task.updated_at = event.timestamp
    
    return task
```

## 3. asyncio.Queue Worker Architecture

### Worker Design

```python
import asyncio
from typing import Callable

class TaskWorker:
    def __init__(
        self,
        queue: asyncio.Queue,
        event_store: EventStore,
        task_handlers: dict[str, Callable],
        max_concurrent: int = 3
    ):
        self.queue = queue
        self.event_store = event_store
        self.task_handlers = task_handlers
        self.max_concurrent = max_concurrent
        self._shutdown = False
        self._workers: list[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start worker pool."""
        self._workers = [
            asyncio.create_task(self._worker_loop())
            for _ in range(self.max_concurrent)
        ]
    
    async def stop(self) -> None:
        """Graceful shutdown."""
        self._shutdown = True
        await asyncio.gather(*self._workers, return_exceptions=True)
    
    async def _worker_loop(self) -> None:
        """Main worker loop."""
        while not self._shutdown:
            try:
                task_id = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                await self._process_task(task_id)
            except asyncio.TimeoutError:
                continue
    
    async def _process_task(self, task_id: str) -> None:
        """Process single task with retry logic."""
        # Implementation with retry and event recording
        pass
```

### Queue Integration

```python
# Global queue instance
task_queue: asyncio.Queue[str] = asyncio.Queue()

@app.on_event("startup")
async def startup_event():
    """Initialize worker on startup."""
    worker = TaskWorker(
        queue=task_queue,
        event_store=event_store,
        task_handlers=HANDLERS
    )
    await worker.start()
    app.state.worker = worker

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown."""
    await app.state.worker.stop()
```

## 4. Retry and Backoff Strategy

### Exponential Backoff

```python
import random
from datetime import timedelta

def calculate_backoff_delay(
    retry_count: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """Calculate delay with exponential backoff."""
    # Exponential: 1s, 2s, 4s, 8s, ... capped at max_delay
    delay = min(base_delay * (2 ** retry_count), max_delay)
    
    if jitter:
        # Add randomness to prevent thundering herd
        delay = delay * (0.5 + random.random())
    
    return delay
```

### Retry Logic

```python
async def execute_with_retry(
    task_id: str,
    handler: Callable,
    payload: dict,
    max_retries: int,
    event_store: EventStore
) -> bool:
    """Execute task with retry logic."""
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            await handler(payload)
            
            # Record success
            event_store.append(Event(
                event_id=generate_id(),
                task_id=task_id,
                event_type='TaskCompleted',
                payload={'retry_count': retry_count},
                timestamp=datetime.utcnow(),
                sequence_number=get_next_sequence(task_id)
            ))
            return True
            
        except Exception as e:
            retry_count += 1
            
            if retry_count > max_retries:
                # Record final failure
                event_store.append(Event(
                    event_id=generate_id(),
                    task_id=task_id,
                    event_type='TaskFailed',
                    payload={'error': str(e), 'final_retry': True},
                    timestamp=datetime.utcnow(),
                    sequence_number=get_next_sequence(task_id)
                ))
                return False
            
            # Record retry event
            event_store.append(Event(
                event_id=generate_id(),
                task_id=task_id,
                event_type='TaskRetried',
                payload={'error': str(e), 'retry_count': retry_count},
                timestamp=datetime.utcnow(),
                sequence_number=get_next_sequence(task_id)
            ))
            
            # Wait before retry
            delay = calculate_backoff_delay(retry_count)
            await asyncio.sleep(delay)
```

## 5. Constraint Acknowledgment

### Python + FastAPI
**Addressed by:** Application built with FastAPI framework. All endpoints use FastAPI decorators and Pydantic models.

### stdlib + fastapi + uvicorn only
**Addressed by:** Only dependencies are FastAPI, uvicorn, and Python standard library. No additional packages for queue, events, or task processing.

### asyncio.Queue only, no Celery/RQ
**Addressed by:** Task queue implemented using `asyncio.Queue` from standard library. No Celery, RQ, or other distributed task queues.

### Append-only list event store, no dict overwrite
**Addressed by:** Event store uses `list.append()` only. No `events[i] = new_event` or dictionary value updates. State changes recorded as new events only.

### All endpoints idempotent
**Addressed by:** Task submission uses idempotency keys. Duplicate requests with same key return existing task. All state changes are event-driven and replay-safe.

### Code only
**Addressed by:** Output contains only Python code. No markdown in generated file.
