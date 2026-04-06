import React, { useState, useCallback, useEffect } from 'react';

// ===================== Interfaces =====================

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

interface WizardState {
  currentStep: number;
  formData: FormData;
  errors: FieldErrors;
  isSubmitted: boolean;
}

// ===================== Validation Functions =====================

function validatePersonalInfo(personalInfo: PersonalInfo): FieldErrors {
  const errors: FieldErrors = {};

  // Name validation
  if (!personalInfo.name.trim()) {
    errors.name = 'Name is required';
  } else if (personalInfo.name.trim().length < 2) {
    errors.name = 'Name must be at least 2 characters';
  } else if (!/^[a-zA-Z\s]+$/.test(personalInfo.name.trim())) {
    errors.name = 'Name can only contain letters and spaces';
  }

  // Email validation
  if (!personalInfo.email.trim()) {
    errors.email = 'Email is required';
  } else {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(personalInfo.email.trim())) {
      errors.email = 'Please enter a valid email address';
    }
  }

  // Phone validation
  if (!personalInfo.phone.trim()) {
    errors.phone = 'Phone number is required';
  } else {
    const digitsOnly = personalInfo.phone.replace(/[\s\-()]/g, '');
    if (!/^\d+$/.test(digitsOnly)) {
      errors.phone = 'Phone number can only contain digits';
    } else if (digitsOnly.length < 10 || digitsOnly.length > 15) {
      errors.phone = 'Phone number must be 10-15 digits';
    }
  }

  return errors;
}

function validateAddress(address: Address): FieldErrors {
  const errors: FieldErrors = {};

  // Street validation
  if (!address.street.trim()) {
    errors.street = 'Street address is required';
  } else if (address.street.trim().length < 5) {
    errors.street = 'Street address must be at least 5 characters';
  }

  // City validation
  if (!address.city.trim()) {
    errors.city = 'City is required';
  } else if (address.city.trim().length < 2) {
    errors.city = 'City must be at least 2 characters';
  } else if (!/^[a-zA-Z\s]+$/.test(address.city.trim())) {
    errors.city = 'City can only contain letters and spaces';
  }

  // State validation
  if (!address.state.trim()) {
    errors.state = 'State is required';
  } else if (address.state.trim().length < 2) {
    errors.state = 'State must be at least 2 characters';
  }

  // ZIP validation
  if (!address.zip.trim()) {
    errors.zip = 'ZIP code is required';
  } else {
    const zipRegex = /^\d{5}(-\d{4})?$/;
    if (!zipRegex.test(address.zip.trim())) {
      errors.zip = 'Please enter a valid ZIP code (5 digits or 5+4 format)';
    }
  }

  return errors;
}

// ===================== Components =====================

const StepIndicator: React.FC<{
  currentStep: number;
  steps: Array<{ title: string }>;
}> = ({ currentStep, steps }) => {
  return (
    <div className="step-indicator">
      {steps.map((step, index) => (
        <div
          key={index}
          className={`step ${index === currentStep ? 'active' : ''} ${
            index < currentStep ? 'completed' : ''
          }`}
        >
          <div className="step-number">
            {index < currentStep ? '✓' : index + 1}
          </div>
          <div className="step-title">{step.title}</div>
          {index < steps.length - 1 && <div className="step-connector" />}
        </div>
      ))}
    </div>
  );
};

const FormField: React.FC<{
  label: string;
  name: string;
  type: string;
  value: string;
  error?: string;
  onChange: (name: string, value: string) => void;
  placeholder?: string;
}> = ({ label, name, type, value, error, onChange, placeholder }) => {
  return (
    <div className="form-field">
      <label htmlFor={name} className="field-label">
        {label}
      </label>
      <input
        id={name}
        type={type}
        name={name}
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={placeholder}
        className={`field-input ${error ? 'error' : ''}`}
      />
      {error && <div className="field-error">{error}</div>}
    </div>
  );
};

const PersonalInfoStep: React.FC<{
  data: PersonalInfo;
  errors: FieldErrors;
  onChange: (data: PersonalInfo) => void;
}> = ({ data, errors, onChange }) => {
  const handleChange = (name: string, value: string) => {
    onChange({ ...data, [name]: value });
  };

  return (
    <div className="step-content">
      <h2 className="step-title">Personal Information</h2>
      <p className="step-description">
        Please provide your personal details. All fields are required.
      </p>
      <div className="form-fields">
        <FormField
          label="Full Name"
          name="name"
          type="text"
          value={data.name}
          error={errors.name}
          onChange={handleChange}
          placeholder="John Doe"
        />
        <FormField
          label="Email Address"
          name="email"
          type="email"
          value={data.email}
          error={errors.email}
          onChange={handleChange}
          placeholder="john@example.com"
        />
        <FormField
          label="Phone Number"
          name="phone"
          type="tel"
          value={data.phone}
          error={errors.phone}
          onChange={handleChange}
          placeholder="123-456-7890"
        />
      </div>
    </div>
  );
};

const AddressStep: React.FC<{
  data: Address;
  errors: FieldErrors;
  onChange: (data: Address) => void;
}> = ({ data, errors, onChange }) => {
  const handleChange = (name: string, value: string) => {
    onChange({ ...data, [name]: value });
  };

  return (
    <div className="step-content">
      <h2 className="step-title">Address Details</h2>
      <p className="step-description">
        Please provide your shipping address. All fields are required.
      </p>
      <div className="form-fields">
        <FormField
          label="Street Address"
          name="street"
          type="text"
          value={data.street}
          error={errors.street}
          onChange={handleChange}
          placeholder="123 Main St"
        />
        <FormField
          label="City"
          name="city"
          type="text"
          value={data.city}
          error={errors.city}
          onChange={handleChange}
          placeholder="New York"
        />
        <div className="form-row">
          <FormField
            label="State"
            name="state"
            type="text"
            value={data.state}
            error={errors.state}
            onChange={handleChange}
            placeholder="NY"
          />
          <FormField
            label="ZIP Code"
            name="zip"
            type="text"
            value={data.zip}
            error={errors.zip}
            onChange={handleChange}
            placeholder="10001"
          />
        </div>
      </div>
    </div>
  );
};

const ConfirmationStep: React.FC<{
  data: FormData;
  onSubmit: () => void;
}> = ({ data, onSubmit }) => {
  return (
    <div className="step-content">
      <h2 className="step-title">Confirmation</h2>
      <p className="step-description">
        Please review your information before submitting.
      </p>
      <div className="confirmation-card">
        <div className="confirmation-section">
          <h3 className="section-title">Personal Information</h3>
          <div className="confirmation-row">
            <span className="row-label">Name:</span>
            <span className="row-value">{data.personalInfo.name}</span>
          </div>
          <div className="confirmation-row">
            <span className="row-label">Email:</span>
            <span className="row-value">{data.personalInfo.email}</span>
          </div>
          <div className="confirmation-row">
            <span className="row-label">Phone:</span>
            <span className="row-value">{data.personalInfo.phone}</span>
          </div>
        </div>
        <div className="confirmation-section">
          <h3 className="section-title">Address Details</h3>
          <div className="confirmation-row">
            <span className="row-label">Street:</span>
            <span className="row-value">{data.address.street}</span>
          </div>
          <div className="confirmation-row">
            <span className="row-label">City:</span>
            <span className="row-value">{data.address.city}</span>
          </div>
          <div className="confirmation-row">
            <span className="row-label">State:</span>
            <span className="row-value">{data.address.state}</span>
          </div>
          <div className="confirmation-row">
            <span className="row-label">ZIP Code:</span>
            <span className="row-value">{data.address.zip}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const NavigationButtons: React.FC<{
  currentStep: number;
  totalSteps: number;
  isNextDisabled?: boolean;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
}> = ({ currentStep, totalSteps, isNextDisabled = false, onBack, onNext, onSubmit }) => {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;

  return (
    <div className="navigation-buttons">
      <button
        type="button"
        className="nav-button back-button"
        onClick={onBack}
        disabled={isFirstStep}
      >
        Back
      </button>
      {!isLastStep ? (
        <button
          type="button"
          className="nav-button next-button"
          onClick={onNext}
          disabled={isNextDisabled}
        >
          Next
        </button>
      ) : (
        <button
          type="button"
          className="nav-button submit-button"
          onClick={onSubmit}
        >
          Submit
        </button>
      )}
    </div>
  );
};

const SuccessScreen: React.FC<{
  data: FormData;
  onReset: () => void;
}> = ({ data, onReset }) => {
  return (
    <div className="success-screen">
      <div className="success-icon">✓</div>
      <h2 className="success-title">Form Submitted Successfully!</h2>
      <p className="success-message">
        Thank you for submitting your information. We have received the following details:
      </p>
      <div className="success-summary">
        <p>
          <strong>Name:</strong> {data.personalInfo.name}
        </p>
        <p>
          <strong>Email:</strong> {data.personalInfo.email}
        </p>
        <p>
          <strong>Address:</strong> {data.address.street}, {data.address.city},{' '}
          {data.address.state} {data.address.zip}
        </p>
      </div>
      <button className="reset-button" onClick={onReset}>
        Start New Form
      </button>
    </div>
  );
};

// ===================== Main Component =====================

const FormWizard: React.FC = () => {
  const [state, setState] = useState<WizardState>({
    currentStep: 0,
    formData: {
      personalInfo: { name: '', email: '', phone: '' },
      address: { street: '', city: '', state: '', zip: '' },
    },
    errors: {},
    isSubmitted: false,
  });

  const steps = [
    { title: 'Personal Info' },
    { title: 'Address' },
    { title: 'Confirmation' },
  ];

  const handleFieldChange = useCallback((section: keyof FormData) => {
    return (data: PersonalInfo | Address) => {
      setState(prev => ({
        ...prev,
        formData: {
          ...prev.formData,
          [section]: data,
        },
        errors: {}, // Clear errors when user starts typing
      }));
    };
  }, []);

  const handleNext = useCallback(() => {
    let validationErrors: FieldErrors = {};

    if (state.currentStep === 0) {
      validationErrors = validatePersonalInfo(state.formData.personalInfo);
    } else if (state.currentStep === 1) {
      validationErrors = validateAddress(state.formData.address);
    }

    if (Object.keys(validationErrors).length > 0) {
      setState(prev => ({ ...prev, errors: validationErrors }));
      return;
    }

    setState(prev => ({
      ...prev,
      currentStep: prev.currentStep + 1,
      errors: {},
    }));
  }, [state.currentStep, state.formData]);

  const handleBack = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentStep: Math.max(0, prev.currentStep - 1),
      errors: {},
    }));
  }, []);

  const handleSubmit = useCallback(() => {
    // All validation should have passed by this point
    console.log('Form submitted with data:', state.formData);
    setState(prev => ({ ...prev, isSubmitted: true }));
  }, [state.formData]);

  const handleReset = useCallback(() => {
    setState({
      currentStep: 0,
      formData: {
        personalInfo: { name: '', email: '', phone: '' },
        address: { street: '', city: '', state: '', zip: '' },
      },
      errors: {},
      isSubmitted: false,
    });
  }, []);

  if (state.isSubmitted) {
    return <SuccessScreen data={state.formData} onReset={handleReset} />;
  }

  return (
    <div className="form-wizard">
      <style>{`
        .form-wizard {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background-color: #f5f5f5;
          padding: 20px;
        }

        .wizard-container {
          width: 100%;
          max-width: 600px;
          background-color: white;
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }

        .step-indicator {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 32px 40px 20px;
          background-color: #f8f9fa;
          border-bottom: 1px solid #e9ecef;
        }

        .step {
          display: flex;
          flex-direction: column;
          align-items: center;
          position: relative;
          flex: 1;
        }

        .step-number {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 16px;
          margin-bottom: 8px;
          background-color: #e9ecef;
          color: #6c757d;
          border: 2px solid transparent;
          transition: all 0.3s ease;
        }

        .step.active .step-number {
          background-color: #007bff;
          color: white;
          border-color: #0056b3;
        }

        .step.completed .step-number {
          background-color: #28a745;
          color: white;
        }

        .step-title {
          font-size: 14px;
          font-weight: 500;
          color: #6c757d;
          transition: color 0.3s ease;
        }

        .step.active .step-title {
          color: #007bff;
          font-weight: 600;
        }

        .step.completed .step-title {
          color: #28a745;
        }

        .step-connector {
          position: absolute;
          top: 18px;
          right: -50%;
          width: 100%;
          height: 2px;
          background-color: #e9ecef;
          z-index: -1;
        }

        .step-content {
          padding: 32px 40px;
        }

        .step-title {
          margin: 0 0 8px 0;
          color: #333;
          font-size: 24px;
          font-weight: 600;
        }

        .step-description {
          margin: 0 0 24px 0;
          color: #666;
          font-size: 16px;
          line-height: 1.5;
        }

        .form-fields {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .form-row {
          display: flex;
          gap: 20px;
        }

        .form-row .form-field {
          flex: 1;
        }

        .form-field {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .field-label {
          font-size: 14px;
          font-weight: 500;
          color: #333;
        }

        .field-input {
          padding: 12px 16px;
          border: 1px solid #ddd;
          border-radius: 8px;
          font-size: 16px;
          transition: all 0.2s ease;
          background-color: #fafafa;
        }

        .field-input:focus {
          outline: none;
          border-color: #007bff;
          background-color: white;
          box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
        }

        .field-input.error {
          border-color: #dc3545;
          background-color: #fff8f8;
        }

        .field-input.error:focus {
          box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
        }

        .field-error {
          color: #dc3545;
          font-size: 13px;
          margin-top: 4px;
        }

        .confirmation-card {
          background-color: #f8f9fa;
          border-radius: 12px;
          padding: 24px;
          border: 1px solid #e9ecef;
        }

        .confirmation-section {
          margin-bottom: 24px;
        }

        .confirmation-section:last-child {
          margin-bottom: 0;
        }

        .section-title {
          margin: 0 0 16px 0;
          color: #333;
          font-size: 18px;
          font-weight: 600;
          padding-bottom: 8px;
          border-bottom: 2px solid #e9ecef;
        }

        .confirmation-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid #f1f3f5;
        }

        .confirmation-row:last-child {
          border-bottom: none;
        }

        .row-label {
          font-weight: 500;
          color: #666;
          font-size: 14px;
        }

        .row-value {
          color: #333;
          font-size: 16px;
          font-weight: 500;
        }

        .navigation-buttons {
          display: flex;
          justify-content: space-between;
          padding: 24px 40px;
          background-color: #f8f9fa;
          border-top: 1px solid #e9ecef;
        }

        .nav-button {
          padding: 12px 32px;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .back-button {
          background-color: transparent;
          color: #6c757d;
          border: 1px solid #ddd;
        }

        .back-button:hover:not(:disabled) {
          background-color: #f8f9fa;
          border-color: #bdbdbd;
        }

        .back-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .next-button,
        .submit-button {
          background-color: #007bff;
          color: white;
        }

        .next-button:hover:not(:disabled),
        .submit-button:hover {
          background-color: #0056b3;
        }

        .next-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .success-screen {
          text-align: center;
          padding: 48px 32px;
          background-color: white;
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          max-width: 500px;
          width: 100%;
        }

        .success-icon {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          background-color: #28a745;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 40px;
          margin: 0 auto 24px;
        }

        .success-title {
          margin: 0 0 16px 0;
          color: #333;
          font-size: 28px;
          font-weight: 600;
        }

        .success-message {
          margin: 0 0 24px 0;
          color: #666;
          font-size: 16px;
          line-height: 1.5;
        }

        .success-summary {
          background-color: #f8f9fa;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 32px;
          text-align: left;
        }

        .success-summary p {
          margin: 8px 0;
          color: #333;
        }

        .reset-button {
          padding: 12px 32px;
          background-color: #007bff;
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s ease;
        }

        .reset-button:hover {
          background-color: #0056b3;
        }
      `}</style>

      <div className="wizard-container">
        <StepIndicator currentStep={state.currentStep} steps={steps} />

        {state.currentStep === 0 && (
          <PersonalInfoStep
            data={state.formData.personalInfo}
            errors={state.errors}
            onChange={handleFieldChange('personalInfo')}
          />
        )}

        {state.currentStep === 1 && (
          <AddressStep
            data={state.formData.address}
            errors={state.errors}
            onChange={handleFieldChange('address')}
          />
        )}

        {state.currentStep === 2 && (
          <ConfirmationStep
            data={state.formData}
            onSubmit={handleSubmit}
          />
        )}

        <NavigationButtons
          currentStep={state.currentStep}
          totalSteps={steps.length}
          isNextDisabled={false}
          onBack={handleBack}
          onNext={handleNext}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
};

export default FormWizard;