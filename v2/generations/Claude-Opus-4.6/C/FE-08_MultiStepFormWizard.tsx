import React, { useState, useCallback } from 'react';

interface PersonalInfo {
  name: string;
  email: string;
}

interface AddressInfo {
  street: string;
  city: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

interface FieldErrors {
  [key: string]: string;
}

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: '', email: '' },
    address: { street: '', city: '', zip: '' },
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const validateEmail = (email: string): boolean => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validateStep = useCallback((currentStep: number): boolean => {
    const newErrors: FieldErrors = {};

    if (currentStep === 0) {
      if (!formData.personal.name.trim()) {
        newErrors.name = 'Name is required';
      } else if (formData.personal.name.trim().length < 2) {
        newErrors.name = 'Name must be at least 2 characters';
      }
      if (!formData.personal.email.trim()) {
        newErrors.email = 'Email is required';
      } else if (!validateEmail(formData.personal.email)) {
        newErrors.email = 'Please enter a valid email';
      }
    }

    if (currentStep === 1) {
      if (!formData.address.street.trim()) {
        newErrors.street = 'Street is required';
      }
      if (!formData.address.city.trim()) {
        newErrors.city = 'City is required';
      }
      if (!formData.address.zip.trim()) {
        newErrors.zip = 'ZIP code is required';
      } else if (!/^\d{5}(-\d{4})?$/.test(formData.address.zip.trim())) {
        newErrors.zip = 'Enter a valid ZIP code (e.g. 12345)';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const handleNext = () => {
    if (validateStep(step)) {
      setStep(s => s + 1);
    }
  };

  const handleBack = () => {
    setErrors({});
    setStep(s => s - 1);
  };

  const handleSubmit = () => {
    console.log('Form submitted:', formData);
    setSubmitted(true);
  };

  const updatePersonal = (field: keyof PersonalInfo, value: string) => {
    setFormData(prev => ({
      ...prev,
      personal: { ...prev.personal, [field]: value },
    }));
    if (errors[field]) {
      setErrors(prev => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const updateAddress = (field: keyof AddressInfo, value: string) => {
    setFormData(prev => ({
      ...prev,
      address: { ...prev.address, [field]: value },
    }));
    if (errors[field]) {
      setErrors(prev => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const steps = ['Personal', 'Address', 'Review'];

  if (submitted) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✓</div>
          <h2 style={styles.successTitle}>Submitted Successfully!</h2>
          <p style={styles.successText}>Check the console for submitted data.</p>
          <button
            style={styles.primaryBtn}
            onClick={() => {
              setSubmitted(false);
              setStep(0);
              setFormData({ personal: { name: '', email: '' }, address: { street: '', city: '', zip: '' } });
            }}
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.stepper}>
          {steps.map((label, i) => (
            <div key={label} style={styles.stepItem}>
              <div
                style={{
                  ...styles.stepCircle,
                  ...(i <= step ? styles.stepCircleActive : {}),
                  ...(i < step ? styles.stepCircleCompleted : {}),
                }}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <span
                style={{
                  ...styles.stepLabel,
                  ...(i <= step ? styles.stepLabelActive : {}),
                }}
              >
                {label}
              </span>
              {i < steps.length - 1 && (
                <div
                  style={{
                    ...styles.stepLine,
                    ...(i < step ? styles.stepLineActive : {}),
                  }}
                />
              )}
            </div>
          ))}
        </div>

        {step === 0 && (
          <div style={styles.formSection}>
            <h3 style={styles.sectionTitle}>Personal Information</h3>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Full Name</label>
              <input
                type="text"
                value={formData.personal.name}
                onChange={e => updatePersonal('name', e.target.value)}
                style={{
                  ...styles.input,
                  ...(errors.name ? styles.inputError : {}),
                }}
                placeholder="John Doe"
              />
              {errors.name && <span style={styles.errorText}>{errors.name}</span>}
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Email Address</label>
              <input
                type="email"
                value={formData.personal.email}
                onChange={e => updatePersonal('email', e.target.value)}
                style={{
                  ...styles.input,
                  ...(errors.email ? styles.inputError : {}),
                }}
                placeholder="john@example.com"
              />
              {errors.email && <span style={styles.errorText}>{errors.email}</span>}
            </div>
          </div>
        )}

        {step === 1 && (
          <div style={styles.formSection}>
            <h3 style={styles.sectionTitle}>Address Information</h3>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Street Address</label>
              <input
                type="text"
                value={formData.address.street}
                onChange={e => updateAddress('street', e.target.value)}
                style={{
                  ...styles.input,
                  ...(errors.street ? styles.inputError : {}),
                }}
                placeholder="123 Main St"
              />
              {errors.street && <span style={styles.errorText}>{errors.street}</span>}
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>City</label>
              <input
                type="text"
                value={formData.address.city}
                onChange={e => updateAddress('city', e.target.value)}
                style={{
                  ...styles.input,
                  ...(errors.city ? styles.inputError : {}),
                }}
                placeholder="San Francisco"
              />
              {errors.city && <span style={styles.errorText}>{errors.city}</span>}
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>ZIP Code</label>
              <input
                type="text"
                value={formData.address.zip}
                onChange={e => updateAddress('zip', e.target.value)}
                style={{
                  ...styles.input,
                  ...(errors.zip ? styles.inputError : {}),
                }}
                placeholder="94102"
              />
              {errors.zip && <span style={styles.errorText}>{errors.zip}</span>}
            </div>
          </div>
        )}

        {step === 2 && (
          <div style={styles.formSection}>
            <h3 style={styles.sectionTitle}>Review Your Information</h3>
            <div style={styles.reviewGroup}>
              <h4 style={styles.reviewSubtitle}>Personal</h4>
              <div style={styles.reviewRow}>
                <span style={styles.reviewLabel}>Name:</span>
                <span style={styles.reviewValue}>{formData.personal.name}</span>
              </div>
              <div style={styles.reviewRow}>
                <span style={styles.reviewLabel}>Email:</span>
                <span style={styles.reviewValue}>{formData.personal.email}</span>
              </div>
            </div>
            <div style={styles.reviewGroup}>
              <h4 style={styles.reviewSubtitle}>Address</h4>
              <div style={styles.reviewRow}>
                <span style={styles.reviewLabel}>Street:</span>
                <span style={styles.reviewValue}>{formData.address.street}</span>
              </div>
              <div style={styles.reviewRow}>
                <span style={styles.reviewLabel}>City:</span>
                <span style={styles.reviewValue}>{formData.address.city}</span>
              </div>
              <div style={styles.reviewRow}>
                <span style={styles.reviewLabel}>ZIP:</span>
                <span style={styles.reviewValue}>{formData.address.zip}</span>
              </div>
            </div>
          </div>
        )}

        <div style={styles.navButtons}>
          {step > 0 && (
            <button style={styles.secondaryBtn} onClick={handleBack}>
              ← Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          {step < 2 ? (
            <button style={styles.primaryBtn} onClick={handleNext}>
              Next →
            </button>
          ) : (
            <button style={styles.submitBtn} onClick={handleSubmit}>
              Submit ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '520px',
    margin: '40px auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '16px',
  },
  card: {
    background: '#ffffff',
    borderRadius: '12px',
    padding: '32px',
    border: '1px solid #e5e7eb',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  stepper: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: '32px',
  },
  stepItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  stepCircle: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: 600,
    background: '#f3f4f6',
    color: '#9ca3af',
    border: '2px solid #e5e7eb',
  },
  stepCircleActive: {
    background: '#eff6ff',
    color: '#2563eb',
    borderColor: '#3b82f6',
  },
  stepCircleCompleted: {
    background: '#22c55e',
    color: '#fff',
    borderColor: '#22c55e',
  },
  stepLabel: {
    fontSize: '13px',
    color: '#9ca3af',
    fontWeight: 500,
  },
  stepLabelActive: {
    color: '#374151',
  },
  stepLine: {
    width: '40px',
    height: '2px',
    background: '#e5e7eb',
    margin: '0 8px',
  },
  stepLineActive: {
    background: '#22c55e',
  },
  formSection: {
    marginBottom: '24px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#1f2937',
    marginBottom: '20px',
    margin: '0 0 20px 0',
  },
  fieldGroup: {
    marginBottom: '16px',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: '#374151',
    marginBottom: '6px',
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s',
  },
  inputError: {
    borderColor: '#ef4444',
    background: '#fef2f2',
  },
  errorText: {
    fontSize: '12px',
    color: '#ef4444',
    marginTop: '4px',
    display: 'block',
  },
  reviewGroup: {
    marginBottom: '20px',
    padding: '16px',
    background: '#f9fafb',
    borderRadius: '8px',
  },
  reviewSubtitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#6b7280',
    marginBottom: '10px',
    margin: '0 0 10px 0',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  reviewRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    borderBottom: '1px solid #f3f4f6',
  },
  reviewLabel: {
    fontSize: '13px',
    color: '#6b7280',
  },
  reviewValue: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#1f2937',
  },
  navButtons: {
    display: 'flex',
    alignItems: 'center',
    paddingTop: '16px',
    borderTop: '1px solid #f3f4f6',
  },
  primaryBtn: {
    padding: '10px 24px',
    background: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  secondaryBtn: {
    padding: '10px 24px',
    background: '#fff',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  submitBtn: {
    padding: '10px 24px',
    background: '#22c55e',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  successIcon: {
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    background: '#22c55e',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '32px',
    margin: '0 auto 16px',
  },
  successTitle: {
    textAlign: 'center',
    color: '#1f2937',
    margin: '0 0 8px 0',
  },
  successText: {
    textAlign: 'center',
    color: '#6b7280',
    margin: '0 0 24px 0',
  },
};

export default MultiStepFormWizard;
