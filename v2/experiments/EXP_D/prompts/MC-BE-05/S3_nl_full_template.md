You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use Python with FastAPI framework.
2. Only use Python standard library, fastapi, and uvicorn as dependencies.
3. Do NOT import or use the Python `logging` module at all. Instead, implement all logging using print() with a custom dict format like print({"level": "INFO", "method": "POST", ...}).
4. Do NOT use Pydantic BaseModel for request/response models. Use raw Python dicts for data handling and implement manual validation (check key existence, type, value range) directly in endpoint functions.
5. All code in a single .py file.
6. Output code only, no explanation text.

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
