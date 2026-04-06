## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, HTTPException` and defines `app = FastAPI(...)` with route decorators.
- C2 (stdlib + fastapi only): PASS — Imports only `asyncio`, `math`, `random`, `uuid`, `contextlib`, `datetime`, `typing` from stdlib, plus `fastapi` and `pydantic` (bundled with fastapi). No other third-party packages.
- C3 (asyncio.Queue, no Celery): PASS — Uses `task_queue: asyncio.Queue[str] = asyncio.Queue()` for task queuing. Worker runs via `asyncio.create_task(worker())`. No Celery, RQ, or task queue library imported.
- C4 (Append-only event store): PASS — `event_store: list[Event] = []` is append-only: `append_event()` only calls `event_store.append(evt)`. State is derived via `derive_task_state()` by replaying events. No delete or overwrite operations on the event store.
- C5 (Idempotent endpoints): PASS — POST `/tasks` uses `idempotency_key` with `idempotency_map` to return the same result for duplicate requests. GET endpoints are naturally idempotent. POST `/tasks/{task_id}/replay` only reads state.
- C6 (Code only): PASS — File contains only code with structural section markers, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Implements a complete event-sourced task queue with: task creation with idempotency keys, async worker with simulated work and configurable retry with exponential backoff + jitter, event replay for state derivation, task lifecycle events (CREATED → QUEUED → STARTED → SUCCEEDED/FAILED → RETRY/EXHAUSTED), background worker via lifespan context manager, and comprehensive REST API (create, list, get, events, replay).

## Corrected Code
No correction needed.
