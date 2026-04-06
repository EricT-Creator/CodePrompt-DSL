You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use TypeScript with React framework.
2. Use CSS Modules for all styling. Do not use Tailwind CSS or any utility-first CSS framework.
3. Implement drag-and-drop using the native HTML5 Drag and Drop API only. Do not use react-dnd, dnd-kit, @hello-pangea/dnd, or any drag-and-drop library.
4. Use useReducer for all state management. Do not use Redux, Zustand, Jotai, or other state management libraries.
5. Deliver a single .tsx file with export default as the main component.
6. Simulate real-time sync with a hand-written mock using setTimeout/setInterval. Do not use socket.io or any WebSocket library.

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
