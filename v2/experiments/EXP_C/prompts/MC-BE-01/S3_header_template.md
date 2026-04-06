[L]Python [F]FastAPI [D]STDLIB+FASTAPI [!D]NO_CELERY [Q]ASYNCIO [STORE]APPEND_ONLY [API]IDEMPOTENT [OUT]CODE_ONLY

You are a senior code reviewer. Review the code below against EACH engineering constraint in the header above.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [F]FastAPI: PASS/FAIL — evidence
- C2 [D]STDLIB+FASTAPI: PASS/FAIL — evidence
- C3 [!D]NO_CELERY [Q]ASYNCIO: PASS/FAIL — evidence
- C4 [STORE]APPEND_ONLY: PASS/FAIL — evidence
- C5 [API]IDEMPOTENT: PASS/FAIL — evidence
- C6 [OUT]CODE_ONLY: PASS/FAIL — evidence

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
