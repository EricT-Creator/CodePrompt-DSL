## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript (types `StepId`, interfaces `PersonalInfo`, `AddressInfo`, `FormData`, `FormState` etc.) and React (`import React, { useState, useCallback } from 'react'`).
- C2 [!D]NO_FORM_LIB [VALID]HANDWRITE: PASS — No form library imported (no Formik, react-hook-form etc.); validation is hand-written via the `validateStep` function with manual regex checks and field-by-field error messages.
- C3 [Y]PLAIN_CSS [!Y]NO_TW: PASS — Styles imported via `import './FormWizard.css'` (plain CSS file); className strings are plain CSS class names (`"form-wizard"`, `"progress-bar"`, `"form-field"` etc.); no Tailwind utility classes present.
- C4 [D]NO_EXTERNAL: PASS — Only React is imported; all validation, step navigation, and form logic is hand-written.
- C5 [O]SFC [EXP]DEFAULT: PASS — `FormWizard` is a single function component exported as `export default function FormWizard()`.
- C6 [OUT]CODE_ONLY: PASS — Output contains only executable code, no prose or explanation.

## Functionality Assessment (0-5)
Score: 5 — Complete 3-step form wizard with progress bar, field validation (name/email/phone regex in step 1, address/city/state/zip in step 2), inline error display with clear-on-type, back/next navigation with validation gating, confirmation page in step 3, and success state with reset. Well-structured with proper TypeScript types.

## Corrected Code
No correction needed.
