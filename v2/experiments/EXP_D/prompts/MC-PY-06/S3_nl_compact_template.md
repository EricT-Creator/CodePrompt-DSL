You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
Python stdlib only. DO NOT use urllib or http.client — implement HTTP using raw socket. DO NOT use f-strings — use .format() or % formatting only. Full type annotations. Response as dataclass. Single file class.

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
