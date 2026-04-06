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
  const [isSubmitted, setIsSubmitted] = useState(false);

  const validateStep1 = (): boolean => {
    const newErrors: Errors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
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
    } else if (!/^\d{5}(-\d{4})?$/.test(formData.zip)) {
      newErrors.zip = 'Please enter a valid ZIP code';
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
    setIsSubmitted(true);
  };

  const handleChange = (field: keyof FormData, value: string) => {
    setFormData({ ...formData, [field]: value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '16px',
    boxSizing: 'border-box',
  };

  const errorStyle: React.CSSProperties = {
    color: '#f44336',
    fontSize: '14px',
    marginTop: '4px',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: '8px',
    fontWeight: 600,
    color: '#333',
  };

  const formGroupStyle: React.CSSProperties = {
    marginBottom: '20px',
  };

  const buttonStyle: React.CSSProperties = {
    padding: '12px 24px',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'background 0.2s',
  };

  const progressStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '24px',
    gap: '8px',
  };

  const stepIndicatorStyle = (isActive: boolean, isCompleted: boolean): React.CSSProperties => ({
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 600,
    background: isActive ? '#2196f3' : isCompleted ? '#4caf50' : '#e0e0e0',
    color: isActive || isCompleted ? 'white' : '#666',
  });

  if (isSubmitted) {
    return (
      <div style={{ maxWidth: '500px', margin: '40px auto', padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '64px', marginBottom: '16px' }}>✓</div>
        <h2 style={{ color: '#4caf50', marginBottom: '16px' }}>Form Submitted Successfully!</h2>
        <p style={{ color: '#666' }}>Check the console for the submitted data.</p>
        <button
          onClick={() => {
            setIsSubmitted(false);
            setStep(1);
            setFormData(initialFormData);
          }}
          style={{ ...buttonStyle, background: '#2196f3', color: 'white', marginTop: '24px' }}
        >
          Start Over
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '500px', margin: '40px auto', padding: '20px' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '24px' }}>Registration Wizard</h2>
      
      <div style={progressStyle}>
        <div style={stepIndicatorStyle(step === 1, step > 1)}>1</div>
        <div style={stepIndicatorStyle(step === 2, step > 2)}>2</div>
        <div style={stepIndicatorStyle(step === 3, false)}>3</div>
      </div>

      <div style={{ background: '#f9f9f9', padding: '24px', borderRadius: '8px' }}>
        {step === 1 && (
          <div>
            <h3 style={{ marginBottom: '20px' }}>Step 1: Personal Information</h3>
            <div style={formGroupStyle}>
              <label style={labelStyle}>Full Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                style={{ ...inputStyle, borderColor: errors.name ? '#f44336' : '#ddd' }}
                placeholder="Enter your full name"
              />
              {errors.name && <div style={errorStyle}>{errors.name}</div>}
            </div>
            <div style={formGroupStyle}>
              <label style={labelStyle}>Email Address *</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                style={{ ...inputStyle, borderColor: errors.email ? '#f44336' : '#ddd' }}
                placeholder="Enter your email"
              />
              {errors.email && <div style={errorStyle}>{errors.email}</div>}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h3 style={{ marginBottom: '20px' }}>Step 2: Address Information</h3>
            <div style={formGroupStyle}>
              <label style={labelStyle}>Street Address *</label>
              <input
                type="text"
                value={formData.street}
                onChange={(e) => handleChange('street', e.target.value)}
                style={{ ...inputStyle, borderColor: errors.street ? '#f44336' : '#ddd' }}
                placeholder="Enter street address"
              />
              {errors.street && <div style={errorStyle}>{errors.street}</div>}
            </div>
            <div style={formGroupStyle}>
              <label style={labelStyle}>City *</label>
              <input
                type="text"
                value={formData.city}
                onChange={(e) => handleChange('city', e.target.value)}
                style={{ ...inputStyle, borderColor: errors.city ? '#f44336' : '#ddd' }}
                placeholder="Enter city"
              />
              {errors.city && <div style={errorStyle}>{errors.city}</div>}
            </div>
            <div style={formGroupStyle}>
              <label style={labelStyle}>ZIP Code *</label>
              <input
                type="text"
                value={formData.zip}
                onChange={(e) => handleChange('zip', e.target.value)}
                style={{ ...inputStyle, borderColor: errors.zip ? '#f44336' : '#ddd' }}
                placeholder="12345"
              />
              {errors.zip && <div style={errorStyle}>{errors.zip}</div>}
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h3 style={{ marginBottom: '20px' }}>Step 3: Review</h3>
            <div style={{ background: 'white', padding: '16px', borderRadius: '4px', marginBottom: '16px' }}>
              <h4 style={{ marginBottom: '12px', color: '#666' }}>Personal Information</h4>
              <p><strong>Name:</strong> {formData.name}</p>
              <p><strong>Email:</strong> {formData.email}</p>
            </div>
            <div style={{ background: 'white', padding: '16px', borderRadius: '4px' }}>
              <h4 style={{ marginBottom: '12px', color: '#666' }}>Address Information</h4>
              <p><strong>Street:</strong> {formData.street}</p>
              <p><strong>City:</strong> {formData.city}</p>
              <p><strong>ZIP:</strong> {formData.zip}</p>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
          {step > 1 ? (
            <button
              onClick={handleBack}
              style={{ ...buttonStyle, background: '#e0e0e0', color: '#333' }}
            >
              Back
            </button>
          ) : (
            <div></div>
          )}
          
          {step < 3 ? (
            <button
              onClick={handleNext}
              style={{ ...buttonStyle, background: '#2196f3', color: 'white' }}
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              style={{ ...buttonStyle, background: '#4caf50', color: 'white' }}
            >
              Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
