import React, { useState, useCallback } from 'react';

// ── Interfaces ──────────────────────────────────────────────────────────────

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

// ── Styles ──────────────────────────────────────────────────────────────────

const STYLE_ID = 'fwz-styles';
const P = 'fwz';

const cssText = `
.${P}-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 580px;
  margin: 40px auto;
  padding: 0 16px;
}
.${P}-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  overflow: hidden;
}
.${P}-step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 20px 20px;
  gap: 0;
  background: #f8f9fb;
  border-bottom: 1px solid #e5e7eb;
}
.${P}-step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  border: 2px solid #d0d5dd;
  color: #999;
  background: #fff;
  transition: all 0.2s;
}
.${P}-step-circle-active {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}
.${P}-step-circle-completed {
  background: #059669;
  border-color: #059669;
  color: #fff;
}
.${P}-step-line {
  width: 60px;
  height: 2px;
  background: #d0d5dd;
  margin: 0 8px;
  transition: background 0.2s;
}
.${P}-step-line-completed {
  background: #059669;
}
.${P}-step-label {
  font-size: 11px;
  color: #888;
  text-align: center;
  margin-top: 6px;
}
.${P}-step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.${P}-body {
  padding: 28px 32px;
}
.${P}-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.${P}-subtitle {
  font-size: 13px;
  color: #888;
  margin-bottom: 24px;
}
.${P}-field {
  margin-bottom: 18px;
}
.${P}-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #444;
  margin-bottom: 6px;
}
.${P}-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}
.${P}-input:focus {
  border-color: #4f46e5;
}
.${P}-input-error {
  border-color: #ef4444;
}
.${P}-error-msg {
  font-size: 12px;
  color: #ef4444;
  margin-top: 4px;
}
.${P}-nav {
  display: flex;
  justify-content: space-between;
  padding: 0 32px 28px;
}
.${P}-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.${P}-btn-primary {
  background: #4f46e5;
  color: #fff;
}
.${P}-btn-primary:hover {
  background: #4338ca;
}
.${P}-btn-secondary {
  background: #f3f4f6;
  color: #555;
}
.${P}-btn-secondary:hover {
  background: #e5e7eb;
}
.${P}-btn-success {
  background: #059669;
  color: #fff;
}
.${P}-btn-success:hover {
  background: #047857;
}
.${P}-summary-section {
  margin-bottom: 18px;
}
.${P}-summary-title {
  font-size: 14px;
  font-weight: 700;
  color: #555;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.${P}-summary-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;
}
.${P}-summary-label {
  color: #888;
}
.${P}-summary-value {
  color: #1a1a2e;
  font-weight: 500;
}
.${P}-success-screen {
  text-align: center;
  padding: 40px 20px;
}
.${P}-success-icon {
  font-size: 56px;
  margin-bottom: 16px;
}
.${P}-success-title {
  font-size: 22px;
  font-weight: 700;
  color: #059669;
  margin-bottom: 8px;
}
.${P}-success-text {
  font-size: 14px;
  color: #888;
}
`;

// ── Validation ──────────────────────────────────────────────────────────────

function validatePersonalInfo(info: PersonalInfo): FieldErrors {
  const errors: FieldErrors = {};

  if (!info.name.trim()) {
    errors.name = 'Name is required';
  } else if (info.name.trim().length < 2) {
    errors.name = 'Name must be at least 2 characters';
  } else if (!/^[a-zA-Z\s]+$/.test(info.name.trim())) {
    errors.name = 'Name must contain only letters and spaces';
  }

  if (!info.email.trim()) {
    errors.email = 'Email is required';
  } else {
    const atIdx = info.email.indexOf('@');
    const dotAfterAt = atIdx >= 0 ? info.email.indexOf('.', atIdx) : -1;
    if (atIdx < 1 || dotAfterAt < atIdx + 2) {
      errors.email = 'Please enter a valid email address';
    }
  }

  const digits = info.phone.replace(/[\s-]/g, '');
  if (!info.phone.trim()) {
    errors.phone = 'Phone is required';
  } else if (!/^\d+$/.test(digits)) {
    errors.phone = 'Phone must contain only digits (dashes and spaces allowed)';
  } else if (digits.length < 10 || digits.length > 15) {
    errors.phone = 'Phone must be 10-15 digits';
  }

  return errors;
}

function validateAddress(addr: Address): FieldErrors {
  const errors: FieldErrors = {};

  if (!addr.street.trim()) {
    errors.street = 'Street is required';
  } else if (addr.street.trim().length < 5) {
    errors.street = 'Street must be at least 5 characters';
  }

  if (!addr.city.trim()) {
    errors.city = 'City is required';
  } else if (addr.city.trim().length < 2) {
    errors.city = 'City must be at least 2 characters';
  } else if (!/^[a-zA-Z\s]+$/.test(addr.city.trim())) {
    errors.city = 'City must contain only letters and spaces';
  }

  if (!addr.state.trim()) {
    errors.state = 'State is required';
  } else if (addr.state.trim().length < 2) {
    errors.state = 'State must be at least 2 characters';
  }

  if (!addr.zip.trim()) {
    errors.zip = 'ZIP code is required';
  } else if (!/^\d{5}(-\d{4})?$/.test(addr.zip.trim())) {
    errors.zip = 'ZIP must be 5 digits (XXXXX) or 5+4 format (XXXXX-XXXX)';
  }

  return errors;
}

// ── Step Components ─────────────────────────────────────────────────────────

const StepIndicator: React.FC<{ currentStep: number }> = ({ currentStep }) => {
  const steps = ['Personal', 'Address', 'Confirm'];

  return (
    <div className={`${P}-step-indicator`}>
      {steps.map((label, i) => (
        <React.Fragment key={label}>
          {i > 0 && (
            <div className={`${P}-step-line ${i <= currentStep ? `${P}-step-line-completed` : ''}`} />
          )}
          <div className={`${P}-step-item`}>
            <div
              className={`${P}-step-circle ${
                i === currentStep
                  ? `${P}-step-circle-active`
                  : i < currentStep
                  ? `${P}-step-circle-completed`
                  : ''
              }`}
            >
              {i < currentStep ? '✓' : i + 1}
            </div>
            <div className={`${P}-step-label`}>{label}</div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
};

interface InputFieldProps {
  label: string;
  name: string;
  value: string;
  error?: string;
  placeholder?: string;
  onChange: (name: string, value: string) => void;
}

const InputField: React.FC<InputFieldProps> = ({ label, name, value, error, placeholder, onChange }) => (
  <div className={`${P}-field`}>
    <label className={`${P}-label`}>{label}</label>
    <input
      className={`${P}-input ${error ? `${P}-input-error` : ''}`}
      value={value}
      placeholder={placeholder}
      onChange={e => onChange(name, e.target.value)}
    />
    {error && <div className={`${P}-error-msg`}>{error}</div>}
  </div>
);

const PersonalInfoStep: React.FC<{
  data: PersonalInfo;
  errors: FieldErrors;
  onChange: (name: string, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div>
    <div className={`${P}-title`}>Personal Information</div>
    <div className={`${P}-subtitle`}>Please provide your personal details</div>
    <InputField label="Full Name" name="name" value={data.name} error={errors.name} placeholder="John Doe" onChange={onChange} />
    <InputField label="Email" name="email" value={data.email} error={errors.email} placeholder="john@example.com" onChange={onChange} />
    <InputField label="Phone" name="phone" value={data.phone} error={errors.phone} placeholder="555-123-4567" onChange={onChange} />
  </div>
);

const AddressStep: React.FC<{
  data: Address;
  errors: FieldErrors;
  onChange: (name: string, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div>
    <div className={`${P}-title`}>Address Details</div>
    <div className={`${P}-subtitle`}>Where can we reach you?</div>
    <InputField label="Street Address" name="street" value={data.street} error={errors.street} placeholder="123 Main Street" onChange={onChange} />
    <InputField label="City" name="city" value={data.city} error={errors.city} placeholder="Springfield" onChange={onChange} />
    <InputField label="State" name="state" value={data.state} error={errors.state} placeholder="Illinois" onChange={onChange} />
    <InputField label="ZIP Code" name="zip" value={data.zip} error={errors.zip} placeholder="62704" onChange={onChange} />
  </div>
);

const ConfirmationStep: React.FC<{ data: FormData }> = ({ data }) => (
  <div>
    <div className={`${P}-title`}>Confirm Your Details</div>
    <div className={`${P}-subtitle`}>Please review the information below before submitting</div>
    <div className={`${P}-summary-section`}>
      <div className={`${P}-summary-title`}>Personal Information</div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>Name</span><span className={`${P}-summary-value`}>{data.personalInfo.name}</span></div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>Email</span><span className={`${P}-summary-value`}>{data.personalInfo.email}</span></div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>Phone</span><span className={`${P}-summary-value`}>{data.personalInfo.phone}</span></div>
    </div>
    <div className={`${P}-summary-section`}>
      <div className={`${P}-summary-title`}>Address</div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>Street</span><span className={`${P}-summary-value`}>{data.address.street}</span></div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>City</span><span className={`${P}-summary-value`}>{data.address.city}</span></div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>State</span><span className={`${P}-summary-value`}>{data.address.state}</span></div>
      <div className={`${P}-summary-row`}><span className={`${P}-summary-label`}>ZIP</span><span className={`${P}-summary-value`}>{data.address.zip}</span></div>
    </div>
  </div>
);

const NavigationButtons: React.FC<{
  currentStep: number;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
}> = ({ currentStep, onBack, onNext, onSubmit }) => (
  <div className={`${P}-nav`}>
    {currentStep > 0 ? (
      <button className={`${P}-btn ${P}-btn-secondary`} onClick={onBack}>← Back</button>
    ) : (
      <div />
    )}
    {currentStep < 2 ? (
      <button className={`${P}-btn ${P}-btn-primary`} onClick={onNext}>Next →</button>
    ) : (
      <button className={`${P}-btn ${P}-btn-success`} onClick={onSubmit}>Submit ✓</button>
    )}
  </div>
);

// ── Main Component ──────────────────────────────────────────────────────────

const FormWizard: React.FC = () => {
  const [wizardState, setWizardState] = useState<WizardState>({
    currentStep: 0,
    formData: {
      personalInfo: { name: '', email: '', phone: '' },
      address: { street: '', city: '', state: '', zip: '' },
    },
    errors: {},
    isSubmitted: false,
  });

  // Inject styles
  React.useEffect(() => {
    if (!document.getElementById(STYLE_ID)) {
      const style = document.createElement('style');
      style.id = STYLE_ID;
      style.textContent = cssText;
      document.head.appendChild(style);
    }
    return () => {
      const el = document.getElementById(STYLE_ID);
      if (el) el.remove();
    };
  }, []);

  const handlePersonalChange = useCallback((name: string, value: string) => {
    setWizardState(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        personalInfo: { ...prev.formData.personalInfo, [name]: value },
      },
      errors: {},
    }));
  }, []);

  const handleAddressChange = useCallback((name: string, value: string) => {
    setWizardState(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        address: { ...prev.formData.address, [name]: value },
      },
      errors: {},
    }));
  }, []);

  const handleNext = useCallback(() => {
    setWizardState(prev => {
      if (prev.currentStep === 0) {
        const errors = validatePersonalInfo(prev.formData.personalInfo);
        if (Object.keys(errors).length > 0) return { ...prev, errors };
        return { ...prev, currentStep: 1, errors: {} };
      }
      if (prev.currentStep === 1) {
        const errors = validateAddress(prev.formData.address);
        if (Object.keys(errors).length > 0) return { ...prev, errors };
        return { ...prev, currentStep: 2, errors: {} };
      }
      return prev;
    });
  }, []);

  const handleBack = useCallback(() => {
    setWizardState(prev => ({
      ...prev,
      currentStep: Math.max(0, prev.currentStep - 1),
      errors: {},
    }));
  }, []);

  const handleSubmit = useCallback(() => {
    console.log('Form submitted:', wizardState.formData);
    setWizardState(prev => ({ ...prev, isSubmitted: true }));
  }, [wizardState.formData]);

  if (wizardState.isSubmitted) {
    return (
      <div className={`${P}-container`}>
        <div className={`${P}-card`}>
          <div className={`${P}-success-screen`}>
            <div className={`${P}-success-icon`}>🎉</div>
            <div className={`${P}-success-title`}>Submitted Successfully!</div>
            <div className={`${P}-success-text`}>
              Thank you, {wizardState.formData.personalInfo.name}. Your information has been received.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${P}-container`}>
      <div className={`${P}-card`}>
        <StepIndicator currentStep={wizardState.currentStep} />
        <div className={`${P}-body`}>
          {wizardState.currentStep === 0 && (
            <PersonalInfoStep
              data={wizardState.formData.personalInfo}
              errors={wizardState.errors}
              onChange={handlePersonalChange}
            />
          )}
          {wizardState.currentStep === 1 && (
            <AddressStep
              data={wizardState.formData.address}
              errors={wizardState.errors}
              onChange={handleAddressChange}
            />
          )}
          {wizardState.currentStep === 2 && (
            <ConfirmationStep data={wizardState.formData} />
          )}
        </div>
        <NavigationButtons
          currentStep={wizardState.currentStep}
          onBack={handleBack}
          onNext={handleNext}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
};

export default FormWizard;
