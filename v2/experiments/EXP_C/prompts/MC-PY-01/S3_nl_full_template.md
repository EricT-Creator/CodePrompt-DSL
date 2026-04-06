You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Do not use importlib for plugin loading. Load plugins by reading the file and using exec().
3. Do not use ABC (Abstract Base Class). Define interfaces using typing.Protocol.
4. Full type annotations on all public methods and class attributes.
5. Plugin errors must be isolated. One plugin failure must not crash the pipeline.
6. Deliver a single Python file with a Pipeline class as main output.

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
