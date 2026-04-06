## Constraint Review
- C1 [L]TS [F]React: PASS — TypeScript types (`StepId`, `PersonalInfo`, `AddressInfo`, `FormData`, `ValidationErrors`, `FormState`) throughout; imports from `'react'`.
- C2 [!D]NO_FORM_LIB [VALID]HANDWRITE: PASS — No form library (Formik, react-hook-form, etc.) imported; all validation is hand-written with custom regex functions (`validateEmail`, `validatePhone`, `validateName`, `validateStreet`, `validateCity`, `validateState`, `validateZip`).
- C3 [Y]PLAIN_CSS [!Y]NO_TW: PASS — `import './FormWizard.css'`; all class names are plain CSS strings (`className="form-wizard"`, `className="step-indicator"`, etc.); no Tailwind utility classes.
- C4 [D]NO_EXTERNAL: PASS — Only `'react'` is imported; the CSS file is a local asset.
- C5 [O]SFC [EXP]DEFAULT: PASS — All React components (`StepIndicator`, `Step1`, `Step2`, `Step3`, `FormWizard`) are `React.FC` function components; file ends with `export default FormWizard`.
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with no explanatory prose outside of code comments.

## Functionality Assessment (0-5)
Score: 4 — Complete 3-step form wizard with step indicator (active/completed visual states), per-field validation on navigation (name, email, phone, street, city, state dropdown, ZIP), back/next navigation with validation gating, review/confirmation step, submit with success screen and reset. Minor issues: the `useEffect` tracking `visitedSteps` omits `visitedSteps` from its dependency array (stale closure risk with React strict mode), and the step indicator's `isCompleted`/`isClickable` variables are computed but `isClickable` is never used to enable step navigation. These are minor quality issues, not constraint violations.

## Corrected Code
No correction needed.
