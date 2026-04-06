You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
Python + FastAPI. Manual JWT via hmac+base64, no PyJWT. stdlib + fastapi + uvicorn only. Single file. Endpoints: login, protected, refresh. Code only.

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
