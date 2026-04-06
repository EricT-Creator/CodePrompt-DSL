# Technical Design Document: Multi-Step Form Wizard

**Task**: MC-FE-04  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]TS [F]React [!D]NO_FORM_LIB [VALID]HANDWRITE [Y]PLAIN_CSS [!Y]NO_TW [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [OUT]CODE_ONLY`

---

## 1. Step State Machine Design

### States and Transitions

The form wizard is modeled as a finite state machine with three states:

```
STEP_1 (Personal Info) → STEP_2 (Address) → STEP_3 (Confirmation)
```

**Transition rules**:
- **Forward** (`STEP_N → STEP_N+1`): Only allowed if all fields in `STEP_N` pass validation.
- **Backward** (`STEP_N → STEP_N-1`): Always allowed. All entered data is preserved.
- **Submit** (from `STEP_3`): Collects all data from steps 1–3 and triggers the final submission.

### State Representation

```
type StepId = 1 | 2 | 3;

interface WizardNavState {
  currentStep: StepId;
  visitedSteps: Set<StepId>;  // tracks which steps have been visited
}
```

The `currentStep` is managed inside the component via a simple numeric state. Navigation functions (`goNext`, `goBack`) encapsulate the validation-then-transition logic.

### Step Rendering

A `switch` on `currentStep` determines which step UI to render. All three steps are **not** unmounted — the data lives in a single form state object that persists across step transitions. Only the visible UI changes.

---

## 2. Validation Rules Per Step

### Step 1: Personal Info

| Field | Type | Rules |
|-------|------|-------|
| `name` | `string` | Required. Min 2 characters. Only letters, spaces, hyphens. |
| `email` | `string` | Required. Must match email regex pattern (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`). |
| `phone` | `string` | Required. Must be 10–15 digits (allows optional leading `+`). |

### Step 2: Address

| Field | Type | Rules |
|-------|------|-------|
| `street` | `string` | Required. Min 5 characters. |
| `city` | `string` | Required. Min 2 characters. |
| `state` | `string` | Required. Exactly 2 uppercase letters (US state abbreviation). |
| `zip` | `string` | Required. Must match 5-digit or 5+4 ZIP format (`/^\d{5}(-\d{4})?$/`). |

### Step 3: Confirmation

No input validation — this step is read-only. It displays all data from steps 1 and 2 for review.

### Validation Engine

A pure function `validateStep(step: StepId, data: FormData): ValidationErrors` runs all rules for the given step and returns a map of `{ fieldName: errorMessage }`. If the map is empty, validation passes.

Validation is triggered:
1. On **forward navigation** attempt — blocks transition if errors exist.
2. On **field blur** (optional enhancement) — shows errors as user tabs through fields.
3. Errors are cleared field-by-field as the user corrects input.

---

## 3. Data Model (TypeScript Interfaces)

```
interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface AddressInfo {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

type ValidationErrors = Record<string, string>;

interface FormState {
  data: FormData;
  errors: {
    step1: ValidationErrors;
    step2: ValidationErrors;
  };
  currentStep: StepId;
  submitted: boolean;
}
```

### Initial State

```
const initialState: FormState = {
  data: {
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  },
  errors: { step1: {}, step2: {} },
  currentStep: 1,
  submitted: false,
};
```

---

## 4. Navigation Flow

### Forward with Validation

```
function goNext():
  errors = validateStep(currentStep, formData)
  if errors is not empty:
    set errors for current step → show inline messages
    return (block navigation)
  clear errors for current step
  set currentStep = currentStep + 1
```

### Backward Preserving Data

```
function goBack():
  set currentStep = currentStep - 1
  // No validation, no data clearing
  // Form fields repopulate from the persistent formData object
```

**Key design**: The `FormData` object is a **single source of truth** that persists across all step transitions. It is never cleared or reset when navigating backward. Each input field is bound to its corresponding `formData` property via controlled component pattern (`value={formData.personal.name}` + `onChange`).

### Final Submit

```
function handleSubmit():
  // Step 3 has no fields to validate
  // Collect formData.personal + formData.address
  console.log('Submitted:', formData)
  set submitted = true
  // Show success message
```

### Step Progress Indicator

A simple progress bar / step indicator at the top of the wizard shows:
- Step numbers (1, 2, 3)
- Current step highlighted
- Completed steps marked with a checkmark
- Clickable only for visited, validated steps (optional enhancement)

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: TypeScript | `[L]TS` | All interfaces, state, validation functions, and event handlers fully typed in TypeScript. |
| Framework: React | `[F]React` | Built with React functional component and hooks (`useState` for form data and step, or a single state object). |
| No form library | `[!D]NO_FORM_LIB` | No react-hook-form, Formik, or any form management library. All form state is manual. |
| Handwritten validation | `[VALID]HANDWRITE` | All validation rules implemented as pure functions with regex and conditional checks. No Yup, Zod, or Joi. |
| Plain CSS | `[Y]PLAIN_CSS` | Styles written in a plain `.css` file. Class names are simple strings (not CSS Modules, not Tailwind). |
| No Tailwind | `[!Y]NO_TW` | Zero Tailwind utility classes anywhere in the component or styles. |
| No external dependencies | `[D]NO_EXTERNAL` | Only React and TypeScript. Validation regex, debounce, and all logic are hand-implemented. |
| Single Functional Component | `[O]SFC` | `FormWizard` is the sole exported component. Step sub-components are internal functions. |
| Default export | `[EXP]DEFAULT` | `export default function FormWizard() {...}` |
| Code only output | `[OUT]CODE_ONLY` | Final S2 deliverable will be pure code. This S1 document is the design phase. |
