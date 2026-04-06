You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
TS + React. Manual virtual scroll, no react-window. CSS Modules, no Tailwind/inline. No external deps. Single file, export default. Inline mock data.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (TS + React): PASS/FAIL — evidence
- C2 (Manual virtual scroll, no windowing libs): PASS/FAIL — evidence
- C3 (CSS Modules, no Tailwind/inline): PASS/FAIL — evidence
- C4 (No external deps): PASS/FAIL — evidence
- C5 (Single file, export default): PASS/FAIL — evidence
- C6 (Inline mock data): PASS/FAIL — evidence

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
