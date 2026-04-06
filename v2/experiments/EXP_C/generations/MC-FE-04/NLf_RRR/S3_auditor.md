## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces (PersonalInfo, Address, FormData, WizardState, etc.) and React (useState, useEffect, useCallback).
- C2 (Hand-written validation, no form libs): PASS — All validation is implemented manually via `validatePersonalInfo()` and `validateAddress()` functions using string checks, regex patterns, and length validation. No react-hook-form, formik, zod, or yup imported.
- C3 (Plain CSS, no Tailwind): PASS — Styles are implemented via a `<style>` tag injection using `injectStyles()`. This is plain CSS. No Tailwind CSS or utility-first framework used.
- C4 (No external deps): PASS — Only React and TypeScript are used. No external npm packages imported.
- C5 (Single file, export default): PASS — All code is in a single .tsx file ending with `export default FormWizard`.
- C6 (Code only): PASS — The file contains only code with structural section markers, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Implements a complete 3-step form wizard with step indicator (active/completed states), personal info form (name/email/phone), address form (street/city/state/zip), confirmation/review step, navigation (back/next/submit), real-time field validation with descriptive error messages, and a success screen. Validation covers required fields, format patterns (email, phone digits, ZIP code), and length minimums. Clean component architecture with InputField, StepIndicator, and step-specific sub-components.

## Corrected Code
No correction needed.
