import React, { useState, useCallback } from "react";

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

interface FormState {
  data: FormData;
  errors: {
    step1: ValidationErrors;
    step2: ValidationErrors;
  };
  currentStep: StepId;
  submitted: boolean;
}

// ─── Initial State ───
const initialState: FormState = {
  data: {
    personal: { name: "", email: "", phone: "" },
    address: { street: "", city: "", state: "", zip: "" },
  },
  errors: { step1: {}, step2: {} },
  currentStep: 1,
  submitted: false,
};

// ─── Validation ───
function validateStep(step: StepId, data: FormData): ValidationErrors {
  const errors: ValidationErrors = {};
  if (step === 1) {
    const { name, email, phone } = data.personal;
    if (!name.trim()) {
      errors.name = "Name is required.";
    } else if (name.trim().length < 2) {
      errors.name = "Name must be at least 2 characters.";
    } else if (!/^[A-Za-z\s\-]+$/.test(name.trim())) {
      errors.name = "Name may only contain letters, spaces, and hyphens.";
    }
    if (!email.trim()) {
      errors.email = "Email is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = "Please enter a valid email address.";
    }
    if (!phone.trim()) {
      errors.phone = "Phone is required.";
    } else if (!/^\+?\d{10,15}$/.test(phone.trim().replace(/[\s\-()]/g, ""))) {
      errors.phone = "Phone must be 10–15 digits (optional leading +).";
    }
  }
  if (step === 2) {
    const { street, city, state, zip } = data.address;
    if (!street.trim()) {
      errors.street = "Street is required.";
    } else if (street.trim().length < 5) {
      errors.street = "Street must be at least 5 characters.";
    }
    if (!city.trim()) {
      errors.city = "City is required.";
    } else if (city.trim().length < 2) {
      errors.city = "City must be at least 2 characters.";
    }
    if (!state.trim()) {
      errors.state = "State is required.";
    } else if (!/^[A-Z]{2}$/.test(state.trim())) {
      errors.state = "State must be exactly 2 uppercase letters.";
    }
    if (!zip.trim()) {
      errors.zip = "ZIP code is required.";
    } else if (!/^\d{5}(-\d{4})?$/.test(zip.trim())) {
      errors.zip = "ZIP must be 5 digits or 5+4 format.";
    }
  }
  return errors;
}

// ─── Styles (Plain CSS injected) ───
const css = `
.wizard {
  max-width: 560px;
  margin: 40px auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.wizard-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  padding: 32px;
}
.progress {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 32px;
}
.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  border: 2px solid #d9d9d9;
  color: #999;
  background: #fff;
  transition: all 0.2s;
}
.step-circle-active {
  border-color: #1890ff;
  color: #1890ff;
  background: #e6f7ff;
}
.step-circle-completed {
  border-color: #52c41a;
  color: #fff;
  background: #52c41a;
}
.step-label {
  font-size: 12px;
  color: #999;
}
.step-label-active {
  color: #1890ff;
  font-weight: 600;
}
.field-group {
  margin-bottom: 20px;
}
.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #333;
}
.field-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}
.field-input:focus {
  border-color: #1890ff;
}
.field-input-error {
  border-color: #ff4d4f;
}
.field-error {
  color: #ff4d4f;
  font-size: 12px;
  margin-top: 4px;
}
.nav-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
}
.btn {
  padding: 10px 24px;
  border-radius: 4px;
  border: 1px solid #d9d9d9;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}
.btn-primary {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}
.btn-primary:hover {
  background: #40a9ff;
  border-color: #40a9ff;
  color: #fff;
}
.btn-success {
  background: #52c41a;
  color: #fff;
  border-color: #52c41a;
}
.btn-success:hover {
  background: #73d13d;
  border-color: #73d13d;
  color: #fff;
}
.summary-section {
  margin-bottom: 16px;
}
.summary-section h4 {
  margin: 0 0 8px;
  color: #333;
  font-size: 14px;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;
}
.summary-label {
  color: #999;
}
.summary-value {
  color: #333;
  font-weight: 500;
}
.success-message {
  text-align: center;
  padding: 40px 0;
}
.success-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.success-title {
  font-size: 20px;
  font-weight: 600;
  color: #52c41a;
  margin-bottom: 8px;
}
.success-subtitle {
  font-size: 14px;
  color: #999;
}
`;

// ─── Step Labels ───
const STEP_LABELS: Record<StepId, string> = {
  1: "Personal Info",
  2: "Address",
  3: "Confirmation",
};

// ─── Sub-components ───
interface StepProgressProps {
  currentStep: StepId;
  submitted: boolean;
}

function StepProgress({ currentStep, submitted }: StepProgressProps) {
  const steps: StepId[] = [1, 2, 3];
  return (
    <div className="progress">
      {steps.map((s) => {
        const isCompleted = submitted || s < currentStep;
        const isActive = s === currentStep && !submitted;
        return (
          <div key={s} className="step-indicator">
            <div
              className={`step-circle ${isActive ? "step-circle-active" : ""} ${isCompleted ? "step-circle-completed" : ""}`}
            >
              {isCompleted ? "✓" : s}
            </div>
            <span className={`step-label ${isActive ? "step-label-active" : ""}`}>
              {STEP_LABELS[s]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

function Field({ label, value, error, onChange, placeholder }: FieldProps) {
  return (
    <div className="field-group">
      <label className="field-label">{label}</label>
      <input
        className={`field-input ${error ? "field-input-error" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {error && <div className="field-error">{error}</div>}
    </div>
  );
}

interface Step1Props {
  data: PersonalInfo;
  errors: ValidationErrors;
  onChange: (field: keyof PersonalInfo, value: string) => void;
}

function Step1({ data, errors, onChange }: Step1Props) {
  return (
    <>
      <Field label="Full Name" value={data.name} error={errors.name} onChange={(v) => onChange("name", v)} placeholder="John Doe" />
      <Field label="Email" value={data.email} error={errors.email} onChange={(v) => onChange("email", v)} placeholder="john@example.com" />
      <Field label="Phone" value={data.phone} error={errors.phone} onChange={(v) => onChange("phone", v)} placeholder="+1234567890" />
    </>
  );
}

interface Step2Props {
  data: AddressInfo;
  errors: ValidationErrors;
  onChange: (field: keyof AddressInfo, value: string) => void;
}

function Step2({ data, errors, onChange }: Step2Props) {
  return (
    <>
      <Field label="Street" value={data.street} error={errors.street} onChange={(v) => onChange("street", v)} placeholder="123 Main St" />
      <Field label="City" value={data.city} error={errors.city} onChange={(v) => onChange("city", v)} placeholder="Springfield" />
      <Field label="State" value={data.state} error={errors.state} onChange={(v) => onChange("state", v)} placeholder="IL" />
      <Field label="ZIP Code" value={data.zip} error={errors.zip} onChange={(v) => onChange("zip", v)} placeholder="62701" />
    </>
  );
}

interface Step3Props {
  data: FormData;
}

function Step3({ data }: Step3Props) {
  return (
    <>
      <div className="summary-section">
        <h4>Personal Information</h4>
        <div className="summary-row"><span className="summary-label">Name</span><span className="summary-value">{data.personal.name}</span></div>
        <div className="summary-row"><span className="summary-label">Email</span><span className="summary-value">{data.personal.email}</span></div>
        <div className="summary-row"><span className="summary-label">Phone</span><span className="summary-value">{data.personal.phone}</span></div>
      </div>
      <div className="summary-section">
        <h4>Address</h4>
        <div className="summary-row"><span className="summary-label">Street</span><span className="summary-value">{data.address.street}</span></div>
        <div className="summary-row"><span className="summary-label">City</span><span className="summary-value">{data.address.city}</span></div>
        <div className="summary-row"><span className="summary-label">State</span><span className="summary-value">{data.address.state}</span></div>
        <div className="summary-row"><span className="summary-label">ZIP</span><span className="summary-value">{data.address.zip}</span></div>
      </div>
    </>
  );
}

// ─── Main Component ───
export default function FormWizard(): React.ReactElement {
  const [formState, setFormState] = useState<FormState>(initialState);

  const updatePersonal = useCallback((field: keyof PersonalInfo, value: string) => {
    setFormState((prev) => ({
      ...prev,
      data: {
        ...prev.data,
        personal: { ...prev.data.personal, [field]: value },
      },
      errors: {
        ...prev.errors,
        step1: { ...prev.errors.step1, [field]: undefined },
      },
    }));
  }, []);

  const updateAddress = useCallback((field: keyof AddressInfo, value: string) => {
    setFormState((prev) => ({
      ...prev,
      data: {
        ...prev.data,
        address: { ...prev.data.address, [field]: value },
      },
      errors: {
        ...prev.errors,
        step2: { ...prev.errors.step2, [field]: undefined },
      },
    }));
  }, []);

  const goNext = useCallback(() => {
    setFormState((prev) => {
      const errors = validateStep(prev.currentStep, prev.data);
      if (Object.keys(errors).length > 0) {
        const errKey = prev.currentStep === 1 ? "step1" : "step2";
        return { ...prev, errors: { ...prev.errors, [errKey]: errors } };
      }
      const nextStep = (prev.currentStep + 1) as StepId;
      return { ...prev, currentStep: nextStep };
    });
  }, []);

  const goBack = useCallback(() => {
    setFormState((prev) => {
      const prevStep = (prev.currentStep - 1) as StepId;
      return { ...prev, currentStep: prevStep };
    });
  }, []);

  const handleSubmit = useCallback(() => {
    setFormState((prev) => {
      console.log("Submitted:", prev.data);
      return { ...prev, submitted: true };
    });
  }, []);

  const { currentStep, data, errors, submitted } = formState;

  if (submitted) {
    return (
      <>
        <style>{css}</style>
        <div className="wizard">
          <div className="wizard-card">
            <StepProgress currentStep={3} submitted={true} />
            <div className="success-message">
              <div className="success-icon">✅</div>
              <div className="success-title">Form Submitted Successfully!</div>
              <div className="success-subtitle">Thank you, {data.personal.name}. Your information has been recorded.</div>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{css}</style>
      <div className="wizard">
        <div className="wizard-card">
          <StepProgress currentStep={currentStep} submitted={false} />
          {currentStep === 1 && <Step1 data={data.personal} errors={errors.step1} onChange={updatePersonal} />}
          {currentStep === 2 && <Step2 data={data.address} errors={errors.step2} onChange={updateAddress} />}
          {currentStep === 3 && <Step3 data={data} />}
          <div className="nav-buttons">
            {currentStep > 1 ? (
              <button className="btn" onClick={goBack}>← Back</button>
            ) : (
              <div />
            )}
            {currentStep < 3 ? (
              <button className="btn btn-primary" onClick={goNext}>Next →</button>
            ) : (
              <button className="btn btn-success" onClick={handleSubmit}>✓ Submit</button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
