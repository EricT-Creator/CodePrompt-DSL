import React, { useState } from 'react';

interface FormData {
  name: string;
  email: string;
  street: string;
  city: string;
  zip: string;
}

interface Errors {
  name?: string;
  email?: string;
  street?: string;
  city?: string;
  zip?: string;
}

const initialFormData: FormData = {
  name: '',
  email: '',
  street: '',
  city: '',
  zip: '',
};

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validateStep1 = (): boolean => {
    const newErrors: Errors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = (): boolean => {
    const newErrors: Errors = {};
    
    if (!formData.street.trim()) {
      newErrors.street = 'Street is required';
    }
    
    if (!formData.city.trim()) {
      newErrors.city = 'City is required';
    }
    
    if (!formData.zip.trim()) {
      newErrors.zip = 'ZIP code is required';
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
    setStep(step - 1);
    setErrors({});
  };

  const handleSubmit = () => {
    console.log('Form submitted:', formData);
    setSubmitted(true);
  };

  const handleChange = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [field]: e.target.value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
    boxSizing: 'border-box',
  };

  const errorInputStyle: React.CSSProperties = {
    ...inputStyle,
    borderColor: '#ff6b6b',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: '6px',
    fontWeight: 500,
    color: '#333',
  };

  const errorStyle: React.CSSProperties = {
    color: '#ff6b6b',
    fontSize: '12px',
    marginTop: '4px',
  };

  const buttonStyle: React.CSSProperties = {
    padding: '10px 24px',
    borderRadius: '4px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
  };

  const primaryButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: '#4a90d9',
    color: '#fff',
  };

  const secondaryButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: '#f0f0f0',
    color: '#333',
  };

  const renderStep1 = () => (
    <div>
      <h3 style={{ marginBottom: '20px' }}>Step 1: Personal Information</h3>
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>Name *</label>
        <input
          type="text"
          value={formData.name}
          onChange={handleChange('name')}
          style={errors.name ? errorInputStyle : inputStyle}
          placeholder="Enter your full name"
        />
        {errors.name && <span style={errorStyle}>{errors.name}</span>}
      </div>
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>Email *</label>
        <input
          type="email"
          value={formData.email}
          onChange={handleChange('email')}
          style={errors.email ? errorInputStyle : inputStyle}
          placeholder="Enter your email address"
        />
        {errors.email && <span style={errorStyle}>{errors.email}</span>}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div>
      <h3 style={{ marginBottom: '20px' }}>Step 2: Address</h3>
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>Street *</label>
        <input
          type="text"
          value={formData.street}
          onChange={handleChange('street')}
          style={errors.street ? errorInputStyle : inputStyle}
          placeholder="Enter street address"
        />
        {errors.street && <span style={errorStyle}>{errors.street}</span>}
      </div>
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>City *</label>
        <input
          type="text"
          value={formData.city}
          onChange={handleChange('city')}
          style={errors.city ? errorInputStyle : inputStyle}
          placeholder="Enter city"
        />
        {errors.city && <span style={errorStyle}>{errors.city}</span>}
      </div>
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>ZIP Code *</label>
        <input
          type="text"
          value={formData.zip}
          onChange={handleChange('zip')}
          style={errors.zip ? errorInputStyle : inputStyle}
          placeholder="Enter ZIP code"
        />
        {errors.zip && <span style={errorStyle}>{errors.zip}</span>}
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div>
      <h3 style={{ marginBottom: '20px' }}>Step 3: Review & Submit</h3>
      <div style={{ backgroundColor: '#f9f9f9', padding: '16px', borderRadius: '8px', marginBottom: '20px' }}>
        <h4 style={{ marginBottom: '12px', color: '#666' }}>Personal Information</h4>
        <p style={{ margin: '8px 0' }}><strong>Name:</strong> {formData.name}</p>
        <p style={{ margin: '8px 0' }}><strong>Email:</strong> {formData.email}</p>
        
        <h4 style={{ margin: '16px 0 12px', color: '#666' }}>Address</h4>
        <p style={{ margin: '8px 0' }}><strong>Street:</strong> {formData.street}</p>
        <p style={{ margin: '8px 0' }}><strong>City:</strong> {formData.city}</p>
        <p style={{ margin: '8px 0' }}><strong>ZIP:</strong> {formData.zip}</p>
      </div>
    </div>
  );

  if (submitted) {
    return (
      <div style={{ maxWidth: '500px', margin: '40px auto', fontFamily: 'system-ui, sans-serif', textAlign: 'center' }}>
        <div style={{ padding: '40px', backgroundColor: '#d4edda', borderRadius: '8px' }}>
          <h2 style={{ color: '#155724', marginBottom: '16px' }}>✓ Form Submitted Successfully!</h2>
          <p style={{ color: '#155724' }}>Thank you for your submission. Check the console for form data.</p>
          <button
            onClick={() => {
              setSubmitted(false);
              setStep(1);
              setFormData(initialFormData);
            }}
            style={{ ...primaryButtonStyle, marginTop: '20px' }}
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '500px', margin: '40px auto', fontFamily: 'system-ui, sans-serif' }}>
      <h2 style={{ marginBottom: '24px', textAlign: 'center' }}>Multi-Step Form Wizard</h2>
      
      <div style={{ display: 'flex', marginBottom: '24px', justifyContent: 'center' }}>
        {[1, 2, 3].map((s) => (
          <div key={s} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: s === step ? '#4a90d9' : s < step ? '#28a745' : '#e0e0e0',
                color: s <= step ? '#fff' : '#666',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}
            >
              {s < step ? '✓' : s}
            </div>
            {s < 3 && (
              <div
                style={{
                  width: '60px',
                  height: '2px',
                  backgroundColor: s < step ? '#28a745' : '#e0e0e0',
                }}
              />
            )}
          </div>
        ))}
      </div>

      <div style={{ backgroundColor: '#fff', padding: '24px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
          {step > 1 ? (
            <button onClick={handleBack} style={secondaryButtonStyle}>
              ← Back
            </button>
          ) : (
            <div />
          )}
          
          {step < 3 ? (
            <button onClick={handleNext} style={primaryButtonStyle}>
              Next →
            </button>
          ) : (
            <button onClick={handleSubmit} style={primaryButtonStyle}>
              Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
