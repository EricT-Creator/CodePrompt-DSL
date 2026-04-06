import React, { useState, useCallback } from "react";

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

// ── Styles ─────────────────────────────────────────────────────────
const S: Record<string, React.CSSProperties> = {
  wrapper: { fontFamily: "'Segoe UI', Tahoma, sans-serif", maxWidth: 560, margin: "40px auto", padding: 24 },
  progress: { display: "flex", justifyContent: "center", alignItems: "center", gap: 0, marginBottom: 32 },
  step: {
    width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
    fontWeight: 700, fontSize: 14, color: "#fff", transition: "background 0.3s",
  },
  stepActive: { background: "#1a73e8" },
  stepDone: { background: "#34a853" },
  stepPending: { background: "#dadce0", color: "#666" },
  connector: { width: 60, height: 3, transition: "background 0.3s" },
  connectorActive: { background: "#1a73e8" },
  connectorPending: { background: "#dadce0" },
  label: { display: "block", fontWeight: 600, marginBottom: 6, fontSize: 14 },
  input: {
    width: "100%", padding: "10px 12px", border: "1px solid #dadce0", borderRadius: 6,
    fontSize: 14, outline: "none", boxSizing: "border-box" as const, marginBottom: 4,
    transition: "border 0.2s",
  },
  inputError: { borderColor: "#d93025" },
  error: { color: "#d93025", fontSize: 12, marginBottom: 12, minHeight: 16 },
  fieldGroup: { marginBottom: 4 },
  buttons: { display: "flex", justifyContent: "space-between", marginTop: 24 },
  btn: {
    padding: "10px 28px", borderRadius: 6, border: "none", fontSize: 14, fontWeight: 600,
    cursor: "pointer", transition: "background 0.2s",
  },
  btnPrimary: { background: "#1a73e8", color: "#fff" },
  btnSecondary: { background: "#f1f3f4", color: "#333" },
  btnDisabled: { opacity: 0.5, cursor: "not-allowed" },
  reviewSection: { marginBottom: 20 },
  reviewTitle: { fontWeight: 700, fontSize: 15, marginBottom: 8, color: "#333" },
  reviewRow: { display: "flex", padding: "6px 0", borderBottom: "1px solid #f1f3f4" },
  reviewLabel: { width: 100, color: "#666", fontSize: 13 },
  reviewValue: { flex: 1, fontSize: 13, fontWeight: 500 },
  success: {
    textAlign: "center" as const, padding: 32, background: "#e8f5e9", borderRadius: 12,
    color: "#2e7d32",
  },
  title: { marginBottom: 4, fontSize: 20, fontWeight: 700 },
  subtitle: { marginBottom: 24, color: "#666", fontSize: 13 },
};

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
      <div style={S.fieldGroup} key={field}>
        <label style={S.label}>{label}</label>
        <input
          style={{ ...S.input, ...(hasError ? S.inputError : {}) }}
          type={type}
          placeholder={placeholder}
          value={(formData[step] as any)[field]}
          onChange={(e) => updateField(step, field, e.target.value)}
          onFocus={(e) => (e.target.style.borderColor = "#1a73e8")}
          onBlur={(e) => (e.target.style.borderColor = hasError ? "#d93025" : "#dadce0")}
        />
        <div style={S.error}>{hasError ? fieldErrors[0] : ""}</div>
      </div>
    );
  };

  if (submitted) {
    return (
      <div style={S.wrapper}>
        <div style={S.success}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
          <h2>Submission Successful!</h2>
          <p style={{ color: "#555" }}>Thank you, {formData.personal.name}. Your information has been submitted.</p>
          <button style={{ ...S.btn, ...S.btnPrimary, marginTop: 16 }} onClick={() => { setSubmitted(false); setCurrentStep("personal"); setFormData({ personal: { name: "", email: "", phone: "" }, address: { street: "", city: "", state: "", zipCode: "" } }); }}>
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={S.wrapper}>
      {/* Progress */}
      <div style={S.progress}>
        {STEPS.map((s, i) => (
          <React.Fragment key={s.id}>
            {i > 0 && (
              <div style={{ ...S.connector, ...(i <= stepIndex ? S.connectorActive : S.connectorPending) }} />
            )}
            <div
              style={{
                ...S.step,
                ...(i < stepIndex ? S.stepDone : i === stepIndex ? S.stepActive : S.stepPending),
              }}
            >
              {i < stepIndex ? "✓" : s.num}
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* Step 1 */}
      {currentStep === "personal" && (
        <div>
          <div style={S.title}>Personal Information</div>
          <div style={S.subtitle}>Please provide your basic details.</div>
          {renderInput("personal", "name", "Full Name", "text", "John Doe")}
          {renderInput("personal", "email", "Email Address", "email", "john@example.com")}
          {renderInput("personal", "phone", "Phone Number", "tel", "(555) 123-4567")}
        </div>
      )}

      {/* Step 2 */}
      {currentStep === "address" && (
        <div>
          <div style={S.title}>Address Information</div>
          <div style={S.subtitle}>Where should we reach you?</div>
          {renderInput("address", "street", "Street Address", "text", "123 Main St")}
          {renderInput("address", "city", "City", "text", "Springfield")}
          {renderInput("address", "state", "State (2-letter code)", "text", "IL")}
          {renderInput("address", "zipCode", "Zip Code", "text", "62704")}
        </div>
      )}

      {/* Step 3 */}
      {currentStep === "confirmation" && (
        <div>
          <div style={S.title}>Review &amp; Confirm</div>
          <div style={S.subtitle}>Please review the information below before submitting.</div>
          <div style={S.reviewSection}>
            <div style={S.reviewTitle}>Personal Information</div>
            {[
              ["Name", formData.personal.name],
              ["Email", formData.personal.email],
              ["Phone", formData.personal.phone],
            ].map(([label, val]) => (
              <div style={S.reviewRow} key={label}>
                <span style={S.reviewLabel}>{label}</span>
                <span style={S.reviewValue}>{val}</span>
              </div>
            ))}
          </div>
          <div style={S.reviewSection}>
            <div style={S.reviewTitle}>Address Information</div>
            {[
              ["Street", formData.address.street],
              ["City", formData.address.city],
              ["State", formData.address.state],
              ["Zip Code", formData.address.zipCode],
            ].map(([label, val]) => (
              <div style={S.reviewRow} key={label}>
                <span style={S.reviewLabel}>{label}</span>
                <span style={S.reviewValue}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div style={S.buttons}>
        {stepIndex > 0 ? (
          <button style={{ ...S.btn, ...S.btnSecondary }} onClick={goBack}>
            ← Back
          </button>
        ) : (
          <div />
        )}
        {currentStep === "confirmation" ? (
          <button style={{ ...S.btn, background: "#34a853", color: "#fff" }} onClick={handleSubmit}>
            Submit ✓
          </button>
        ) : (
          <button style={{ ...S.btn, ...S.btnPrimary }} onClick={goNext}>
            Next →
          </button>
        )}
      </div>
    </div>
  );
};

export default FormWizard;
