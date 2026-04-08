# Technical Design: Logging REST API

## Overview
FastAPI CRUD application for items with print-based request logging.

## Data Model
- `items: list[dict]` — Each item: `{"id": int, "name": str, "price": float, "category": str}`
- `logs: list[dict]` — Each log: `{"level": str, "method": str, "path": str, "timestamp": str, "status_code": int, "response_time_ms": float}`
- `_next_id: int = 1` — Auto-increment

## API Endpoints

### Items CRUD
- `POST /items` — Create item. Body: raw JSON dict. Manual validation: name (str, required), price (number, >0), category (str, required). Returns 201 + item with generated id. Returns 422 + errors list on validation failure.
- `GET /items` — Return all items list.
- `GET /items/{item_id}` — Return single item or 404.
- `PUT /items/{item_id}` — Update item fields. Partial update (only provided fields). 404 if not found.
- `DELETE /items/{item_id}` — Remove item. 404 if not found. Return 204.

### Logging
- `GET /logs` — Return all log entries. Optional query param `level` filters by exact match.

## Request Logging Architecture

Use a FastAPI middleware that:
1. Records `start_time = time.time()` before request
2. Passes request through
3. After response, creates log dict with method, path, status_code, timestamp (datetime.utcnow().isoformat()), response_time_ms
4. Sets level: "ERROR" if status >= 400, else "INFO"
5. Appends to `logs` list
6. Calls `print(log_entry)` — this is the ONLY logging mechanism (NO `import logging`)

## Manual Validation (No Pydantic)

Every create/update endpoint:
1. Parse body with `await request.json()`
2. Check each required field exists and has correct type
3. Collect errors in list
4. If errors: return JSONResponse(status_code=422, content={"errors": errors})
5. NO Pydantic BaseModel anywhere in the code

## Constraint Acknowledgment
- C1: Python + FastAPI — `from fastapi import FastAPI`
- C2: NO logging module — all logging via `print()` with dict format
- C3: NO Pydantic BaseModel — raw dict + manual isinstance/key checks
- C4: stdlib + fastapi + uvicorn only — no other imports
- C5: Single .py file — all code in one file
- C6: Code only — no markdown or explanation
