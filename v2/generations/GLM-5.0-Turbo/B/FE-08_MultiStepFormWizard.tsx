import React, { useReducer, useCallback } from 'react';

/* ===== Types ===== */
interface FormData {
  name: string;
  email: string;
  street: string;
  city: string;
  zip: string;
}

interface FormErrors {
  name?: string;
  email?: string;
  street?: string;
  city?: string;
  zip?: string;
}

type Step = 1 | 2 | 3;

interface WizardState {
  step: Step;
  data: FormData;
  errors: FormErrors;
  submitted: boolean;
}

type WizardAction =
  | { type: 'NEXT' }
  | { type: 'BACK' }
  | { type: 'UPDATE_FIELD'; field: keyof FormData; value: string }
  | { type: 'SUBMIT' }
  | { type: 'RESET' };

/* ===== Validation ===== */
function validateStep1(data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!data.name.trim()) {
    errors.name = 'Name is required';
  } else if (data.name.trim().length < 2) {
    errors.name = 'Name must be at least 2 characters';
  }
  if (!data.email.trim()) {
    errors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    errors.email = 'Invalid email format';
  }
  return errors;
}

function validateStep2(data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!data.street.trim()) {
    errors.street = 'Street is required';
  }
  if (!data.city.trim()) {
    errors.city = 'City is required';
  }
  if (!data.zip.trim()) {
    errors.zip = 'ZIP code is required';
  } else if (!/^\d{5}(-\d{4})?$/.test(data.zip.trim())) {
    errors.zip = 'Invalid ZIP code (e.g. 12345 or 12345-6789)';
  }
  return errors;
}

function validateStep(step: Step, data: FormData): FormErrors {
  if (step === 1) return validateStep1(data);
  if (step === 2) return validateStep2(data);
  return {};
}

function hasErrors(errors: FormErrors): boolean {
  return Object.values(errors).some(v => v !== undefined && v.length > 0);
}

/* ===== Reducer ===== */
const initialData: FormData = {
  name: '',
  email: '',
  street: '',
  city: '',
  zip: '',
};

const initialState: WizardState = {
  step: 1,
  data: initialData,
  errors: {},
  submitted: false,
};

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'UPDATE_FIELD':
      return {
        ...state,
        data: { ...state.data, [action.field]: action.value },
        errors: { ...state.errors, [action.field]: undefined },
      };
    case 'NEXT': {
      const errors = validateStep(state.step, state.data);
      if (hasErrors(errors)) {
        return { ...state, errors };
      }
      return {
        ...state,
        step: Math.min(state.step + 1, 3) as Step,
        errors: {},
      };
    }
    case 'BACK':
      return {
        ...state,
        step: Math.max(state.step - 1, 1) as Step,
        errors: {},
      };
    case 'SUBMIT':
      return { ...state, submitted: true };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

/* ===== Components ===== */
function StepIndicator({ current }: { current: Step }) {
  const steps = [
    { num: 1, label: 'Personal' },
    { num: 2, label: 'Address' },
    { num: 3, label: 'Review' },
  ];
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, marginBottom: 32 }}>
      {steps.map((s, i) => (
        <React.Fragment key={s.num}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 4px',
              fontSize: 14,
              fontWeight: 600,
              background: current >= s.num ? '#4a90d9' : '#e0e0e0',
              color: current >= s.num ? '#fff' : '#888',
              transition: 'background 0.2s, color 0.2s',
            }}>
              {current > s.num ? '✓' : s.num}
            </div>
            <div style={{
              fontSize: 12,
              color: current >= s.num ? '#4a90d9' : '#aaa',
              fontWeight: current === s.num ? 600 : 400,
            }}>
              {s.label}
            </div>
          </div>
          {i < steps.length - 1 && (
            <div style={{
              width: 60,
              height: 2,
              background: current > s.num ? '#4a90d9' : '#e0e0e0',
              margin: '0 8px',
              marginBottom: 20,
              transition: 'background 0.2s',
            }} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

function TextField({
  label,
  name,
  value,
  error,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string;
  name: string;
  value: string;
  error?: string;
  onChange: (field: string, value: string) => void;
  placeholder: string;
  type?: string;
}) {
  return (
    <div style={{ marginBottom: 20 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#555', marginBottom: 6 }}>
        {label}
      </label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={e => onChange(name, e.target.value)}
        placeholder={placeholder}
        style={{
          width: '100%',
          padding: '10px 14px',
          border: error ? '2px solid #e63946' : '1px solid #ddd',
          borderRadius: 8,
          fontSize: 14,
          outline: 'none',
          boxSizing: 'border-box',
          transition: 'border-color 0.15s',
        }}
      />
      {error && (
        <div style={{ color: '#e63946', fontSize: 12, marginTop: 4 }}>{error}</div>
      )}
    </div>
  );
}

/* ===== Main ===== */
export default function MultiStepFormWizard() {
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  const updateField = useCallback((field: string, value: string) => {
    dispatch({ type: 'UPDATE_FIELD', field: field as keyof FormData, value });
  }, []);

  if (state.submitted) {
    return (
      <div style={{ padding: 24 }}>
        <style>{`
          .wizard-root {
            max-width: 520px;
            margin: 0 auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          }
          .wizard-card {
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
          }
          .wizard-title {
            text-align: center;
            font-size: 22px;
            color: #333;
            margin-bottom: 24px;
          }
          .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s, transform 0.1s;
          }
          .btn:active { transform: scale(0.98); }
          .btn-primary {
            background: #4a90d9;
            color: #fff;
          }
          .btn-primary:hover { background: #3a7bc8; }
          .btn-secondary {
            background: #f0f0f0;
            color: #555;
          }
          .btn-secondary:hover { background: #e4e4e4; }
          .btn-row {
            display: flex;
            justify-content: space-between;
            margin-top: 24px;
          }
          .review-section {
            margin-bottom: 20px;
          }
          .review-section h3 {
            font-size: 15px;
            color: #4a90d9;
            margin-bottom: 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #eef1f5;
          }
          .review-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 14px;
          }
          .review-label { color: #888; }
          .review-value { color: #333; font-weight: 500; }
          .success-icon { font-size: 48px; text-align: center; margin-bottom: 16px; }
          .success-text { text-align: center; color: #2a9d8f; font-size: 18px; font-weight: 600; margin-bottom: 8px; }
          .success-sub { text-align: center; color: #888; font-size: 13px; margin-bottom: 24px; }
        `}</style>
        <div className="wizard-root">
          <div className="wizard-card">
            <div className="success-icon">✅</div>
            <div className="success-text">Submission Successful!</div>
            <div className="success-sub">Your information has been logged to the console.</div>
            <div className="review-section">
              <h3>Personal</h3>
              <div className="review-row">
                <span className="review-label">Name</span>
                <span className="review-value">{state.data.name}</span>
              </div>
              <div className="review-row">
                <span className="review-label">Email</span>
                <span className="review-value">{state.data.email}</span>
              </div>
            </div>
            <div className="review-section">
              <h3>Address</h3>
              <div className="review-row">
                <span className="review-label">Street</span>
                <span className="review-value">{state.data.street}</span>
              </div>
              <div className="review-row">
                <span className="review-label">City</span>
                <span className="review-value">{state.data.city}</span>
              </div>
              <div className="review-row">
                <span className="review-label">ZIP</span>
                <span className="review-value">{state.data.zip}</span>
              </div>
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => dispatch({ type: 'RESET' })}>
              Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <style>{`
        .wizard-root {
          max-width: 520px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .wizard-card {
          background: #fff;
          border: 1px solid #e0e0e0;
          border-radius: 12px;
          padding: 32px;
          box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }
        .wizard-title {
          text-align: center;
          font-size: 22px;
          color: #333;
          margin-bottom: 24px;
        }
        .btn {
          padding: 10px 24px;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s, transform 0.1s;
        }
        .btn:active { transform: scale(0.98); }
        .btn-primary {
          background: #4a90d9;
          color: #fff;
        }
        .btn-primary:hover { background: #3a7bc8; }
        .btn-secondary {
          background: #f0f0f0;
          color: #555;
        }
        .btn-secondary:hover { background: #e4e4e4; }
        .btn-row {
          display: flex;
          justify-content: space-between;
          margin-top: 24px;
        }
        .review-section {
          margin-bottom: 20px;
        }
        .review-section h3 {
          font-size: 15px;
          color: #4a90d9;
          margin-bottom: 8px;
          padding-bottom: 4px;
          border-bottom: 1px solid #eef1f5;
        }
        .review-row {
          display: flex;
          justify-content: space-between;
          padding: 6px 0;
          font-size: 14px;
        }
        .review-label { color: #888; }
        .review-value { color: #333; font-weight: 500; }
      `}</style>
      <div className="wizard-root">
        <div className="wizard-card">
          <div className="wizard-title">📋 Registration Wizard</div>
          <StepIndicator current={state.step} />

          {state.step === 1 && (
            <div>
              <TextField
                label="Full Name"
                name="name"
                value={state.data.name}
                error={state.errors.name}
                onChange={updateField}
                placeholder="John Doe"
              />
              <TextField
                label="Email Address"
                name="email"
                value={state.data.email}
                error={state.errors.email}
                onChange={updateField}
                placeholder="john@example.com"
                type="email"
              />
            </div>
          )}

          {state.step === 2 && (
            <div>
              <TextField
                label="Street Address"
                name="street"
                value={state.data.street}
                error={state.errors.street}
                onChange={updateField}
                placeholder="123 Main St"
              />
              <TextField
                label="City"
                name="city"
                value={state.data.city}
                error={state.errors.city}
                onChange={updateField}
                placeholder="San Francisco"
              />
              <TextField
                label="ZIP Code"
                name="zip"
                value={state.data.zip}
                error={state.errors.zip}
                onChange={updateField}
                placeholder="94102"
              />
            </div>
          )}

          {state.step === 3 && (
            <div>
              <div className="review-section">
                <h3>Personal Information</h3>
                <div className="review-row">
                  <span className="review-label">Name</span>
                  <span className="review-value">{state.data.name}</span>
                </div>
                <div className="review-row">
                  <span className="review-label">Email</span>
                  <span className="review-value">{state.data.email}</span>
                </div>
              </div>
              <div className="review-section">
                <h3>Address</h3>
                <div className="review-row">
                  <span className="review-label">Street</span>
                  <span className="review-value">{state.data.street}</span>
                </div>
                <div className="review-row">
                  <span className="review-label">City</span>
                  <span className="review-value">{state.data.city}</span>
                </div>
                <div className="review-row">
                  <span className="review-label">ZIP</span>
                  <span className="review-value">{state.data.zip}</span>
                </div>
              </div>
            </div>
          )}

          <div className="btn-row">
            {state.step > 1 && (
              <button className="btn btn-secondary" onClick={() => dispatch({ type: 'BACK' })}>
                ← Back
              </button>
            )}
            {state.step < 3 && (
              <button className="btn btn-primary" onClick={() => dispatch({ type: 'NEXT' })}>
                Next →
              </button>
            )}
            {state.step === 3 && (
              <button
                className="btn btn-primary"
                onClick={() => {
                  console.log('Form Submitted:', JSON.stringify(state.data, null, 2));
                  dispatch({ type: 'SUBMIT' });
                }}
              >
                ✅ Submit
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
