[L]PY310 [D]STDLIB_ONLY [!D]NO_GRAPH_LIB [O]CLASS [TYPE]FULL_HINTS [ERR]CYCLE_EXC [FILE]SINGLE

You are a senior code reviewer. Review the code below against EACH engineering constraint in the header above.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS/FAIL — evidence
- C2 [!D]NO_GRAPH_LIB: PASS/FAIL — evidence
- C3 [O]CLASS: PASS/FAIL — evidence
- C4 [TYPE]FULL_HINTS: PASS/FAIL — evidence
- C5 [ERR]CYCLE_EXC: PASS/FAIL — evidence
- C6 [FILE]SINGLE: PASS/FAIL — evidence

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
