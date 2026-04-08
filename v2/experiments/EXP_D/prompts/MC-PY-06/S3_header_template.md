[L]Python [D]STDLIB_ONLY [!URL]SOCKET_RAW_HTTP [!FSTR]NO_FSTRING [TYPE]FULL_ANNOTATIONS [RES]RESPONSE_DATACLASS [OUT]SINGLE_CLASS

You are a senior code reviewer. Review the code below against EACH engineering constraint in the header above.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [D]STDLIB_ONLY: PASS/FAIL — evidence
- C2 [!URL]SOCKET_RAW_HTTP (no urllib/http.client): PASS/FAIL — evidence
- C3 [!FSTR]NO_FSTRING (use .format() or %): PASS/FAIL — evidence
- C4 [TYPE]FULL_ANNOTATIONS: PASS/FAIL — evidence
- C5 [RES]RESPONSE_DATACLASS: PASS/FAIL — evidence
- C6 [OUT]SINGLE_CLASS: PASS/FAIL — evidence

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
