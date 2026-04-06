You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use TypeScript with React framework.
2. Implement virtual scrolling manually. Do not use react-window, react-virtualized, @tanstack/virtual, or any windowing library.
3. Use CSS Modules for all styling. Do not use Tailwind CSS or inline styles.
4. Do not use any external npm packages beyond React and TypeScript.
5. Deliver a single .tsx file with export default.
6. Generate mock data inline in the file. Do not import from external data files.

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
