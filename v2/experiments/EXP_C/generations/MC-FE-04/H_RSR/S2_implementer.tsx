import React, { useState, useEffect } from 'react';
import './FormWizard.css';

type StepId = 1 | 2 | 3;

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

type ValidationErrors = Record<string, string>;

interface FormState {
  data: FormData;
  errors: {
    step1: ValidationErrors;
    step2: ValidationErrors;
  };
  currentStep: StepId;
  submitted: boolean;
}

const initialState: FormState = {
  data: {
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' }
  },
  errors: { step1: {}, step2: {} },
  currentStep: 1,
  submitted: false
};

const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const validatePhone = (phone: string): boolean => {
  const phoneRegex = /^\+?[0-9]{10,15}$/;
  return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
};

const validateName = (name: string): boolean => {
  const nameRegex = /^[A-Za-z\s\-]{2,}$/;
  return nameRegex.test(name);
};

const validateStreet = (street: string): boolean => {
  return street.trim().length >= 5;
};

const validateCity = (city: string): boolean => {
  return city.trim().length >= 2;
};

const validateState = (state: string): boolean => {
  const stateRegex = /^[A-Z]{2}$/;
  return stateRegex.test(state);
};

const validateZip = (zip: string): boolean => {
  const zipRegex = /^\d{5}(-\d{4})?$/;
  return zipRegex.test(zip);
};

const validateStep = (step: StepId, data: FormData): ValidationErrors => {
  const errors: ValidationErrors = {};

  if (step === 1) {
    if (!data.personal.name.trim()) {
      errors.name = 'Name is required';
    } else if (!validateName(data.personal.name)) {
      errors.name = 'Name must be at least 2 characters and contain only letters, spaces, and hyphens';
    }

    if (!data.personal.email.trim()) {
      errors.email = 'Email is required';
    } else if (!validateEmail(data.personal.email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!data.personal.phone.trim()) {
      errors.phone = 'Phone number is required';
    } else if (!validatePhone(data.personal.phone)) {
      errors.phone = 'Please enter a valid 10-15 digit phone number';
    }
  } else if (step === 2) {
    if (!data.address.street.trim()) {
      errors.street = 'Street address is required';
    } else if (!validateStreet(data.address.street)) {
      errors.street = 'Street address must be at least 5 characters';
    }

    if (!data.address.city.trim()) {
      errors.city = 'City is required';
    } else if (!validateCity(data.address.city)) {
      errors.city = 'City must be at least 2 characters';
    }

    if (!data.address.state.trim()) {
      errors.state = 'State is required';
    } else if (!validateState(data.address.state)) {
      errors.state = 'State must be a 2-letter abbreviation (e.g., CA, NY)';
    }

    if (!data.address.zip.trim()) {
      errors.zip = 'ZIP code is required';
    } else if (!validateZip(data.address.zip)) {
      errors.zip = 'Please enter a valid 5-digit or 5+4 ZIP code';
    }
  }

  return errors;
};

const StepIndicator: React.FC<{
  currentStep: StepId;
  visitedSteps: Set<StepId>;
}> = ({ currentStep, visitedSteps }) => {
  const steps = [
    { id: 1 as StepId, label: 'Personal Info' },
    { id: 2 as StepId, label: 'Address' },
    { id: 3 as StepId, label: 'Confirmation' }
  ];

  return (
    <div className="step-indicator">
      {steps.map((step, index) => {
        const isActive = step.id === currentStep;
        const isCompleted = visitedSteps.has(step.id) || step.id < currentStep;
        const isClickable = visitedSteps.has(step.id) || step.id < currentStep;

        return (
          <div key={step.id} className="step-item">
            <div className="step-connector">
              {index > 0 && (
                <div className={`connector-line ${isCompleted ? 'completed' : ''}`} />
              )}
            </div>
            <div
              className={`step-circle ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              title={step.label}
            >
              {isCompleted ? '✓' : step.id}
            </div>
            <div className="step-label">{step.label}</div>
          </div>
        );
      })}
    </div>
  );
};

const Step1: React.FC<{
  data: PersonalInfo;
  errors: ValidationErrors;
  onChange: (field: keyof PersonalInfo, value: string) => void;
}> = ({ data, errors, onChange }) => {
  return (
    <div className="step-content">
      <h2 className="step-title">Personal Information</h2>
      <p className="step-description">Please provide your personal details.</p>
      
      <div className="form-group">
        <label htmlFor="name" className="form-label">
          Full Name *
        </label>
        <input
          id="name"
          type="text"
          className={`form-input ${errors.name ? 'error' : ''}`}
          value={data.name}
          onChange={(e) => onChange('name', e.target.value)}
          placeholder="Enter your full name"
        />
        {errors.name && <div className="error-message">{errors.name}</div>}
      </div>

      <div className="form-group">
        <label htmlFor="email" className="form-label">
          Email Address *
        </label>
        <input
          id="email"
          type="email"
          className={`form-input ${errors.email ? 'error' : ''}`}
          value={data.email}
          onChange={(e) => onChange('email', e.target.value)}
          placeholder="Enter your email address"
        />
        {errors.email && <div className="error-message">{errors.email}</div>}
      </div>

      <div className="form-group">
        <label htmlFor="phone" className="form-label">
          Phone Number *
        </label>
        <input
          id="phone"
          type="tel"
          className={`form-input ${errors.phone ? 'error' : ''}`}
          value={data.phone}
          onChange={(e) => onChange('phone', e.target.value)}
          placeholder="Enter your phone number"
        />
        {errors.phone && <div className="error-message">{errors.phone}</div>}
      </div>
    </div>
  );
};

const Step2: React.FC<{
  data: AddressInfo;
  errors: ValidationErrors;
  onChange: (field: keyof AddressInfo, value: string) => void;
}> = ({ data, errors, onChange }) => {
  const usStates = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
  ];

  return (
    <div className="step-content">
      <h2 className="step-title">Address Information</h2>
      <p className="step-description">Please provide your shipping address.</p>
      
      <div className="form-group">
        <label htmlFor="street" className="form-label">
          Street Address *
        </label>
        <input
          id="street"
          type="text"
          className={`form-input ${errors.street ? 'error' : ''}`}
          value={data.street}
          onChange={(e) => onChange('street', e.target.value)}
          placeholder="Enter your street address"
        />
        {errors.street && <div className="error-message">{errors.street}</div>}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="city" className="form-label">
            City *
          </label>
          <input
            id="city"
            type="text"
            className={`form-input ${errors.city ? 'error' : ''}`}
            value={data.city}
            onChange={(e) => onChange('city', e.target.value)}
            placeholder="Enter city"
          />
          {errors.city && <div className="error-message">{errors.city}</div>}
        </div>

        <div className="form-group">
          <label htmlFor="state" className="form-label">
            State *
          </label>
          <select
            id="state"
            className={`form-input ${errors.state ? 'error' : ''}`}
            value={data.state}
            onChange={(e) => onChange('state', e.target.value)}
          >
            <option value="">Select State</option>
            {usStates.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </select>
          {errors.state && <div className="error-message">{errors.state}</div>}
        </div>

        <div className="form-group">
          <label htmlFor="zip" className="form-label">
            ZIP Code *
          </label>
          <input
            id="zip"
            type="text"
            className={`form-input ${errors.zip ? 'error' : ''}`}
            value={data.zip}
            onChange={(e) => onChange('zip', e.target.value)}
            placeholder="Enter ZIP code"
          />
          {errors.zip && <div className="error-message">{errors.zip}</div>}
        </div>
      </div>
    </div>
  );
};

const Step3: React.FC<{
  data: FormData;
  onSubmit: () => void;
}> = ({ data, onSubmit }) => {
  return (
    <div className="step-content">
      <h2 className="step-title">Confirmation</h2>
      <p className="step-description">Please review your information before submitting.</p>
      
      <div className="review-section">
        <h3 className="review-title">Personal Information</h3>
        <div className="review-grid">
          <div className="review-item">
            <span className="review-label">Name:</span>
            <span className="review-value">{data.personal.name}</span>
          </div>
          <div className="review-item">
            <span className="review-label">Email:</span>
            <span className="review-value">{data.personal.email}</span>
          </div>
          <div className="review-item">
            <span className="review-label">Phone:</span>
            <span className="review-value">{data.personal.phone}</span>
          </div>
        </div>
      </div>

      <div className="review-section">
        <h3 className="review-title">Address Information</h3>
        <div className="review-grid">
          <div className="review-item">
            <span className="review-label">Street:</span>
            <span className="review-value">{data.address.street}</span>
          </div>
          <div className="review-item">
            <span className="review-label">City:</span>
            <span className="review-value">{data.address.city}</span>
          </div>
          <div className="review-item">
            <span className="review-label">State:</span>
            <span className="review-value">{data.address.state}</span>
          </div>
          <div className="review-item">
            <span className="review-label">ZIP Code:</span>
            <span className="review-value">{data.address.zip}</span>
          </div>
        </div>
      </div>

      <div className="confirmation-note">
        <p>By submitting this form, you confirm that all the information provided is accurate.</p>
      </div>
    </div>
  );
};

const FormWizard: React.FC = () => {
  const [state, setState] = useState<FormState>(initialState);
  const [visitedSteps, setVisitedSteps] = useState<Set<StepId>>(new Set([1]));

  useEffect(() => {
    const newVisited = new Set(visitedSteps);
    newVisited.add(state.currentStep);
    setVisitedSteps(newVisited);
  }, [state.currentStep]);

  const handlePersonalChange = (field: keyof PersonalInfo, value: string) => {
    setState(prev => ({
      ...prev,
      data: {
        ...prev.data,
        personal: { ...prev.data.personal, [field]: value }
      }
    }));
  };

  const handleAddressChange = (field: keyof AddressInfo, value: string) => {
    setState(prev => ({
      ...prev,
      data: {
        ...prev.data,
        address: { ...prev.data.address, [field]: value }
      }
    }));
  };

  const goNext = () => {
    const errors = validateStep(state.currentStep, state.data);
    
    if (Object.keys(errors).length > 0) {
      setState(prev => ({
        ...prev,
        errors: {
          ...prev.errors,
          [`step${state.currentStep}`]: errors
        }
      }));
      return;
    }

    setState(prev => ({
      ...prev,
      errors: {
        ...prev.errors,
        [`step${state.currentStep}`]: {}
      },
      currentStep: Math.min(3, prev.currentStep + 1) as StepId
    }));
  };

  const goBack = () => {
    if (state.currentStep > 1) {
      setState(prev => ({
        ...prev,
        currentStep: Math.max(1, prev.currentStep - 1) as StepId
      }));
    }
  };

  const handleSubmit = () => {
    setState(prev => ({
      ...prev,
      submitted: true
    }));
    
    console.log('Form submitted:', state.data);
  };

  const renderStep = () => {
    switch (state.currentStep) {
      case 1:
        return (
          <Step1
            data={state.data.personal}
            errors={state.errors.step1}
            onChange={handlePersonalChange}
          />
        );
      case 2:
        return (
          <Step2
            data={state.data.address}
            errors={state.errors.step2}
            onChange={handleAddressChange}
          />
        );
      case 3:
        return (
          <Step3
            data={state.data}
            onSubmit={handleSubmit}
          />
        );
      default:
        return null;
    }
  };

  if (state.submitted) {
    return (
      <div className="form-wizard">
        <div className="success-container">
          <div className="success-icon">✓</div>
          <h2 className="success-title">Form Submitted Successfully!</h2>
          <p className="success-message">
            Thank you for submitting your information. We'll process your request shortly.
          </p>
          <button
            className="success-button"
            onClick={() => setState(initialState)}
          >
            Start New Form
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="form-wizard">
      <div className="wizard-header">
        <h1 className="wizard-title">Multi-Step Form Wizard</h1>
        <p className="wizard-description">Complete all steps to submit your information.</p>
      </div>

      <StepIndicator
        currentStep={state.currentStep}
        visitedSteps={visitedSteps}
      />

      <div className="wizard-body">
        {renderStep()}
      </div>

      <div className="wizard-footer">
        <div className="button-group">
          <button
            className="button secondary"
            onClick={goBack}
            disabled={state.currentStep === 1}
          >
            Back
          </button>
          
          {state.currentStep < 3 ? (
            <button
              className="button primary"
              onClick={goNext}
            >
              Next
            </button>
          ) : (
            <button
              className="button submit"
              onClick={handleSubmit}
            >
              Submit
            </button>
          )}
        </div>
        
        <div className="step-counter">
          Step {state.currentStep} of 3
        </div>
      </div>
    </div>
  );
};

export default FormWizard;