import React, { useState, useCallback } from 'react';

interface FormData {
  name: string;
  email: string;
  street: string;
  city: string;
  zipCode: string;
}

interface Errors {
  name?: string;
  email?: string;
  street?: string;
  city?: string;
  zipCode?: string;
}

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    street: '',
    city: '',
    zipCode: '',
  });
  const [errors, setErrors] = useState<Errors>({});

  const validateEmail = (email: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const validateStep1 = useCallback((): boolean => {
    const newErrors: Errors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData.name, formData.email]);

  const validateStep2 = useCallback((): boolean => {
    const newErrors: Errors = {};
    if (!formData.street.trim()) {
      newErrors.street = 'Street is required';
    }
    if (!formData.city.trim()) {
      newErrors.city = 'City is required';
    }
    if (!formData.zipCode.trim()) {
      newErrors.zipCode = 'Zip code is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData.street, formData.city, formData.zipCode]);

  const handleNext = useCallback(() => {
    let isValid = false;
    if (step === 1) {
      isValid = validateStep1();
    } else if (step === 2) {
      isValid = validateStep2();
    }
    if (isValid) {
      setStep(prev => prev + 1);
      setErrors({});
    }
  }, [step, validateStep1, validateStep2]);

  const handleBack = useCallback(() => {
    setStep(prev => prev - 1);
    setErrors({});
  }, []);

  const handleChange = useCallback((field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = useCallback(() => {
    console.log('Form submitted:', formData);
    alert('Form submitted successfully! Check console for data.');
  }, [formData]);

  const inputStyle: React.CSSProperties = {
    padding: '10px',
    fontSize: '16px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    width: '100%',
    boxSizing: 'border-box',
  };

  const errorStyle: React.CSSProperties = {
    color: '#f44336',
    fontSize: '14px',
    marginTop: '4px',
  };

  const buttonStyle: React.CSSProperties = {
    padding: '10px 20px',
    fontSize: '16px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '500px' }}>
      <h2>Multi-Step Form Wizard</h2>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          {[1, 2, 3].map(s => (
            <div
              key={s}
              style={{
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                background: s === step ? '#2196f3' : s < step ? '#4caf50' : '#e0e0e0',
                color: s === step || s < step ? '#fff' : '#666',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}
            >
              {s}
            </div>
          ))}
        </div>

        {step === 1 && (
          <div>
            <h3>Step 1: Personal Information</h3>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px' }}>Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                style={inputStyle}
                placeholder="Enter your name"
              />
              {errors.name && <div style={errorStyle}>{errors.name}</div>}
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px' }}>Email *</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                style={inputStyle}
                placeholder="Enter your email"
              />
              {errors.email && <div style={errorStyle}>{errors.email}</div>}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h3>Step 2: Address</h3>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px' }}>Street *</label>
              <input
                type="text"
                value={formData.street}
                onChange={(e) => handleChange('street', e.target.value)}
                style={inputStyle}
                placeholder="Enter street address"
              />
              {errors.street && <div style={errorStyle}>{errors.street}</div>}
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px' }}>City *</label>
              <input
                type="text"
                value={formData.city}
                onChange={(e) => handleChange('city', e.target.value)}
                style={inputStyle}
                placeholder="Enter city"
              />
              {errors.city && <div style={errorStyle}>{errors.city}</div>}
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px' }}>Zip Code *</label>
              <input
                type="text"
                value={formData.zipCode}
                onChange={(e) => handleChange('zipCode', e.target.value)}
                style={inputStyle}
                placeholder="Enter zip code"
              />
              {errors.zipCode && <div style={errorStyle}>{errors.zipCode}</div>}
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h3>Step 3: Review & Confirm</h3>
            <div style={{ background: '#f5f5f5', padding: '15px', borderRadius: '4px', marginBottom: '15px' }}>
              <h4>Personal Information</h4>
              <p><strong>Name:</strong> {formData.name}</p>
              <p><strong>Email:</strong> {formData.email}</p>
              <h4 style={{ marginTop: '15px' }}>Address</h4>
              <p><strong>Street:</strong> {formData.street}</p>
              <p><strong>City:</strong> {formData.city}</p>
              <p><strong>Zip Code:</strong> {formData.zipCode}</p>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
          {step > 1 && (
            <button
              onClick={handleBack}
              style={{ ...buttonStyle, background: '#e0e0e0', color: '#333' }}
            >
              Back
            </button>
          )}
          {step < 3 ? (
            <button
              onClick={handleNext}
              style={{ ...buttonStyle, background: '#2196f3', color: '#fff' }}
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              style={{ ...buttonStyle, background: '#4caf50', color: '#fff' }}
            >
              Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
