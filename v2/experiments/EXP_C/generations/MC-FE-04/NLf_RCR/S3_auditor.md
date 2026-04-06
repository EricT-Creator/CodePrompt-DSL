## Constraint Review
- C1 (TS + React): PASS — File uses `import React, { useState } from 'react'` with TypeScript interfaces (`PersonalInfo`, `Address`, `FormData`, `FieldErrors`).
- C2 (Hand-written validation, no form libs): PASS — Validation is implemented manually via `validatePersonalInfo()` and `validateAddress()` functions using regex and string checks. No react-hook-form, formik, zod, or yup imported.
- C3 (Plain CSS, no Tailwind): PASS — Styles are defined via inline `<style>` tags with plain CSS class selectors. No Tailwind CSS classes used.
- C4 (No external deps): PASS — Only React is imported. No external npm packages used.
- C5 (Single file, export default): PASS — Single file with `export default function FormWizard()`.
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 4 — Well-structured multi-step form wizard with 3 steps (Personal Info → Address → Confirmation), per-step validation, forward/back navigation, summary review, and success screen. Validation rules are sensible (name length/alpha, email regex, phone digits, ZIP format). Minor issues: no real-time validation feedback (only on "Next" click); no field-level `onBlur` validation; the `disabled` attribute on Back button at step 0 doesn't have matching CSS for disabled state.

## Corrected Code
No correction needed.
