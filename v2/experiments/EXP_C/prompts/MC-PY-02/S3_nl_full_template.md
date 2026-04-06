You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Do not use networkx, graphlib, or any graph library. Implement topological sort from scratch.
3. The main output must be a class (not standalone functions).
4. Full type annotations on all public methods.
5. Raise a custom CycleError exception when a cycle is detected.
6. Deliver a single Python file.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python 3.10+, stdlib): PASS/FAIL — evidence
- C2 (No graph libs): PASS/FAIL — evidence
- C3 (Class output): PASS/FAIL — evidence
- C4 (Full type annotations): PASS/FAIL — evidence
- C5 (CycleError): PASS/FAIL — evidence
- C6 (Single file): PASS/FAIL — evidence

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
