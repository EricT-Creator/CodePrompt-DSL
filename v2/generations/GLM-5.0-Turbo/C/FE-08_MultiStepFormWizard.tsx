import React, { useState, useCallback } from 'react';

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

const INITIAL_DATA: FormData = {
  name: '',
  email: '',
  street: '',
  city: '',
  zip: '',
};

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
    errors.email = 'Please enter a valid email address';
  }
  return errors;
}

function validateStep2(data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!data.street.trim()) {
    errors.street = 'Street address is required';
  }
  if (!data.city.trim()) {
    errors.city = 'City is required';
  }
  if (!data.zip.trim()) {
    errors.zip = 'ZIP code is required';
  } else if (!/^\d{5}(-\d{4})?$/.test(data.zip.trim())) {
    errors.zip = 'Please enter a valid ZIP code (e.g. 12345 or 12345-6789)';
  }
  return errors;
}

const STEP_LABELS = ['Personal Info', 'Address', 'Review & Submit'];

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<FormData>(INITIAL_DATA);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [touched, setTouched] = useState<Partial<Record<keyof FormData, boolean>>>({});

  const updateField = useCallback(
    (field: keyof FormData, value: string) => {
      setData((prev) => ({ ...prev, [field]: value }));
      setTouched((prev) => ({ ...prev, [field]: true }));
      setErrors((prev) => {
        const updated = { ...prev };
        delete updated[field];
        return updated;
      });
    },
    []
  );

  const handleBlur = useCallback(
    (field: keyof FormData) => {
      setTouched((prev) => ({ ...prev, [field]: true }));
      if (step === 0) {
        const stepErrors = validateStep1(data);
        setErrors((prev) => ({ ...prev, [field]: stepErrors[field as keyof FormErrors] }));
      } else if (step === 1) {
        const stepErrors = validateStep2(data);
        setErrors((prev) => ({ ...prev, [field]: stepErrors[field as keyof FormErrors] }));
      }
    },
    [step, data]
  );

  const canGoNext = (): boolean => {
    if (step === 0) {
      return Object.keys(validateStep1(data)).length === 0;
    }
    if (step === 1) {
      return Object.keys(validateStep2(data)).length === 0;
    }
    return true;
  };

  const handleNext = () => {
    if (step === 0) {
      const stepErrors = validateStep1(data);
      setErrors(stepErrors);
      if (Object.keys(stepErrors).length > 0) return;
    }
    if (step === 1) {
      const stepErrors = validateStep2(data);
      setErrors(stepErrors);
      if (Object.keys(stepErrors).length > 0) return;
    }
    setStep((s) => Math.min(s + 1, 2));
  };

  const handleBack = () => {
    setStep((s) => Math.max(s - 1, 0));
    setErrors({});
  };

  const handleSubmit = () => {
    console.log('Form submitted:', JSON.stringify(data, null, 2));
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={successIconStyle}>✓</div>
          <h2 style={{ ...headingStyle, textAlign: 'center', color: '#22c55e' }}>Submitted Successfully!</h2>
          <div style={summaryStyle}>
            <div style={summaryRowStyle}><span style={labelStyle}>Name:</span><span>{data.name}</span></div>
            <div style={summaryRowStyle}><span style={labelStyle}>Email:</span><span>{data.email}</span></div>
            <div style={summaryRowStyle}><span style={labelStyle}>Street:</span><span>{data.street}</span></div>
            <div style={summaryRowStyle}><span style={labelStyle}>City:</span><span>{data.city}</span></div>
            <div style={summaryRowStyle}><span style={labelStyle}>ZIP:</span><span>{data.zip}</span></div>
          </div>
          <p style={{ textAlign: 'center', color: '#64748b', fontSize: 13, marginTop: 16 }}>
            Check the browser console for the submitted data.
          </p>
          <button
            style={{ ...primaryBtnStyle, marginTop: 16, width: '100%' }}
            onClick={() => {
              setSubmitted(false);
              setData(INITIAL_DATA);
              setStep(0);
              setErrors({});
              setTouched({});
            }}
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <h2 style={headingStyle}>Multi-Step Form Wizard</h2>

      {/* Stepper */}
      <div style={stepperStyle}>
        {STEP_LABELS.map((label, i) => (
          <React.Fragment key={label}>
            <div style={stepIndicatorStyle}>
              <div
                style={{
                  ...stepCircleStyle,
                  ...(i === step ? stepCircleActiveStyle : {}),
                  ...(i < step ? stepCircleDoneStyle : {}),
                }}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <span style={{ ...stepLabelStyle, ...(i === step ? stepLabelActiveStyle : {}) }}>
                {label}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div style={{ ...lineStyle, ...(i < step ? lineDoneStyle : {}) }} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Form Card */}
      <div style={cardStyle}>
        {/* Step 1: Personal */}
        {step === 0 && (
          <div>
            <h3 style={sectionTitleStyle}>Personal Information</h3>
            <div style={fieldGroupStyle}>
              <label style={labelStyle}>Full Name *</label>
              <input
                type="text"
                value={data.name}
                onChange={(e) => updateField('name', e.target.value)}
                onBlur={() => handleBlur('name')}
                placeholder="Enter your name"
                style={{ ...inputStyle, ...(errors.name && touched.name ? inputErrorStyle : {}) }}
              />
              {errors.name && touched.name && <span style={errorTextStyle}>{errors.name}</span>}
            </div>
            <div style={fieldGroupStyle}>
              <label style={labelStyle}>Email *</label>
              <input
                type="email"
                value={data.email}
                onChange={(e) => updateField('email', e.target.value)}
                onBlur={() => handleBlur('email')}
                placeholder="you@example.com"
                style={{ ...inputStyle, ...(errors.email && touched.email ? inputErrorStyle : {}) }}
              />
              {errors.email && touched.email && <span style={errorTextStyle}>{errors.email}</span>}
            </div>
          </div>
        )}

        {/* Step 2: Address */}
        {step === 1 && (
          <div>
            <h3 style={sectionTitleStyle}>Address</h3>
            <div style={fieldGroupStyle}>
              <label style={labelStyle}>Street Address *</label>
              <input
                type="text"
                value={data.street}
                onChange={(e) => updateField('street', e.target.value)}
                onBlur={() => handleBlur('street')}
                placeholder="123 Main St"
                style={{ ...inputStyle, ...(errors.street && touched.street ? inputErrorStyle : {}) }}
              />
              {errors.street && touched.street && <span style={errorTextStyle}>{errors.street}</span>}
            </div>
            <div style={fieldRowStyle}>
              <div style={{ ...fieldGroupStyle, flex: 1 }}>
                <label style={labelStyle}>City *</label>
                <input
                  type="text"
                  value={data.city}
                  onChange={(e) => updateField('city', e.target.value)}
                  onBlur={() => handleBlur('city')}
                  placeholder="New York"
                  style={{ ...inputStyle, ...(errors.city && touched.city ? inputErrorStyle : {}) }}
                />
                {errors.city && touched.city && <span style={errorTextStyle}>{errors.city}</span>}
              </div>
              <div style={{ ...fieldGroupStyle, width: 160 }}>
                <label style={labelStyle}>ZIP Code *</label>
                <input
                  type="text"
                  value={data.zip}
                  onChange={(e) => updateField('zip', e.target.value)}
                  onBlur={() => handleBlur('zip')}
                  placeholder="10001"
                  style={{ ...inputStyle, ...(errors.zip && touched.zip ? inputErrorStyle : {}) }}
                />
                {errors.zip && touched.zip && <span style={errorTextStyle}>{errors.zip}</span>}
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Review */}
        {step === 2 && (
          <div>
            <h3 style={sectionTitleStyle}>Review Your Information</h3>
            <div style={reviewGridStyle}>
              <div style={reviewItemStyle}>
                <span style={reviewLabelStyle}>Name</span>
                <span style={reviewValueStyle}>{data.name || '—'}</span>
              </div>
              <div style={reviewItemStyle}>
                <span style={reviewLabelStyle}>Email</span>
                <span style={reviewValueStyle}>{data.email || '—'}</span>
              </div>
              <div style={reviewItemStyle}>
                <span style={reviewLabelStyle}>Street</span>
                <span style={reviewValueStyle}>{data.street || '—'}</span>
              </div>
              <div style={reviewItemStyle}>
                <span style={reviewLabelStyle}>City</span>
                <span style={reviewValueStyle}>{data.city || '—'}</span>
              </div>
              <div style={reviewItemStyle}>
                <span style={reviewLabelStyle}>ZIP Code</span>
                <span style={reviewValueStyle}>{data.zip || '—'}</span>
              </div>
            </div>
            <p style={reviewNoteStyle}>
              Please review all information before submitting. You can go back to edit any section.
            </p>
          </div>
        )}

        {/* Navigation */}
        <div style={navStyle}>
          {step > 0 && (
            <button style={secondaryBtnStyle} onClick={handleBack}>
              ← Back
            </button>
          )}
          {step < 2 && (
            <button style={primaryBtnStyle} onClick={handleNext}>
              Next →
            </button>
          )}
          {step === 2 && (
            <button style={submitBtnStyle} onClick={handleSubmit}>
              ✓ Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  maxWidth: 560, margin: '40px auto', padding: '0 20px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};
const headingStyle: React.CSSProperties = { fontSize: 24, fontWeight: 700, color: '#1e293b', marginBottom: 24 };
const stepperStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', marginBottom: 24 };
const stepIndicatorStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 };
const stepCircleStyle: React.CSSProperties = { width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 600, border: '2px solid #e2e8f0', color: '#94a3b8', background: '#fff' };
const stepCircleActiveStyle: React.CSSProperties = { borderColor: '#3b82f6', color: '#3b82f6', background: '#eff6ff' };
const stepCircleDoneStyle: React.CSSProperties = { borderColor: '#22c55e', color: '#fff', background: '#22c55e' };
const stepLabelStyle: React.CSSProperties = { fontSize: 12, color: '#94a3b8', fontWeight: 500 };
const stepLabelActiveStyle: React.CSSProperties = { color: '#3b82f6', fontWeight: 600 };
const lineStyle: React.CSSProperties = { flex: 1, height: 2, background: '#e2e8f0', margin: '0 8px', marginBottom: 24 };
const lineDoneStyle: React.CSSProperties = { background: '#22c55e' };
const cardStyle: React.CSSProperties = { border: '1px solid #e2e8f0', borderRadius: 12, padding: 24, background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' };
const sectionTitleStyle: React.CSSProperties = { fontSize: 17, fontWeight: 600, color: '#1e293b', marginBottom: 20 };
const fieldGroupStyle: React.CSSProperties = { marginBottom: 18 };
const fieldRowStyle: React.CSSProperties = { display: 'flex', gap: 16 };
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6 };
const inputStyle: React.CSSProperties = { width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #e2e8f0', borderRadius: 8, outline: 'none', boxSizing: 'border-box', color: '#334155' };
const inputErrorStyle: React.CSSProperties = { borderColor: '#ef4444' };
const errorTextStyle: React.CSSProperties = { display: 'block', fontSize: 12, color: '#ef4444', marginTop: 4 };
const navStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', marginTop: 28 };
const primaryBtnStyle: React.CSSProperties = { padding: '10px 24px', fontSize: 14, fontWeight: 600, color: '#fff', background: '#3b82f6', border: 'none', borderRadius: 8, cursor: 'pointer' };
const secondaryBtnStyle: React.CSSProperties = { padding: '10px 24px', fontSize: 14, fontWeight: 600, color: '#475569', background: '#f1f5f9', border: 'none', borderRadius: 8, cursor: 'pointer' };
const submitBtnStyle: React.CSSProperties = { padding: '10px 32px', fontSize: 15, fontWeight: 600, color: '#fff', background: '#22c55e', border: 'none', borderRadius: 8, cursor: 'pointer' };
const reviewGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 };
const reviewItemStyle: React.CSSProperties = { padding: '12px 14px', background: '#f8fafc', borderRadius: 8, border: '1px solid #f1f5f9' };
const reviewLabelStyle: React.CSSProperties = { display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 };
const reviewValueStyle: React.CSSProperties = { fontSize: 14, fontWeight: 500, color: '#1e293b' };
const reviewNoteStyle: React.CSSProperties = { fontSize: 13, color: '#64748b', marginTop: 16, padding: 12, background: '#fffbeb', borderRadius: 8, border: '1px solid #fef3c7' };
const successIconStyle: React.CSSProperties = { width: 56, height: 56, borderRadius: '50%', background: '#dcfce7', color: '#22c55e', fontSize: 28, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' };
const summaryStyle: React.CSSProperties = { background: '#f8fafc', borderRadius: 8, padding: 16, marginTop: 16 };
const summaryRowStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f5f9', fontSize: 14 };
