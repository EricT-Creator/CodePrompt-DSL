[L]TS [F]React [!D]NO_VIRT_LIB [SCROLL]MANUAL [Y]CSS_MODULES [!Y]NO_TW_INLINE [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [DT]INLINE_MOCK

You are a senior code reviewer. Review the code below against EACH engineering constraint in the header above.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 [L]TS [F]React: PASS/FAIL — evidence
- C2 [!D]NO_VIRT_LIB [SCROLL]MANUAL: PASS/FAIL — evidence
- C3 [Y]CSS_MODULES [!Y]NO_TW_INLINE: PASS/FAIL — evidence
- C4 [D]NO_EXTERNAL: PASS/FAIL — evidence
- C5 [O]SFC [EXP]DEFAULT: PASS/FAIL — evidence
- C6 [DT]INLINE_MOCK: PASS/FAIL — evidence

## Functionality Assessment (0-5)
Score: X — brief justification

## Corrected Code
If ANY constraint is FAIL, output the COMPLETE corrected .tsx file below. If all PASS, output "No correction needed."

```tsx
{corrected code here if needed}
```

Code to review:
---
{S2_OUTPUT}
---
