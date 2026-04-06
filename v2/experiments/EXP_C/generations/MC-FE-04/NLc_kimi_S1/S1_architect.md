# MC-FE-04: 3-Step Form Wizard - Technical Design Document

## 1. Step State Machine Design

### State Machine Architecture

The form wizard implements a finite state machine with 3 primary states:

```typescript
type Step = 'personal' | 'address' | 'confirmation';

type WizardState = {
  currentStep: Step;
  formData: FormData;
  stepValidation: Record<Step, boolean>;
  touched: Record<string, boolean>;
};
```

### State Transitions

```
[Personal Info] --(valid)--> [Address] --(valid)--> [Confirmation] --(submit)--> [Complete]
     ↑                              ↑
     |________(back)_______________|________(back)_______________|
```

**Transition Rules:**
- Forward navigation: Only allowed if current step is valid
- Backward navigation: Always allowed, preserves all entered data
- Step indicator: Shows current position and completion status

### Navigation Controller

```typescript
interface NavigationState {
  canGoNext: boolean;
  canGoBack: boolean;
  isLastStep: boolean;
  isFirstStep: boolean;
}

const getNavigationState = (state: WizardState): NavigationState => ({
  canGoNext: state.stepValidation[state.currentStep],
  canGoBack: state.currentStep !== 'personal',
  isLastStep: state.currentStep === 'confirmation',
  isFirstStep: state.currentStep === 'personal'
});
```

## 2. Validation Rules per Step

### Step 1: Personal Info

**Fields:**
- `name`: Required, min 2 characters, alphabetic only
- `email`: Required, valid email format (regex)
- `phone`: Required, valid phone format (flexible: 10+ digits)

**Validation Schema:**
```typescript
const personalInfoRules = {
  name: {
    required: true,
    minLength: 2,
    pattern: /^[a-zA-Z\s]+$/
  },
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  },
  phone: {
    required: true,
    pattern: /^[\d\s\-\(\)\+]{10,}$/
  }
};
```

### Step 2: Address

**Fields:**
- `street`: Required, min 5 characters
- `city`: Required, min 2 characters
- `state`: Required, 2 characters (US state code)
- `zip`: Required, 5 digits or 5+4 format

**Validation Schema:**
```typescript
const addressRules = {
  street: {
    required: true,
    minLength: 5
  },
  city: {
    required: true,
    minLength: 2
  },
  state: {
    required: true,
    pattern: /^[A-Z]{2}$/i
  },
  zip: {
    required: true,
    pattern: /^\d{5}(-\d{4})?$/
  }
};
```

### Step 3: Confirmation

**Validation:**
- No input fields to validate
- Display summary of all entered data
- Final submit button triggers data collection

### Validation Engine

```typescript
interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

const validateField = (
  value: string,
  rules: ValidationRule
): string | null => {
  if (rules.required && !value.trim()) {
    return 'This field is required';
  }
  if (rules.minLength && value.length < rules.minLength) {
    return `Minimum ${rules.minLength} characters required`;
  }
  if (rules.pattern && !rules.pattern.test(value)) {
    return 'Invalid format';
  }
  return null;
};

const validateStep = (
  step: Step,
  formData: FormData
): ValidationResult => {
  const rules = getRulesForStep(step);
  const errors: Record<string, string> = {};
  
  for (const [field, rule] of Object.entries(rules)) {
    const value = formData[step][field] || '';
    const error = validateField(value, rule);
    if (error) errors[field] = error;
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
};
```

## 3. Data Model

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

interface WizardProps {
  onSubmit: (data: FormData) => void;
  initialData?: Partial<FormData>;
}

interface StepProps {
  data: PersonalInfo | Address;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  onChange: (field: string, value: string) => void;
  onBlur: (field: string) => void;
}
```

## 4. Navigation Flow

### Forward Navigation with Validation

```typescript
const handleNext = (): void => {
  const validation = validateStep(state.currentStep, state.formData);
  
  if (!validation.isValid) {
    // Mark all fields as touched to show errors
    dispatch({ type: 'MARK_STEP_TOUCHED', step: state.currentStep });
    return;
  }
  
  // Update validation state and proceed
  dispatch({ type: 'VALIDATE_STEP', step: state.currentStep, isValid: true });
  dispatch({ type: 'NEXT_STEP' });
};
```

### Backward Navigation Preserving Data

```typescript
const handleBack = (): void => {
  dispatch({ type: 'PREV_STEP' });
  // No data loss - formData remains intact
};
```

### Step Progress Indicator

```typescript
const StepIndicator: React.FC<{ currentStep: Step }> = ({ currentStep }) => {
  const steps: Step[] = ['personal', 'address', 'confirmation'];
  const stepLabels: Record<Step, string> = {
    personal: 'Personal Info',
    address: 'Address',
    confirmation: 'Confirmation'
  };
  
  return (
    <div className={styles.stepIndicator}>
      {steps.map((step, index) => (
        <div
          key={step}
          className={getStepClass(step, currentStep)}
        >
          <span className={styles.stepNumber}>{index + 1}</span>
          <span className={styles.stepLabel}>{stepLabels[step]}</span>
        </div>
      ))}
    </div>
  );
};
```

## 5. Constraint Acknowledgment

### TS + React
**Addressed by:** All components use TypeScript with strict typing. Interfaces defined for all data structures and component props.

### Hand-written validation, no formik/zod
**Addressed by:** Custom validation engine using pure TypeScript functions. No Formik, React Hook Form, Zod, or Yup libraries. Regex patterns and validation rules implemented manually.

### Plain CSS, no Tailwind
**Addressed by:** All styles in `.module.css` files. No Tailwind utility classes. CSS modules for scoped styling.

### No external deps
**Addressed by:** Only React and TypeScript as dependencies. No form validation or wizard libraries.

### Single file, export default
**Addressed by:** All wizard code in single `.tsx` file with `export default FormWizard`. Step components and validation logic co-located.

### Code only
**Addressed by:** Output contains only code. No markdown documentation in generated file.
