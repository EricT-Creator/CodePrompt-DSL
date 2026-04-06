You are a developer. Implement the technical design below as a single Python file (.py). Follow ALL engineering constraints listed below strictly. Output code only, no explanation.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. Do not use Celery, RQ, or any task queue library. Implement the queue using asyncio.Queue.
4. The event store must be an append-only list. Never overwrite or delete events. Derive current state by replaying events.
5. All API endpoints must be idempotent (same request twice = same result).
6. Output code only, no explanation text.

Technical Design:
---
{S1_OUTPUT}
---
