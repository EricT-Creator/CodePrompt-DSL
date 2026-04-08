You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. ALL route handler functions must be defined with `def`, NOT `async def`. FastAPI supports synchronous route handlers — use them exclusively.
4. Do NOT import or use pathlib at all. Use os.path module for all file path operations (os.path.exists, os.path.getsize, os.path.splitext, os.path.getmtime, os.path.isdir, etc.).
5. All code in a single .py file.
6. Output code only, no explanation text.

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
