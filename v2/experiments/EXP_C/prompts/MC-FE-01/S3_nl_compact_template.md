You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
TS + React. CSS Modules only, no Tailwind. HTML5 native drag, no dnd libs. useReducer only, no state libs. Single file, export default. Hand-written WS mock, no socket.io.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (TS + React): PASS/FAIL — evidence
- C2 (CSS Modules, no Tailwind): PASS/FAIL — evidence
- C3 (HTML5 Drag, no dnd libs): PASS/FAIL — evidence
- C4 (useReducer only): PASS/FAIL — evidence
- C5 (Single file, export default): PASS/FAIL — evidence
- C6 (Hand-written WS mock, no socket.io): PASS/FAIL — evidence

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
