You are a senior code reviewer. Review the code below against EACH engineering constraint listed below.

Engineering Constraints:
1. Use TypeScript with React framework.
2. Implement all form validation by hand. Do not use react-hook-form, formik, zod, yup, or any form/validation library.
3. Use plain CSS (style tags or CSS files) for styling. Do not use Tailwind CSS.
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
- C2 (Hand-written validation, no form libs): PASS/FAIL — evidence
- C3 (Plain CSS, no Tailwind): PASS/FAIL — evidence
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
