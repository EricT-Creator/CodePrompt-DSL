import React, { useReducer, useCallback } from 'react';

interface FormData {
  name: string;
  email: string;
  street: string;
  city: string;
  zipCode: string;
}

interface FormErrors {
  [key: string]: string;
}

type Step = 1 | 2 | 3;

type Action =
  | { type: 'UPDATE_FIELD'; field: keyof FormData; value: string }
  | { type: 'SET_ERRORS'; errors: FormErrors }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'SUBMIT' }
  | { type: 'SET_TOUCHED'; field: keyof FormData };

interface State {
  step: Step;
  formData: FormData;
  errors: FormErrors;
  touched: Partial<Record<keyof FormData, boolean>>;
}

const initialState: State = {
  step: 1,
  formData: { name: '', email: '', street: '', city: '', zipCode: '' },
  errors: {},
  touched: {},
};

function validateStep1(data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!data.name.trim()) errors.name = 'Name is required';
  if (!data.email.trim()) {
    errors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    errors.email = 'Invalid email format';
  }
  return errors;
}

function validateStep2(data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!data.street.trim()) errors.street = 'Street is required';
  if (!data.city.trim()) errors.city = 'City is required';
  if (!data.zipCode.trim()) {
    errors.zipCode = 'Zip code is required';
  } else if (!/^\d{5}(-\d{4})?$/.test(data.zipCode)) {
    errors.zipCode = 'Invalid zip code format (e.g. 12345)';
  }
  return errors;
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'UPDATE_FIELD':
      return {
        ...state,
        formData: { ...state.formData, [action.field]: action.value },
        errors: { ...state.errors, [action.field]: '' },
      };
    case 'SET_ERRORS':
      return { ...state, errors: action.errors };
    case 'SET_TOUCHED':
      return { ...state, touched: { ...state.touched, [action.field]: true } };
    case 'NEXT_STEP': {
      if (state.step === 1) {
        const errors = validateStep1(state.formData);
        if (Object.keys(errors).length > 0) return { ...state, errors };
        return { ...state, step: 2, errors: {} };
      }
      if (state.step === 2) {
        const errors = validateStep2(state.formData);
        if (Object.keys(errors).length > 0) return { ...state, errors };
        return { ...state, step: 3, errors: {} };
      }
      return state;
    }
    case 'PREV_STEP': {
      if (state.step === 2) return { ...state, step: 1, errors: {} };
      if (state.step === 3) return { ...state, step: 2, errors: {} };
      return state;
    }
    case 'SUBMIT': {
      console.log('Form submitted:', state.formData);
      return state;
    }
    default:
      return state;
  }
}

const MultiStepFormWizard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleBlur = useCallback((field: keyof FormData) => {
    dispatch({ type: 'SET_TOUCHED', field });
    const errors = state.step === 1 ? validateStep1(state.formData) : validateStep2(state.formData);
    if (errors[field]) {
      dispatch({ type: 'SET_ERRORS', errors });
    }
  }, [state.step, state.formData]);

  const inputStyle = (field: keyof FormData): React.CSSProperties => ({
    ...styles.input,
    borderColor: state.errors[field] && state.touched[field] ? '#d32f2f' : '#ddd',
  });

  const errorStyle: React.CSSProperties = {
    color: '#d32f2f',
    fontSize: 12,
    marginTop: 4,
    minHeight: 16,
  };

  const renderStep1 = () => (
    <div>
      <h3 style={styles.stepTitle}>Personal Information</h3>
      <div style={styles.field}>
        <label style={styles.label}>Name *</label>
        <input
          style={inputStyle('name')}
          type="text"
          value={state.formData.name}
          onChange={(e) => dispatch({ type: 'UPDATE_FIELD', field: 'name', value: e.target.value })}
          onBlur={() => handleBlur('name')}
          placeholder="Enter your name"
        />
        <div style={errorStyle}>{state.touched.name && state.errors.name}</div>
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Email *</label>
        <input
          style={inputStyle('email')}
          type="email"
          value={state.formData.email}
          onChange={(e) => dispatch({ type: 'UPDATE_FIELD', field: 'email', value: e.target.value })}
          onBlur={() => handleBlur('email')}
          placeholder="Enter your email"
        />
        <div style={errorStyle}>{state.touched.email && state.errors.email}</div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div>
      <h3 style={styles.stepTitle}>Address</h3>
      <div style={styles.field}>
        <label style={styles.label}>Street *</label>
        <input
          style={inputStyle('street')}
          type="text"
          value={state.formData.street}
          onChange={(e) => dispatch({ type: 'UPDATE_FIELD', field: 'street', value: e.target.value })}
          onBlur={() => handleBlur('street')}
          placeholder="Enter your street address"
        />
        <div style={errorStyle}>{state.touched.street && state.errors.street}</div>
      </div>
      <div style={styles.field}>
        <label style={styles.label}>City *</label>
        <input
          style={inputStyle('city')}
          type="text"
          value={state.formData.city}
          onChange={(e) => dispatch({ type: 'UPDATE_FIELD', field: 'city', value: e.target.value })}
          onBlur={() => handleBlur('city')}
          placeholder="Enter your city"
        />
        <div style={errorStyle}>{state.touched.city && state.errors.city}</div>
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Zip Code *</label>
        <input
          style={inputStyle('zipCode')}
          type="text"
          value={state.formData.zipCode}
          onChange={(e) => dispatch({ type: 'UPDATE_FIELD', field: 'zipCode', value: e.target.value })}
          onBlur={() => handleBlur('zipCode')}
          placeholder="Enter your zip code"
        />
        <div style={errorStyle}>{state.touched.zipCode && state.errors.zipCode}</div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div>
      <h3 style={styles.stepTitle}>Review & Confirm</h3>
      <div style={styles.reviewSection}>
        <h4 style={styles.reviewSubtitle}>Personal Information</h4>
        <div style={styles.reviewRow}><span style={styles.reviewLabel}>Name:</span> {state.formData.name}</div>
        <div style={styles.reviewRow}><span style={styles.reviewLabel}>Email:</span> {state.formData.email}</div>
        <h4 style={styles.reviewSubtitle}>Address</h4>
        <div style={styles.reviewRow}><span style={styles.reviewLabel}>Street:</span> {state.formData.street}</div>
        <div style={styles.reviewRow}><span style={styles.reviewLabel}>City:</span> {state.formData.city}</div>
        <div style={styles.reviewRow}><span style={styles.reviewLabel}>Zip Code:</span> {state.formData.zipCode}</div>
      </div>
      <button style={{ ...styles.btn, ...styles.submitBtn }} onClick={() => dispatch({ type: 'SUBMIT' })}>
        ✅ Submit
      </button>
    </div>
  );

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Multi-Step Form Wizard</h2>
      <div style={styles.stepsIndicator}>
        {[1, 2, 3].map((s) => (
          <React.Fragment key={s}>
            <div style={{ ...styles.stepDot, ...(state.step >= (s as Step) ? styles.stepDotActive : {}) }}>
              {s}
            </div>
            {s < 3 && <div style={{ ...styles.stepLine, ...(state.step > (s as Step) ? styles.stepLineActive : {}) }} />}
          </React.Fragment>
        ))}
      </div>
      <div style={styles.card}>
        {state.step === 1 && renderStep1()}
        {state.step === 2 && renderStep2()}
        {state.step === 3 && renderStep3()}
        {state.step < 3 && (
          <div style={styles.navButtons}>
            {state.step > 1 && (
              <button style={{ ...styles.btn, ...styles.backBtn }} onClick={() => dispatch({ type: 'PREV_STEP' })}>
                ← Back
              </button>
            )}
            <button
              style={{ ...styles.btn, ...styles.nextBtn }}
              onClick={() => dispatch({ type: 'NEXT_STEP' })}
            >
              Next →
            </button>
          </div>
        )}
        {state.step === 3 && (
          <div style={styles.navButtons}>
            <button style={{ ...styles.btn, ...styles.backBtn }} onClick={() => dispatch({ type: 'PREV_STEP' })}>
              ← Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { maxWidth: 500, margin: '40px auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  title: { fontSize: 20, fontWeight: 600, marginBottom: 24, color: '#1a1a1a' },
  stepsIndicator: { display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 24 },
  stepDot: { width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 600, border: '2px solid #ddd', color: '#aaa', background: '#fff' },
  stepDotActive: { borderColor: '#1976d2', color: '#1976d2', background: '#e3f2fd' },
  stepLine: { width: 60, height: 2, background: '#ddd', margin: '0 8px' },
  stepLineActive: { background: '#1976d2' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: 12, padding: 24 },
  stepTitle: { fontSize: 17, fontWeight: 600, marginBottom: 20, color: '#333' },
  field: { marginBottom: 16 },
  label: { display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#555' },
  input: { width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 6, fontSize: 14, outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.2s' },
  reviewSection: { background: '#f8f9fa', borderRadius: 8, padding: 16 },
  reviewSubtitle: { fontSize: 14, fontWeight: 600, color: '#555', marginTop: 12, marginBottom: 8 },
  reviewRow: { fontSize: 14, color: '#333', marginBottom: 4 },
  reviewLabel: { fontWeight: 500, color: '#666' },
  navButtons: { display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 24 },
  btn: { padding: '10px 24px', borderRadius: 8, fontSize: 14, fontWeight: 500, cursor: 'pointer', border: 'none' },
  nextBtn: { background: '#1976d2', color: '#fff' },
  backBtn: { background: '#f5f5f5', color: '#555', border: '1px solid #ddd' },
  submitBtn: { background: '#2e7d32', color: '#fff', marginTop: 16, width: '100%' },
};

export default MultiStepFormWizard;
