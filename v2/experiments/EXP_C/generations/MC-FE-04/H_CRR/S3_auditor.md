## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript (`Step`, `PersonalInfo`, `Address`, `FormData`, `ValidationResult` types, typed hooks) and React functional components.
- C2 [!D]NO_FORM_LIB [VALID]HANDWRITE: PASS — Validation is fully hand-written (`validatePersonalInfo`, `validateAddress`, `validateStep`) using manual regex and string checks. No form library (react-hook-form, formik, etc.) is imported.
- C3 [Y]PLAIN_CSS [!Y]NO_TW: PASS — Styling uses plain CSS via inline style objects (`const css: Record<string, React.CSSProperties>`), which qualifies as plain CSS. No Tailwind classes used.
- C4 [D]NO_EXTERNAL: PASS — Only `react` is imported; no external dependencies.
- C5 [O]SFC [EXP]DEFAULT: PASS — `FormWizard` is a single functional component exported as `export default FormWizard`. Sub-component `Field` is also a SFC.
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with no extraneous narrative.

## Functionality Assessment (0-5)
Score: 5 — Fully functional multi-step form wizard with 3 steps (Personal Info → Address → Review & Confirm), per-field validation on blur, full-step validation on Next, step indicator with active/completed states, back navigation preserving data, summary view on step 3, and success screen on submit. Validation includes regex-based email and phone checks, ZIP code format, and state code length validation.

## Corrected Code
No correction needed.
