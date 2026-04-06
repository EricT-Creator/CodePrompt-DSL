# Technical Design Document — Event-Sourced Task Queue

## 1. Overview

This document describes the architecture for a FastAPI event-sourced task queue. The system supports task submission with idempotency keys, task status queries, automatic retry with configurable max retries and exponential backoff, an event replay endpoint that reconstructs current state from the event log, and an asyncio.Queue-driven background worker.

## 2. API Endpoint Design

### 2.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Submit a new task. Accepts an idempotency key. Returns task ID and status. |
| GET | `/tasks/{task_id}` | Query current task status (derived from event log). |
| GET | `/tasks/{task_id}/events` | Return the raw event log for a specific task. |
| POST | `/tasks/{task_id}/replay` | Replay all events for a task and return reconstructed current state. |
| GET | `/tasks` | List all tasks with their current derived status. |

### 2.2 Request/Response Models

- **TaskSubmission**: `{ idempotency_key: str; payload: dict; max_retries: int (default 3); backoff_base: float (default 1.0) }`
- **TaskResponse**: `{ task_id: str; status: str; created_at: str; payload: dict; retry_count: int; last_error: str | None }`
- **EventResponse**: `{ event_id: str; task_id: str; event_type: str; timestamp: str; data: dict }`

### 2.3 Idempotency

Each task submission includes an `idempotency_key`. A dictionary maps keys to task IDs. If a POST arrives with a key that already exists, the existing task is returned without creating a new one. This ensures the same request sent twice produces the same result.

## 3. Event Store Data Model

### 3.1 Design Principles

The event store is an append-only list. Events are never overwritten or deleted. Current task state is always derived by replaying events from the beginning.

### 3.2 Event Types

| Event Type | Data | Meaning |
|------------|------|---------|
| `TASK_CREATED` | `{ payload, max_retries, backoff_base }` | Task was submitted |
| `TASK_QUEUED` | `{}` | Task placed in asyncio.Queue |
| `TASK_STARTED` | `{ attempt: int }` | Worker picked up the task |
| `TASK_SUCCEEDED` | `{ result: dict }` | Task completed successfully |
| `TASK_FAILED` | `{ error: str, attempt: int }` | Task execution failed |
| `TASK_RETRY_SCHEDULED` | `{ next_attempt: int, delay: float }` | Retry scheduled after failure |
| `TASK_EXHAUSTED` | `{ total_attempts: int }` | All retries exhausted, task permanently failed |

### 3.3 Data Structures

- **Event**: `{ event_id: str; task_id: str; event_type: str; timestamp: datetime; data: dict }`
- **EventStore**: A plain Python list (`list[Event]`). Append-only. Global singleton.
- **Task index**: A dictionary `{ task_id: list[int] }` mapping task IDs to their event indices in the store for efficient replay.

### 3.4 State Derivation

To get the current state of a task, filter events by `task_id` and replay them in order:
- Start with status = "pending"
- Apply each event: CREATED → "pending", QUEUED → "queued", STARTED → "running", SUCCEEDED → "completed", FAILED → check retries, RETRY_SCHEDULED → "retrying", EXHAUSTED → "failed"

## 4. asyncio.Queue Worker Architecture

### 4.1 Queue Setup

A single `asyncio.Queue` is created at application startup. Tasks are enqueued when submitted via POST.

### 4.2 Worker Loop

A background `asyncio.Task` runs a perpetual loop:
1. `task_info = await queue.get()`
2. Emit `TASK_STARTED` event.
3. Execute the task (simulated work with random success/failure).
4. On success: emit `TASK_SUCCEEDED`.
5. On failure: emit `TASK_FAILED`. If retries remain, emit `TASK_RETRY_SCHEDULED`, sleep for backoff delay, re-enqueue. If retries exhausted, emit `TASK_EXHAUSTED`.

### 4.3 Lifecycle

- The worker is launched via FastAPI's `lifespan` context manager (or `on_event("startup")`).
- On shutdown, the worker is cancelled gracefully.

## 5. Retry and Backoff Strategy

### 5.1 Exponential Backoff

Delay for attempt `n` is: `backoff_base × 2^(n-1)` seconds, capped at 60 seconds.

- Attempt 1 (first retry): `base × 1`
- Attempt 2: `base × 2`
- Attempt 3: `base × 4`
- Max delay: 60 seconds

### 5.2 Retry Flow

1. Task fails → `TASK_FAILED` event with current attempt number.
2. Check `attempt < max_retries`.
3. If yes: calculate delay, emit `TASK_RETRY_SCHEDULED`, `await asyncio.sleep(delay)`, re-enqueue task.
4. If no: emit `TASK_EXHAUSTED`. Task status becomes "failed" permanently.

### 5.3 Jitter

Optional: add a small random jitter (±10%) to the backoff delay to prevent thundering herd in high-concurrency scenarios.

## 6. Idempotency Implementation

- Maintain a `dict[str, str]` mapping `idempotency_key → task_id`.
- On POST `/tasks`, first check if the key exists. If yes, return the existing task.
- If no, create a new task, store the mapping, and enqueue.
- This makes POST idempotent: sending the same request twice returns the same task without side effects.

GET endpoints are naturally idempotent (read-only). The replay endpoint is also idempotent since it reads from the immutable event log.

## 7. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python with FastAPI | The application is built entirely on FastAPI with Pydantic models for request/response validation. |
| 2 | Only Python stdlib, fastapi, and uvicorn | No additional packages are used. All data structures (lists, dicts), async primitives (asyncio.Queue, asyncio.sleep), and utility functions are from the standard library. |
| 3 | No Celery/RQ/task queue library; use asyncio.Queue | The worker is driven by `asyncio.Queue`. Task enqueue and dequeue use native asyncio primitives. No external task queue is imported. |
| 4 | Append-only event store; never overwrite or delete; derive state by replaying | The event store is a `list[Event]` with only `.append()` operations. Current state is computed by replaying events. No mutation or deletion of events occurs. |
| 5 | All API endpoints must be idempotent | POST uses idempotency keys to prevent duplicate creation. GET and replay endpoints are inherently idempotent. Same request twice always produces the same result. |
| 6 | Output code only, no explanation text | The final implementation will contain pure code. This document is the design artifact only. |
