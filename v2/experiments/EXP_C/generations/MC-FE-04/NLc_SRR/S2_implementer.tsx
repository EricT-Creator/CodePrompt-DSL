import React, { useReducer, useCallback, useEffect } from 'react';

// ── Types ──────────────────────────────────────────────────────────────

type WizardStep = 'personal' | 'address' | 'confirmation';

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

interface ValidationRule {
  required: boolean;
  pattern?: RegExp;
  minLength?: number;
  maxLength?: number;
  message: string;
}

interface StepState {
  isValid: boolean;
  isTouched: boolean;
  isCompleted: boolean;
  errors: Record<string, string>;
}

interface WizardState {
  currentStep: WizardStep;
  personal: PersonalInfo;
  address: AddressInfo;
  steps: Record<WizardStep, StepState>;
  isSubmitting: boolean;
  isSubmitted: boolean;
  touchedFields: Set<string>;
}

type WizardAction =
  | { type: 'SET_FIELD'; payload: { section: 'personal' | 'address'; field: string; value: string } }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'GO_TO_STEP'; payload: WizardStep }
  | { type: 'VALIDATE_STEP'; payload: { step: WizardStep; errors: Record<string, string> } }
  | { type: 'TOUCH_FIELD'; payload: string }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_SUCCESS' }
  | { type: 'RESET' };

// ── CSS ────────────────────────────────────────────────────────────────

const css = `
.wizard-container{max-width:600px;margin:40px auto;font-family:system-ui,-apple-system,sans-serif;padding:0 20px}
.wizard-progress{display:flex;align-items:center;margin-bottom:32px}
.wizard-step-indicator{display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;font-size:14px;font-weight:600;transition:all .2s;cursor:pointer}
.step-pending{background:#e5e7eb;color:#6b7280}
.step-active{background:#3b82f6;color:#fff;box-shadow:0 0 0 4px rgba(59,130,246,.2)}
.step-completed{background:#22c55e;color:#fff}
.wizard-step-label{font-size:12px;color:#6b7280;margin-top:4px;text-align:center}
.wizard-step-wrapper{display:flex;flex-direction:column;align-items:center;flex:0 0 auto}
.wizard-line{flex:1;height:2px;background:#e5e7eb;margin:0 8px}
.wizard-line.completed{background:#22c55e}
.wizard-card{background:#fff;border-radius:12px;box-shadow:0 1px 6px rgba(0,0,0,.08);padding:28px;margin-bottom:20px}
.wizard-card h2{margin:0 0 20px;font-size:20px;color:#1f2937}
.form-group{margin-bottom:18px}
.form-group label{display:block;font-size:13px;font-weight:500;color:#374151;margin-bottom:5px}
.form-group input{width:100%;padding:10px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;transition:border-color .15s}
.form-group input:focus{border-color:#3b82f6;box-shadow:0 0 0 2px rgba(59,130,246,.15)}
.form-group input.input-error{border-color:#ef4444;box-shadow:0 0 0 2px rgba(239,68,68,.15)}
.error-text{font-size:12px;color:#ef4444;margin-top:4px}
.wizard-nav{display:flex;justify-content:space-between;gap:12px}
.wizard-btn{padding:10px 24px;border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer;transition:background .15s}
.btn-primary{background:#3b82f6;color:#fff}
.btn-primary:hover{background:#2563eb}
.btn-primary:disabled{background:#93c5fd;cursor:not-allowed}
.btn-secondary{background:#f3f4f6;color:#374151}
.btn-secondary:hover{background:#e5e7eb}
.btn-success{background:#22c55e;color:#fff}
.btn-success:hover{background:#16a34a}
.btn-success:disabled{background:#86efac;cursor:not-allowed}
.summary-section{margin-bottom:16px}
.summary-section h3{font-size:14px;color:#6b7280;margin:0 0 8px;text-transform:uppercase;letter-spacing:0.5px}
.summary-row{display:flex;justify-content:space-between;padding:6px 0;font-size:14px;border-bottom:1px solid #f3f4f6}
.summary-label{color:#6b7280}
.summary-value{color:#1f2937;font-weight:500}
.success-message{text-align:center;padding:40px 0}
.success-message h2{color:#22c55e;margin-bottom:8px}
.success-message p{color:#6b7280;font-size:14px}
`;

// ── Validation rules ───────────────────────────────────────────────────

const personalRules: Record<string, ValidationRule> = {
  name: { required: true, minLength: 2, maxLength: 50, pattern: /^[a-zA-Z\s]+$/, message: 'Name must be 2-50 letters' },
  email: { required: true, pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email address' },
  phone: { required: true, pattern: /^\+?[\d\s\-()]{10,}$/, message: 'Enter a valid phone number' },
};

const addressRules: Record<string, ValidationRule> = {
  street: { required: true, minLength: 5, maxLength: 100, message: 'Street must be 5-100 characters' },
  city: { required: true, minLength: 2, maxLength: 50, message: 'City must be 2-50 characters' },
  state: { required: true, pattern: /^[A-Z]{2}$/, message: 'State must be 2 uppercase letters (e.g. CA)' },
  zip: { required: true, pattern: /^\d{5}(-\d{4})?$/, message: 'ZIP must be 5 or 9 digits (e.g. 12345)' },
};

function validateField(value: string, rule: ValidationRule): string | null {
  if (rule.required && !value.trim()) return `This field is required`;
  if (rule.minLength && value.length < rule.minLength) return rule.message;
  if (rule.maxLength && value.length > rule.maxLength) return rule.message;
  if (rule.pattern && value.trim() && !rule.pattern.test(value.trim())) return rule.message;
  return null;
}

function validateSection(data: Record<string, string>, rules: Record<string, ValidationRule>): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [field, rule] of Object.entries(rules)) {
    const err = validateField(data[field] || '', rule);
    if (err) errors[field] = err;
  }
  return errors;
}

// ── Steps config ───────────────────────────────────────────────────────

const STEPS: WizardStep[] = ['personal', 'address', 'confirmation'];
const STEP_LABELS: Record<WizardStep, string> = { personal: 'Personal', address: 'Address', confirmation: 'Confirm' };

// ── Reducer ─────────────────────────────────────────────────────────────

const emptyStepState: StepState = { isValid: false, isTouched: false, isCompleted: false, errors: {} };

const initialState: WizardState = {
  currentStep: 'personal',
  personal: { name: '', email: '', phone: '' },
  address: { street: '', city: '', state: '', zip: '' },
  steps: { personal: { ...emptyStepState }, address: { ...emptyStepState }, confirmation: { ...emptyStepState } },
  isSubmitting: false,
  isSubmitted: false,
  touchedFields: new Set<string>(),
};

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_FIELD': {
      const { section, field, value } = action.payload;
      const sectionData = { ...state[section], [field]: value };
      const rules = section === 'personal' ? personalRules : addressRules;
      const errors = validateSection(sectionData as unknown as Record<string, string>, rules);
      const isValid = Object.keys(errors).length === 0;
      return {
        ...state,
        [section]: sectionData,
        steps: {
          ...state.steps,
          [section]: { ...state.steps[section], errors, isValid, isTouched: true },
        },
      };
    }
    case 'TOUCH_FIELD': {
      const next = new Set(state.touchedFields);
      next.add(action.payload);
      return { ...state, touchedFields: next };
    }
    case 'NEXT_STEP': {
      const idx = STEPS.indexOf(state.currentStep);
      if (idx >= STEPS.length - 1) return state;
      const nextStep = STEPS[idx + 1];
      return {
        ...state,
        currentStep: nextStep,
        steps: { ...state.steps, [state.currentStep]: { ...state.steps[state.currentStep], isCompleted: true } },
      };
    }
    case 'PREV_STEP': {
      const idx2 = STEPS.indexOf(state.currentStep);
      if (idx2 <= 0) return state;
      return { ...state, currentStep: STEPS[idx2 - 1] };
    }
    case 'GO_TO_STEP':
      return { ...state, currentStep: action.payload };
    case 'VALIDATE_STEP':
      return {
        ...state,
        steps: {
          ...state.steps,
          [action.payload.step]: {
            ...state.steps[action.payload.step],
            errors: action.payload.errors,
            isValid: Object.keys(action.payload.errors).length === 0,
            isTouched: true,
          },
        },
      };
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true };
    case 'SUBMIT_SUCCESS':
      return { ...state, isSubmitting: false, isSubmitted: true };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

// ── Field Component ────────────────────────────────────────────────────

interface FieldProps {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  value: string;
  error?: string;
  touched: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
}

const Field: React.FC<FieldProps> = ({ label, name, type = 'text', placeholder, value, error, touched, onChange, onBlur }) => (
  <div className="form-group">
    <label htmlFor={name}>{label}</label>
    <input
      id={name}
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      className={touched && error ? 'input-error' : ''}
    />
    {touched && error && <div className="error-text">{error}</div>}
  </div>
);

// ── Main Component ─────────────────────────────────────────────────────

const FormWizard: React.FC = () => {
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  // Persist to localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('formWizardState');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.personal) dispatch({ type: 'SET_FIELD', payload: { section: 'personal', field: 'name', value: parsed.personal.name || '' } });
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem('formWizardState', JSON.stringify({ personal: state.personal, address: state.address }));
    } catch { /* ignore */ }
  }, [state.personal, state.address]);

  const handleFieldChange = useCallback((section: 'personal' | 'address', field: string, value: string) => {
    dispatch({ type: 'SET_FIELD', payload: { section, field, value } });
  }, []);

  const handleBlur = useCallback((field: string) => {
    dispatch({ type: 'TOUCH_FIELD', payload: field });
  }, []);

  const handleNext = useCallback(() => {
    // Validate current step before proceeding
    const step = state.currentStep;
    let errors: Record<string, string> = {};
    if (step === 'personal') {
      errors = validateSection(state.personal as unknown as Record<string, string>, personalRules);
      // Touch all fields
      Object.keys(personalRules).forEach((f) => dispatch({ type: 'TOUCH_FIELD', payload: f }));
    } else if (step === 'address') {
      errors = validateSection(state.address as unknown as Record<string, string>, addressRules);
      Object.keys(addressRules).forEach((f) => dispatch({ type: 'TOUCH_FIELD', payload: f }));
    }
    dispatch({ type: 'VALIDATE_STEP', payload: { step, errors } });
    if (Object.keys(errors).length === 0) {
      dispatch({ type: 'NEXT_STEP' });
    }
  }, [state.currentStep, state.personal, state.address]);

  const handleSubmit = useCallback(() => {
    dispatch({ type: 'SUBMIT_START' });
    // Simulate API call
    setTimeout(() => {
      dispatch({ type: 'SUBMIT_SUCCESS' });
      localStorage.removeItem('formWizardState');
    }, 1500);
  }, []);

  const currentIdx = STEPS.indexOf(state.currentStep);
  const isTouched = (field: string) => state.touchedFields.has(field);
  const pErrors = state.steps.personal.errors;
  const aErrors = state.steps.address.errors;

  if (state.isSubmitted) {
    return (
      <>
        <style>{css}</style>
        <div className="wizard-container">
          <div className="wizard-card">
            <div className="success-message">
              <h2>✅ Submission Successful!</h2>
              <p>Your information has been submitted successfully.</p>
              <button className="wizard-btn btn-primary" style={{ marginTop: 20 }} onClick={() => dispatch({ type: 'RESET' })}>
                Start Over
              </button>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{css}</style>
      <div className="wizard-container">
        {/* Progress indicator */}
        <div className="wizard-progress">
          {STEPS.map((step, i) => {
            const isActive = step === state.currentStep;
            const isCompleted = state.steps[step].isCompleted;
            let cls = 'step-pending';
            if (isActive) cls = 'step-active';
            else if (isCompleted) cls = 'step-completed';
            return (
              <React.Fragment key={step}>
                {i > 0 && <div className={`wizard-line${state.steps[STEPS[i - 1]].isCompleted ? ' completed' : ''}`} />}
                <div className="wizard-step-wrapper">
                  <div
                    className={`wizard-step-indicator ${cls}`}
                    onClick={() => {
                      if (isCompleted || i <= currentIdx) dispatch({ type: 'GO_TO_STEP', payload: step });
                    }}
                  >
                    {isCompleted && !isActive ? '✓' : i + 1}
                  </div>
                  <div className="wizard-step-label">{STEP_LABELS[step]}</div>
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* Step content */}
        <div className="wizard-card">
          {state.currentStep === 'personal' && (
            <>
              <h2>Personal Information</h2>
              <Field label="Full Name" name="name" placeholder="John Doe" value={state.personal.name} error={pErrors.name} touched={isTouched('name')} onChange={(v) => handleFieldChange('personal', 'name', v)} onBlur={() => handleBlur('name')} />
              <Field label="Email Address" name="email" type="email" placeholder="john@example.com" value={state.personal.email} error={pErrors.email} touched={isTouched('email')} onChange={(v) => handleFieldChange('personal', 'email', v)} onBlur={() => handleBlur('email')} />
              <Field label="Phone Number" name="phone" type="tel" placeholder="+1 (555) 123-4567" value={state.personal.phone} error={pErrors.phone} touched={isTouched('phone')} onChange={(v) => handleFieldChange('personal', 'phone', v)} onBlur={() => handleBlur('phone')} />
            </>
          )}

          {state.currentStep === 'address' && (
            <>
              <h2>Address Information</h2>
              <Field label="Street Address" name="street" placeholder="123 Main St" value={state.address.street} error={aErrors.street} touched={isTouched('street')} onChange={(v) => handleFieldChange('address', 'street', v)} onBlur={() => handleBlur('street')} />
              <Field label="City" name="city" placeholder="San Francisco" value={state.address.city} error={aErrors.city} touched={isTouched('city')} onChange={(v) => handleFieldChange('address', 'city', v)} onBlur={() => handleBlur('city')} />
              <Field label="State" name="state" placeholder="CA" value={state.address.state} error={aErrors.state} touched={isTouched('state')} onChange={(v) => handleFieldChange('address', 'state', v)} onBlur={() => handleBlur('state')} />
              <Field label="ZIP Code" name="zip" placeholder="94105" value={state.address.zip} error={aErrors.zip} touched={isTouched('zip')} onChange={(v) => handleFieldChange('address', 'zip', v)} onBlur={() => handleBlur('zip')} />
            </>
          )}

          {state.currentStep === 'confirmation' && (
            <>
              <h2>Review & Confirm</h2>
              <div className="summary-section">
                <h3>Personal Information</h3>
                <div className="summary-row"><span className="summary-label">Name</span><span className="summary-value">{state.personal.name}</span></div>
                <div className="summary-row"><span className="summary-label">Email</span><span className="summary-value">{state.personal.email}</span></div>
                <div className="summary-row"><span className="summary-label">Phone</span><span className="summary-value">{state.personal.phone}</span></div>
              </div>
              <div className="summary-section">
                <h3>Address</h3>
                <div className="summary-row"><span className="summary-label">Street</span><span className="summary-value">{state.address.street}</span></div>
                <div className="summary-row"><span className="summary-label">City</span><span className="summary-value">{state.address.city}</span></div>
                <div className="summary-row"><span className="summary-label">State</span><span className="summary-value">{state.address.state}</span></div>
                <div className="summary-row"><span className="summary-label">ZIP</span><span className="summary-value">{state.address.zip}</span></div>
              </div>
            </>
          )}
        </div>

        {/* Navigation */}
        <div className="wizard-nav">
          <button className="wizard-btn btn-secondary" onClick={() => dispatch({ type: 'PREV_STEP' })} disabled={currentIdx === 0} style={{ visibility: currentIdx === 0 ? 'hidden' : 'visible' }}>
            ← Back
          </button>
          {state.currentStep !== 'confirmation' ? (
            <button className="wizard-btn btn-primary" onClick={handleNext}>
              Next →
            </button>
          ) : (
            <button className="wizard-btn btn-success" onClick={handleSubmit} disabled={state.isSubmitting}>
              {state.isSubmitting ? 'Submitting…' : '✓ Submit'}
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default FormWizard;
