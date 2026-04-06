You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Implement rate limiting using the Token Bucket algorithm. Do not use simple counter-based or fixed window approaches.
3. Only use Python standard library and fastapi. Do not use Redis, memcached, or any external storage.
4. Deliver everything in a single Python file.
5. Return HTTP 429 with Retry-After header when rate exceeded. Support an IP whitelist that bypasses rate limiting.
6. Output code only, no explanation text.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python + FastAPI): PASS/FAIL — evidence
- C2 (Token Bucket, no counter): PASS/FAIL — evidence
- C3 (stdlib + fastapi, no Redis): PASS/FAIL — evidence
- C4 (Single file): PASS/FAIL — evidence
- C5 (429 + Retry-After + whitelist): PASS/FAIL — evidence
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
