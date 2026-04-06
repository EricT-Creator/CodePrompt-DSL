import React, { useState } from 'react';
import styles from './S2_implementer.module.css';

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

function validateStep(step: number, data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (step === 1) {
    if (!data.personal.name || data.personal.name.length < 2) {
      errors.name = 'Name is required and must be at least 2 characters';
    }
    if (!data.personal.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.personal.email)) {
      errors.email = 'Valid email is required';
    }
    if (!data.personal.phone || !/^\+?[\d\s\-()]{7,15}$/.test(data.personal.phone)) {
      errors.phone = 'Valid phone number is required';
    }
  } else if (step === 2) {
    if (!data.address.street) {
      errors.street = 'Street address is required';
    }
    if (!data.address.city || data.address.city.length < 2) {
      errors.city = 'City is required';
    }
    if (!data.address.state) {
      errors.state = 'State is required';
    }
    if (!data.address.zip || !/^\d{5}(-\d{4})?$/.test(data.address.zip)) {
      errors.zip = 'Valid ZIP code is required';
    }
  }
  return errors;
}

const FieldError: React.FC<{ message?: string }> = ({ message }) => {
  if (!message) return null;
  return <span className={styles.error}>{message}</span>;
};

const StepPersonal: React.FC<{
  values: PersonalInfo;
  errors: FormErrors;
  onChange: (field: keyof PersonalInfo, value: string) => void;
}> = ({ values, errors, onChange }) => {
  return (
    <div className={styles.step}>
      <h2>Personal Information</h2>
      <div className={styles.field}>
        <label>Name</label>
        <input
          type="text"
          value={values.name}
          onChange={(e) => onChange('name', e.target.value)}
        />
        <FieldError message={errors.name} />
      </div>
      <div className={styles.field}>
        <label>Email</label>
        <input
          type="email"
          value={values.email}
          onChange={(e) => onChange('email', e.target.value)}
        />
        <FieldError message={errors.email} />
      </div>
      <div className={styles.field}>
        <label>Phone</label>
        <input
          type="tel"
          value={values.phone}
          onChange={(e) => onChange('phone', e.target.value)}
        />
        <FieldError message={errors.phone} />
      </div>
    </div>
  );
};

const StepAddress: React.FC<{
  values: AddressInfo;
  errors: FormErrors;
  onChange: (field: keyof AddressInfo, value: string) => void;
}> = ({ values, errors, onChange }) => {
  const states = ['CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI'];
  return (
    <div className={styles.step}>
      <h2>Address Information</h2>
      <div className={styles.field}>
        <label>Street</label>
        <input
          type="text"
          value={values.street}
          onChange={(e) => onChange('street', e.target.value)}
        />
        <FieldError message={errors.street} />
      </div>
      <div className={styles.field}>
        <label>City</label>
        <input
          type="text"
          value={values.city}
          onChange={(e) => onChange('city', e.target.value)}
        />
        <FieldError message={errors.city} />
      </div>
      <div className={styles.field}>
        <label>State</label>
        <select value={values.state} onChange={(e) => onChange('state', e.target.value)}>
          <option value="">Select State</option>
          {states.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <FieldError message={errors.state} />
      </div>
      <div className={styles.field}>
        <label>ZIP Code</label>
        <input
          type="text"
          value={values.zip}
          onChange={(e) => onChange('zip', e.target.value)}
        />
        <FieldError message={errors.zip} />
      </div>
    </div>
  );
};

const StepConfirmation: React.FC<{
  data: FormData;
}> = ({ data }) => {
  return (
    <div className={styles.step}>
      <h2>Confirmation</h2>
      <div className={styles.summary}>
        <h3>Personal Information</h3>
        <p><strong>Name:</strong> {data.personal.name}</p>
        <p><strong>Email:</strong> {data.personal.email}</p>
        <p><strong>Phone:</strong> {data.personal.phone}</p>
        <h3>Address Information</h3>
        <p><strong>Street:</strong> {data.address.street}</p>
        <p><strong>City:</strong> {data.address.city}</p>
        <p><strong>State:</strong> {data.address.state}</p>
        <p><strong>ZIP:</strong> {data.address.zip}</p>
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

  const updatePersonal = (field: keyof PersonalInfo, value: string) => {
    setFormData(prev => ({ ...prev, personal: { ...prev.personal, [field]: value } }));
    if (errors[field]) {
      setErrors(prev => { const next = { ...prev }; delete next[field]; return next; });
    }
  };

  const updateAddress = (field: keyof AddressInfo, value: string) => {
    setFormData(prev => ({ ...prev, address: { ...prev.address, [field]: value } }));
    if (errors[field]) {
      setErrors(prev => { const next = { ...prev }; delete next[field]; return next; });
    }
  };

  const handleNext = () => {
    const validationErrors = validateStep(currentStep, formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
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
    }
  };

  const handleSubmit = () => {
    console.log('Form submitted:', formData);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className={styles.wizard}>
        <div className={styles.success}>
          <h2>Success!</h2>
          <p>Your form has been submitted successfully.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wizard}>
      <div className={styles.stepIndicator}>
        {[1, 2, 3].map(step => (
          <div key={step} className={`${styles.stepCircle} ${currentStep >= step ? styles.active : ''}`}>
            {step}
          </div>
        ))}
      </div>
      {currentStep === 1 && (
        <StepPersonal values={formData.personal} errors={errors} onChange={updatePersonal} />
      )}
      {currentStep === 2 && (
        <StepAddress values={formData.address} errors={errors} onChange={updateAddress} />
      )}
      {currentStep === 3 && <StepConfirmation data={formData} />}
      <div className={styles.buttons}>
        {currentStep > 1 && (
          <button className={styles.secondary} onClick={handleBack}>Back</button>
        )}
        {currentStep < 3 ? (
          <button className={styles.primary} onClick={handleNext}>Next</button>
        ) : (
          <button className={styles.primary} onClick={handleSubmit}>Submit</button>
        )}
      </div>
    </div>
  );
};

export default FormWizard;
