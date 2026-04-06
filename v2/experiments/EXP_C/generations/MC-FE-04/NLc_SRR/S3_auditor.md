## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces (`WizardStep`, `PersonalInfo`, `AddressInfo`, `ValidationRule`, `WizardState`, `WizardAction`) and React hooks (`useReducer`, `useCallback`, `useEffect`).
- C2 (Hand-written validation, no form libs): PASS — Validation is hand-written via `validateField` and `validateSection` functions with custom `ValidationRule` objects using regex, minLength, maxLength, required checks. No formik, zod, yup, or any form library imported.
- C3 (Plain CSS, no Tailwind): PASS — CSS is defined as a plain CSS string in `const css` and injected via `<style>{css}</style>`. No Tailwind classes or utility-first patterns used.
- C4 (No external deps): PASS — Only `import React` is used; validation, state management, and localStorage persistence are all hand-written.
- C5 (Single file, export default): PASS — All code in one file; `export default FormWizard` at end.
- C6 (Code only): PASS — File contains only executable code with no prose or markdown.

## Functionality Assessment (0-5)
Score: 5 — Complete multi-step wizard with progress indicators, step navigation (back/next/go-to), per-field validation with touch tracking, real-time error display, localStorage persistence and restore, confirmation/summary step, async submit simulation with loading state, and reset capability. Comprehensive implementation.

## Corrected Code
No correction needed.
