[L]PY310 [D]STDLIB_ONLY [MUST]AST_VISITOR [!D]NO_REGEX [O]DATACLASS [TYPE]FULL_HINTS [CHECK]IMPORT+VAR+LEN+NEST [O]CLASS [FILE]SINGLE

You are a senior code reviewer. Review the code below against EACH engineering constraint in the header above.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]PY310 [D]STDLIB_ONLY: PASS/FAIL — evidence
- C2 [MUST]AST_VISITOR [!D]NO_REGEX: PASS/FAIL — evidence
- C3 [O]DATACLASS: PASS/FAIL — evidence
- C4 [TYPE]FULL_HINTS: PASS/FAIL — evidence
- C5 [CHECK]IMPORT+VAR+LEN+NEST: PASS/FAIL — evidence
- C6 [O]CLASS [FILE]SINGLE: PASS/FAIL — evidence

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
