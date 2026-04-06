import React, { useState } from 'react';

interface PersonalInfo {
  name: string;
  email: string;
}

interface AddressInfo {
  street: string;
  city: string;
  zipCode: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

interface Errors {
  [key: string]: string;
}

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: '', email: '' },
    address: { street: '', city: '', zipCode: '' },
  });
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);

  const validateEmail = (email: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const validateStep1 = (): boolean => {
    const newErrors: Errors = {};
    if (!formData.personal.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.personal.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(formData.personal.email)) {
      newErrors.email = 'Invalid email format';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = (): boolean => {
    const newErrors: Errors = {};
    if (!formData.address.street.trim()) {
      newErrors.street = 'Street is required';
    }
    if (!formData.address.city.trim()) {
      newErrors.city = 'City is required';
    }
    if (!formData.address.zipCode.trim()) {
      newErrors.zipCode = 'Zip code is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (step === 1 && validateStep1()) {
      setStep(2);
      setErrors({});
    } else if (step === 2 && validateStep2()) {
      setStep(3);
      setErrors({});
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

  if (submitted) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={successStyle}>
            <span style={{ fontSize: '48px' }}>✅</span>
            <h2 style={{ color: '#2e7d32', margin: '12px 0' }}>Form Submitted!</h2>
            <p style={{ color: '#555' }}>Check the console for submitted data.</p>
            <button
              style={primaryBtnStyle}
              onClick={() => { setSubmitted(false); setStep(1); setFormData({ personal: { name: '', email: '' }, address: { street: '', city: '', zipCode: '' } }); }}
            >
              Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h2 style={titleStyle}>Multi-Step Form</h2>

        <div style={stepsBarStyle}>
          {[1, 2, 3].map(s => (
            <div key={s} style={stepIndicatorWrapperStyle}>
              <div style={{
                ...stepCircleStyle,
                background: s <= step ? '#1976d2' : '#e0e0e0',
                color: s <= step ? '#fff' : '#999',
              }}>
                {s}
              </div>
              <span style={{
                fontSize: '12px',
                color: s <= step ? '#1976d2' : '#999',
                marginTop: '4px',
              }}>
                {s === 1 ? 'Personal' : s === 2 ? 'Address' : 'Review'}
              </span>
            </div>
          ))}
        </div>

        {step === 1 && (
          <div>
            <h3 style={stepTitleStyle}>Personal Information</h3>
            <div style={fieldStyle}>
              <label style={labelStyle}>Name *</label>
              <input
                style={errors.name ? errorInputStyle : inputStyle}
                value={formData.personal.name}
                onChange={e => updatePersonal('name', e.target.value)}
                placeholder="Enter your name"
              />
              {errors.name && <span style={errorTextStyle}>{errors.name}</span>}
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Email *</label>
              <input
                style={errors.email ? errorInputStyle : inputStyle}
                value={formData.personal.email}
                onChange={e => updatePersonal('email', e.target.value)}
                placeholder="Enter your email"
                type="email"
              />
              {errors.email && <span style={errorTextStyle}>{errors.email}</span>}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h3 style={stepTitleStyle}>Address Information</h3>
            <div style={fieldStyle}>
              <label style={labelStyle}>Street *</label>
              <input
                style={errors.street ? errorInputStyle : inputStyle}
                value={formData.address.street}
                onChange={e => updateAddress('street', e.target.value)}
                placeholder="Enter street address"
              />
              {errors.street && <span style={errorTextStyle}>{errors.street}</span>}
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>City *</label>
              <input
                style={errors.city ? errorInputStyle : inputStyle}
                value={formData.address.city}
                onChange={e => updateAddress('city', e.target.value)}
                placeholder="Enter city"
              />
              {errors.city && <span style={errorTextStyle}>{errors.city}</span>}
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Zip Code *</label>
              <input
                style={errors.zipCode ? errorInputStyle : inputStyle}
                value={formData.address.zipCode}
                onChange={e => updateAddress('zipCode', e.target.value)}
                placeholder="Enter zip code"
              />
              {errors.zipCode && <span style={errorTextStyle}>{errors.zipCode}</span>}
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h3 style={stepTitleStyle}>Review & Confirm</h3>
            <div style={reviewSectionStyle}>
              <h4 style={reviewHeadingStyle}>Personal Information</h4>
              <div style={reviewRowStyle}>
                <span style={reviewLabelStyle}>Name:</span>
                <span>{formData.personal.name}</span>
              </div>
              <div style={reviewRowStyle}>
                <span style={reviewLabelStyle}>Email:</span>
                <span>{formData.personal.email}</span>
              </div>
            </div>
            <div style={reviewSectionStyle}>
              <h4 style={reviewHeadingStyle}>Address</h4>
              <div style={reviewRowStyle}>
                <span style={reviewLabelStyle}>Street:</span>
                <span>{formData.address.street}</span>
              </div>
              <div style={reviewRowStyle}>
                <span style={reviewLabelStyle}>City:</span>
                <span>{formData.address.city}</span>
              </div>
              <div style={reviewRowStyle}>
                <span style={reviewLabelStyle}>Zip Code:</span>
                <span>{formData.address.zipCode}</span>
              </div>
            </div>
          </div>
        )}

        <div style={navStyle}>
          {step > 1 && (
            <button style={secondaryBtnStyle} onClick={handleBack}>
              ← Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          {step < 3 && (
            <button style={primaryBtnStyle} onClick={handleNext}>
              Next →
            </button>
          )}
          {step === 3 && (
            <button style={submitBtnStyle} onClick={handleSubmit}>
              Submit ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  maxWidth: '500px',
  margin: '40px auto',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: '12px',
  padding: '32px',
  boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
  border: '1px solid #e0e0e0',
};

const titleStyle: React.CSSProperties = {
  textAlign: 'center',
  color: '#333',
  margin: '0 0 24px 0',
};

const stepsBarStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'center',
  gap: '40px',
  marginBottom: '28px',
};

const stepIndicatorWrapperStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
};

const stepCircleStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 600,
  fontSize: '15px',
  transition: 'background 0.3s, color 0.3s',
};

const stepTitleStyle: React.CSSProperties = {
  color: '#444',
  marginBottom: '16px',
  fontSize: '17px',
};

const fieldStyle: React.CSSProperties = {
  marginBottom: '16px',
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '13px',
  fontWeight: 600,
  color: '#555',
  marginBottom: '6px',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #ccc',
  borderRadius: '6px',
  fontSize: '14px',
  boxSizing: 'border-box',
  outline: 'none',
};

const errorInputStyle: React.CSSProperties = {
  ...inputStyle,
  borderColor: '#e53935',
  boxShadow: '0 0 0 2px rgba(229,57,53,0.15)',
};

const errorTextStyle: React.CSSProperties = {
  display: 'block',
  color: '#e53935',
  fontSize: '12px',
  marginTop: '4px',
};

const navStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  marginTop: '24px',
  gap: '12px',
};

const primaryBtnStyle: React.CSSProperties = {
  padding: '10px 24px',
  background: '#1976d2',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 600,
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: '10px 24px',
  background: '#f5f5f5',
  color: '#555',
  border: '1px solid #ccc',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
};

const submitBtnStyle: React.CSSProperties = {
  padding: '10px 24px',
  background: '#2e7d32',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 600,
};

const successStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '20px',
};

const reviewSectionStyle: React.CSSProperties = {
  background: '#fafafa',
  borderRadius: '8px',
  padding: '16px',
  marginBottom: '12px',
  border: '1px solid #eee',
};

const reviewHeadingStyle: React.CSSProperties = {
  margin: '0 0 10px 0',
  fontSize: '14px',
  color: '#1976d2',
};

const reviewRowStyle: React.CSSProperties = {
  display: 'flex',
  padding: '4px 0',
  fontSize: '14px',
};

const reviewLabelStyle: React.CSSProperties = {
  fontWeight: 600,
  color: '#555',
  width: '80px',
};

export default MultiStepFormWizard;
