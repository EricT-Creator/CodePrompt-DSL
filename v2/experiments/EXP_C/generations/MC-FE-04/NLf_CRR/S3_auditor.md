## Constraint Review
- C1 (TS + React): PASS — File imports `React, { useReducer, useRef, useCallback } from 'react'` with full TypeScript interfaces (`PersonalInfo`, `Address`, `FormData`, `WizardState`, etc.).
- C2 (Hand-written validation, no form libs): PASS — Validation implemented via custom `validators` record with regex-based checks (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, `/^\d{5}$/`, etc.) and `validateSection()` function. No react-hook-form, formik, zod, or yup imported.
- C3 (Plain CSS, no Tailwind): FAIL — Styles are defined as `const css: Record<string, React.CSSProperties> = { ... }` and applied via `style={css.wrapper}` (inline style objects). The constraint requires "plain CSS (style tags or CSS files)", not inline styles.
- C4 (No external deps): PASS — Only `React` is imported; no external npm packages.
- C5 (Single file, export default): PASS — `export default FormWizard` at end of file.
- C6 (Code only): PASS — No explanatory prose; file contains only executable code.

## Functionality Assessment (0-5)
Score: 5 — Full 3-step form wizard with personal info, address, and confirmation steps. Features include: per-field real-time validation on blur, touch tracking, step navigation with validation gates, summary review, simulated async submission, success screen with reset, and clean stepper UI. All validators are thorough (email regex, phone digit count, state code, ZIP format).

## Corrected Code
```tsx
import React, { useReducer, useRef, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

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

interface TouchedFields {
  personal: Record<keyof PersonalInfo, boolean>;
  address: Record<keyof Address, boolean>;
}

interface WizardState {
  currentStep: 1 | 2 | 3;
  formData: FormData;
  errors: FormErrors;
  touched: TouchedFields;
  isSubmitting: boolean;
  isComplete: boolean;
}

type WizardAction =
  | { type: 'SET_PERSONAL_FIELD'; field: keyof PersonalInfo; value: string }
  | { type: 'SET_ADDRESS_FIELD'; field: keyof Address; value: string }
  | { type: 'TOUCH_FIELD'; section: 'personal' | 'address'; field: string }
  | { type: 'TOUCH_ALL_CURRENT' }
  | { type: 'SET_ERRORS'; errors: FormErrors }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_COMPLETE' }
  | { type: 'RESET' };

// ─── Validators ──────────────────────────────────────────────────────────────

const validators: Record<string, (value: string) => string | null> = {
  name: (v: string) => {
    if (!v.trim()) return 'Name is required';
    if (v.trim().length < 2) return 'Name must be at least 2 characters';
    if (!/^[a-zA-Z\s]+$/.test(v.trim())) return 'Name can only contain letters and spaces';
    return null;
  },
  email: (v: string) => {
    if (!v.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())) return 'Please enter a valid email address';
    return null;
  },
  phone: (v: string) => {
    if (!v.trim()) return 'Phone is required';
    const digits = v.replace(/\D/g, '');
    if (digits.length < 10) return 'Phone must have at least 10 digits';
    return null;
  },
  street: (v: string) => {
    if (!v.trim()) return 'Street address is required';
    if (v.trim().length < 5) return 'Street must be at least 5 characters';
    return null;
  },
  city: (v: string) => {
    if (!v.trim()) return 'City is required';
    if (v.trim().length < 2) return 'City must be at least 2 characters';
    return null;
  },
  state: (v: string) => {
    if (!v.trim()) return 'State is required';
    if (!/^[A-Za-z]{2}$/.test(v.trim())) return 'Please enter a valid 2-letter state code';
    return null;
  },
  zip: (v: string) => {
    if (!v.trim()) return 'ZIP code is required';
    if (!/^\d{5}$/.test(v.trim())) return 'Please enter a valid 5-digit ZIP code';
    return null;
  },
};

function validateSection(section: 'personal' | 'address', data: PersonalInfo | Address): Partial<Record<string, string>> {
  const errors: Partial<Record<string, string>> = {};
  for (const [field, value] of Object.entries(data)) {
    const validator = validators[field];
    if (validator) {
      const error = validator(value as string);
      if (error) errors[field] = error;
    }
  }
  return errors;
}

// ─── Styles (plain CSS via <style> tag) ──────────────────────────────────────

const cssText = `
.wizardWrapper {
  font-family: 'Segoe UI', system-ui, sans-serif;
  max-width: 560px;
  margin: 40px auto;
  padding: 20px;
}
.wizardCard {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.08);
  overflow: hidden;
}
.stepper {
  display: flex;
  background: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
}
.step {
  flex: 1;
  text-align: center;
  padding: 16px 8px;
  font-size: 13px;
  font-weight: 600;
  color: #999;
  position: relative;
  transition: all 0.2s;
}
.stepActive { color: #1a73e8; background: #e8f0fe; }
.stepDone { color: #34a853; background: #e6f4ea; }
.stepNumber {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e0e0e0;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 4px;
}
.stepNumberActive { background: #1a73e8; }
.stepNumberDone { background: #34a853; }
.wizardBody { padding: 28px 32px; }
.wizardTitle {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin-top: 0;
  margin-bottom: 20px;
}
.formGroup { margin-bottom: 16px; }
.formLabel {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #444;
  margin-bottom: 6px;
}
.formInput {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.formInputError { border-color: #e53935; }
.errorText { font-size: 12px; color: #e53935; margin-top: 4px; }
.wizardActions {
  display: flex;
  justify-content: space-between;
  padding: 0 32px 28px;
}
.btnPrimary {
  padding: 10px 28px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btnSecondary {
  padding: 10px 28px;
  background: #f0f2f5;
  color: #555;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btnDisabled { opacity: 0.5; cursor: not-allowed; }
.summarySection { margin-bottom: 16px; }
.summaryTitle {
  font-size: 14px;
  font-weight: 700;
  color: #444;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #eee;
}
.summaryRow {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
  color: #555;
}
.summaryLabel { color: #999; }
.successPanel { text-align: center; padding: 40px 20px; }
.successIcon { font-size: 48px; margin-bottom: 16px; }
.successText { font-size: 20px; font-weight: 700; color: #34a853; margin-bottom: 8px; }
.flexRow { display: flex; gap: 12px; }
.flexChild { flex: 1; }
`;

let styleInjected = false;
function injectWizardStyles(): void {
  if (styleInjected) return;
  styleInjected = true;
  const el = document.createElement('style');
  el.textContent = cssText;
  document.head.appendChild(el);
}

// ─── Reducer ─────────────────────────────────────────────────────────────────

const initialState: WizardState = {
  currentStep: 1,
  formData: {
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  },
  errors: {
    personal: {},
    address: {},
  },
  touched: {
    personal: { name: false, email: false, phone: false },
    address: { street: false, city: false, state: false, zip: false },
  },
  isSubmitting: false,
  isComplete: false,
};

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_PERSONAL_FIELD':
      return {
        ...state,
        formData: {
          ...state.formData,
          personal: { ...state.formData.personal, [action.field]: action.value },
        },
      };
    case 'SET_ADDRESS_FIELD':
      return {
        ...state,
        formData: {
          ...state.formData,
          address: { ...state.formData.address, [action.field]: action.value },
        },
      };
    case 'TOUCH_FIELD': {
      const section = action.section;
      return {
        ...state,
        touched: {
          ...state.touched,
          [section]: { ...state.touched[section], [action.field]: true },
        },
      };
    }
    case 'TOUCH_ALL_CURRENT': {
      if (state.currentStep === 1) {
        return { ...state, touched: { ...state.touched, personal: { name: true, email: true, phone: true } } };
      }
      if (state.currentStep === 2) {
        return { ...state, touched: { ...state.touched, address: { street: true, city: true, state: true, zip: true } } };
      }
      return state;
    }
    case 'SET_ERRORS':
      return { ...state, errors: action.errors };
    case 'NEXT_STEP':
      return { ...state, currentStep: Math.min(state.currentStep + 1, 3) as 1 | 2 | 3 };
    case 'PREV_STEP':
      return { ...state, currentStep: Math.max(state.currentStep - 1, 1) as 1 | 2 | 3 };
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true };
    case 'SUBMIT_COMPLETE':
      return { ...state, isSubmitting: false, isComplete: true };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

// ─── Step Components ─────────────────────────────────────────────────────────

const FormField: React.FC<{
  label: string;
  value: string;
  error?: string;
  touched: boolean;
  placeholder?: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  inputRef?: React.Ref<HTMLInputElement>;
}> = ({ label, value, error, touched, placeholder, onChange, onBlur, inputRef }) => (
  <div className="formGroup">
    <label className="formLabel">{label}</label>
    <input
      ref={inputRef}
      className={`formInput${touched && error ? ' formInputError' : ''}`}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
    />
    {touched && error && <div className="errorText">{error}</div>}
  </div>
);

const PersonalInfoStep: React.FC<{
  data: PersonalInfo;
  errors: Partial<Record<keyof PersonalInfo, string>>;
  touched: Record<keyof PersonalInfo, boolean>;
  dispatch: React.Dispatch<WizardAction>;
}> = ({ data, errors, touched, dispatch }) => {
  const firstRef = useRef<HTMLInputElement>(null);
  return (
    <div>
      <h2 className="wizardTitle">Personal Information</h2>
      <FormField
        label="Full Name" value={data.name} error={errors.name} touched={touched.name}
        placeholder="John Doe"
        onChange={(v) => dispatch({ type: 'SET_PERSONAL_FIELD', field: 'name', value: v })}
        onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'personal', field: 'name' })}
        inputRef={firstRef}
      />
      <FormField
        label="Email Address" value={data.email} error={errors.email} touched={touched.email}
        placeholder="john@example.com"
        onChange={(v) => dispatch({ type: 'SET_PERSONAL_FIELD', field: 'email', value: v })}
        onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'personal', field: 'email' })}
      />
      <FormField
        label="Phone Number" value={data.phone} error={errors.phone} touched={touched.phone}
        placeholder="(555) 123-4567"
        onChange={(v) => dispatch({ type: 'SET_PERSONAL_FIELD', field: 'phone', value: v })}
        onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'personal', field: 'phone' })}
      />
    </div>
  );
};

const AddressStep: React.FC<{
  data: Address;
  errors: Partial<Record<keyof Address, string>>;
  touched: Record<keyof Address, boolean>;
  dispatch: React.Dispatch<WizardAction>;
}> = ({ data, errors, touched, dispatch }) => (
  <div>
    <h2 className="wizardTitle">Address</h2>
    <FormField
      label="Street Address" value={data.street} error={errors.street} touched={touched.street}
      placeholder="123 Main Street"
      onChange={(v) => dispatch({ type: 'SET_ADDRESS_FIELD', field: 'street', value: v })}
      onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'address', field: 'street' })}
    />
    <FormField
      label="City" value={data.city} error={errors.city} touched={touched.city}
      placeholder="New York"
      onChange={(v) => dispatch({ type: 'SET_ADDRESS_FIELD', field: 'city', value: v })}
      onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'address', field: 'city' })}
    />
    <div className="flexRow">
      <div className="flexChild">
        <FormField
          label="State" value={data.state} error={errors.state} touched={touched.state}
          placeholder="NY"
          onChange={(v) => dispatch({ type: 'SET_ADDRESS_FIELD', field: 'state', value: v })}
          onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'address', field: 'state' })}
        />
      </div>
      <div className="flexChild">
        <FormField
          label="ZIP Code" value={data.zip} error={errors.zip} touched={touched.zip}
          placeholder="10001"
          onChange={(v) => dispatch({ type: 'SET_ADDRESS_FIELD', field: 'zip', value: v })}
          onBlur={() => dispatch({ type: 'TOUCH_FIELD', section: 'address', field: 'zip' })}
        />
      </div>
    </div>
  </div>
);

const ConfirmationStep: React.FC<{ formData: FormData }> = ({ formData }) => (
  <div>
    <h2 className="wizardTitle">Confirm Your Information</h2>
    <div className="summarySection">
      <div className="summaryTitle">Personal Info</div>
      <div className="summaryRow"><span className="summaryLabel">Name</span><span>{formData.personal.name}</span></div>
      <div className="summaryRow"><span className="summaryLabel">Email</span><span>{formData.personal.email}</span></div>
      <div className="summaryRow"><span className="summaryLabel">Phone</span><span>{formData.personal.phone}</span></div>
    </div>
    <div className="summarySection">
      <div className="summaryTitle">Address</div>
      <div className="summaryRow"><span className="summaryLabel">Street</span><span>{formData.address.street}</span></div>
      <div className="summaryRow"><span className="summaryLabel">City</span><span>{formData.address.city}</span></div>
      <div className="summaryRow"><span className="summaryLabel">State</span><span>{formData.address.state}</span></div>
      <div className="summaryRow"><span className="summaryLabel">ZIP</span><span>{formData.address.zip}</span></div>
    </div>
  </div>
);

// ─── Main Component ──────────────────────────────────────────────────────────

const FormWizard: React.FC = () => {
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  React.useEffect(() => {
    injectWizardStyles();
  }, []);

  const stepLabels = ['Personal Info', 'Address', 'Confirmation'];

  const handleNext = useCallback(() => {
    dispatch({ type: 'TOUCH_ALL_CURRENT' });
    let sectionErrors: Partial<Record<string, string>> = {};
    if (state.currentStep === 1) {
      sectionErrors = validateSection('personal', state.formData.personal);
    } else if (state.currentStep === 2) {
      sectionErrors = validateSection('address', state.formData.address);
    }
    const newErrors: FormErrors = { ...state.errors };
    if (state.currentStep === 1) {
      newErrors.personal = sectionErrors as Partial<Record<keyof PersonalInfo, string>>;
    } else if (state.currentStep === 2) {
      newErrors.address = sectionErrors as Partial<Record<keyof Address, string>>;
    }
    dispatch({ type: 'SET_ERRORS', errors: newErrors });
    if (Object.keys(sectionErrors).length === 0) {
      dispatch({ type: 'NEXT_STEP' });
    }
  }, [state.currentStep, state.formData, state.errors]);

  const handleSubmit = useCallback(() => {
    dispatch({ type: 'SUBMIT_START' });
    setTimeout(() => {
      dispatch({ type: 'SUBMIT_COMPLETE' });
    }, 1000);
  }, []);

  const liveValidate = useCallback(() => {
    const newErrors: FormErrors = {
      personal: validateSection('personal', state.formData.personal) as Partial<Record<keyof PersonalInfo, string>>,
      address: validateSection('address', state.formData.address) as Partial<Record<keyof Address, string>>,
    };
    dispatch({ type: 'SET_ERRORS', errors: newErrors });
  }, [state.formData]);

  React.useEffect(() => {
    liveValidate();
  }, [liveValidate]);

  if (state.isComplete) {
    return (
      <div className="wizardWrapper">
        <div className="wizardCard">
          <div className="successPanel">
            <div className="successIcon">✅</div>
            <div className="successText">Submission Complete!</div>
            <p style={{ color: '#666', fontSize: 14 }}>
              Thank you, {state.formData.personal.name}. Your information has been submitted successfully.
            </p>
            <button className="btnPrimary" style={{ marginTop: 16 }} onClick={() => dispatch({ type: 'RESET' })}>
              Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wizardWrapper">
      <div className="wizardCard">
        {/* Stepper */}
        <div className="stepper">
          {stepLabels.map((label, i) => {
            const stepNum = i + 1;
            const isActive = state.currentStep === stepNum;
            const isDone = state.currentStep > stepNum;
            return (
              <div key={label} className={`step${isActive ? ' stepActive' : ''}${isDone ? ' stepDone' : ''}`}>
                <div>
                  <span className={`stepNumber${isActive ? ' stepNumberActive' : ''}${isDone ? ' stepNumberDone' : ''}`}>
                    {isDone ? '✓' : stepNum}
                  </span>
                </div>
                {label}
              </div>
            );
          })}
        </div>

        {/* Body */}
        <div className="wizardBody">
          {state.currentStep === 1 && (
            <PersonalInfoStep data={state.formData.personal} errors={state.errors.personal} touched={state.touched.personal} dispatch={dispatch} />
          )}
          {state.currentStep === 2 && (
            <AddressStep data={state.formData.address} errors={state.errors.address} touched={state.touched.address} dispatch={dispatch} />
          )}
          {state.currentStep === 3 && <ConfirmationStep formData={state.formData} />}
        </div>

        {/* Actions */}
        <div className="wizardActions">
          <div>
            {state.currentStep > 1 && (
              <button className="btnSecondary" onClick={() => dispatch({ type: 'PREV_STEP' })}>← Back</button>
            )}
          </div>
          <div>
            {state.currentStep < 3 ? (
              <button className="btnPrimary" onClick={handleNext}>Continue →</button>
            ) : (
              <button
                className={`btnPrimary${state.isSubmitting ? ' btnDisabled' : ''}`}
                onClick={handleSubmit}
                disabled={state.isSubmitting}
              >
                {state.isSubmitting ? 'Submitting...' : 'Submit'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FormWizard;
```
