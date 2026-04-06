## Constraint Review
- C1 (Python + FastAPI): PASS — File uses Python with `from fastapi import FastAPI, HTTPException` and defines a FastAPI application instance.
- C2 (stdlib + fastapi only): PASS — All imports are from Python stdlib (`asyncio`, `time`, `uuid`, `typing`, `dataclasses`, `datetime`, `random`) or FastAPI/Pydantic (`fastapi`, `pydantic`); `uvicorn` used only in `__main__` block.
- C3 (asyncio.Queue, no Celery): PASS — `TaskWorker` uses `self.queue = asyncio.Queue()` for task queuing; no Celery, RQ, or other task queue libraries imported.
- C4 (Append-only event store): PASS — `EventStore.append_event()` only uses `self._events[task_id].append(event)`; no event deletion or overwrite anywhere. State is derived via `derive_state_from_events()` by replaying the event list.
- C5 (Idempotent endpoints): PASS — `POST /tasks` checks `idempotency_key` via `get_task_id_by_key()` and returns existing state if key already registered; `GET` endpoints are naturally idempotent; `POST /replay` is read-only state derivation.
- C6 (Code only): PASS — File contains only executable Python code with no embedded documentation or non-code content.

## Functionality Assessment (0-5)
Score: 5 — Complete event-sourced task queue with full lifecycle (SUBMITTED → QUEUED → PROCESSING → SUCCEEDED/FAILED → RETRY_SCHEDULED → EXHAUSTED), exponential backoff with jitter for retries, event replay endpoint for state reconstruction, idempotency key management, and proper async worker with graceful shutdown. The architecture cleanly separates event storage, state derivation, and task processing.

## Corrected Code
No correction needed.
