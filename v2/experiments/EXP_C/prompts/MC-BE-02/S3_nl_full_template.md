You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Do not use PyJWT, python-jose, or any JWT library. Implement JWT signing and verification using hmac and base64 from the standard library.
3. Only use Python standard library, fastapi, and uvicorn. No other third-party packages.
4. Deliver everything in a single Python file.
5. Provide at minimum: POST /login, GET /protected, POST /refresh endpoints.
6. Output code only, no explanation text.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python + FastAPI): PASS/FAIL — evidence
- C2 (Manual JWT, no PyJWT): PASS/FAIL — evidence
- C3 (stdlib + fastapi only): PASS/FAIL — evidence
- C4 (Single file): PASS/FAIL — evidence
- C5 (login/protected/refresh endpoints): PASS/FAIL — evidence
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
