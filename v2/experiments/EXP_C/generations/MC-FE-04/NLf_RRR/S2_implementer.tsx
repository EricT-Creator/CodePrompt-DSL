import React, { useCallback } from 'react';

// ─── Interfaces ──────────────────────────────────────────────

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

// ─── Style Injection ─────────────────────────────────────────

const STYLE_ID = 'fwz-styles';
const CSS = `
.fwz-root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 40px 20px;
  background: #f0f2f5;
  min-height: 100vh;
}
.fwz-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  width: 100%;
  max-width: 520px;
  padding: 32px;
}
.fwz-step-indicator {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-bottom: 28px;
}
.fwz-step-item {
  display: flex;
  align-items: center;
}
.fwz-step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border: 2px solid #d1d5db;
  color: #9ca3af;
  background: #fff;
  transition: all 0.2s;
}
.fwz-step-circle-active {
  border-color: #6366f1;
  color: #fff;
  background: #6366f1;
}
.fwz-step-circle-completed {
  border-color: #10b981;
  color: #fff;
  background: #10b981;
}
.fwz-step-line {
  width: 60px;
  height: 2px;
  background: #e5e7eb;
  margin: 0 8px;
}
.fwz-step-line-completed {
  background: #10b981;
}
.fwz-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20px;
  text-align: center;
}
.fwz-field {
  margin-bottom: 16px;
}
.fwz-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
}
.fwz-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.fwz-input:focus {
  border-color: #6366f1;
}
.fwz-input-error {
  border-color: #ef4444;
}
.fwz-error {
  font-size: 12px;
  color: #ef4444;
  margin-top: 4px;
}
.fwz-nav {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  gap: 12px;
}
.fwz-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.fwz-btn-primary {
  background: #6366f1;
  color: #fff;
}
.fwz-btn-primary:hover {
  background: #4f46e5;
}
.fwz-btn-secondary {
  background: #e5e7eb;
  color: #374151;
}
.fwz-btn-secondary:hover {
  background: #d1d5db;
}
.fwz-btn-success {
  background: #10b981;
  color: #fff;
}
.fwz-btn-success:hover {
  background: #059669;
}
.fwz-summary {
  margin-bottom: 16px;
}
.fwz-summary-section {
  margin-bottom: 16px;
}
.fwz-summary-title {
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.fwz-summary-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  border-bottom: 1px solid #f3f4f6;
}
.fwz-summary-label {
  color: #6b7280;
}
.fwz-summary-value {
  color: #1f2937;
  font-weight: 500;
}
.fwz-success {
  text-align: center;
  padding: 40px 0;
}
.fwz-success-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.fwz-success-title {
  font-size: 20px;
  font-weight: 600;
  color: #10b981;
  margin-bottom: 8px;
}
.fwz-success-text {
  font-size: 14px;
  color: #6b7280;
}
`;

function injectStyles() {
  if (typeof document !== 'undefined' && !document.getElementById(STYLE_ID)) {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }
}

// ─── Validation ──────────────────────────────────────────────

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
    const dotIdx = info.email.lastIndexOf('.');
    if (atIdx < 1 || dotIdx <= atIdx + 1 || dotIdx >= info.email.length - 1) {
      errors.email = 'Please enter a valid email address';
    }
  }

  if (!info.phone.trim()) {
    errors.phone = 'Phone is required';
  } else {
    const digits = info.phone.replace(/[\s-]/g, '');
    if (!/^\d+$/.test(digits)) {
      errors.phone = 'Phone must contain only digits, dashes, or spaces';
    } else if (digits.length < 10 || digits.length > 15) {
      errors.phone = 'Phone must be 10-15 digits';
    }
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
    errors.zip = 'ZIP must be 5 digits or XXXXX-XXXX format';
  }

  return errors;
}

// ─── Sub-Components ──────────────────────────────────────────

function StepIndicator({ currentStep }: { currentStep: number }) {
  const steps = [1, 2, 3];
  return (
    <div className="fwz-step-indicator">
      {steps.map((s, i) => (
        <div key={s} className="fwz-step-item">
          <div
            className={
              'fwz-step-circle' +
              (i === currentStep ? ' fwz-step-circle-active' : '') +
              (i < currentStep ? ' fwz-step-circle-completed' : '')
            }
          >
            {i < currentStep ? '✓' : s}
          </div>
          {i < steps.length - 1 && (
            <div className={'fwz-step-line' + (i < currentStep ? ' fwz-step-line-completed' : '')} />
          )}
        </div>
      ))}
    </div>
  );
}

function InputField({
  label,
  name,
  value,
  error,
  onChange,
  placeholder,
}: {
  label: string;
  name: string;
  value: string;
  error?: string;
  onChange: (name: string, value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="fwz-field">
      <label className="fwz-label">{label}</label>
      <input
        className={'fwz-input' + (error ? ' fwz-input-error' : '')}
        value={value}
        onChange={e => onChange(name, e.target.value)}
        placeholder={placeholder}
      />
      {error && <div className="fwz-error">{error}</div>}
    </div>
  );
}

function PersonalInfoStep({
  data,
  errors,
  onChange,
}: {
  data: PersonalInfo;
  errors: FieldErrors;
  onChange: (name: string, value: string) => void;
}) {
  return (
    <div>
      <div className="fwz-title">Personal Information</div>
      <InputField label="Full Name" name="name" value={data.name} error={errors.name} onChange={onChange} placeholder="John Doe" />
      <InputField label="Email Address" name="email" value={data.email} error={errors.email} onChange={onChange} placeholder="john@example.com" />
      <InputField label="Phone Number" name="phone" value={data.phone} error={errors.phone} onChange={onChange} placeholder="123-456-7890" />
    </div>
  );
}

function AddressStep({
  data,
  errors,
  onChange,
}: {
  data: Address;
  errors: FieldErrors;
  onChange: (name: string, value: string) => void;
}) {
  return (
    <div>
      <div className="fwz-title">Address Details</div>
      <InputField label="Street Address" name="street" value={data.street} error={errors.street} onChange={onChange} placeholder="123 Main Street" />
      <InputField label="City" name="city" value={data.city} error={errors.city} onChange={onChange} placeholder="New York" />
      <InputField label="State" name="state" value={data.state} error={errors.state} onChange={onChange} placeholder="NY" />
      <InputField label="ZIP Code" name="zip" value={data.zip} error={errors.zip} onChange={onChange} placeholder="10001" />
    </div>
  );
}

function ConfirmationStep({ formData }: { formData: FormData }) {
  return (
    <div>
      <div className="fwz-title">Review & Confirm</div>
      <div className="fwz-summary">
        <div className="fwz-summary-section">
          <div className="fwz-summary-title">Personal Information</div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">Name</span>
            <span className="fwz-summary-value">{formData.personalInfo.name}</span>
          </div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">Email</span>
            <span className="fwz-summary-value">{formData.personalInfo.email}</span>
          </div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">Phone</span>
            <span className="fwz-summary-value">{formData.personalInfo.phone}</span>
          </div>
        </div>
        <div className="fwz-summary-section">
          <div className="fwz-summary-title">Address</div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">Street</span>
            <span className="fwz-summary-value">{formData.address.street}</span>
          </div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">City</span>
            <span className="fwz-summary-value">{formData.address.city}</span>
          </div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">State</span>
            <span className="fwz-summary-value">{formData.address.state}</span>
          </div>
          <div className="fwz-summary-row">
            <span className="fwz-summary-label">ZIP Code</span>
            <span className="fwz-summary-value">{formData.address.zip}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function NavigationButtons({
  currentStep,
  onBack,
  onNext,
  onSubmit,
}: {
  currentStep: number;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="fwz-nav">
      {currentStep > 0 ? (
        <button className="fwz-btn fwz-btn-secondary" onClick={onBack}>
          ← Back
        </button>
      ) : (
        <div />
      )}
      {currentStep < 2 ? (
        <button className="fwz-btn fwz-btn-primary" onClick={onNext}>
          Next →
        </button>
      ) : (
        <button className="fwz-btn fwz-btn-success" onClick={onSubmit}>
          Submit ✓
        </button>
      )}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────

const initialWizardState: WizardState = {
  currentStep: 0,
  formData: {
    personalInfo: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  },
  errors: {},
  isSubmitted: false,
};

function FormWizard() {
  const [state, setState] = React.useState<WizardState>(initialWizardState);

  React.useEffect(() => {
    injectStyles();
  }, []);

  const handlePersonalInfoChange = useCallback((name: string, value: string) => {
    setState(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        personalInfo: { ...prev.formData.personalInfo, [name]: value },
      },
    }));
  }, []);

  const handleAddressChange = useCallback((name: string, value: string) => {
    setState(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        address: { ...prev.formData.address, [name]: value },
      },
    }));
  }, []);

  const handleNext = useCallback(() => {
    setState(prev => {
      let errors: FieldErrors = {};
      if (prev.currentStep === 0) {
        errors = validatePersonalInfo(prev.formData.personalInfo);
      } else if (prev.currentStep === 1) {
        errors = validateAddress(prev.formData.address);
      }

      if (Object.keys(errors).length > 0) {
        return { ...prev, errors };
      }

      return { ...prev, errors: {}, currentStep: prev.currentStep + 1 };
    });
  }, []);

  const handleBack = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentStep: prev.currentStep - 1,
      errors: {},
    }));
  }, []);

  const handleSubmit = useCallback(() => {
    setState(prev => {
      console.log('Form submitted:', prev.formData);
      return { ...prev, isSubmitted: true };
    });
  }, []);

  if (state.isSubmitted) {
    return (
      <div className="fwz-root">
        <div className="fwz-card">
          <div className="fwz-success">
            <div className="fwz-success-icon">🎉</div>
            <div className="fwz-success-title">Submitted Successfully!</div>
            <div className="fwz-success-text">
              Thank you, {state.formData.personalInfo.name}. Your information has been submitted.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fwz-root">
      <div className="fwz-card">
        <StepIndicator currentStep={state.currentStep} />

        {state.currentStep === 0 && (
          <PersonalInfoStep
            data={state.formData.personalInfo}
            errors={state.errors}
            onChange={handlePersonalInfoChange}
          />
        )}

        {state.currentStep === 1 && (
          <AddressStep
            data={state.formData.address}
            errors={state.errors}
            onChange={handleAddressChange}
          />
        )}

        {state.currentStep === 2 && (
          <ConfirmationStep formData={state.formData} />
        )}

        <NavigationButtons
          currentStep={state.currentStep}
          onBack={handleBack}
          onNext={handleNext}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
}

export default FormWizard;
