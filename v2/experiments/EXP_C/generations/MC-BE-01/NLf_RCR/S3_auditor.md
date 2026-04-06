## Constraint Review
- C1 (Python + FastAPI): PASS — File uses `from fastapi import FastAPI, HTTPException` and defines `app = FastAPI(lifespan=lifespan)`.
- C2 (stdlib + fastapi only): PASS — Imports are limited to `asyncio`, `hashlib`, `json`, `random`, `time`, `uuid`, `contextlib`, `datetime`, `typing` (all stdlib) plus `fastapi` and `pydantic` (bundled with FastAPI).
- C3 (asyncio.Queue, no Celery): PASS — Task queue is implemented as `task_queue: asyncio.Queue = asyncio.Queue()` with `worker_loop()` consuming from it. No Celery or RQ imported.
- C4 (Append-only event store): PASS — `event_store: List[Event] = []` is only modified via `.append()`. No delete or overwrite operations on event_store. State is derived by replaying events via `derive_task_status()`.
- C5 (Idempotent endpoints): PASS — `POST /tasks` checks `idempotency_map` for duplicate `idempotency_key` and returns existing task if found. `GET` endpoints are naturally idempotent. `POST /tasks/{task_id}/replay` is read-only (returns derived state).
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 4 — Complete event-sourced task queue with asyncio worker, retry with exponential backoff, idempotent task creation, event replay, and task status derivation from event history. Minor issues: `app = FastAPI()` is defined twice (line 18 and line 121) — the first instance is overwritten, which is harmless but sloppy; the `random.random() < 0.3` failure simulation means task processing is non-deterministic; `except Exception: pass` in worker_loop silently swallows errors which could hide bugs.

## Corrected Code
No correction needed.
