import React, { useState, useCallback, useEffect, useRef } from 'react';

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

// ── Constants ───────────────────────────────────────────────────────────────

const PREFIX = 'fwz_';

const STEP_LABELS = ['Personal Info', 'Address', 'Confirmation'];

// ── Styles ──────────────────────────────────────────────────────────────────

const cssText = `
.${PREFIX}container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 560px;
  margin: 40px auto;
  padding: 0 20px;
}
.${PREFIX}card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.08);
  padding: 32px;
}
.${PREFIX}title {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 24px;
}
.${PREFIX}stepIndicator {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  margin-bottom: 32px;
}
.${PREFIX}stepCircle {
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
.${PREFIX}stepCircleActive {
  border-color: #5b6abf;
  color: #fff;
  background: #5b6abf;
}
.${PREFIX}stepCircleDone {
  border-color: #2ecc71;
  color: #fff;
  background: #2ecc71;
}
.${PREFIX}stepLine {
  width: 60px;
  height: 2px;
  background: #d0d5dd;
  transition: background 0.2s;
}
.${PREFIX}stepLineDone {
  background: #2ecc71;
}
.${PREFIX}stepLabel {
  font-size: 11px;
  color: #999;
  text-align: center;
  margin-top: 4px;
}
.${PREFIX}stepLabelActive {
  color: #5b6abf;
  font-weight: 600;
}
.${PREFIX}stepItem {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.${PREFIX}fieldGroup {
  margin-bottom: 20px;
}
.${PREFIX}label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #444;
  margin-bottom: 6px;
}
.${PREFIX}input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.${PREFIX}input:focus {
  border-color: #5b6abf;
}
.${PREFIX}inputError {
  border-color: #e74c3c;
}
.${PREFIX}errorMsg {
  font-size: 12px;
  color: #e74c3c;
  margin-top: 4px;
}
.${PREFIX}navRow {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
  gap: 12px;
}
.${PREFIX}btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.${PREFIX}btnPrimary {
  background: #5b6abf;
  color: #fff;
}
.${PREFIX}btnPrimary:hover {
  background: #4a59a8;
}
.${PREFIX}btnSecondary {
  background: #f0f0f0;
  color: #555;
}
.${PREFIX}btnSecondary:hover {
  background: #e0e0e0;
}
.${PREFIX}btnSubmit {
  background: #2ecc71;
  color: #fff;
}
.${PREFIX}btnSubmit:hover {
  background: #27ae60;
}
.${PREFIX}summary {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
}
.${PREFIX}summarySection {
  margin-bottom: 16px;
}
.${PREFIX}summarySectionTitle {
  font-size: 13px;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.${PREFIX}summaryRow {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  color: #333;
  border-bottom: 1px solid #eee;
}
.${PREFIX}summaryLabel {
  color: #888;
}
.${PREFIX}successScreen {
  text-align: center;
  padding: 40px 20px;
}
.${PREFIX}successIcon {
  font-size: 60px;
  margin-bottom: 16px;
}
.${PREFIX}successTitle {
  font-size: 20px;
  font-weight: 700;
  color: #2ecc71;
  margin-bottom: 8px;
}
.${PREFIX}successMsg {
  font-size: 14px;
  color: #666;
}
`;

// ── Validation ──────────────────────────────────────────────────────────────

function validatePersonalInfo(data: PersonalInfo): FieldErrors {
  const errors: FieldErrors = {};

  if (!data.name.trim()) {
    errors.name = 'Name is required';
  } else if (data.name.trim().length < 2) {
    errors.name = 'Name must be at least 2 characters';
  } else if (!/^[a-zA-Z\s]+$/.test(data.name.trim())) {
    errors.name = 'Name must contain only letters and spaces';
  }

  if (!data.email.trim()) {
    errors.email = 'Email is required';
  } else {
    const atIdx = data.email.indexOf('@');
    const dotAfterAt = atIdx > 0 ? data.email.indexOf('.', atIdx) : -1;
    if (atIdx <= 0 || dotAfterAt <= atIdx + 1) {
      errors.email = 'Please enter a valid email address';
    }
  }

  if (!data.phone.trim()) {
    errors.phone = 'Phone is required';
  } else {
    const digits = data.phone.replace(/[\s\-]/g, '');
    if (!/^\d+$/.test(digits)) {
      errors.phone = 'Phone must contain only digits (dashes and spaces allowed)';
    } else if (digits.length < 10 || digits.length > 15) {
      errors.phone = 'Phone must be 10-15 digits';
    }
  }

  return errors;
}

function validateAddress(data: Address): FieldErrors {
  const errors: FieldErrors = {};

  if (!data.street.trim()) {
    errors.street = 'Street is required';
  } else if (data.street.trim().length < 5) {
    errors.street = 'Street must be at least 5 characters';
  }

  if (!data.city.trim()) {
    errors.city = 'City is required';
  } else if (data.city.trim().length < 2) {
    errors.city = 'City must be at least 2 characters';
  } else if (!/^[a-zA-Z\s]+$/.test(data.city.trim())) {
    errors.city = 'City must contain only letters and spaces';
  }

  if (!data.state.trim()) {
    errors.state = 'State is required';
  } else if (data.state.trim().length < 2) {
    errors.state = 'State must be at least 2 characters';
  }

  if (!data.zip.trim()) {
    errors.zip = 'ZIP code is required';
  } else if (!/^\d{5}(-\d{4})?$/.test(data.zip.trim())) {
    errors.zip = 'ZIP must be 5 digits (XXXXX) or 5+4 format (XXXXX-XXXX)';
  }

  return errors;
}

// ── Sub-components ──────────────────────────────────────────────────────────

const StepIndicator: React.FC<{ currentStep: number }> = ({ currentStep }) => (
  <div className={`${PREFIX}stepIndicator`}>
    {STEP_LABELS.map((label, i) => (
      <React.Fragment key={i}>
        {i > 0 && (
          <div className={`${PREFIX}stepLine ${i <= currentStep ? `${PREFIX}stepLineDone` : ''}`} />
        )}
        <div className={`${PREFIX}stepItem`}>
          <div
            className={`${PREFIX}stepCircle ${
              i < currentStep ? `${PREFIX}stepCircleDone` :
              i === currentStep ? `${PREFIX}stepCircleActive` : ''
            }`}
          >
            {i < currentStep ? '✓' : i + 1}
          </div>
          <div className={`${PREFIX}stepLabel ${i === currentStep ? `${PREFIX}stepLabelActive` : ''}`}>
            {label}
          </div>
        </div>
      </React.Fragment>
    ))}
  </div>
);

const FormField: React.FC<{
  label: string;
  name: string;
  value: string;
  error?: string;
  placeholder?: string;
  onChange: (name: string, value: string) => void;
}> = ({ label, name, value, error, placeholder, onChange }) => (
  <div className={`${PREFIX}fieldGroup`}>
    <label className={`${PREFIX}label`}>{label}</label>
    <input
      className={`${PREFIX}input ${error ? `${PREFIX}inputError` : ''}`}
      value={value}
      placeholder={placeholder}
      onChange={e => onChange(name, e.target.value)}
    />
    {error && <div className={`${PREFIX}errorMsg`}>{error}</div>}
  </div>
);

const PersonalInfoStep: React.FC<{
  data: PersonalInfo;
  errors: FieldErrors;
  onChange: (name: string, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div>
    <FormField label="Full Name" name="name" value={data.name} error={errors.name} placeholder="John Doe" onChange={onChange} />
    <FormField label="Email" name="email" value={data.email} error={errors.email} placeholder="john@example.com" onChange={onChange} />
    <FormField label="Phone" name="phone" value={data.phone} error={errors.phone} placeholder="123-456-7890" onChange={onChange} />
  </div>
);

const AddressStep: React.FC<{
  data: Address;
  errors: FieldErrors;
  onChange: (name: string, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div>
    <FormField label="Street Address" name="street" value={data.street} error={errors.street} placeholder="123 Main St" onChange={onChange} />
    <FormField label="City" name="city" value={data.city} error={errors.city} placeholder="Springfield" onChange={onChange} />
    <FormField label="State" name="state" value={data.state} error={errors.state} placeholder="IL" onChange={onChange} />
    <FormField label="ZIP Code" name="zip" value={data.zip} error={errors.zip} placeholder="62704" onChange={onChange} />
  </div>
);

const ConfirmationStep: React.FC<{ formData: FormData }> = ({ formData }) => (
  <div className={`${PREFIX}summary`}>
    <div className={`${PREFIX}summarySection`}>
      <div className={`${PREFIX}summarySectionTitle`}>Personal Information</div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>Name</span><span>{formData.personalInfo.name}</span></div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>Email</span><span>{formData.personalInfo.email}</span></div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>Phone</span><span>{formData.personalInfo.phone}</span></div>
    </div>
    <div className={`${PREFIX}summarySection`}>
      <div className={`${PREFIX}summarySectionTitle`}>Address</div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>Street</span><span>{formData.address.street}</span></div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>City</span><span>{formData.address.city}</span></div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>State</span><span>{formData.address.state}</span></div>
      <div className={`${PREFIX}summaryRow`}><span className={`${PREFIX}summaryLabel`}>ZIP</span><span>{formData.address.zip}</span></div>
    </div>
  </div>
);

const NavigationButtons: React.FC<{
  currentStep: number;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
}> = ({ currentStep, onBack, onNext, onSubmit }) => (
  <div className={`${PREFIX}navRow`}>
    {currentStep > 0 ? (
      <button className={`${PREFIX}btn ${PREFIX}btnSecondary`} onClick={onBack}>Back</button>
    ) : <div />}
    {currentStep < 2 ? (
      <button className={`${PREFIX}btn ${PREFIX}btnPrimary`} onClick={onNext}>Next</button>
    ) : (
      <button className={`${PREFIX}btn ${PREFIX}btnSubmit`} onClick={onSubmit}>Submit</button>
    )}
  </div>
);

// ── Main component ──────────────────────────────────────────────────────────

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
  const styleRef = useRef<HTMLStyleElement | null>(null);

  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = cssText;
    document.head.appendChild(style);
    styleRef.current = style;
    return () => { style.remove(); };
  }, []);

  const handlePersonalChange = useCallback((name: string, value: string) => {
    setWizardState(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        personalInfo: { ...prev.formData.personalInfo, [name]: value },
      },
    }));
  }, []);

  const handleAddressChange = useCallback((name: string, value: string) => {
    setWizardState(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        address: { ...prev.formData.address, [name]: value },
      },
    }));
  }, []);

  const handleNext = useCallback(() => {
    setWizardState(prev => {
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
    setWizardState(prev => ({
      ...prev,
      currentStep: prev.currentStep - 1,
      errors: {},
    }));
  }, []);

  const handleSubmit = useCallback(() => {
    console.log('Form submitted:', wizardState.formData);
    setWizardState(prev => ({ ...prev, isSubmitted: true }));
  }, [wizardState.formData]);

  if (wizardState.isSubmitted) {
    return (
      <div className={`${PREFIX}container`}>
        <div className={`${PREFIX}card`}>
          <div className={`${PREFIX}successScreen`}>
            <div className={`${PREFIX}successIcon`}>🎉</div>
            <div className={`${PREFIX}successTitle`}>Successfully Submitted!</div>
            <div className={`${PREFIX}successMsg`}>Thank you, {wizardState.formData.personalInfo.name}. Your information has been received.</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${PREFIX}container`}>
      <div className={`${PREFIX}card`}>
        <div className={`${PREFIX}title`}>Registration Form</div>
        <StepIndicator currentStep={wizardState.currentStep} />

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
          <ConfirmationStep formData={wizardState.formData} />
        )}

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
