import React, { useState, useCallback } from 'react';

// ── Types ──

interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface AddressInfo {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

interface FormErrors {
  [field: string]: string;
}

type StepNumber = 1 | 2 | 3;

// ── Validation ──

function validateStep(step: StepNumber, data: FormData): FormErrors {
  const errors: FormErrors = {};

  if (step === 1) {
    if (!data.personal.name || data.personal.name.trim().length < 2) {
      errors.name = 'Name is required and must be at least 2 characters';
    }
    if (!data.personal.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.personal.email)) {
      errors.email = 'Valid email is required';
    }
    if (!data.personal.phone || !/^\+?[\d\s\-()]{7,15}$/.test(data.personal.phone)) {
      errors.phone = 'Valid phone number is required';
    }
  }

  if (step === 2) {
    if (!data.address.street.trim()) {
      errors.street = 'Street address is required';
    }
    if (!data.address.city || data.address.city.trim().length < 2) {
      errors.city = 'City is required';
    }
    if (!data.address.state.trim()) {
      errors.state = 'State is required';
    }
    if (!data.address.zip || !/^\d{5}(-\d{4})?$/.test(data.address.zip)) {
      errors.zip = 'Valid ZIP code is required';
    }
  }

  return errors;
}

// ── Styles ──

const css = `
  .wizard-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    max-width: 600px;
    margin: 40px auto;
    padding: 0 20px;
  }
  .wizard-title {
    text-align: center;
    font-size: 24px;
    font-weight: 700;
    color: #2d3436;
    margin-bottom: 24px;
  }
  .step-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 32px;
  }
  .step-circle {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
    border: 2px solid #b2bec3;
    color: #b2bec3;
    background: #fff;
    transition: all 0.2s;
  }
  .step-circle.active {
    border-color: #0984e3;
    background: #0984e3;
    color: #fff;
  }
  .step-circle.completed {
    border-color: #00b894;
    background: #00b894;
    color: #fff;
  }
  .step-line {
    width: 60px;
    height: 2px;
    background: #b2bec3;
    margin: 0 8px;
    transition: background 0.2s;
  }
  .step-line.active {
    background: #00b894;
  }
  .form-card {
    background: #fff;
    border-radius: 12px;
    padding: 28px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    margin-bottom: 20px;
  }
  .form-group {
    margin-bottom: 18px;
  }
  .form-label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #636e72;
    margin-bottom: 6px;
  }
  .form-input {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
    box-sizing: border-box;
  }
  .form-input:focus {
    border-color: #0984e3;
  }
  .form-input.error {
    border-color: #d63031;
  }
  .error-message {
    color: #d63031;
    font-size: 12px;
    margin-top: 4px;
  }
  .button-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .btn {
    padding: 10px 24px;
    border-radius: 8px;
    border: none;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-primary {
    background: #0984e3;
    color: #fff;
  }
  .btn-primary:hover {
    background: #0773c5;
  }
  .btn-secondary {
    background: #dfe6e9;
    color: #2d3436;
  }
  .btn-secondary:hover {
    background: #b2bec3;
  }
  .btn-success {
    background: #00b894;
    color: #fff;
  }
  .btn-success:hover {
    background: #00a381;
  }
  .confirmation-section {
    margin-bottom: 16px;
  }
  .confirmation-title {
    font-size: 14px;
    font-weight: 700;
    color: #2d3436;
    margin-bottom: 8px;
    border-bottom: 1px solid #eee;
    padding-bottom: 4px;
  }
  .confirmation-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
  }
  .confirmation-label {
    color: #636e72;
  }
  .confirmation-value {
    font-weight: 500;
    color: #2d3436;
  }
  .success-message {
    text-align: center;
    padding: 40px 20px;
  }
  .success-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }
  .success-text {
    font-size: 20px;
    font-weight: 700;
    color: #00b894;
    margin-bottom: 8px;
  }
  .success-sub {
    font-size: 14px;
    color: #636e72;
  }
`;

// ── FieldError ──

const FieldError: React.FC<{ message?: string }> = ({ message }) => {
  if (!message) return null;
  return <div className="error-message">{message}</div>;
};

// ── StepPersonal ──

const StepPersonal: React.FC<{
  values: PersonalInfo;
  errors: FormErrors;
  onChange: (field: string, value: string) => void;
}> = ({ values, errors, onChange }) => (
  <div>
    <div className="form-group">
      <label className="form-label">Name</label>
      <input
        className={`form-input ${errors.name ? 'error' : ''}`}
        type="text"
        value={values.name}
        onChange={(e) => onChange('name', e.target.value)}
        placeholder="Enter your name"
      />
      <FieldError message={errors.name} />
    </div>
    <div className="form-group">
      <label className="form-label">Email</label>
      <input
        className={`form-input ${errors.email ? 'error' : ''}`}
        type="email"
        value={values.email}
        onChange={(e) => onChange('email', e.target.value)}
        placeholder="Enter your email"
      />
      <FieldError message={errors.email} />
    </div>
    <div className="form-group">
      <label className="form-label">Phone</label>
      <input
        className={`form-input ${errors.phone ? 'error' : ''}`}
        type="tel"
        value={values.phone}
        onChange={(e) => onChange('phone', e.target.value)}
        placeholder="Enter your phone number"
      />
      <FieldError message={errors.phone} />
    </div>
  </div>
);

// ── StepAddress ──

const StepAddress: React.FC<{
  values: AddressInfo;
  errors: FormErrors;
  onChange: (field: string, value: string) => void;
}> = ({ values, errors, onChange }) => (
  <div>
    <div className="form-group">
      <label className="form-label">Street</label>
      <input
        className={`form-input ${errors.street ? 'error' : ''}`}
        type="text"
        value={values.street}
        onChange={(e) => onChange('street', e.target.value)}
        placeholder="Enter street address"
      />
      <FieldError message={errors.street} />
    </div>
    <div className="form-group">
      <label className="form-label">City</label>
      <input
        className={`form-input ${errors.city ? 'error' : ''}`}
        type="text"
        value={values.city}
        onChange={(e) => onChange('city', e.target.value)}
        placeholder="Enter city"
      />
      <FieldError message={errors.city} />
    </div>
    <div className="form-group">
      <label className="form-label">State</label>
      <input
        className={`form-input ${errors.state ? 'error' : ''}`}
        type="text"
        value={values.state}
        onChange={(e) => onChange('state', e.target.value)}
        placeholder="Enter state"
      />
      <FieldError message={errors.state} />
    </div>
    <div className="form-group">
      <label className="form-label">ZIP Code</label>
      <input
        className={`form-input ${errors.zip ? 'error' : ''}`}
        type="text"
        value={values.zip}
        onChange={(e) => onChange('zip', e.target.value)}
        placeholder="Enter ZIP code"
      />
      <FieldError message={errors.zip} />
    </div>
  </div>
);

// ── StepConfirmation ──

const StepConfirmation: React.FC<{ data: FormData }> = ({ data }) => (
  <div>
    <div className="confirmation-section">
      <div className="confirmation-title">Personal Information</div>
      <div className="confirmation-row">
        <span className="confirmation-label">Name</span>
        <span className="confirmation-value">{data.personal.name}</span>
      </div>
      <div className="confirmation-row">
        <span className="confirmation-label">Email</span>
        <span className="confirmation-value">{data.personal.email}</span>
      </div>
      <div className="confirmation-row">
        <span className="confirmation-label">Phone</span>
        <span className="confirmation-value">{data.personal.phone}</span>
      </div>
    </div>
    <div className="confirmation-section">
      <div className="confirmation-title">Address</div>
      <div className="confirmation-row">
        <span className="confirmation-label">Street</span>
        <span className="confirmation-value">{data.address.street}</span>
      </div>
      <div className="confirmation-row">
        <span className="confirmation-label">City</span>
        <span className="confirmation-value">{data.address.city}</span>
      </div>
      <div className="confirmation-row">
        <span className="confirmation-label">State</span>
        <span className="confirmation-value">{data.address.state}</span>
      </div>
      <div className="confirmation-row">
        <span className="confirmation-label">ZIP Code</span>
        <span className="confirmation-value">{data.address.zip}</span>
      </div>
    </div>
  </div>
);

// ── FormWizard (root) ──

const FormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<StepNumber>(1);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const handlePersonalChange = useCallback(
    (field: string, value: string) => {
      setFormData((prev) => ({
        ...prev,
        personal: { ...prev.personal, [field]: value },
      }));
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const handleAddressChange = useCallback(
    (field: string, value: string) => {
      setFormData((prev) => ({
        ...prev,
        address: { ...prev.address, [field]: value },
      }));
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const handleNext = useCallback(() => {
    const validationErrors = validateStep(currentStep, formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    setErrors({});
    setCurrentStep((prev) => (prev < 3 ? ((prev + 1) as StepNumber) : prev));
  }, [currentStep, formData]);

  const handleBack = useCallback(() => {
    setErrors({});
    setCurrentStep((prev) => (prev > 1 ? ((prev - 1) as StepNumber) : prev));
  }, []);

  const handleSubmit = useCallback(() => {
    console.log('Form submitted:', formData);
    setSubmitted(true);
  }, [formData]);

  if (submitted) {
    return (
      <>
        <style>{css}</style>
        <div className="wizard-container">
          <div className="form-card">
            <div className="success-message">
              <div className="success-icon">✅</div>
              <div className="success-text">Form Submitted Successfully!</div>
              <div className="success-sub">Thank you for your submission.</div>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{css}</style>
      <div className="wizard-container">
        <div className="wizard-title">Multi-Step Form Wizard</div>

        <div className="step-indicator">
          {[1, 2, 3].map((step, idx) => (
            <React.Fragment key={step}>
              {idx > 0 && (
                <div
                  className={`step-line ${currentStep > step - 1 ? 'active' : ''}`}
                />
              )}
              <div
                className={`step-circle ${
                  currentStep === step
                    ? 'active'
                    : currentStep > step
                    ? 'completed'
                    : ''
                }`}
              >
                {currentStep > step ? '✓' : step}
              </div>
            </React.Fragment>
          ))}
        </div>

        <div className="form-card">
          {currentStep === 1 && (
            <StepPersonal
              values={formData.personal}
              errors={errors}
              onChange={handlePersonalChange}
            />
          )}
          {currentStep === 2 && (
            <StepAddress
              values={formData.address}
              errors={errors}
              onChange={handleAddressChange}
            />
          )}
          {currentStep === 3 && <StepConfirmation data={formData} />}
        </div>

        <div className="button-row">
          {currentStep > 1 ? (
            <button className="btn btn-secondary" onClick={handleBack}>
              Back
            </button>
          ) : (
            <div />
          )}
          {currentStep < 3 ? (
            <button className="btn btn-primary" onClick={handleNext}>
              Next
            </button>
          ) : (
            <button className="btn btn-success" onClick={handleSubmit}>
              Submit
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default FormWizard;
