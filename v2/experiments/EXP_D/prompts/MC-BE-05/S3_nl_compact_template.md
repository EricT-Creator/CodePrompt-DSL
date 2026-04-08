You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
Python + FastAPI. stdlib + fastapi + uvicorn only. DO NOT use Python logging module — use print() with custom dict format for all logging. DO NOT use Pydantic BaseModel — use raw dict and manual validation. Single file. Code only.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [F]FastAPI: PASS/FAIL — evidence
- C2 [!LOG]NO_LOGGING_MODULE (must use print, not logging): PASS/FAIL — evidence
- C3 [!PYDANTIC]NO_BASEMODEL (raw dict, manual validation): PASS/FAIL — evidence
- C4 [D]STDLIB+FASTAPI only: PASS/FAIL — evidence
- C5 [FILE]SINGLE: PASS/FAIL — evidence
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
