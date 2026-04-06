# MC-FE-04: Multi-Step Form Wizard — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Step State Machine Design

### 1.1 State Machine Diagram

```
[Step 1: Personal Info] --(valid)--> [Step 2: Address] --(valid)--> [Step 3: Confirmation]
       ^                                    ^
       |                                    |
     (back)                              (back)
```

### 1.2 Step States

```typescript
type Step = 1 | 2 | 3;

type WizardState = 
  | { step: 1; data: PersonalInfo }
  | { step: 2; data: PersonalInfo & Address }
  | { step: 3; data: PersonalInfo & Address & { confirmed: boolean } };
```

### 1.3 Navigation Rules

| From | To | Condition |
|------|-----|-----------|
| Step 1 | Step 2 | All personal fields valid |
| Step 2 | Step 3 | All address fields valid |
| Step 2 | Step 1 | Always allowed (preserve data) |
| Step 3 | Step 2 | Always allowed |
| Step 3 | Submit | Confirmation acknowledged |

---

## 2. Validation Rules Per Step

### 2.1 Step 1: Personal Info

| Field | Rule | Error Message |
|-------|------|---------------|
| `name` | Required, min 2 chars | "Name is required" |
| `email` | Required, valid email format | "Valid email required" |
| `phone` | Required, 10+ digits | "Valid phone required" |

### 2.2 Step 2: Address

| Field | Rule | Error Message |
|-------|------|---------------|
| `street` | Required | "Street is required" |
| `city` | Required | "City is required" |
| `state` | Required, 2 chars | "State code required" |
| `zip` | Required, 5 digits | "Valid ZIP required" |

### 2.3 Validation Timing

- **On blur**: Validate individual field, show inline error
- **On next**: Validate all step fields, block if invalid
- **On back**: No validation, preserve all data

---

## 3. Data Model (TypeScript Interfaces)

```typescript
// Step 1 data
interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

// Step 2 data
interface Address {
  street: string;
  city: string;
  state: string;
  zip: string;
}

// Complete form data
interface FormData extends PersonalInfo, Address {}

// Wizard state
interface WizardState {
  currentStep: Step;
  formData: Partial<FormData>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
}

// Validation result
interface ValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}
```

---

## 4. Navigation Flow

### 4.1 Forward Navigation

```typescript
function handleNext() {
  const result = validateStep(currentStep, formData);
  
  if (!result.valid) {
    setErrors(result.errors);
    return; // Block navigation
  }
  
  if (currentStep < 3) {
    setCurrentStep(currentStep + 1);
  }
}
```

### 4.2 Backward Navigation

```typescript
function handleBack() {
  if (currentStep > 1) {
    setCurrentStep(currentStep - 1);
  }
  // No validation, data preserved
}
```

### 4.3 Data Preservation

- Form data stored in parent state
- Each step receives `initialData` prop
- Changes bubble up via `onChange` callback
- Data persists across step transitions

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]TS` | All interfaces typed; strict validation types |
| `[F]React` | Functional components with hooks |
| `[!D]NO_FORM_LIB` | No react-hook-form or formik; hand-written validation |
| `[VALID]HANDWRITE` | Custom validation functions per field |
| `[Y]PLAIN_CSS` | Regular CSS files (not modules) |
| `[!Y]NO_TW` | No Tailwind classes |
| `[D]NO_EXTERNAL` | No external form libraries |
| `[O]SFC` | Single file default export |
| `[EXP]DEFAULT` | `export default FormWizard` |
| `[OUT]CODE_ONLY` | Output will be code only |

---

## 6. Component Structure

```
FormWizard
├── StepIndicator (1-2-3 progress)
├── StepContent (conditional render)
│   ├── PersonalInfoStep
│   ├── AddressStep
│   └── ConfirmationStep
└── NavigationButtons
    ├── BackButton (hidden on step 1)
    └── Next/SubmitButton
```

---

## 7. File Structure

```
MC-FE-04/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
├── S2_developer/
│   └── FormWizard.tsx
├── FormWizard.css
└── types.ts
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
