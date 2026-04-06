## Constraint Review
- C1 (TS + React): PASS — File uses `import React, { useReducer, useCallback } from "react"` with TypeScript interfaces (`PersonalInfo`, `Address`, `FormData`, `WizardState`, etc.).
- C2 (Hand-written validation, no form libs): PASS — Custom `validateField()` and `validateStep()` functions with hand-written rules (`personalRules`, `addressRules`); no formik, zod, yup, or any validation library imported.
- C3 (Plain CSS, no Tailwind): PASS — Uses inline style objects (`const css: Record<string, React.CSSProperties>`); no Tailwind classes or CSS framework imported.
- C4 (No external deps): PASS — Only `react` is imported; all logic is hand-written.
- C5 (Single file, export default): PASS — All code in one file; `export default FormWizard` at the end.
- C6 (Code only): PASS — No prose or explanation; the file contains only executable code.

## Functionality Assessment (0-5)
Score: 5 — Complete multi-step form wizard with 3 steps (Personal → Address → Confirmation), step indicator with progress visualization, per-field validation with regex patterns (email, phone, zip code), touch-on-blur error display, step-level validation gate before advancing, back/next navigation, summary review page, submission success state, and proper form UX patterns. All core features fully implemented.

## Corrected Code
No correction needed.
