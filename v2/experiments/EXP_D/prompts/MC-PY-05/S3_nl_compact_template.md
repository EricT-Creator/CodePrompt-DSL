You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
Python stdlib only. DO NOT use configparser/json/yaml modules for parsing. DO NOT store config data in plain dict — use NamedTuple or dataclass with __slots__. Full type annotations. ConfigError custom exception. Single file class.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]Python [D]STDLIB_ONLY: PASS/FAIL — evidence
- C2 [!CFG]NO_CONFIGPARSER_JSON_YAML: PASS/FAIL — evidence
- C3 [!DICT]NAMEDTUPLE_OR_DATACLASS (no plain dict for config storage): PASS/FAIL — evidence
- C4 [TYPE]FULL_ANNOTATIONS: PASS/FAIL — evidence
- C5 [ERR]ConfigError exception: PASS/FAIL — evidence
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
