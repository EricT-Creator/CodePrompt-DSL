import React, { useState, useCallback } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

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

// ─── Styles ──────────────────────────────────────────────────────────────────

const css = `
* { box-sizing: border-box; }
.wizardContainer { max-width: 580px; margin: 40px auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 0 16px; }
.stepIndicator { display: flex; align-items: center; justify-content: center; margin-bottom: 32px; }
.stepCircle { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; border: 2px solid #d1d5db; color: #6b7280; background: #fff; transition: all 0.2s; }
.stepCircleActive { border-color: #3b82f6; background: #3b82f6; color: #fff; }
.stepCircleCompleted { border-color: #22c55e; background: #22c55e; color: #fff; }
.stepLine { width: 60px; height: 2px; background: #d1d5db; margin: 0 8px; transition: background 0.2s; }
.stepLineActive { background: #22c55e; }
.stepLabel { text-align: center; font-size: 11px; color: #6b7280; margin-top: 4px; }
.stepGroup { display: flex; flex-direction: column; align-items: center; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 28px; box-shadow: 0 1px 6px rgba(0,0,0,0.06); }
.cardTitle { font-size: 20px; font-weight: 700; color: #1f2937; margin: 0 0 20px; }
.fieldGroup { margin-bottom: 18px; }
.label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.input { width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.15s; }
.input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.12); }
.inputError { border-color: #ef4444; }
.inputError:focus { box-shadow: 0 0 0 2px rgba(239,68,68,0.12); }
.errorText { color: #ef4444; font-size: 12px; margin-top: 4px; }
.select { width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; outline: none; background: #fff; }
.btnRow { display: flex; justify-content: space-between; margin-top: 24px; }
.btn { padding: 10px 24px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: all 0.15s; }
.btnPrimary { background: #3b82f6; color: #fff; }
.btnPrimary:hover { background: #2563eb; }
.btnSecondary { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btnSecondary:hover { background: #e5e7eb; }
.btnSuccess { background: #22c55e; color: #fff; }
.btnSuccess:hover { background: #16a34a; }
.confirmSection { margin-bottom: 16px; }
.confirmLabel { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.confirmValue { font-size: 15px; color: #1f2937; padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
.successBox { text-align: center; padding: 48px 24px; }
.successIcon { font-size: 48px; margin-bottom: 16px; }
.successTitle { font-size: 22px; font-weight: 700; color: #22c55e; margin-bottom: 8px; }
.successMsg { font-size: 14px; color: #6b7280; }
`;

// ─── Validation ──────────────────────────────────────────────────────────────

function validateStep(step: 1 | 2, data: FormData): FormErrors {
  const errors: FormErrors = {};

  if (step === 1) {
    if (!data.personal.name || data.personal.name.trim().length < 2) {
      errors.name = "Name is required and must be at least 2 characters";
    }
    if (!data.personal.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.personal.email)) {
      errors.email = "Valid email is required";
    }
    if (!data.personal.phone || !/^\+?[\d\s\-()]{7,15}$/.test(data.personal.phone)) {
      errors.phone = "Valid phone number is required";
    }
  }

  if (step === 2) {
    if (!data.address.street.trim()) {
      errors.street = "Street address is required";
    }
    if (!data.address.city || data.address.city.trim().length < 2) {
      errors.city = "City is required";
    }
    if (!data.address.state.trim()) {
      errors.state = "State is required";
    }
    if (!data.address.zip || !/^\d{5}(-\d{4})?$/.test(data.address.zip)) {
      errors.zip = "Valid ZIP code is required";
    }
  }

  return errors;
}

// ─── FieldError ──────────────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <div className="errorText">{message}</div>;
}

// ─── Step Indicator ──────────────────────────────────────────────────────────

function StepIndicator({ currentStep }: { currentStep: 1 | 2 | 3 }) {
  const steps = [
    { num: 1, label: "Personal" },
    { num: 2, label: "Address" },
    { num: 3, label: "Confirm" },
  ];

  return (
    <div className="stepIndicator">
      {steps.map((s, i) => (
        <React.Fragment key={s.num}>
          <div className="stepGroup">
            <div
              className={`stepCircle${
                s.num === currentStep
                  ? " stepCircleActive"
                  : s.num < currentStep
                  ? " stepCircleCompleted"
                  : ""
              }`}
            >
              {s.num < currentStep ? "✓" : s.num}
            </div>
            <div className="stepLabel">{s.label}</div>
          </div>
          {i < steps.length - 1 && (
            <div className={`stepLine${s.num < currentStep ? " stepLineActive" : ""}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ─── StepPersonal ────────────────────────────────────────────────────────────

function StepPersonal({
  values,
  errors,
  onChange,
}: {
  values: PersonalInfo;
  errors: FormErrors;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <div>
      <h2 className="cardTitle">Personal Information</h2>
      <div className="fieldGroup">
        <label className="label">Name</label>
        <input
          className={`input${errors.name ? " inputError" : ""}`}
          value={values.name}
          onChange={(e) => onChange("name", e.target.value)}
          placeholder="John Doe"
        />
        <FieldError message={errors.name} />
      </div>
      <div className="fieldGroup">
        <label className="label">Email</label>
        <input
          className={`input${errors.email ? " inputError" : ""}`}
          value={values.email}
          onChange={(e) => onChange("email", e.target.value)}
          placeholder="john@example.com"
          type="email"
        />
        <FieldError message={errors.email} />
      </div>
      <div className="fieldGroup">
        <label className="label">Phone</label>
        <input
          className={`input${errors.phone ? " inputError" : ""}`}
          value={values.phone}
          onChange={(e) => onChange("phone", e.target.value)}
          placeholder="+1 (555) 123-4567"
        />
        <FieldError message={errors.phone} />
      </div>
    </div>
  );
}

// ─── StepAddress ─────────────────────────────────────────────────────────────

function StepAddress({
  values,
  errors,
  onChange,
}: {
  values: AddressInfo;
  errors: FormErrors;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <div>
      <h2 className="cardTitle">Address Details</h2>
      <div className="fieldGroup">
        <label className="label">Street</label>
        <input
          className={`input${errors.street ? " inputError" : ""}`}
          value={values.street}
          onChange={(e) => onChange("street", e.target.value)}
          placeholder="123 Main St"
        />
        <FieldError message={errors.street} />
      </div>
      <div className="fieldGroup">
        <label className="label">City</label>
        <input
          className={`input${errors.city ? " inputError" : ""}`}
          value={values.city}
          onChange={(e) => onChange("city", e.target.value)}
          placeholder="Springfield"
        />
        <FieldError message={errors.city} />
      </div>
      <div className="fieldGroup">
        <label className="label">State</label>
        <input
          className={`input${errors.state ? " inputError" : ""}`}
          value={values.state}
          onChange={(e) => onChange("state", e.target.value)}
          placeholder="IL"
        />
        <FieldError message={errors.state} />
      </div>
      <div className="fieldGroup">
        <label className="label">ZIP Code</label>
        <input
          className={`input${errors.zip ? " inputError" : ""}`}
          value={values.zip}
          onChange={(e) => onChange("zip", e.target.value)}
          placeholder="62701"
        />
        <FieldError message={errors.zip} />
      </div>
    </div>
  );
}

// ─── StepConfirmation ────────────────────────────────────────────────────────

function StepConfirmation({ data }: { data: FormData }) {
  return (
    <div>
      <h2 className="cardTitle">Review &amp; Confirm</h2>
      <div className="confirmSection">
        <div className="confirmLabel">Personal Information</div>
        <div className="confirmValue">Name: {data.personal.name}</div>
        <div className="confirmValue">Email: {data.personal.email}</div>
        <div className="confirmValue">Phone: {data.personal.phone}</div>
      </div>
      <div className="confirmSection">
        <div className="confirmLabel">Address</div>
        <div className="confirmValue">Street: {data.address.street}</div>
        <div className="confirmValue">City: {data.address.city}</div>
        <div className="confirmValue">State: {data.address.state}</div>
        <div className="confirmValue">ZIP: {data.address.zip}</div>
      </div>
    </div>
  );
}

// ─── FormWizard (root) ───────────────────────────────────────────────────────

function FormWizard() {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: "", email: "", phone: "" },
    address: { street: "", city: "", state: "", zip: "" },
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const handlePersonalChange = useCallback(
    (field: string, value: string) => {
      setFormData((prev) => ({
        ...prev,
        personal: { ...prev.personal, [field]: value },
      }));
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const handleAddressChange = useCallback(
    (field: string, value: string) => {
      setFormData((prev) => ({
        ...prev,
        address: { ...prev.address, [field]: value },
      }));
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const handleNext = useCallback(() => {
    if (currentStep === 1 || currentStep === 2) {
      const stepErrors = validateStep(currentStep, formData);
      if (Object.keys(stepErrors).length > 0) {
        setErrors(stepErrors);
        return;
      }
      setErrors({});
      setCurrentStep((currentStep + 1) as 1 | 2 | 3);
    }
  }, [currentStep, formData]);

  const handleBack = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as 1 | 2 | 3);
    }
  }, [currentStep]);

  const handleSubmit = useCallback(() => {
    console.log("Form submitted:", JSON.stringify(formData, null, 2));
    setSubmitted(true);
  }, [formData]);

  if (submitted) {
    return (
      <div className="wizardContainer">
        <style>{css}</style>
        <div className="card">
          <div className="successBox">
            <div className="successIcon">🎉</div>
            <div className="successTitle">Successfully Submitted!</div>
            <div className="successMsg">
              Thank you, {formData.personal.name}. Your information has been recorded.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wizardContainer">
      <style>{css}</style>
      <StepIndicator currentStep={currentStep} />
      <div className="card">
        {currentStep === 1 && (
          <StepPersonal values={formData.personal} errors={errors} onChange={handlePersonalChange} />
        )}
        {currentStep === 2 && (
          <StepAddress values={formData.address} errors={errors} onChange={handleAddressChange} />
        )}
        {currentStep === 3 && <StepConfirmation data={formData} />}

        <div className="btnRow">
          {currentStep > 1 ? (
            <button className="btn btnSecondary" onClick={handleBack}>
              ← Back
            </button>
          ) : (
            <div />
          )}
          {currentStep < 3 ? (
            <button className="btn btnPrimary" onClick={handleNext}>
              Next →
            </button>
          ) : (
            <button className="btn btnSuccess" onClick={handleSubmit}>
              ✓ Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default FormWizard;
