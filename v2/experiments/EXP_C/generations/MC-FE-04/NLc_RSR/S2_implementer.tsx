import React, { useState } from 'react';
import './styles.css';

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

const validatePersonalInfo = (data: PersonalInfo): FormErrors => {
  const errors: FormErrors = {};
  
  if (!data.name.trim() || data.name.length < 2) {
    errors.name = 'Name is required and must be at least 2 characters';
  }
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!data.email.trim() || !emailRegex.test(data.email)) {
    errors.email = 'Valid email is required';
  }
  
  const phoneRegex = /^\+?[\d\s\-()]{7,15}$/;
  if (!data.phone.trim() || !phoneRegex.test(data.phone.replace(/\s/g, ''))) {
    errors.phone = 'Valid phone number is required';
  }
  
  return errors;
};

const validateAddressInfo = (data: AddressInfo): FormErrors => {
  const errors: FormErrors = {};
  
  if (!data.street.trim()) {
    errors.street = 'Street address is required';
  }
  
  if (!data.city.trim() || data.city.length < 2) {
    errors.city = 'City is required';
  }
  
  if (!data.state.trim()) {
    errors.state = 'State is required';
  }
  
  const zipRegex = /^\d{5}(-\d{4})?$/;
  if (!data.zip.trim() || !zipRegex.test(data.zip)) {
    errors.zip = 'Valid ZIP code is required';
  }
  
  return errors;
};

const FieldError: React.FC<{ error?: string }> = ({ error }) => {
  if (!error) return null;
  return <div className="field-error">{error}</div>;
};

const StepIndicator: React.FC<{ currentStep: number }> = ({ currentStep }) => {
  const steps = [
    { number: 1, label: 'Personal Info' },
    { number: 2, label: 'Address' },
    { number: 3, label: 'Confirmation' },
  ];
  
  return (
    <div className="step-indicator">
      {steps.map((step, index) => (
        <React.Fragment key={step.number}>
          <div className={`step-circle ${currentStep >= step.number ? 'active' : ''}`}>
            {step.number}
          </div>
          {index < steps.length - 1 && (
            <div className={`step-line ${currentStep > step.number ? 'active' : ''}`} />
          )}
        </React.Fragment>
      ))}
      <div className="step-labels">
        {steps.map(step => (
          <div
            key={step.number}
            className={`step-label ${currentStep >= step.number ? 'active' : ''}`}
          >
            {step.label}
          </div>
        ))}
      </div>
    </div>
  );
};

const StepPersonal: React.FC<{
  data: PersonalInfo;
  errors: FormErrors;
  onChange: (data: PersonalInfo) => void;
}> = ({ data, errors, onChange }) => {
  const handleChange = (field: keyof PersonalInfo, value: string) => {
    onChange({ ...data, [field]: value });
  };
  
  return (
    <div className="step-content">
      <h2>Personal Information</h2>
      <div className="form-group">
        <label htmlFor="name">Full Name</label>
        <input
          id="name"
          type="text"
          value={data.name}
          onChange={(e) => handleChange('name', e.target.value)}
          className={errors.name ? 'error' : ''}
          placeholder="Enter your full name"
        />
        <FieldError error={errors.name} />
      </div>
      
      <div className="form-group">
        <label htmlFor="email">Email Address</label>
        <input
          id="email"
          type="email"
          value={data.email}
          onChange={(e) => handleChange('email', e.target.value)}
          className={errors.email ? 'error' : ''}
          placeholder="Enter your email"
        />
        <FieldError error={errors.email} />
      </div>
      
      <div className="form-group">
        <label htmlFor="phone">Phone Number</label>
        <input
          id="phone"
          type="tel"
          value={data.phone}
          onChange={(e) => handleChange('phone', e.target.value)}
          className={errors.phone ? 'error' : ''}
          placeholder="Enter your phone number"
        />
        <FieldError error={errors.phone} />
      </div>
    </div>
  );
};

const StepAddress: React.FC<{
  data: AddressInfo;
  errors: FormErrors;
  onChange: (data: AddressInfo) => void;
}> = ({ data, errors, onChange }) => {
  const handleChange = (field: keyof AddressInfo, value: string) => {
    onChange({ ...data, [field]: value });
  };
  
  const states = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming',
  ];
  
  return (
    <div className="step-content">
      <h2>Address Information</h2>
      <div className="form-group">
        <label htmlFor="street">Street Address</label>
        <input
          id="street"
          type="text"
          value={data.street}
          onChange={(e) => handleChange('street', e.target.value)}
          className={errors.street ? 'error' : ''}
          placeholder="Enter your street address"
        />
        <FieldError error={errors.street} />
      </div>
      
      <div className="form-group">
        <label htmlFor="city">City</label>
        <input
          id="city"
          type="text"
          value={data.city}
          onChange={(e) => handleChange('city', e.target.value)}
          className={errors.city ? 'error' : ''}
          placeholder="Enter your city"
        />
        <FieldError error={errors.city} />
      </div>
      
      <div className="form-group">
        <label htmlFor="state">State</label>
        <select
          id="state"
          value={data.state}
          onChange={(e) => handleChange('state', e.target.value)}
          className={errors.state ? 'error' : ''}
        >
          <option value="">Select a state</option>
          {states.map(state => (
            <option key={state} value={state}>{state}</option>
          ))}
        </select>
        <FieldError error={errors.state} />
      </div>
      
      <div className="form-group">
        <label htmlFor="zip">ZIP Code</label>
        <input
          id="zip"
          type="text"
          value={data.zip}
          onChange={(e) => handleChange('zip', e.target.value)}
          className={errors.zip ? 'error' : ''}
          placeholder="Enter your ZIP code"
        />
        <FieldError error={errors.zip} />
      </div>
    </div>
  );
};

const StepConfirmation: React.FC<{ data: FormData }> = ({ data }) => {
  return (
    <div className="step-content">
      <h2>Confirmation</h2>
      <div className="confirmation-section">
        <h3>Personal Information</h3>
        <div className="confirmation-row">
          <span className="label">Name:</span>
          <span className="value">{data.personal.name}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">Email:</span>
          <span className="value">{data.personal.email}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">Phone:</span>
          <span className="value">{data.personal.phone}</span>
        </div>
      </div>
      
      <div className="confirmation-section">
        <h3>Address Information</h3>
        <div className="confirmation-row">
          <span className="label">Street:</span>
          <span className="value">{data.address.street}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">City:</span>
          <span className="value">{data.address.city}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">State:</span>
          <span className="value">{data.address.state}</span>
        </div>
        <div className="confirmation-row">
          <span className="label">ZIP Code:</span>
          <span className="value">{data.address.zip}</span>
        </div>
      </div>
      
      <div className="confirmation-notice">
        <p>Please review all information above. If everything looks correct, click "Submit" to complete the form.</p>
      </div>
    </div>
  );
};

const FormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  
  const handleNext = () => {
    let validationErrors: FormErrors = {};
    
    if (currentStep === 1) {
      validationErrors = validatePersonalInfo(formData.personal);
    } else if (currentStep === 2) {
      validationErrors = validateAddressInfo(formData.address);
    }
    
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      // Scroll to first error
      const firstErrorField = Object.keys(validationErrors)[0];
      const element = document.getElementById(firstErrorField);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }
    
    setErrors({});
    if (currentStep < 3) {
      setCurrentStep((currentStep + 1) as 1 | 2 | 3);
    }
  };
  
  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as 1 | 2 | 3);
      setErrors({});
    }
  };
  
  const handleSubmit = () => {
    setSubmitted(true);
    // In a real application, you would send the data to a server here
    console.log('Form submitted with data:', formData);
  };
  
  const handlePersonalChange = (personal: PersonalInfo) => {
    setFormData({ ...formData, personal });
    // Clear errors for changed field
    if (errors.name || errors.email || errors.phone) {
      setErrors({});
    }
  };
  
  const handleAddressChange = (address: AddressInfo) => {
    setFormData({ ...formData, address });
    // Clear errors for changed field
    if (errors.street || errors.city || errors.state || errors.zip) {
      setErrors({});
    }
  };
  
  if (submitted) {
    return (
      <div className="form-wizard submitted">
        <div className="success-message">
          <div className="success-icon">✓</div>
          <h2>Form Submitted Successfully!</h2>
          <p>Thank you for completing the form. Your information has been received.</p>
          <button
            className="button primary"
            onClick={() => {
              setSubmitted(false);
              setCurrentStep(1);
              setFormData({
                personal: { name: '', email: '', phone: '' },
                address: { street: '', city: '', state: '', zip: '' },
              });
              setErrors({});
            }}
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
        <h1>Multi-Step Form Wizard</h1>
        <p>Complete all steps to submit your information</p>
      </div>
      
      <StepIndicator currentStep={currentStep} />
      
      <div className="wizard-content">
        {currentStep === 1 && (
          <StepPersonal
            data={formData.personal}
            errors={errors}
            onChange={handlePersonalChange}
          />
        )}
        
        {currentStep === 2 && (
          <StepAddress
            data={formData.address}
            errors={errors}
            onChange={handleAddressChange}
          />
        )}
        
        {currentStep === 3 && (
          <StepConfirmation data={formData} />
        )}
      </div>
      
      <div className="wizard-navigation">
        {currentStep > 1 && (
          <button className="button secondary" onClick={handleBack}>
            Back
          </button>
        )}
        
        <div className="nav-spacer" />
        
        {currentStep < 3 ? (
          <button className="button primary" onClick={handleNext}>
            Next
          </button>
        ) : (
          <button className="button submit" onClick={handleSubmit}>
            Submit
          </button>
        )}
      </div>
      
      <div className="wizard-footer">
        <div className="step-info">
          Step {currentStep} of 3
        </div>
        {Object.keys(errors).length > 0 && (
          <div className="error-summary">
            Please fix the errors above before proceeding.
          </div>
        )}
      </div>
    </div>
  );
};

export default FormWizard;