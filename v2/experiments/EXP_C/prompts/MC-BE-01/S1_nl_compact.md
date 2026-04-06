You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python + FastAPI. stdlib + fastapi + uvicorn only. asyncio.Queue only, no Celery/RQ. Append-only list event store, no dict overwrite. All endpoints idempotent. Code only.

Include:
1. API endpoint design
2. Event store data model
3. asyncio.Queue worker architecture
4. Retry and backoff strategy
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI event-sourced task queue. Support: POST to submit a task (with idempotency key), GET to query task status, automatic retry with configurable max retries and backoff, event replay endpoint that reconstructs current state from the event log, and an asyncio.Queue-driven worker.
