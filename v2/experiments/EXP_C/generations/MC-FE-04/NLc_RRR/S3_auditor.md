## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces (PersonalInfo, AddressInfo, FormData, FormErrors) and React hooks (useState, useCallback).
- C2 (Hand-written validation, no form libs): PASS — `validateStep()` function implements validation manually with regex (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, `/^\+?[\d\s\-()]{7,15}$/`, `/^\d{5}(-\d{4})?$/`) and length checks; no formik, yup, or zod imported.
- C3 (Plain CSS, no Tailwind): PASS — Styles defined as plain CSS via `React.CSSProperties` objects; no Tailwind classes anywhere.
- C4 (No external deps): PASS — Only import is `from "react"`; no external dependencies.
- C5 (Single file, export default): PASS — All code in one file, ends with `export default FormWizard`.
- C6 (Code only): PASS — File contains only code with no prose or documentation blocks.

## Functionality Assessment (0-5)
Score: 5 — Complete 3-step form wizard with: step indicator showing progress (numbers/checkmarks), personal info step (name/email/phone with validation), address step (street/city/state/zip with validation), confirmation/review step, inline error display per field, clear error on input change, back/next navigation with validation gating, submit action with success screen, and clean component decomposition (StepPersonal, StepAddress, StepConfirmation, StepIndicator, FieldError).

## Corrected Code
No correction needed.
