# Technical Design Document — Multi-Step Form Wizard

## 1. Overview

A three-step form wizard collecting personal information, address details, and displaying a confirmation summary. Each step enforces field-level validation before allowing forward navigation. Back navigation preserves all entered data. Final submission aggregates the complete dataset.

## 2. Step State Machine Design

The wizard is modeled as a simple finite state machine:

```
States: STEP_1 → STEP_2 → STEP_3
Transitions:
  NEXT (STEP_1 → STEP_2): requires STEP_1 fields valid
  NEXT (STEP_2 → STEP_3): requires STEP_2 fields valid
  BACK (STEP_2 → STEP_1): unconditional, data preserved
  BACK (STEP_3 → STEP_2): unconditional, data preserved
  SUBMIT (STEP_3 → done): collects all data, triggers callback
```

A numeric `currentStep` (1 | 2 | 3) drives which sub-form renders. The state machine transition function validates before incrementing and always allows decrementing.

## 3. Component Architecture

### 3.1 `FormWizard` (root, export default)
- Manages `currentStep`, `formData`, and `errors` as local state.
- Renders the active step component and navigation buttons (Back / Next / Submit).
- Calls the step-specific validator on "Next" click; blocks transition if errors exist.

### 3.2 `StepPersonal`
- Fields: Name (text), Email (text), Phone (text).
- Receives current values + error messages + onChange handler from parent.

### 3.3 `StepAddress`
- Fields: Street (text), City (text), State (dropdown or text), Zip (text).
- Same prop contract as StepPersonal.

### 3.4 `StepConfirmation`
- Read-only display of all collected fields grouped by step.
- Shows a "Submit" button instead of "Next".

### 3.5 `FieldError`
- Small inline component that renders a red error message below its field when present.

## 4. Validation Rules Per Step

### Step 1 — Personal Info
| Field | Rule | Error Message |
|-------|------|---------------|
| Name | Non-empty, ≥ 2 characters | "Name is required and must be at least 2 characters" |
| Email | Non-empty, matches `/^[^\s@]+@[^\s@]+\.[^\s@]+$/` | "Valid email is required" |
| Phone | Non-empty, matches `/^\+?[\d\s\-()]{7,15}$/` | "Valid phone number is required" |

### Step 2 — Address
| Field | Rule | Error Message |
|-------|------|---------------|
| Street | Non-empty | "Street address is required" |
| City | Non-empty, ≥ 2 characters | "City is required" |
| State | Non-empty | "State is required" |
| Zip | Non-empty, matches `/^\d{5}(-\d{4})?$/` | "Valid ZIP code is required" |

### Step 3 — Confirmation
No field-level validation. The user reviews data and clicks Submit.

### Validation Execution
- Each step has a pure function `validateStep(step, data) → errors` that returns a `Record<string, string>`.
- On "Next" click, `validateStep` runs; if the returned object has any keys, errors are set in state and the step transition is blocked.
- Errors clear on the next validation pass or when the user modifies the offending field.

## 5. Data Model

### Interfaces

- **PersonalInfo**: `{ name: string; email: string; phone: string }`
- **AddressInfo**: `{ street: string; city: string; state: string; zip: string }`
- **FormData**: `{ personal: PersonalInfo; address: AddressInfo }`
- **FormErrors**: `{ [field: string]: string }`
- **WizardState**: `{ currentStep: 1 | 2 | 3; formData: FormData; errors: FormErrors; submitted: boolean }`

All state is held in the parent `FormWizard`. Child step components are controlled — they receive values and call back on change.

## 6. Navigation Flow

### Forward Navigation (Next)
1. User clicks "Next".
2. `validateStep(currentStep, formData)` executes.
3. If errors exist → set `errors` state, remain on current step, scroll to first error.
4. If valid → clear errors, increment `currentStep`.

### Backward Navigation (Back)
1. User clicks "Back".
2. Decrement `currentStep` unconditionally.
3. `formData` is untouched — all previously entered values are still present because they are stored in the parent's single state object, not in step-local state.

### Final Submit
1. On Step 3, user clicks "Submit".
2. `formData` is serialized (or passed to a callback / logged to console).
3. `submitted` flag is set to `true`; a success message replaces the form.

### Data Preservation Guarantee
Because `FormData` lives in `FormWizard`'s state (not inside individual step components), navigating back and forth never loses data. Step components are pure controlled renders of whatever `formData` currently holds.

## 7. Styling Approach

- Plain CSS with a single stylesheet (no modules needed for a single file, but a co-located `.css` is acceptable).
- Step indicator bar at top: three numbered circles connected by a line; active step is highlighted.
- Form fields use standard block layout with labels above inputs.
- Error messages are red, 12px, displayed directly below the input.
- Buttons are styled with primary (Next/Submit) and secondary (Back) visual distinction.

## 8. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **TS + React** | All components written as TypeScript React functional components with explicit interface typing. |
| 2 | **Hand-written validation, no formik/zod** | All validation logic is implemented as pure functions with regex and conditional checks. No form library or schema validation library is used. |
| 3 | **Plain CSS, no Tailwind** | Styling uses a plain `.css` file. No Tailwind, CSS-in-JS, or utility-class framework. |
| 4 | **No external deps** | Zero third-party package imports. Only React and ReactDOM. |
| 5 | **Single file, export default** | All components, validation functions, and type definitions are in one `.tsx` file with `export default FormWizard`. |
| 6 | **Code only** | The implementation deliverable will be pure source code output. |
