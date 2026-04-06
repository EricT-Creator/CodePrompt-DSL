## Constraint Review
- C1 [L]Python [F]FastAPI: PASS — Python file using `from fastapi import FastAPI, HTTPException, Depends, status`; app created with `FastAPI(...)`.
- C2 [D]STDLIB+FASTAPI: PASS — All imports are stdlib (`typing`, `datetime`, `asyncio`, `uuid`, `dataclasses`, `contextlib`, `random`) or FastAPI/Pydantic; no external packages.
- C3 [!D]NO_CELERY [Q]ASYNCIO: PASS — No Celery import; task queue uses `asyncio.Queue` and `asyncio.create_task` for the worker loop.
- C4 [STORE]APPEND_ONLY: PASS — `EventStore` only exposes `append()` for writes; no update or delete methods; task state is reconstructed by replaying events via `reconstruct()`.
- C5 [API]IDEMPOTENT: PASS — `CreateTaskRequest` requires `idempotency_key`; `create_task` checks `get_task_id_by_idempotency_key()` and returns the existing task ID if duplicate, preventing double-creation.
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with no explanatory prose outside of docstrings and comments.

## Functionality Assessment (0-5)
Score: 4 — Complete event-sourced task queue with idempotent creation, async worker loop, retry with exponential backoff, event replay for state reconstruction, and REST endpoints for task CRUD and event history. Issues: both `lifespan` context manager and `@app.on_event` decorators are defined (redundant — FastAPI ignores `on_event` when `lifespan` is set); simulated task success uses `random.random()` making behavior non-deterministic; `_process_task` imports `random` inline. These are minor quality concerns, not constraint violations.

## Corrected Code
No correction needed.
