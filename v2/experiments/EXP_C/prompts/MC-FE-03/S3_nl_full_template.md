You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use TypeScript with React framework.
2. Use native Canvas 2D context API only. Do not use fabric.js, konva, p5.js, or any canvas/drawing library.
3. Use useReducer for ALL state management. Do not use useState at all.
4. No external npm packages beyond React and TypeScript.
5. Deliver a single .tsx file with export default.
6. Output code only, no explanation text.

For each constraint, output:
- PASS: if fully complied
- FAIL: if violated
- evidence: one-line proof

Format your review as:

## Constraint Review
- C1 (TS + React): PASS/FAIL — evidence
- C2 (Native Canvas 2D, no libs): PASS/FAIL — evidence
- C3 (useReducer only, no useState): PASS/FAIL — evidence
- C4 (No external deps): PASS/FAIL — evidence
- C5 (Single file, export default): PASS/FAIL — evidence
- C6 (Code only): PASS/FAIL — evidence

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
