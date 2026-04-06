# Technical Design Document — Multi-Step Form Wizard

## 1. Overview

This document describes the architecture for a 3-step form wizard. Step 1 collects personal information (name, email, phone), Step 2 collects address details (street, city, state, zip), and Step 3 displays a confirmation summary of all entered data. Each step validates its fields before allowing forward navigation. Back navigation preserves entered data. A final submit action collects all data.

## 2. Step State Machine Design

### 2.1 States

The wizard operates as a linear state machine with three states:

```
[PERSONAL_INFO] → [ADDRESS] → [CONFIRMATION]
```

- **PERSONAL_INFO** (Step 1): Entry state. Forward transition requires validation pass.
- **ADDRESS** (Step 2): Forward transition requires validation pass. Back transition always allowed.
- **CONFIRMATION** (Step 3): Read-only display. Back transition always allowed. Submit action triggers final data collection.

### 2.2 Transitions

| From | To | Trigger | Guard |
|------|----|---------|-------|
| PERSONAL_INFO | ADDRESS | "Next" click | All Step 1 fields valid |
| ADDRESS | CONFIRMATION | "Next" click | All Step 2 fields valid |
| ADDRESS | PERSONAL_INFO | "Back" click | None (always allowed) |
| CONFIRMATION | ADDRESS | "Back" click | None (always allowed) |
| CONFIRMATION | (submitted) | "Submit" click | None (data already validated) |

### 2.3 State Representation

A `currentStep` value (0, 1, or 2) tracks which step is active. Navigation simply increments or decrements this value, guarded by validation for forward moves.

## 3. Validation Rules Per Step

### 3.1 Step 1 — Personal Info

| Field | Rules |
|-------|-------|
| name | Required, minimum 2 characters, letters and spaces only |
| email | Required, must match a basic email pattern (contains `@` and `.` after `@`) |
| phone | Required, digits only (after stripping dashes/spaces), 10–15 digits |

### 3.2 Step 2 — Address

| Field | Rules |
|-------|-------|
| street | Required, minimum 5 characters |
| city | Required, minimum 2 characters, letters and spaces only |
| state | Required, minimum 2 characters |
| zip | Required, 5 digits (US format) or 5+4 format (XXXXX or XXXXX-XXXX) |

### 3.3 Step 3 — Confirmation

No validation. This step is display-only. All data was validated in prior steps.

### 3.4 Validation Behavior

- Validation runs on "Next" button click (not on every keystroke).
- Per-field error messages are displayed below each invalid field.
- Fields that pass validation show no indicator (clean state).
- All errors for the current step are shown simultaneously (not one at a time).

## 4. Data Model

### 4.1 Interfaces

- **PersonalInfo**: `{ name: string; email: string; phone: string }`
- **Address**: `{ street: string; city: string; state: string; zip: string }`
- **FormData**: `{ personalInfo: PersonalInfo; address: Address }`
- **FieldErrors**: `{ [fieldName: string]: string }` — maps field names to error messages.
- **WizardState**: `{ currentStep: number; formData: FormData; errors: FieldErrors; isSubmitted: boolean }`

### 4.2 Initial State

All fields initialized to empty strings. `currentStep = 0`. `errors = {}`. `isSubmitted = false`.

## 5. Navigation Flow

### 5.1 Forward with Validation

1. User clicks "Next" on Step 1.
2. Run `validatePersonalInfo(formData.personalInfo)`.
3. If errors exist: set `errors` state, remain on Step 1.
4. If no errors: clear `errors`, set `currentStep = 1`.

Same pattern for Step 2 → Step 3.

### 5.2 Backward Preserving Data

1. User clicks "Back" on Step 2.
2. Set `currentStep = 0`. No validation. No data reset.
3. Step 1 fields still contain previously entered values.

Data is preserved because `formData` is never cleared during navigation. Each step reads from and writes to the same `formData` object.

### 5.3 Final Submit

1. User clicks "Submit" on Step 3.
2. The complete `FormData` object (personalInfo + address) is collected.
3. A simulated submission occurs (e.g., `console.log` or display a success message).
4. `isSubmitted` is set to `true`, optionally showing a success screen.

## 6. Component Architecture

### 6.1 Component Tree

- **FormWizard** (root): Owns `WizardState`. Renders the step indicator and the active step component. Exported as default.
  - **StepIndicator**: Displays step numbers (1, 2, 3) with visual highlighting for the current step and completed steps.
  - **PersonalInfoStep**: Renders name, email, phone inputs. Receives field values and errors as props.
  - **AddressStep**: Renders street, city, state, zip inputs. Same prop pattern.
  - **ConfirmationStep**: Displays all data in a read-only summary layout.
  - **NavigationButtons**: Renders "Back" and/or "Next"/"Submit" buttons based on current step.

### 6.2 Data Flow

- **FormWizard** holds `formData` and `errors` in local state.
- Each step component receives its relevant slice of `formData` and an `onChange` callback.
- `onChange` updates the corresponding fields in `formData`.
- "Next" triggers the validation function for the current step.
- "Back" simply decrements `currentStep`.

## 7. Styling Approach

All styles use plain CSS via `<style>` tags within the single .tsx file. The form uses a centered card layout with consistent spacing, clear field labels, visible error messages in red, and a step indicator bar at the top.

## 8. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | TypeScript with React | All components are typed React functional components. PersonalInfo, Address, FormData, FieldErrors, and WizardState are TypeScript interfaces. |
| 2 | Hand-written form validation, no react-hook-form/formik/zod/yup | All validation logic is implemented as pure functions (e.g., `validatePersonalInfo`, `validateAddress`) using string methods and regex. No form or validation library is imported. |
| 3 | Plain CSS styling, no Tailwind | Styles are defined in `<style>` tags using plain CSS selectors. No Tailwind utility classes are used. |
| 4 | No external npm packages beyond React and TypeScript | Only React and TypeScript are used. Validation, navigation logic, and step state machine are all hand-written. |
| 5 | Single .tsx file with export default | The entire wizard — components, validation functions, interfaces, styles — lives in one file. `export default FormWizard`. |
| 6 | Output code only, no explanation text | The final implementation deliverable will contain only code. This document serves as the design phase artifact. |
