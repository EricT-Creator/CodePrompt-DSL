import React, { useState, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

type Step = 1 | 2 | 3;

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

interface FormData extends PersonalInfo, Address {}

interface ValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}

// ─── Validation ──────────────────────────────────────────────────────────────

function validatePersonalInfo(data: Partial<FormData>): ValidationResult {
  const errors: Record<string, string> = {};

  if (!data.name || data.name.trim().length < 2) {
    errors.name = 'Name is required (min 2 characters)';
  }

  if (!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    errors.email = 'Valid email required';
  }

  if (!data.phone || !/^\d{10,}$/.test(data.phone.replace(/\D/g, ''))) {
    errors.phone = 'Valid phone required (10+ digits)';
  }

  return { valid: Object.keys(errors).length === 0, errors };
}

function validateAddress(data: Partial<FormData>): ValidationResult {
  const errors: Record<string, string> = {};

  if (!data.street || data.street.trim().length === 0) {
    errors.street = 'Street is required';
  }

  if (!data.city || data.city.trim().length === 0) {
    errors.city = 'City is required';
  }

  if (!data.state || data.state.trim().length !== 2) {
    errors.state = 'State code required (2 characters)';
  }

  if (!data.zip || !/^\d{5}$/.test(data.zip.trim())) {
    errors.zip = 'Valid ZIP required (5 digits)';
  }

  return { valid: Object.keys(errors).length === 0, errors };
}

function validateStep(step: Step, data: Partial<FormData>): ValidationResult {
  switch (step) {
    case 1:
      return validatePersonalInfo(data);
    case 2:
      return validateAddress(data);
    case 3:
      return { valid: true, errors: {} };
  }
}

// ─── Styles (plain CSS via style objects, no Tailwind) ───────────────────────

const css: Record<string, React.CSSProperties> = {
  wrapper: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: 560,
    margin: '40px auto',
    padding: 24,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    textAlign: 'center' as const,
    marginBottom: 24,
  },
  stepIndicator: {
    display: 'flex',
    justifyContent: 'center',
    gap: 0,
    marginBottom: 28,
  },
  stepDot: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 14,
    fontWeight: 600,
    border: '2px solid #dee2e6',
    background: '#fff',
    color: '#868e96',
  },
  stepDotActive: {
    border: '2px solid #228be6',
    background: '#228be6',
    color: '#fff',
  },
  stepDotCompleted: {
    border: '2px solid #40c057',
    background: '#40c057',
    color: '#fff',
  },
  stepLine: {
    width: 60,
    height: 2,
    background: '#dee2e6',
    alignSelf: 'center' as const,
  },
  stepLineActive: {
    background: '#40c057',
  },
  card: {
    background: '#f8f9fa',
    borderRadius: 10,
    padding: 24,
    border: '1px solid #e9ecef',
  },
  fieldGroup: {
    marginBottom: 16,
  },
  fieldLabel: {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    marginBottom: 4,
    color: '#495057',
  },
  fieldInput: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ced4da',
    borderRadius: 6,
    fontSize: 14,
    boxSizing: 'border-box' as const,
  },
  fieldInputError: {
    borderColor: '#e03131',
  },
  fieldError: {
    fontSize: 12,
    color: '#e03131',
    marginTop: 4,
  },
  nav: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: 24,
  },
  backBtn: {
    padding: '10px 20px',
    border: '1px solid #dee2e6',
    borderRadius: 6,
    background: '#fff',
    cursor: 'pointer',
    fontSize: 14,
  },
  nextBtn: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: 6,
    background: '#228be6',
    color: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 14,
  },
  submitBtn: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: 6,
    background: '#40c057',
    color: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 14,
  },
  summaryRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px 0',
    borderBottom: '1px solid #e9ecef',
    fontSize: 14,
  },
  summaryLabel: {
    fontWeight: 600,
    color: '#495057',
  },
  summaryValue: {
    color: '#212529',
  },
  successBox: {
    textAlign: 'center' as const,
    padding: 40,
  },
  successIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  successTitle: {
    fontSize: 20,
    fontWeight: 700,
    color: '#40c057',
    marginBottom: 8,
  },
};

// ─── Sub-components ──────────────────────────────────────────────────────────

interface FieldProps {
  label: string;
  name: string;
  value: string;
  error?: string;
  touched: boolean;
  type?: string;
  placeholder?: string;
  onChange: (name: string, value: string) => void;
  onBlur: (name: string) => void;
}

function Field({ label, name, value, error, touched, type = 'text', placeholder, onChange, onBlur }: FieldProps) {
  return (
    <div style={css.fieldGroup}>
      <label style={css.fieldLabel}>{label}</label>
      <input
        type={type}
        style={{ ...css.fieldInput, ...(touched && error ? css.fieldInputError : {}) }}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(name, e.target.value)}
        onBlur={() => onBlur(name)}
      />
      {touched && error && <div style={css.fieldError}>{error}</div>}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

const FormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [formData, setFormData] = useState<Partial<FormData>>({
    name: '',
    email: '',
    phone: '',
    street: '',
    city: '',
    state: '',
    zip: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [submitted, setSubmitted] = useState(false);

  const handleChange = useCallback((name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  const handleBlur = useCallback(
    (name: string) => {
      setTouched((prev) => ({ ...prev, [name]: true }));
      const result = validateStep(currentStep, formData);
      if (result.errors[name]) {
        setErrors((prev) => ({ ...prev, [name]: result.errors[name] }));
      }
    },
    [currentStep, formData],
  );

  const handleNext = useCallback(() => {
    const result = validateStep(currentStep, formData);
    if (!result.valid) {
      setErrors(result.errors);
      const allTouched: Record<string, boolean> = {};
      for (const key of Object.keys(result.errors)) {
        allTouched[key] = true;
      }
      setTouched((prev) => ({ ...prev, ...allTouched }));
      return;
    }
    if (currentStep < 3) {
      setCurrentStep((currentStep + 1) as Step);
      setErrors({});
    }
  }, [currentStep, formData]);

  const handleBack = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as Step);
      setErrors({});
    }
  }, [currentStep]);

  const handleSubmit = useCallback(() => {
    setSubmitted(true);
  }, []);

  if (submitted) {
    return (
      <div style={css.wrapper}>
        <div style={css.card}>
          <div style={css.successBox}>
            <div style={css.successIcon}>✅</div>
            <div style={css.successTitle}>Form Submitted!</div>
            <p style={{ color: '#868e96', fontSize: 14 }}>
              Thank you, {formData.name}. Your information has been received.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={css.wrapper}>
      <div style={css.title}>Registration Wizard</div>

      {/* Step indicator */}
      <div style={css.stepIndicator}>
        {[1, 2, 3].map((step, idx) => (
          <React.Fragment key={step}>
            {idx > 0 && (
              <div
                style={{
                  ...css.stepLine,
                  ...(currentStep > idx ? css.stepLineActive : {}),
                }}
              />
            )}
            <div
              style={{
                ...css.stepDot,
                ...(currentStep === step
                  ? css.stepDotActive
                  : currentStep > step
                  ? css.stepDotCompleted
                  : {}),
              }}
            >
              {currentStep > step ? '✓' : step}
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* Card */}
      <div style={css.card}>
        {/* Step 1: Personal Info */}
        {currentStep === 1 && (
          <>
            <h3 style={{ marginTop: 0, marginBottom: 16 }}>Personal Information</h3>
            <Field label="Full Name" name="name" value={formData.name || ''} error={errors.name} touched={!!touched.name} placeholder="John Doe" onChange={handleChange} onBlur={handleBlur} />
            <Field label="Email Address" name="email" value={formData.email || ''} error={errors.email} touched={!!touched.email} type="email" placeholder="john@example.com" onChange={handleChange} onBlur={handleBlur} />
            <Field label="Phone Number" name="phone" value={formData.phone || ''} error={errors.phone} touched={!!touched.phone} type="tel" placeholder="1234567890" onChange={handleChange} onBlur={handleBlur} />
          </>
        )}

        {/* Step 2: Address */}
        {currentStep === 2 && (
          <>
            <h3 style={{ marginTop: 0, marginBottom: 16 }}>Address</h3>
            <Field label="Street" name="street" value={formData.street || ''} error={errors.street} touched={!!touched.street} placeholder="123 Main St" onChange={handleChange} onBlur={handleBlur} />
            <Field label="City" name="city" value={formData.city || ''} error={errors.city} touched={!!touched.city} placeholder="Springfield" onChange={handleChange} onBlur={handleBlur} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label="State" name="state" value={formData.state || ''} error={errors.state} touched={!!touched.state} placeholder="IL" onChange={handleChange} onBlur={handleBlur} />
              <Field label="ZIP Code" name="zip" value={formData.zip || ''} error={errors.zip} touched={!!touched.zip} placeholder="62701" onChange={handleChange} onBlur={handleBlur} />
            </div>
          </>
        )}

        {/* Step 3: Confirmation */}
        {currentStep === 3 && (
          <>
            <h3 style={{ marginTop: 0, marginBottom: 16 }}>Review &amp; Confirm</h3>
            {[
              { label: 'Name', value: formData.name },
              { label: 'Email', value: formData.email },
              { label: 'Phone', value: formData.phone },
              { label: 'Street', value: formData.street },
              { label: 'City', value: formData.city },
              { label: 'State', value: formData.state },
              { label: 'ZIP', value: formData.zip },
            ].map((row) => (
              <div key={row.label} style={css.summaryRow}>
                <span style={css.summaryLabel}>{row.label}</span>
                <span style={css.summaryValue}>{row.value || '—'}</span>
              </div>
            ))}
          </>
        )}

        {/* Navigation */}
        <div style={css.nav}>
          <div>
            {currentStep > 1 && (
              <button style={css.backBtn} onClick={handleBack}>
                ← Back
              </button>
            )}
          </div>
          <div>
            {currentStep < 3 ? (
              <button style={css.nextBtn} onClick={handleNext}>
                Next →
              </button>
            ) : (
              <button style={css.submitBtn} onClick={handleSubmit}>
                Submit ✓
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FormWizard;
