# Technical Design: Sync File Metadata API

## Overview
FastAPI app for file metadata queries using synchronous handlers and os.path (not pathlib).

## Data Model
- `recent_queries: list[str]` — Last 10 queried file paths (most recent first)

## API Endpoints

### POST /metadata
- Body: `{"paths": ["path1", "path2", ...]}`
- For each path, return metadata dict:
  - `path`: original path string
  - `size_bytes`: file size (os.path.getsize)
  - `extension`: file extension (os.path.splitext)
  - `modified_time`: last modification time ISO format (os.path.getmtime → datetime.fromtimestamp)
  - `is_directory`: bool (os.path.isdir)
- If path doesn't exist: `{"path": path, "error": "File not found"}`
- Update recent_queries with all queried paths
- Handler MUST be `def` (synchronous), NOT `async def`

### GET /recent
- Return the 10 most recently queried file paths
- Handler MUST be `def` (synchronous), NOT `async def`

## Synchronous Design
ALL route handlers use `def`, not `async def`. FastAPI runs sync handlers in a threadpool automatically. This is the explicit constraint.

## File Operations
Use ONLY `os.path` functions:
- `os.path.exists(path)` — check existence
- `os.path.getsize(path)` — file size
- `os.path.splitext(path)` — extension
- `os.path.getmtime(path)` — modification time
- `os.path.isdir(path)` — directory check
NO `from pathlib import Path` or `Path()` anywhere.

## Recent Tracking
- Maintain a list of max 10 entries
- Each POST adds paths to front of list
- Trim to 10 after each addition
- Dedup: if path already in list, move to front

## Constraint Acknowledgment
- C1: Python + FastAPI
- C2: ALL handlers are `def`, NOT `async def`
- C3: Only os.path, NO pathlib import
- C4: stdlib + fastapi + uvicorn only
- C5: Single .py file
- C6: Code only
