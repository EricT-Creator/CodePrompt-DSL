You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Python 3.10 or later, standard library only.
2. Do not use jinja2, mako, or any template library. Parse templates using regular expressions.
3. Do not use the ast module for expression evaluation.
4. Full type annotations on all public methods.
5. Raise a custom TemplateSyntaxError for malformed templates.
6. Deliver a single Python file with a TemplateEngine class.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (Python 3.10+, stdlib): PASS/FAIL — evidence
- C2 (Regex parsing, no jinja2): PASS/FAIL — evidence
- C3 (No ast module): PASS/FAIL — evidence
- C4 (Full type annotations): PASS/FAIL — evidence
- C5 (TemplateSyntaxError): PASS/FAIL — evidence
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
