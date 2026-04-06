[L]Python [F]FastAPI [ALGO]TOKEN_BUCKET [!A]NO_COUNTER [D]STDLIB+FASTAPI [!D]NO_REDIS [O]SINGLE_FILE [RESP]429_RETRY_AFTER [WL]IP [OUT]CODE_ONLY

You are a senior code reviewer. Review the code below against EACH engineering constraint in the header above.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [F]FastAPI: PASS/FAIL — evidence
- C2 [ALGO]TOKEN_BUCKET [!A]NO_COUNTER: PASS/FAIL — evidence
- C3 [D]STDLIB+FASTAPI [!D]NO_REDIS: PASS/FAIL — evidence
- C4 [O]SINGLE_FILE: PASS/FAIL — evidence
- C5 [RESP]429_RETRY_AFTER [WL]IP: PASS/FAIL — evidence
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
