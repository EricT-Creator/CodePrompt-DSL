You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. Do not use Celery, RQ, or any task queue library. Implement the queue using asyncio.Queue.
4. The event store must be an append-only list. Never overwrite or delete events. Derive current state by replaying events.
5. All API endpoints must be idempotent (same request twice = same result).
6. Output code only, no explanation text.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python + FastAPI): PASS/FAIL — evidence
- C2 (stdlib + fastapi only): PASS/FAIL — evidence
- C3 (asyncio.Queue, no Celery): PASS/FAIL — evidence
- C4 (Append-only event store): PASS/FAIL — evidence
- C5 (Idempotent endpoints): PASS/FAIL — evidence
- C6 (Code only): PASS/FAIL — evidence

## Functionality Assessment (0-5)
Score: X — brief justification

## Corrected Code
If ANY constraint is FAIL, output the COMPLETE corrected .py file below. If all PASS, output "No correction needed."

```py
{corrected code here if needed}
```

Code to review:
---
{S2_OUTPUT}
---
