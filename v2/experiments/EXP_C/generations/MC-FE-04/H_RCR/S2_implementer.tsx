import React, { useState, useCallback } from 'react';
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
    address: { street: '', city: '', state: '', zip: '' },
  },
  errors: { step1: {}, step2: {} },
  currentStep: 1,
  submitted: false,
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^\+?\d{10,15}$/;
const ZIP_REGEX = /^\d{5}(-\d{4})?$/;

function validateStep(step: StepId, data: FormData): ValidationErrors {
  const errors: ValidationErrors = {};

  if (step === 1) {
    if (!data.personal.name.trim()) {
      errors.name = 'Name is required';
    } else if (data.personal.name.length < 2) {
      errors.name = 'Name must be at least 2 characters';
    } else if (!/^[a-zA-Z\s\-]+$/.test(data.personal.name)) {
      errors.name = 'Name can only contain letters, spaces, and hyphens';
    }

    if (!data.personal.email.trim()) {
      errors.email = 'Email is required';
    } else if (!EMAIL_REGEX.test(data.personal.email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!data.personal.phone.trim()) {
      errors.phone = 'Phone is required';
    } else if (!PHONE_REGEX.test(data.personal.phone.replace(/\s/g, ''))) {
      errors.phone = 'Phone must be 10-15 digits';
    }
  }

  if (step === 2) {
    if (!data.address.street.trim()) {
      errors.street = 'Street is required';
    } else if (data.address.street.length < 5) {
      errors.street = 'Street must be at least 5 characters';
    }

    if (!data.address.city.trim()) {
      errors.city = 'City is required';
    } else if (data.address.city.length < 2) {
      errors.city = 'City must be at least 2 characters';
    }

    if (!data.address.state.trim()) {
      errors.state = 'State is required';
    } else if (!/^[A-Z]{2}$/.test(data.address.state)) {
      errors.state = 'State must be 2 uppercase letters';
    }

    if (!data.address.zip.trim()) {
      errors.zip = 'ZIP code is required';
    } else if (!ZIP_REGEX.test(data.address.zip)) {
      errors.zip = 'ZIP must be 5 digits or 5+4 format';
    }
  }

  return errors;
}

export default function FormWizard() {
  const [state, setState] = useState<FormState>(initialState);

  const updateField = useCallback((section: 'personal' | 'address', field: string, value: string) => {
    setState(prev => ({
      ...prev,
      data: {
        ...prev.data,
        [section]: {
          ...prev.data[section],
          [field]: value,
        },
      },
    }));
  }, []);

  const clearError = useCallback((step: 'step1' | 'step2', field: string) => {
    setState(prev => ({
      ...prev,
      errors: {
        ...prev.errors,
        [step]: {
          ...prev.errors[step],
          [field]: undefined,
        },
      },
    }));
  }, []);

  const goNext = useCallback(() => {
    const errors = validateStep(state.currentStep, state.data);
    const stepKey = state.currentStep === 1 ? 'step1' : 'step2';

    if (Object.keys(errors).length > 0) {
      setState(prev => ({
        ...prev,
        errors: {
          ...prev.errors,
          [stepKey]: errors,
        },
      }));
      return;
    }

    setState(prev => ({
      ...prev,
      errors: {
        ...prev.errors,
        [stepKey]: {},
      },
      currentStep: (prev.currentStep + 1) as StepId,
    }));
  }, [state.currentStep, state.data]);

  const goBack = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentStep: (prev.currentStep - 1) as StepId,
    }));
  }, []);

  const handleSubmit = useCallback(() => {
    console.log('Submitted:', state.data);
    setState(prev => ({ ...prev, submitted: true }));
  }, [state.data]);

  const renderProgress = () => (
    <div className="progress-bar">
      <div className={`step ${state.currentStep >= 1 ? 'active' : ''} ${state.currentStep > 1 ? 'completed' : ''}`}>
        <div className="step-number">{state.currentStep > 1 ? '✓' : '1'}</div>
        <div className="step-label">Personal</div>
      </div>
      <div className={`step-connector ${state.currentStep >= 2 ? 'active' : ''}`} />
      <div className={`step ${state.currentStep >= 2 ? 'active' : ''} ${state.currentStep > 2 ? 'completed' : ''}`}>
        <div className="step-number">{state.currentStep > 2 ? '✓' : '2'}</div>
        <div className="step-label">Address</div>
      </div>
      <div className={`step-connector ${state.currentStep >= 3 ? 'active' : ''}`} />
      <div className={`step ${state.currentStep >= 3 ? 'active' : ''}`}>
        <div className="step-number">3</div>
        <div className="step-label">Confirm</div>
      </div>
    </div>
  );

  const renderStep1 = () => (
    <div className="form-step">
      <h2>Personal Information</h2>
      <div className="form-field">
        <label htmlFor="name">Full Name</label>
        <input
          type="text"
          id="name"
          value={state.data.personal.name}
          onChange={(e) => {
            updateField('personal', 'name', e.target.value);
            clearError('step1', 'name');
          }}
          className={state.errors.step1.name ? 'error' : ''}
        />
        {state.errors.step1.name && <span className="error-message">{state.errors.step1.name}</span>}
      </div>
      <div className="form-field">
        <label htmlFor="email">Email</label>
        <input
          type="email"
          id="email"
          value={state.data.personal.email}
          onChange={(e) => {
            updateField('personal', 'email', e.target.value);
            clearError('step1', 'email');
          }}
          className={state.errors.step1.email ? 'error' : ''}
        />
        {state.errors.step1.email && <span className="error-message">{state.errors.step1.email}</span>}
      </div>
      <div className="form-field">
        <label htmlFor="phone">Phone</label>
        <input
          type="tel"
          id="phone"
          value={state.data.personal.phone}
          onChange={(e) => {
            updateField('personal', 'phone', e.target.value);
            clearError('step1', 'phone');
          }}
          className={state.errors.step1.phone ? 'error' : ''}
        />
        {state.errors.step1.phone && <span className="error-message">{state.errors.step1.phone}</span>}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="form-step">
      <h2>Address Information</h2>
      <div className="form-field">
        <label htmlFor="street">Street Address</label>
        <input
          type="text"
          id="street"
          value={state.data.address.street}
          onChange={(e) => {
            updateField('address', 'street', e.target.value);
            clearError('step2', 'street');
          }}
          className={state.errors.step2.street ? 'error' : ''}
        />
        {state.errors.step2.street && <span className="error-message">{state.errors.step2.street}</span>}
      </div>
      <div className="form-field">
        <label htmlFor="city">City</label>
        <input
          type="text"
          id="city"
          value={state.data.address.city}
          onChange={(e) => {
            updateField('address', 'city', e.target.value);
            clearError('step2', 'city');
          }}
          className={state.errors.step2.city ? 'error' : ''}
        />
        {state.errors.step2.city && <span className="error-message">{state.errors.step2.city}</span>}
      </div>
      <div className="form-row">
        <div className="form-field">
          <label htmlFor="state">State (2 letters)</label>
          <input
            type="text"
            id="state"
            maxLength={2}
            value={state.data.address.state}
            onChange={(e) => {
              updateField('address', 'state', e.target.value.toUpperCase());
              clearError('step2', 'state');
            }}
            className={state.errors.step2.state ? 'error' : ''}
          />
          {state.errors.step2.state && <span className="error-message">{state.errors.step2.state}</span>}
        </div>
        <div className="form-field">
          <label htmlFor="zip">ZIP Code</label>
          <input
            type="text"
            id="zip"
            value={state.data.address.zip}
            onChange={(e) => {
              updateField('address', 'zip', e.target.value);
              clearError('step2', 'zip');
            }}
            className={state.errors.step2.zip ? 'error' : ''}
          />
          {state.errors.step2.zip && <span className="error-message">{state.errors.step2.zip}</span>}
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="form-step">
      <h2>Confirm Your Information</h2>
      <div className="confirmation-section">
        <h3>Personal Information</h3>
        <div className="confirmation-row">
          <span className="label">Name:</span>
          <span className="value">{state.data.personal.name}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">Email:</span>
          <span className="value">{state.data.personal.email}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">Phone:</span>
          <span className="value">{state.data.personal.phone}</span>
        </div>
      </div>
      <div className="confirmation-section">
        <h3>Address</h3>
        <div className="confirmation-row">
          <span className="label">Street:</span>
          <span className="value">{state.data.address.street}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">City:</span>
          <span className="value">{state.data.address.city}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">State:</span>
          <span className="value">{state.data.address.state}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">ZIP:</span>
          <span className="value">{state.data.address.zip}</span>
        </div>
      </div>
    </div>
  );

  if (state.submitted) {
    return (
      <div className="form-wizard">
        <div className="success-message">
          <h2>✓ Success!</h2>
          <p>Your information has been submitted successfully.</p>
          <button onClick={() => setState(initialState)}>Start Over</button>
        </div>
      </div>
    );
  }

  return (
    <div className="form-wizard">
      {renderProgress()}
      <div className="form-content">
        {state.currentStep === 1 && renderStep1()}
        {state.currentStep === 2 && renderStep2()}
        {state.currentStep === 3 && renderStep3()}
      </div>
      <div className="form-actions">
        {state.currentStep > 1 && (
          <button className="btn-secondary" onClick={goBack}>
            Back
          </button>
        )}
        {state.currentStep < 3 ? (
          <button className="btn-primary" onClick={goNext}>
            Next
          </button>
        ) : (
          <button className="btn-primary" onClick={handleSubmit}>
            Submit
          </button>
        )}
      </div>
    </div>
  );
}
