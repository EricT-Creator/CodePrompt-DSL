import React, { useState, useCallback } from "react";

// ── Data Model ──
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

// ── Plain CSS (embedded as style tag via component) ──
const css = `
.wizard-container {
  max-width: 640px;
  margin: 40px auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #333;
}

.wizard-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  padding: 32px;
}

.step-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  margin-bottom: 32px;
}

.step-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border: 2px solid #d9d9d9;
  background: #fff;
  color: #999;
  transition: all 0.3s;
}

.step-dot.active {
  border-color: #1890ff;
  background: #1890ff;
  color: #fff;
}

.step-dot.completed {
  border-color: #52c41a;
  background: #52c41a;
  color: #fff;
}

.step-connector {
  width: 60px;
  height: 2px;
  background: #e8e8e8;
  margin: 0 8px;
}

.step-connector.active {
  background: #1890ff;
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #222;
}

.step-subtitle {
  font-size: 13px;
  color: #999;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24,144,255,0.1);
}

.form-input.error {
  border-color: #ff4d4f;
}

.error-text {
  color: #ff4d4f;
  font-size: 12px;
  margin-top: 4px;
}

.button-row {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
  gap: 12px;
}

.btn {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #1890ff;
  color: #fff;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-secondary {
  background: #f0f0f0;
  color: #555;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-success {
  background: #52c41a;
  color: #fff;
}

.btn-success:hover {
  background: #73d13d;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.summary-section {
  margin-bottom: 20px;
}

.summary-title {
  font-size: 14px;
  font-weight: 600;
  color: #555;
  margin-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 6px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
}

.summary-label {
  color: #888;
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
  font-size: 22px;
  font-weight: 600;
  color: #52c41a;
  margin-bottom: 8px;
}

.success-text {
  font-size: 14px;
  color: #888;
}
`;

// ── Validation ──
function validateStep(step: StepId, data: FormData): ValidationErrors {
  const errors: ValidationErrors = {};

  if (step === 1) {
    const { name, email, phone } = data.personal;
    if (!name.trim()) {
      errors.name = "Name is required";
    } else if (name.trim().length < 2) {
      errors.name = "Name must be at least 2 characters";
    } else if (!/^[a-zA-Z\s-]+$/.test(name.trim())) {
      errors.name = "Name can only contain letters, spaces, and hyphens";
    }

    if (!email.trim()) {
      errors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = "Please enter a valid email address";
    }

    if (!phone.trim()) {
      errors.phone = "Phone is required";
    } else if (!/^\+?\d{10,15}$/.test(phone.trim().replace(/[\s-]/g, ""))) {
      errors.phone = "Phone must be 10-15 digits (optional leading +)";
    }
  }

  if (step === 2) {
    const { street, city, state: st, zip } = data.address;
    if (!street.trim()) {
      errors.street = "Street is required";
    } else if (street.trim().length < 5) {
      errors.street = "Street must be at least 5 characters";
    }

    if (!city.trim()) {
      errors.city = "City is required";
    } else if (city.trim().length < 2) {
      errors.city = "City must be at least 2 characters";
    }

    if (!st.trim()) {
      errors.state = "State is required";
    } else if (!/^[A-Z]{2}$/.test(st.trim())) {
      errors.state = "State must be exactly 2 uppercase letters";
    }

    if (!zip.trim()) {
      errors.zip = "ZIP code is required";
    } else if (!/^\d{5}(-\d{4})?$/.test(zip.trim())) {
      errors.zip = "ZIP must be 5 digits or 5+4 format (e.g. 12345 or 12345-6789)";
    }
  }

  return errors;
}

// ── Sub-components ──
function StepIndicator({
  currentStep,
  completedSteps,
}: {
  currentStep: StepId;
  completedSteps: Set<number>;
}) {
  const steps = [1, 2, 3] as StepId[];
  return (
    <div className="step-indicator">
      {steps.map((step, i) => (
        <React.Fragment key={step}>
          {i > 0 && (
            <div className={`step-connector ${completedSteps.has(step - 1) ? "active" : ""}`} />
          )}
          <div
            className={`step-dot ${
              currentStep === step ? "active" : completedSteps.has(step) ? "completed" : ""
            }`}
          >
            {completedSteps.has(step) && currentStep !== step ? "✓" : step}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

function Step1({
  data,
  errors,
  onChange,
  onBlur,
}: {
  data: PersonalInfo;
  errors: ValidationErrors;
  onChange: (field: string, value: string) => void;
  onBlur: (field: string) => void;
}) {
  return (
    <div>
      <div className="step-title">Personal Information</div>
      <div className="step-subtitle">Tell us about yourself</div>

      <div className="form-group">
        <label className="form-label">Full Name</label>
        <input
          className={`form-input ${errors.name ? "error" : ""}`}
          value={data.name}
          onChange={(e) => onChange("name", e.target.value)}
          onBlur={() => onBlur("name")}
          placeholder="John Doe"
        />
        {errors.name && <div className="error-text">{errors.name}</div>}
      </div>

      <div className="form-group">
        <label className="form-label">Email Address</label>
        <input
          className={`form-input ${errors.email ? "error" : ""}`}
          type="email"
          value={data.email}
          onChange={(e) => onChange("email", e.target.value)}
          onBlur={() => onBlur("email")}
          placeholder="john@example.com"
        />
        {errors.email && <div className="error-text">{errors.email}</div>}
      </div>

      <div className="form-group">
        <label className="form-label">Phone Number</label>
        <input
          className={`form-input ${errors.phone ? "error" : ""}`}
          value={data.phone}
          onChange={(e) => onChange("phone", e.target.value)}
          onBlur={() => onBlur("phone")}
          placeholder="+1234567890"
        />
        {errors.phone && <div className="error-text">{errors.phone}</div>}
      </div>
    </div>
  );
}

function Step2({
  data,
  errors,
  onChange,
  onBlur,
}: {
  data: AddressInfo;
  errors: ValidationErrors;
  onChange: (field: string, value: string) => void;
  onBlur: (field: string) => void;
}) {
  return (
    <div>
      <div className="step-title">Address Details</div>
      <div className="step-subtitle">Where can we reach you?</div>

      <div className="form-group">
        <label className="form-label">Street Address</label>
        <input
          className={`form-input ${errors.street ? "error" : ""}`}
          value={data.street}
          onChange={(e) => onChange("street", e.target.value)}
          onBlur={() => onBlur("street")}
          placeholder="123 Main Street"
        />
        {errors.street && <div className="error-text">{errors.street}</div>}
      </div>

      <div className="form-group">
        <label className="form-label">City</label>
        <input
          className={`form-input ${errors.city ? "error" : ""}`}
          value={data.city}
          onChange={(e) => onChange("city", e.target.value)}
          onBlur={() => onBlur("city")}
          placeholder="New York"
        />
        {errors.city && <div className="error-text">{errors.city}</div>}
      </div>

      <div style={{ display: "flex", gap: "16px" }}>
        <div className="form-group" style={{ flex: 1 }}>
          <label className="form-label">State</label>
          <input
            className={`form-input ${errors.state ? "error" : ""}`}
            value={data.state}
            onChange={(e) => onChange("state", e.target.value.toUpperCase())}
            onBlur={() => onBlur("state")}
            placeholder="NY"
            maxLength={2}
          />
          {errors.state && <div className="error-text">{errors.state}</div>}
        </div>

        <div className="form-group" style={{ flex: 1 }}>
          <label className="form-label">ZIP Code</label>
          <input
            className={`form-input ${errors.zip ? "error" : ""}`}
            value={data.zip}
            onChange={(e) => onChange("zip", e.target.value)}
            onBlur={() => onBlur("zip")}
            placeholder="10001"
          />
          {errors.zip && <div className="error-text">{errors.zip}</div>}
        </div>
      </div>
    </div>
  );
}

function Step3({ data }: { data: FormData }) {
  return (
    <div>
      <div className="step-title">Review & Confirm</div>
      <div className="step-subtitle">Please review your information before submitting</div>

      <div className="summary-section">
        <div className="summary-title">Personal Information</div>
        <div className="summary-row">
          <span className="summary-label">Name</span>
          <span className="summary-value">{data.personal.name}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">Email</span>
          <span className="summary-value">{data.personal.email}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">Phone</span>
          <span className="summary-value">{data.personal.phone}</span>
        </div>
      </div>

      <div className="summary-section">
        <div className="summary-title">Address</div>
        <div className="summary-row">
          <span className="summary-label">Street</span>
          <span className="summary-value">{data.address.street}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">City</span>
          <span className="summary-value">{data.address.city}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">State</span>
          <span className="summary-value">{data.address.state}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">ZIP</span>
          <span className="summary-value">{data.address.zip}</span>
        </div>
      </div>
    </div>
  );
}

function SuccessScreen() {
  return (
    <div className="success-message">
      <div className="success-icon">✅</div>
      <div className="success-title">Submission Successful!</div>
      <div className="success-text">Your information has been submitted successfully.</div>
    </div>
  );
}

// ── Main Component ──
export default function FormWizard() {
  const [currentStep, setCurrentStep] = useState<StepId>(1);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: "", email: "", phone: "" },
    address: { street: "", city: "", state: "", zip: "" },
  });
  const [errors, setErrors] = useState<{ step1: ValidationErrors; step2: ValidationErrors }>({
    step1: {},
    step2: {},
  });
  const [submitted, setSubmitted] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  const handlePersonalChange = useCallback(
    (field: string, value: string) => {
      setFormData((prev) => ({
        ...prev,
        personal: { ...prev.personal, [field]: value },
      }));
      if (errors.step1[field]) {
        setErrors((prev) => {
          const newErrors = { ...prev.step1 };
          delete newErrors[field];
          return { ...prev, step1: newErrors };
        });
      }
    },
    [errors.step1]
  );

  const handleAddressChange = useCallback(
    (field: string, value: string) => {
      setFormData((prev) => ({
        ...prev,
        address: { ...prev.address, [field]: value },
      }));
      if (errors.step2[field]) {
        setErrors((prev) => {
          const newErrors = { ...prev.step2 };
          delete newErrors[field];
          return { ...prev, step2: newErrors };
        });
      }
    },
    [errors.step2]
  );

  const handleBlur = useCallback(
    (step: StepId, field: string) => {
      const stepErrors = validateStep(step, formData);
      if (stepErrors[field]) {
        setErrors((prev) => ({
          ...prev,
          [`step${step}`]: { ...prev[`step${step}` as "step1" | "step2"], [field]: stepErrors[field] },
        }));
      }
    },
    [formData]
  );

  const goNext = useCallback(() => {
    const stepErrors = validateStep(currentStep, formData);
    if (Object.keys(stepErrors).length > 0) {
      setErrors((prev) => ({
        ...prev,
        [`step${currentStep}`]: stepErrors,
      }));
      return;
    }
    setErrors((prev) => ({
      ...prev,
      [`step${currentStep}`]: {},
    }));
    setCompletedSteps((prev) => new Set([...prev, currentStep]));
    setCurrentStep((prev) => Math.min(prev + 1, 3) as StepId);
  }, [currentStep, formData]);

  const goBack = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 1) as StepId);
  }, []);

  const handleSubmit = useCallback(() => {
    console.log("Submitted:", formData);
    setCompletedSteps(new Set([1, 2, 3]));
    setSubmitted(true);
  }, [formData]);

  return (
    <>
      <style>{css}</style>
      <div className="wizard-container">
        <div className="wizard-card">
          <StepIndicator currentStep={currentStep} completedSteps={completedSteps} />

          {submitted ? (
            <SuccessScreen />
          ) : (
            <>
              {currentStep === 1 && (
                <Step1
                  data={formData.personal}
                  errors={errors.step1}
                  onChange={handlePersonalChange}
                  onBlur={(field) => handleBlur(1, field)}
                />
              )}
              {currentStep === 2 && (
                <Step2
                  data={formData.address}
                  errors={errors.step2}
                  onChange={handleAddressChange}
                  onBlur={(field) => handleBlur(2, field)}
                />
              )}
              {currentStep === 3 && <Step3 data={formData} />}

              <div className="button-row">
                <button
                  className="btn btn-secondary"
                  onClick={goBack}
                  disabled={currentStep === 1}
                >
                  ← Back
                </button>
                {currentStep < 3 ? (
                  <button className="btn btn-primary" onClick={goNext}>
                    Next →
                  </button>
                ) : (
                  <button className="btn btn-success" onClick={handleSubmit}>
                    Submit ✓
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
