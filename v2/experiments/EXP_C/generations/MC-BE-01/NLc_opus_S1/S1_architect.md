# Technical Design Document — Event-Sourced Task Queue

## 1. Overview

A FastAPI-based event-sourced task queue service. Tasks are submitted with idempotency keys, processed by an `asyncio.Queue`-driven worker with configurable retry and exponential backoff, and their full event history can be replayed to reconstruct current state.

## 2. API Endpoint Design

| Method | Path | Purpose | Idempotent |
|--------|------|---------|-----------|
| `POST` | `/tasks` | Submit a new task with an idempotency key | Yes — if key already exists, returns existing task state |
| `GET` | `/tasks/{task_id}` | Query current task status (derived from events) | Yes (read) |
| `GET` | `/tasks/{task_id}/events` | Return raw event log for a task | Yes (read) |
| `POST` | `/tasks/{task_id}/replay` | Reconstruct current state from event log and return it | Yes (pure derivation) |
| `GET` | `/health` | Health check | Yes |

### Idempotency Mechanism
- The `POST /tasks` body includes an `idempotency_key` string.
- A dictionary `idempotency_index: dict[str, str]` maps keys to task IDs.
- If the key is already present, the endpoint returns the existing task's current state with HTTP 200 instead of creating a duplicate.

## 3. Event Store Data Model

### Core Types

- **Event**: `{ event_id: str, task_id: str, event_type: str, timestamp: float, payload: dict }`
- **EventType** enum: `SUBMITTED`, `QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED`, `RETRY_SCHEDULED`, `EXHAUSTED`
- **Task** (derived): `{ task_id: str, idempotency_key: str, status: str, retries: int, max_retries: int, result: Any, created_at: float, updated_at: float }`

### Storage Structure

- `event_store: dict[str, list[Event]]` — maps `task_id` to an append-only list of events.
- Events are never mutated or deleted; current state is always derived by replaying the list.

### State Derivation (Replay)
Iterate through the event list for a task in order:
1. Start with a blank `Task` state.
2. For each event, apply its `event_type` to update the derived fields (`status`, `retries`, `result`, `updated_at`).
3. Return the final state after all events are processed.

This is the sole mechanism for computing task status — no separate mutable status field exists.

## 4. asyncio.Queue Worker Architecture

### Queue Setup
- A single `asyncio.Queue` instance created at app startup.
- A background worker task (`asyncio.create_task`) runs an infinite loop: `await queue.get()`, process, `queue.task_done()`.

### Worker Loop
```
while True:
    task_id = await queue.get()
    append_event(task_id, PROCESSING)
    try:
        result = await execute_task(task_id)
        append_event(task_id, SUCCEEDED, result)
    except Exception as e:
        append_event(task_id, FAILED, error=str(e))
        if retries_remaining(task_id):
            schedule_retry(task_id)
        else:
            append_event(task_id, EXHAUSTED)
    queue.task_done()
```

### Task Execution
- `execute_task` is a pluggable async function. For this design, it simulates work with `asyncio.sleep` and a random success/failure ratio.

### Lifecycle Events
The worker appends events to the event store at each state transition, maintaining a complete audit trail.

## 5. Retry and Backoff Strategy

### Configuration
- `max_retries`: configurable per task (default: 3), set at submission time.
- `base_delay`: 1.0 second.
- `backoff_multiplier`: 2.0 (exponential).
- `max_delay`: 30.0 seconds (cap).

### Backoff Calculation
```
delay = min(base_delay * (backoff_multiplier ** retry_count), max_delay)
```

### Retry Scheduling
1. On `FAILED` event, check `retries_remaining` (derived from event count of `RETRY_SCHEDULED` events).
2. If retries remain: append `RETRY_SCHEDULED` event, use `asyncio.create_task(delayed_requeue(task_id, delay))`.
3. `delayed_requeue` sleeps for the computed delay, then puts the task_id back on the `asyncio.Queue`.
4. If no retries remain: append `EXHAUSTED` event. Task is terminal.

### Jitter (optional)
A small random jitter (±10%) can be added to the delay to prevent thundering herd when many tasks fail simultaneously.

## 6. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python + FastAPI** | Application is a FastAPI app served by uvicorn. All endpoints use FastAPI decorators and Pydantic models. |
| 2 | **stdlib + fastapi + uvicorn only** | No external packages beyond `fastapi` and `uvicorn`. Data structures use Python stdlib (`dict`, `list`, `dataclasses`). UUID generation via `uuid` stdlib module. |
| 3 | **asyncio.Queue only, no Celery/RQ** | Task processing uses a single `asyncio.Queue` with an `async` worker loop. No Celery, RQ, Dramatiq, or other task queue frameworks. |
| 4 | **Append-only list event store, no dict overwrite** | The event store is `dict[str, list[Event]]`. Events are only appended. Current state is derived by replaying the event list — no mutable status field is ever overwritten. |
| 5 | **All endpoints idempotent** | `POST /tasks` uses an idempotency key to prevent duplicates. `GET` endpoints are naturally idempotent. `POST /replay` is a pure derivation with no side effects. |
| 6 | **Code only** | The deliverable is a single Python file with no prose or markdown. |
