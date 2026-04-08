You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
Python + FastAPI. stdlib + fastapi + uvicorn only. ALL route handlers must use sync `def`, NOT `async def`. DO NOT use pathlib — use os.path for all file operations. Single file. Code only.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [F]FastAPI: PASS/FAIL — evidence
- C2 [!ASYNC]SYNC_DEF_ONLY (no async def in route handlers): PASS/FAIL — evidence
- C3 [!PATH]OS_PATH_ONLY (no pathlib import): PASS/FAIL — evidence
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
