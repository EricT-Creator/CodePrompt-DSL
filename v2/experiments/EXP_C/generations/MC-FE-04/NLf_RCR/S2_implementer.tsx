import React, { useState } from 'react';

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

interface FormData {
  personalInfo: PersonalInfo;
  address: Address;
}

interface FieldErrors {
  [fieldName: string]: string;
}

export default function FormWizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<FormData>({
    personalInfo: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [isSubmitted, setIsSubmitted] = useState(false);

  const validatePersonalInfo = (data: PersonalInfo): FieldErrors => {
    const errs: FieldErrors = {};
    if (!data.name || data.name.length < 2) errs.name = 'Name must be at least 2 characters';
    else if (!/^[a-zA-Z\s]+$/.test(data.name)) errs.name = 'Name must contain only letters and spaces';
    if (!data.email) errs.email = 'Email is required';
    else if (!/^[^@]+@[^@]+\.[^@]+$/.test(data.email)) errs.email = 'Invalid email format';
    if (!data.phone) errs.phone = 'Phone is required';
    else {
      const digits = data.phone.replace(/[\s\-]/g, '');
      if (!/^\d{10,15}$/.test(digits)) errs.phone = 'Phone must be 10-15 digits';
    }
    return errs;
  };

  const validateAddress = (data: Address): FieldErrors => {
    const errs: FieldErrors = {};
    if (!data.street || data.street.length < 5) errs.street = 'Street must be at least 5 characters';
    if (!data.city || data.city.length < 2) errs.city = 'City must be at least 2 characters';
    else if (!/^[a-zA-Z\s]+$/.test(data.city)) errs.city = 'City must contain only letters and spaces';
    if (!data.state || data.state.length < 2) errs.state = 'State must be at least 2 characters';
    if (!data.zip) errs.zip = 'ZIP is required';
    else if (!/^\d{5}(-\d{4})?$/.test(data.zip)) errs.zip = 'ZIP must be 5 digits or 5+4 format';
    return errs;
  };

  const handleNext = () => {
    if (currentStep === 0) {
      const errs = validatePersonalInfo(formData.personalInfo);
      if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    } else if (currentStep === 1) {
      const errs = validateAddress(formData.address);
      if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    }
    setErrors({});
    setCurrentStep(currentStep + 1);
  };

  const handleBack = () => {
    setErrors({});
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = () => {
    console.log('Form submitted:', formData);
    setIsSubmitted(true);
  };

  const updatePersonalInfo = (field: keyof PersonalInfo, value: string) => {
    setFormData({ ...formData, personalInfo: { ...formData.personalInfo, [field]: value } });
  };

  const updateAddress = (field: keyof Address, value: string) => {
    setFormData({ ...formData, address: { ...formData.address, [field]: value } });
  };

  if (isSubmitted) {
    return (
      <div className="wizard-container">
        <style>{`
          .wizard-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 500px; margin: 50px auto; padding: 40px; text-align: center; }
          .success-message { color: #4CAF50; font-size: 24px; }
        `}</style>
        <div className="success-message">✓ Form submitted successfully!</div>
      </div>
    );
  }

  return (
    <div className="wizard-container">
      <style>{`
        .wizard-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; }
        .step-indicator { display: flex; justify-content: center; margin-bottom: 30px; }
        .step { width: 40px; height: 40px; border-radius: 50%; background: #ddd; display: flex; align-items: center; justify-content: center; margin: 0 10px; font-weight: 600; }
        .step.active { background: #2196F3; color: white; }
        .step.completed { background: #4CAF50; color: white; }
        .step-content { background: #f9f9f9; padding: 24px; border-radius: 8px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 500; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; }
        .error { color: #f44336; font-size: 12px; margin-top: 4px; }
        .navigation { display: flex; justify-content: space-between; margin-top: 24px; }
        .nav-button { padding: 10px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .nav-button.back { background: #f0f0f0; }
        .nav-button.next { background: #2196F3; color: white; }
        .nav-button.submit { background: #4CAF50; color: white; }
        .summary-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .summary-label { font-weight: 500; color: #666; }
        .summary-value { font-weight: 600; }
      `}</style>
      
      <div className="step-indicator">
        <div className={`step ${currentStep === 0 ? 'active' : currentStep > 0 ? 'completed' : ''}`}>1</div>
        <div className={`step ${currentStep === 1 ? 'active' : currentStep > 1 ? 'completed' : ''}`}>2</div>
        <div className={`step ${currentStep === 2 ? 'active' : ''}`}>3</div>
      </div>
      
      <div className="step-content">
        {currentStep === 0 && (
          <>
            <h2>Personal Information</h2>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={formData.personalInfo.name} onChange={e => updatePersonalInfo('name', e.target.value)} />
              {errors.name && <div className="error">{errors.name}</div>}
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={formData.personalInfo.email} onChange={e => updatePersonalInfo('email', e.target.value)} />
              {errors.email && <div className="error">{errors.email}</div>}
            </div>
            <div className="form-group">
              <label>Phone</label>
              <input type="tel" value={formData.personalInfo.phone} onChange={e => updatePersonalInfo('phone', e.target.value)} />
              {errors.phone && <div className="error">{errors.phone}</div>}
            </div>
          </>
        )}
        
        {currentStep === 1 && (
          <>
            <h2>Address</h2>
            <div className="form-group">
              <label>Street</label>
              <input type="text" value={formData.address.street} onChange={e => updateAddress('street', e.target.value)} />
              {errors.street && <div className="error">{errors.street}</div>}
            </div>
            <div className="form-group">
              <label>City</label>
              <input type="text" value={formData.address.city} onChange={e => updateAddress('city', e.target.value)} />
              {errors.city && <div className="error">{errors.city}</div>}
            </div>
            <div className="form-group">
              <label>State</label>
              <input type="text" value={formData.address.state} onChange={e => updateAddress('state', e.target.value)} />
              {errors.state && <div className="error">{errors.state}</div>}
            </div>
            <div className="form-group">
              <label>ZIP</label>
              <input type="text" value={formData.address.zip} onChange={e => updateAddress('zip', e.target.value)} />
              {errors.zip && <div className="error">{errors.zip}</div>}
            </div>
          </>
        )}
        
        {currentStep === 2 && (
          <>
            <h2>Confirmation</h2>
            <div className="summary-row"><span className="summary-label">Name:</span><span className="summary-value">{formData.personalInfo.name}</span></div>
            <div className="summary-row"><span className="summary-label">Email:</span><span className="summary-value">{formData.personalInfo.email}</span></div>
            <div className="summary-row"><span className="summary-label">Phone:</span><span className="summary-value">{formData.personalInfo.phone}</span></div>
            <div className="summary-row"><span className="summary-label">Street:</span><span className="summary-value">{formData.address.street}</span></div>
            <div className="summary-row"><span className="summary-label">City:</span><span className="summary-value">{formData.address.city}</span></div>
            <div className="summary-row"><span className="summary-label">State:</span><span className="summary-value">{formData.address.state}</span></div>
            <div className="summary-row"><span className="summary-label">ZIP:</span><span className="summary-value">{formData.address.zip}</span></div>
          </>
        )}
      </div>
      
      <div className="navigation">
        <button className="nav-button back" onClick={handleBack} disabled={currentStep === 0}>Back</button>
        {currentStep < 2 ? (
          <button className="nav-button next" onClick={handleNext}>Next</button>
        ) : (
          <button className="nav-button submit" onClick={handleSubmit}>Submit</button>
        )}
      </div>
    </div>
  );
}
