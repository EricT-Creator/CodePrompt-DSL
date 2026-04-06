You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Must use ast.NodeVisitor or ast.walk for code analysis. Do not use regular expressions for code pattern matching.
3. Wrap all check results in dataclass instances.
4. Full type annotations on all public methods.
5. Implement all four checks: unused imports, unused variables, function length > 50 lines, nesting depth > 4.
6. Deliver a single Python file with a CodeChecker class.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python 3.10+, stdlib): PASS/FAIL — evidence
- C2 (ast.NodeVisitor, no regex): PASS/FAIL — evidence
- C3 (Dataclass results): PASS/FAIL — evidence
- C4 (Full type annotations): PASS/FAIL — evidence
- C5 (4 checks: import/var/len/nest): PASS/FAIL — evidence
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
