# MC-FE-04: 3-Step Form Wizard - Technical Design

## Overview

This document outlines the technical design for a 3-step form wizard with validation: Personal Info (Step 1), Address (Step 2), and Confirmation (Step 3). Each step validates before allowing forward navigation.

## 1. Step State Machine Design

### State Machine Diagram

```
                    ┌─────────────────┐
         ┌─────────│   STEP_1_PERSONAL │◄────────┐
         │         │     (Initial)     │         │
         │         └─────────┬─────────┘         │
         │                   │ validate()        │
         │                   ▼                   │
         │         ┌─────────────────┐           │
         │    ┌────│   STEP_2_ADDRESS  │────┐    │
         │    │    └─────────┬─────────┘    │    │
         │    │              │ validate()   │    │
         │ back              ▼              │ back
         │    │    ┌─────────────────┐     │    │
         │    └───►│ STEP_3_CONFIRMATION │◄────┘
         │         └─────────┬─────────┘
         │                   │ submit()
         │                   ▼
         │         ┌─────────────────┐
         └────────►│    COMPLETED    │
                   └─────────────────┘
```

### Step Configuration

```typescript
const STEP_CONFIG = {
  1: {
    id: 'personal',
    title: 'Personal Info',
    fields: ['name', 'email', 'phone'],
    nextButton: 'Continue',
    prevButton: null
  },
  2: {
    id: 'address',
    title: 'Address',
    fields: ['street', 'city', 'state', 'zip'],
    nextButton: 'Continue',
    prevButton: 'Back'
  },
  3: {
    id: 'confirmation',
    title: 'Confirmation',
    fields: [], // Display only
    nextButton: 'Submit',
    prevButton: 'Back'
  }
} as const;
```

## 2. Validation Rules Per Step

### Step 1: Personal Info Validation

| Field | Rules | Error Message |
|-------|-------|---------------|
| name | Required, min 2 chars, letters/spaces only | "Name must be at least 2 characters" |
| email | Required, valid email format | "Please enter a valid email address" |
| phone | Required, 10+ digits | "Phone must have at least 10 digits" |

### Step 2: Address Validation

| Field | Rules | Error Message |
|-------|-------|---------------|
| street | Required, min 5 chars | "Street address is required" |
| city | Required, min 2 chars | "City is required" |
| state | Required, 2 chars (US state code) | "Please enter a valid state code" |
| zip | Required, 5 digits | "Please enter a valid 5-digit ZIP code" |

### Validation Implementation

```typescript
const validators: Record<string, (value: string) => string | null> = {
  name: (v) => {
    if (!v.trim()) return 'Name is required';
    if (v.trim().length < 2) return 'Name must be at least 2 characters';
    if (!/^[a-zA-Z\s]+$/.test(v)) return 'Name can only contain letters';
    return null;
  },
  email: (v) => {
    if (!v.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return 'Invalid email format';
    return null;
  },
  phone: (v) => {
    if (!v.trim()) return 'Phone is required';
    const digits = v.replace(/\D/g, '');
    if (digits.length < 10) return 'Phone must have at least 10 digits';
    return null;
  },
  // ... similar for address fields
};
```

## 3. Data Model

### TypeScript Interfaces

```typescript
interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface Address {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: Address;
}

interface FormErrors {
  personal: Partial<Record<keyof PersonalInfo, string>>;
  address: Partial<Record<keyof Address, string>>;
}

interface WizardState {
  currentStep: 1 | 2 | 3;
  formData: FormData;
  errors: FormErrors;
  touched: {
    personal: Record<keyof PersonalInfo, boolean>;
    address: Record<keyof Address, boolean>;
  };
  isSubmitting: boolean;
  isComplete: boolean;
}
```

### Initial State

```typescript
const initialState: WizardState = {
  currentStep: 1,
  formData: {
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' }
  },
  errors: {
    personal: {},
    address: {}
  },
  touched: {
    personal: { name: false, email: false, phone: false },
    address: { street: false, city: false, state: false, zip: false }
  },
  isSubmitting: false,
  isComplete: false
};
```

## 4. Navigation Flow

### Forward Navigation with Validation

```
1. User clicks "Continue"
2. Mark all current step fields as touched
3. Validate all current step fields
4. If errors exist:
   - Show error messages
   - Focus first error field
   - Stay on current step
5. If no errors:
   - Advance to next step
   - Update currentStep in state
```

### Back Navigation with Data Preservation

```
1. User clicks "Back"
2. No validation required
3. Decrement currentStep
4. All entered data remains in formData state
5. Previous step displays with saved values
```

### Step Component Rendering

```typescript
const renderStep = () => {
  switch (state.currentStep) {
    case 1:
      return <PersonalInfoStep 
        data={state.formData.personal}
        errors={state.errors.personal}
        touched={state.touched.personal}
        onChange={handleFieldChange}
      />;
    case 2:
      return <AddressStep 
        data={state.formData.address}
        errors={state.errors.address}
        touched={state.touched.address}
        onChange={handleFieldChange}
      />;
    case 3:
      return <ConfirmationStep formData={state.formData} />;
  }
};
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **TypeScript + React** | Full type annotations on all interfaces and component props |
| **Hand-written validation** | Custom validator functions for each field; no react-hook-form, formik, zod, or yup |
| **Plain CSS** | Use CSS file with class selectors; no Tailwind CSS classes |
| **No external npm packages** | Only React and TypeScript dependencies |
| **Single .tsx file** | All step components, validation logic, and types in one file with default export |
| **Output code only** | Design structured for direct implementation |

## Summary

This design implements a robust 3-step form wizard with manual validation and state management. The state machine approach ensures clear navigation rules: forward movement requires validation, backward movement preserves data. Hand-written validators provide full control over error messages and validation logic without external form libraries. The single-file structure keeps all components, types, and logic co-located for maintainability.
