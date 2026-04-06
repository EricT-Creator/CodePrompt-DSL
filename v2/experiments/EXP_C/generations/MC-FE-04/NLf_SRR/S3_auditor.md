## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces (`PersonalInfo`, `AddressInfo`, `Errors`) and React (`import React, { useState, useCallback } from "react"`).
- C2 (Hand-written validation, no form libs): PASS — Validation is implemented manually via `validatePersonal()` and `validateAddress()` functions with hand-written regex and length checks. No form library is imported.
- C3 (Plain CSS, no Tailwind): PASS — Styles are defined as a plain CSS string injected via `<style>{css}</style>`. No Tailwind CSS classes are used.
- C4 (No external deps): PASS — Only React and TypeScript are used. No external npm packages are imported.
- C5 (Single file, export default): PASS — All code is in a single file with `export default function FormWizard()`.
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Complete multi-step form wizard with step indicator, personal info and address forms, comprehensive validation (name, email, phone, street, city, state code, ZIP), real-time error clearing on input change, review/confirm step, simulated async submission, and success state. Clean component decomposition with `FormInput` and `StepIndicator` helpers.

## Corrected Code
No correction needed.
