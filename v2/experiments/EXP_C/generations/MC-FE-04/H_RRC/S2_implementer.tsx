import React, { useState, useCallback } from 'react';

// ─── Types ───
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

// ─── CSS (Plain CSS injected via style tag) ───
const STYLE_CONTENT = `
.wizard {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 560px;
  margin: 40px auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  overflow: hidden;
}
.wizardHeader {
  background: #f8f9fa;
  padding: 24px 32px;
  border-bottom: 1px solid #e8e8e8;
}
.stepIndicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}
.stepDot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border: 2px solid #d9d9d9;
  color: #999;
  background: #fff;
  transition: all 0.3s;
}
.stepDotActive {
  border-color: #1890ff;
  color: #1890ff;
  background: #e6f7ff;
}
.stepDotCompleted {
  border-color: #52c41a;
  color: #fff;
  background: #52c41a;
}
.stepLine {
  width: 60px;
  height: 2px;
  background: #d9d9d9;
  transition: background 0.3s;
}
.stepLineActive {
  background: #52c41a;
}
.wizardBody {
  padding: 32px;
}
.stepTitle {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 24px;
  color: #333;
}
.formGroup {
  margin-bottom: 20px;
}
.formLabel {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #555;
  margin-bottom: 6px;
}
.formInput {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.formInput:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24,144,255,0.1);
}
.formInputError {
  border-color: #ff4d4f;
}
.formInputError:focus {
  box-shadow: 0 0 0 2px rgba(255,77,79,0.1);
}
.errorText {
  font-size: 12px;
  color: #ff4d4f;
  margin-top: 4px;
}
.wizardFooter {
  display: flex;
  justify-content: space-between;
  padding: 20px 32px;
  border-top: 1px solid #e8e8e8;
  background: #fafafa;
}
.btnPrimary {
  padding: 10px 24px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}
.btnPrimary:hover {
  background: #40a9ff;
}
.btnSecondary {
  padding: 10px 24px;
  background: #fff;
  color: #555;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btnSecondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}
.btnSuccess {
  padding: 10px 24px;
  background: #52c41a;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
.btnSuccess:hover {
  background: #73d13d;
}
.summarySection {
  margin-bottom: 16px;
}
.summaryLabel {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.summaryValue {
  font-size: 15px;
  color: #333;
  padding: 4px 0;
}
.summaryDivider {
  border: none;
  border-top: 1px solid #f0f0f0;
  margin: 16px 0;
}
.successMessage {
  text-align: center;
  padding: 40px 0;
}
.successIcon {
  font-size: 48px;
  margin-bottom: 16px;
}
.successTitle {
  font-size: 22px;
  font-weight: 600;
  color: #52c41a;
  margin-bottom: 8px;
}
.successSubtitle {
  font-size: 14px;
  color: #888;
}
`;

// ─── Validation ───
function validateStep(step: StepId, data: FormData): ValidationErrors {
  const errors: ValidationErrors = {};

  if (step === 1) {
    const { name, email, phone } = data.personal;
    if (!name.trim()) {
      errors.name = 'Name is required';
    } else if (name.trim().length < 2) {
      errors.name = 'Name must be at least 2 characters';
    } else if (!/^[a-zA-Z\s-]+$/.test(name.trim())) {
      errors.name = 'Name can only contain letters, spaces, and hyphens';
    }

    if (!email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = 'Please enter a valid email address';
    }

    if (!phone.trim()) {
      errors.phone = 'Phone is required';
    } else if (!/^\+?\d{10,15}$/.test(phone.trim().replace(/\s/g, ''))) {
      errors.phone = 'Phone must be 10-15 digits (optional leading +)';
    }
  }

  if (step === 2) {
    const { street, city, state: st, zip } = data.address;
    if (!street.trim()) {
      errors.street = 'Street is required';
    } else if (street.trim().length < 5) {
      errors.street = 'Street must be at least 5 characters';
    }

    if (!city.trim()) {
      errors.city = 'City is required';
    } else if (city.trim().length < 2) {
      errors.city = 'City must be at least 2 characters';
    }

    if (!st.trim()) {
      errors.state = 'State is required';
    } else if (!/^[A-Z]{2}$/.test(st.trim())) {
      errors.state = 'State must be exactly 2 uppercase letters';
    }

    if (!zip.trim()) {
      errors.zip = 'ZIP code is required';
    } else if (!/^\d{5}(-\d{4})?$/.test(zip.trim())) {
      errors.zip = 'ZIP must be 5 digits or 5+4 format (e.g. 12345 or 12345-6789)';
    }
  }

  return errors;
}

// ─── Sub-components (internal) ───

function StepIndicator({ currentStep }: { currentStep: StepId }) {
  const labels = ['Personal', 'Address', 'Confirm'];
  return (
    <div className="stepIndicator">
      {labels.map((label, i) => {
        const stepNum = (i + 1) as StepId;
        const isActive = stepNum === currentStep;
        const isCompleted = stepNum < currentStep;
        return (
          <React.Fragment key={stepNum}>
            {i > 0 && (
              <div className={`stepLine ${isCompleted ? 'stepLineActive' : ''}`} />
            )}
            <div
              className={`stepDot ${isActive ? 'stepDotActive' : ''} ${isCompleted ? 'stepDotCompleted' : ''}`}
              title={label}
            >
              {isCompleted ? '✓' : stepNum}
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}

function PersonalInfoStep({
  data,
  errors,
  onChange,
}: {
  data: PersonalInfo;
  errors: ValidationErrors;
  onChange: (field: keyof PersonalInfo, value: string) => void;
}) {
  return (
    <div>
      <h2 className="stepTitle">Personal Information</h2>
      <div className="formGroup">
        <label className="formLabel">Full Name</label>
        <input
          className={`formInput ${errors.name ? 'formInputError' : ''}`}
          value={data.name}
          onChange={(e) => onChange('name', e.target.value)}
          placeholder="John Doe"
        />
        {errors.name && <div className="errorText">{errors.name}</div>}
      </div>
      <div className="formGroup">
        <label className="formLabel">Email</label>
        <input
          className={`formInput ${errors.email ? 'formInputError' : ''}`}
          type="email"
          value={data.email}
          onChange={(e) => onChange('email', e.target.value)}
          placeholder="john@example.com"
        />
        {errors.email && <div className="errorText">{errors.email}</div>}
      </div>
      <div className="formGroup">
        <label className="formLabel">Phone</label>
        <input
          className={`formInput ${errors.phone ? 'formInputError' : ''}`}
          value={data.phone}
          onChange={(e) => onChange('phone', e.target.value)}
          placeholder="+1234567890"
        />
        {errors.phone && <div className="errorText">{errors.phone}</div>}
      </div>
    </div>
  );
}

function AddressStep({
  data,
  errors,
  onChange,
}: {
  data: AddressInfo;
  errors: ValidationErrors;
  onChange: (field: keyof AddressInfo, value: string) => void;
}) {
  return (
    <div>
      <h2 className="stepTitle">Address Information</h2>
      <div className="formGroup">
        <label className="formLabel">Street</label>
        <input
          className={`formInput ${errors.street ? 'formInputError' : ''}`}
          value={data.street}
          onChange={(e) => onChange('street', e.target.value)}
          placeholder="123 Main Street"
        />
        {errors.street && <div className="errorText">{errors.street}</div>}
      </div>
      <div className="formGroup">
        <label className="formLabel">City</label>
        <input
          className={`formInput ${errors.city ? 'formInputError' : ''}`}
          value={data.city}
          onChange={(e) => onChange('city', e.target.value)}
          placeholder="San Francisco"
        />
        {errors.city && <div className="errorText">{errors.city}</div>}
      </div>
      <div className="formGroup">
        <label className="formLabel">State</label>
        <input
          className={`formInput ${errors.state ? 'formInputError' : ''}`}
          value={data.state}
          onChange={(e) => onChange('state', e.target.value.toUpperCase())}
          placeholder="CA"
          maxLength={2}
        />
        {errors.state && <div className="errorText">{errors.state}</div>}
      </div>
      <div className="formGroup">
        <label className="formLabel">ZIP Code</label>
        <input
          className={`formInput ${errors.zip ? 'formInputError' : ''}`}
          value={data.zip}
          onChange={(e) => onChange('zip', e.target.value)}
          placeholder="94105"
        />
        {errors.zip && <div className="errorText">{errors.zip}</div>}
      </div>
    </div>
  );
}

function ConfirmationStep({ data }: { data: FormData }) {
  return (
    <div>
      <h2 className="stepTitle">Review & Confirm</h2>
      <div className="summarySection">
        <div className="summaryLabel">Personal Information</div>
        <div className="summaryValue"><strong>Name:</strong> {data.personal.name}</div>
        <div className="summaryValue"><strong>Email:</strong> {data.personal.email}</div>
        <div className="summaryValue"><strong>Phone:</strong> {data.personal.phone}</div>
      </div>
      <hr className="summaryDivider" />
      <div className="summarySection">
        <div className="summaryLabel">Address</div>
        <div className="summaryValue"><strong>Street:</strong> {data.address.street}</div>
        <div className="summaryValue"><strong>City:</strong> {data.address.city}</div>
        <div className="summaryValue"><strong>State:</strong> {data.address.state}</div>
        <div className="summaryValue"><strong>ZIP:</strong> {data.address.zip}</div>
      </div>
    </div>
  );
}

function SuccessScreen() {
  return (
    <div className="successMessage">
      <div className="successIcon">🎉</div>
      <div className="successTitle">Submitted Successfully!</div>
      <div className="successSubtitle">Your information has been recorded.</div>
    </div>
  );
}

// ─── Main Component ───
export default function FormWizard(): React.ReactElement {
  const [currentStep, setCurrentStep] = useState<StepId>(1);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: '', email: '', phone: '' },
    address: { street: '', city: '', state: '', zip: '' },
  });
  const [errors, setErrors] = useState<{ step1: ValidationErrors; step2: ValidationErrors }>({
    step1: {},
    step2: {},
  });
  const [submitted, setSubmitted] = useState(false);

  const handlePersonalChange = useCallback((field: keyof PersonalInfo, value: string) => {
    setFormData((prev) => ({
      ...prev,
      personal: { ...prev.personal, [field]: value },
    }));
    setErrors((prev) => {
      const newStep1 = { ...prev.step1 };
      delete newStep1[field];
      return { ...prev, step1: newStep1 };
    });
  }, []);

  const handleAddressChange = useCallback((field: keyof AddressInfo, value: string) => {
    setFormData((prev) => ({
      ...prev,
      address: { ...prev.address, [field]: value },
    }));
    setErrors((prev) => {
      const newStep2 = { ...prev.step2 };
      delete newStep2[field];
      return { ...prev, step2: newStep2 };
    });
  }, []);

  const goNext = useCallback(() => {
    const validationErrors = validateStep(currentStep, formData);
    if (Object.keys(validationErrors).length > 0) {
      if (currentStep === 1) {
        setErrors((prev) => ({ ...prev, step1: validationErrors }));
      } else if (currentStep === 2) {
        setErrors((prev) => ({ ...prev, step2: validationErrors }));
      }
      return;
    }
    if (currentStep === 1) setErrors((prev) => ({ ...prev, step1: {} }));
    if (currentStep === 2) setErrors((prev) => ({ ...prev, step2: {} }));
    setCurrentStep((prev) => Math.min(prev + 1, 3) as StepId);
  }, [currentStep, formData]);

  const goBack = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 1) as StepId);
  }, []);

  const handleSubmit = useCallback(() => {
    console.log('Submitted:', formData);
    setSubmitted(true);
  }, [formData]);

  if (submitted) {
    return (
      <>
        <style>{STYLE_CONTENT}</style>
        <div className="wizard">
          <div className="wizardHeader">
            <StepIndicator currentStep={3} />
          </div>
          <div className="wizardBody">
            <SuccessScreen />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{STYLE_CONTENT}</style>
      <div className="wizard">
        <div className="wizardHeader">
          <StepIndicator currentStep={currentStep} />
        </div>
        <div className="wizardBody">
          {currentStep === 1 && (
            <PersonalInfoStep
              data={formData.personal}
              errors={errors.step1}
              onChange={handlePersonalChange}
            />
          )}
          {currentStep === 2 && (
            <AddressStep
              data={formData.address}
              errors={errors.step2}
              onChange={handleAddressChange}
            />
          )}
          {currentStep === 3 && <ConfirmationStep data={formData} />}
        </div>
        <div className="wizardFooter">
          <div>
            {currentStep > 1 && (
              <button className="btnSecondary" onClick={goBack}>
                ← Back
              </button>
            )}
          </div>
          <div>
            {currentStep < 3 ? (
              <button className="btnPrimary" onClick={goNext}>
                Next →
              </button>
            ) : (
              <button className="btnSuccess" onClick={handleSubmit}>
                Submit ✓
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
