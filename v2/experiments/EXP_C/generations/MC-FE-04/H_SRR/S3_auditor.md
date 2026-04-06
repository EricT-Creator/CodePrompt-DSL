## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript types/interfaces and imports from "react"
- C2 [!D]NO_FORM_LIB [VALID]HANDWRITE: PASS — No form library imported; validation is handwritten with custom `validatePersonal()` and `validateAddress()` functions using regex and string checks
- C3 [Y]PLAIN_CSS [!Y]NO_TW: FAIL — No plain CSS file used; styles are inline `React.CSSProperties` objects (`const S: Record<string, React.CSSProperties>`), not a `.css` file or `<style>` element. No Tailwind present (PASS on `!Y`).
- C4 [D]NO_EXTERNAL: PASS — Only imports from "react"; no external dependencies
- C5 [O]SFC [EXP]DEFAULT: PASS — Single `const FormWizard: React.FC` component with `export default FormWizard`
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with no prose or markdown outside code

## Functionality Assessment (0-5)
Score: 5 — Complete multi-step form wizard with 3 steps (personal, address, confirmation), progress indicator with step numbers/checkmarks, field-level validation with real-time error clearing, email/phone/zip regex validation, review page before submission, success state with reset, and keyboard-accessible navigation.

## Corrected Code
```tsx
import React, { useState, useCallback } from "react";
import "./FormWizard.css";

// ── Types ──────────────────────────────────────────────────────────
type StepType = "personal" | "address" | "confirmation";

interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface AddressInfo {
  street: string;
  city: string;
  state: string;
  zipCode: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

type FieldErrors = Record<string, string[]>;
type ValidationErrors = {
  personal: FieldErrors;
  address: FieldErrors;
};

// ── Validation ─────────────────────────────────────────────────────
function validatePersonal(data: PersonalInfo): FieldErrors {
  const errors: FieldErrors = {};
  if (!data.name.trim() || data.name.trim().length < 2)
    errors.name = ["Name must be at least 2 characters"];
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email))
    errors.email = ["Please enter a valid email address"];
  if (!/^\d{10,}$/.test(data.phone.replace(/\D/g, "")))
    errors.phone = ["Please enter a valid phone number (at least 10 digits)"];
  return errors;
}

function validateAddress(data: AddressInfo): FieldErrors {
  const errors: FieldErrors = {};
  if (!data.street.trim() || data.street.trim().length < 5)
    errors.street = ["Street must be at least 5 characters"];
  if (!data.city.trim() || data.city.trim().length < 2)
    errors.city = ["City must be at least 2 characters"];
  if (!/^[A-Za-z]{2}$/.test(data.state.trim()))
    errors.state = ["State code must be exactly 2 letters"];
  if (!/^\d{5}(-\d{4})?$/.test(data.zipCode))
    errors.zipCode = ["Zip code must be 5 or 9 digits (e.g. 12345 or 12345-6789)"];
  return errors;
}

const STEPS: { id: StepType; label: string; num: number }[] = [
  { id: "personal", label: "Personal", num: 1 },
  { id: "address", label: "Address", num: 2 },
  { id: "confirmation", label: "Confirm", num: 3 },
];

// ── Component ──────────────────────────────────────────────────────
const FormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<StepType>("personal");
  const [formData, setFormData] = useState<FormData>({
    personal: { name: "", email: "", phone: "" },
    address: { street: "", city: "", state: "", zipCode: "" },
  });
  const [errors, setErrors] = useState<ValidationErrors>({ personal: {}, address: {} });
  const [showErrors, setShowErrors] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const stepIndex = STEPS.findIndex((s) => s.id === currentStep);

  const updateField = useCallback(
    (step: "personal" | "address", field: string, value: string) => {
      setFormData((prev) => ({ ...prev, [step]: { ...prev[step], [field]: value } }));
      if (showErrors) {
        setErrors((prev) => {
          const copy = { ...prev, [step]: { ...prev[step] } };
          delete copy[step][field];
          return copy;
        });
      }
    },
    [showErrors]
  );

  const goNext = useCallback(() => {
    if (currentStep === "personal") {
      const errs = validatePersonal(formData.personal);
      if (Object.keys(errs).length > 0) {
        setErrors((prev) => ({ ...prev, personal: errs }));
        setShowErrors(true);
        return;
      }
      setShowErrors(false);
      setCurrentStep("address");
    } else if (currentStep === "address") {
      const errs = validateAddress(formData.address);
      if (Object.keys(errs).length > 0) {
        setErrors((prev) => ({ ...prev, address: errs }));
        setShowErrors(true);
        return;
      }
      setShowErrors(false);
      setCurrentStep("confirmation");
    }
  }, [currentStep, formData]);

  const goBack = useCallback(() => {
    setShowErrors(false);
    if (currentStep === "address") setCurrentStep("personal");
    else if (currentStep === "confirmation") setCurrentStep("address");
  }, [currentStep]);

  const handleSubmit = useCallback(() => {
    const pErr = validatePersonal(formData.personal);
    const aErr = validateAddress(formData.address);
    if (Object.keys(pErr).length > 0 || Object.keys(aErr).length > 0) {
      setErrors({ personal: pErr, address: aErr });
      setShowErrors(true);
      if (Object.keys(pErr).length > 0) setCurrentStep("personal");
      else setCurrentStep("address");
      return;
    }
    setSubmitted(true);
  }, [formData]);

  const renderInput = (
    step: "personal" | "address",
    field: string,
    label: string,
    type: string = "text",
    placeholder: string = ""
  ) => {
    const fieldErrors = errors[step]?.[field] ?? [];
    const hasError = showErrors && fieldErrors.length > 0;
    return (
      <div className="fw-field-group" key={field}>
        <label className="fw-label">{label}</label>
        <input
          className={`fw-input ${hasError ? "fw-input-error" : ""}`}
          type={type}
          placeholder={placeholder}
          value={(formData[step] as any)[field]}
          onChange={(e) => updateField(step, field, e.target.value)}
        />
        <div className="fw-error">{hasError ? fieldErrors[0] : ""}</div>
      </div>
    );
  };

  if (submitted) {
    return (
      <div className="fw-wrapper">
        <div className="fw-success">
          <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
          <h2>Submission Successful!</h2>
          <p style={{ color: "#555" }}>Thank you, {formData.personal.name}. Your information has been submitted.</p>
          <button className="fw-btn fw-btn-primary" style={{ marginTop: 16 }} onClick={() => { setSubmitted(false); setCurrentStep("personal"); setFormData({ personal: { name: "", email: "", phone: "" }, address: { street: "", city: "", state: "", zipCode: "" } }); }}>
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fw-wrapper">
      {/* Progress */}
      <div className="fw-progress">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.id}>
            {i > 0 && (
              <div className={`fw-connector ${i <= stepIndex ? "fw-connector-active" : "fw-connector-pending"}`} />
            )}
            <div
              className={`fw-step ${i < stepIndex ? "fw-step-done" : i === stepIndex ? "fw-step-active" : "fw-step-pending"}`}
            >
              {i < stepIndex ? "✓" : s.num}
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* Step 1 */}
      {currentStep === "personal" && (
        <div>
          <div className="fw-title">Personal Information</div>
          <div className="fw-subtitle">Please provide your basic details.</div>
          {renderInput("personal", "name", "Full Name", "text", "John Doe")}
          {renderInput("personal", "email", "Email Address", "email", "john@example.com")}
          {renderInput("personal", "phone", "Phone Number", "tel", "(555) 123-4567")}
        </div>
      )}

      {/* Step 2 */}
      {currentStep === "address" && (
        <div>
          <div className="fw-title">Address Information</div>
          <div className="fw-subtitle">Where should we reach you?</div>
          {renderInput("address", "street", "Street Address", "text", "123 Main St")}
          {renderInput("address", "city", "City", "text", "Springfield")}
          {renderInput("address", "state", "State (2-letter code)", "text", "IL")}
          {renderInput("address", "zipCode", "Zip Code", "text", "62704")}
        </div>
      )}

      {/* Step 3 */}
      {currentStep === "confirmation" && (
        <div>
          <div className="fw-title">Review &amp; Confirm</div>
          <div className="fw-subtitle">Please review the information below before submitting.</div>
          <div className="fw-review-section">
            <div className="fw-review-title">Personal Information</div>
            {[
              ["Name", formData.personal.name],
              ["Email", formData.personal.email],
              ["Phone", formData.personal.phone],
            ].map(([label, val]) => (
              <div className="fw-review-row" key={label}>
                <span className="fw-review-label">{label}</span>
                <span className="fw-review-value">{val}</span>
              </div>
            ))}
          </div>
          <div className="fw-review-section">
            <div className="fw-review-title">Address Information</div>
            {[
              ["Street", formData.address.street],
              ["City", formData.address.city],
              ["State", formData.address.state],
              ["Zip Code", formData.address.zipCode],
            ].map(([label, val]) => (
              <div className="fw-review-row" key={label}>
                <span className="fw-review-label">{label}</span>
                <span className="fw-review-value">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="fw-buttons">
        {stepIndex > 0 ? (
          <button className="fw-btn fw-btn-secondary" onClick={goBack}>
            ← Back
          </button>
        ) : (
          <div />
        )}
        {currentStep === "confirmation" ? (
          <button className="fw-btn fw-btn-submit" onClick={handleSubmit}>
            Submit ✓
          </button>
        ) : (
          <button className="fw-btn fw-btn-primary" onClick={goNext}>
            Next →
          </button>
        )}
      </div>
    </div>
  );
};

export default FormWizard;
```
