You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
Python 3.10+, stdlib only. exec() for plugin loading, no importlib. Protocol for interfaces, no ABC. Full type annotations. Plugin errors isolated. Single file, class output.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python 3.10+, stdlib): PASS/FAIL — evidence
- C2 (exec() loading, no importlib): PASS/FAIL — evidence
- C3 (Protocol, no ABC): PASS/FAIL — evidence
- C4 (Full type annotations): PASS/FAIL — evidence
- C5 (Error isolation): PASS/FAIL — evidence
- C6 (Single file, class): PASS/FAIL — evidence

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
