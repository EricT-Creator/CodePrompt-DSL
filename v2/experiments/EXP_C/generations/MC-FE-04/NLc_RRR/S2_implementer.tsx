import React, { useState, useCallback } from "react";

// ---- Types ----

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

// ---- Styles ----

const css: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: "600px",
    margin: "40px auto",
    padding: "0 20px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#333",
    textAlign: "center" as const,
    marginBottom: "24px",
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: "12px",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
    padding: "32px",
  },
  stepIndicator: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "32px",
  },
  stepCircle: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "14px",
    fontWeight: "600",
    transition: "all 0.3s",
  },
  stepLine: {
    width: "60px",
    height: "2px",
    margin: "0 8px",
  },
  fieldGroup: {
    marginBottom: "20px",
  },
  label: {
    display: "block",
    fontSize: "14px",
    fontWeight: "500",
    color: "#555",
    marginBottom: "6px",
  },
  input: {
    width: "100%",
    padding: "10px 12px",
    border: "1px solid #ddd",
    borderRadius: "6px",
    fontSize: "14px",
    boxSizing: "border-box" as const,
    transition: "border-color 0.2s",
  },
  inputError: {
    width: "100%",
    padding: "10px 12px",
    border: "1px solid #e53935",
    borderRadius: "6px",
    fontSize: "14px",
    boxSizing: "border-box" as const,
    backgroundColor: "#fff5f5",
  },
  errorText: {
    color: "#e53935",
    fontSize: "12px",
    marginTop: "4px",
  },
  buttonRow: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: "28px",
    gap: "12px",
  },
  primaryButton: {
    padding: "10px 24px",
    backgroundColor: "#4a90d9",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "14px",
    fontWeight: "500",
    cursor: "pointer",
  },
  secondaryButton: {
    padding: "10px 24px",
    backgroundColor: "#fff",
    color: "#555",
    border: "1px solid #ddd",
    borderRadius: "6px",
    fontSize: "14px",
    fontWeight: "500",
    cursor: "pointer",
  },
  summarySection: {
    marginBottom: "20px",
  },
  summaryTitle: {
    fontSize: "15px",
    fontWeight: "600",
    color: "#333",
    marginBottom: "8px",
    borderBottom: "1px solid #eee",
    paddingBottom: "4px",
  },
  summaryRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "6px 0",
    fontSize: "14px",
  },
  summaryLabel: {
    color: "#777",
  },
  summaryValue: {
    color: "#333",
    fontWeight: "500",
  },
  successContainer: {
    textAlign: "center" as const,
    padding: "40px 0",
  },
  successIcon: {
    fontSize: "48px",
    marginBottom: "16px",
  },
  successText: {
    fontSize: "20px",
    fontWeight: "600",
    color: "#2e7d32",
    marginBottom: "8px",
  },
  successSubtext: {
    fontSize: "14px",
    color: "#777",
  },
};

// ---- Validation ----

function validateStep(step: 1 | 2 | 3, data: FormData): FormErrors {
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
    if (!data.address.street || data.address.street.trim().length === 0) {
      errors.street = "Street address is required";
    }
    if (!data.address.city || data.address.city.trim().length < 2) {
      errors.city = "City is required";
    }
    if (!data.address.state || data.address.state.trim().length === 0) {
      errors.state = "State is required";
    }
    if (!data.address.zip || !/^\d{5}(-\d{4})?$/.test(data.address.zip)) {
      errors.zip = "Valid ZIP code is required";
    }
  }

  return errors;
}

// ---- FieldError Component ----

const FieldError: React.FC<{ message?: string }> = ({ message }) => {
  if (!message) return null;
  return <div style={css.errorText}>{message}</div>;
};

// ---- Step Indicator ----

const StepIndicator: React.FC<{ currentStep: 1 | 2 | 3 }> = ({ currentStep }) => {
  const steps = [1, 2, 3];
  return (
    <div style={css.stepIndicator}>
      {steps.map((step, i) => (
        <React.Fragment key={step}>
          <div
            style={{
              ...css.stepCircle,
              backgroundColor: step <= currentStep ? "#4a90d9" : "#e0e0e0",
              color: step <= currentStep ? "#fff" : "#999",
            }}
          >
            {step <= currentStep && step < currentStep ? "✓" : step}
          </div>
          {i < steps.length - 1 && (
            <div
              style={{
                ...css.stepLine,
                backgroundColor: step < currentStep ? "#4a90d9" : "#e0e0e0",
              }}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

// ---- Step Components ----

const StepPersonal: React.FC<{
  data: PersonalInfo;
  errors: FormErrors;
  onChange: (field: string, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div>
    <div style={css.fieldGroup}>
      <label style={css.label}>Name</label>
      <input
        style={errors.name ? css.inputError : css.input}
        value={data.name}
        onChange={(e) => onChange("name", e.target.value)}
        placeholder="Enter your name"
      />
      <FieldError message={errors.name} />
    </div>
    <div style={css.fieldGroup}>
      <label style={css.label}>Email</label>
      <input
        style={errors.email ? css.inputError : css.input}
        value={data.email}
        onChange={(e) => onChange("email", e.target.value)}
        placeholder="Enter your email"
        type="email"
      />
      <FieldError message={errors.email} />
    </div>
    <div style={css.fieldGroup}>
      <label style={css.label}>Phone</label>
      <input
        style={errors.phone ? css.inputError : css.input}
        value={data.phone}
        onChange={(e) => onChange("phone", e.target.value)}
        placeholder="Enter your phone number"
        type="tel"
      />
      <FieldError message={errors.phone} />
    </div>
  </div>
);

const StepAddress: React.FC<{
  data: AddressInfo;
  errors: FormErrors;
  onChange: (field: string, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div>
    <div style={css.fieldGroup}>
      <label style={css.label}>Street</label>
      <input
        style={errors.street ? css.inputError : css.input}
        value={data.street}
        onChange={(e) => onChange("street", e.target.value)}
        placeholder="Enter street address"
      />
      <FieldError message={errors.street} />
    </div>
    <div style={css.fieldGroup}>
      <label style={css.label}>City</label>
      <input
        style={errors.city ? css.inputError : css.input}
        value={data.city}
        onChange={(e) => onChange("city", e.target.value)}
        placeholder="Enter city"
      />
      <FieldError message={errors.city} />
    </div>
    <div style={css.fieldGroup}>
      <label style={css.label}>State</label>
      <input
        style={errors.state ? css.inputError : css.input}
        value={data.state}
        onChange={(e) => onChange("state", e.target.value)}
        placeholder="Enter state"
      />
      <FieldError message={errors.state} />
    </div>
    <div style={css.fieldGroup}>
      <label style={css.label}>ZIP Code</label>
      <input
        style={errors.zip ? css.inputError : css.input}
        value={data.zip}
        onChange={(e) => onChange("zip", e.target.value)}
        placeholder="Enter ZIP code"
      />
      <FieldError message={errors.zip} />
    </div>
  </div>
);

const StepConfirmation: React.FC<{ data: FormData }> = ({ data }) => (
  <div>
    <div style={css.summarySection}>
      <div style={css.summaryTitle}>Personal Information</div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>Name</span>
        <span style={css.summaryValue}>{data.personal.name}</span>
      </div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>Email</span>
        <span style={css.summaryValue}>{data.personal.email}</span>
      </div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>Phone</span>
        <span style={css.summaryValue}>{data.personal.phone}</span>
      </div>
    </div>
    <div style={css.summarySection}>
      <div style={css.summaryTitle}>Address Details</div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>Street</span>
        <span style={css.summaryValue}>{data.address.street}</span>
      </div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>City</span>
        <span style={css.summaryValue}>{data.address.city}</span>
      </div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>State</span>
        <span style={css.summaryValue}>{data.address.state}</span>
      </div>
      <div style={css.summaryRow}>
        <span style={css.summaryLabel}>ZIP</span>
        <span style={css.summaryValue}>{data.address.zip}</span>
      </div>
    </div>
  </div>
);

// ---- Main Component ----

const FormWizard: React.FC = () => {
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
    const validationErrors = validateStep(currentStep, formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    setErrors({});
    setCurrentStep((prev) => Math.min(prev + 1, 3) as 1 | 2 | 3);
  }, [currentStep, formData]);

  const handleBack = useCallback(() => {
    setErrors({});
    setCurrentStep((prev) => Math.max(prev - 1, 1) as 1 | 2 | 3);
  }, []);

  const handleSubmit = useCallback(() => {
    console.log("Form submitted:", formData);
    setSubmitted(true);
  }, [formData]);

  if (submitted) {
    return (
      <div style={css.container}>
        <div style={css.card}>
          <div style={css.successContainer}>
            <div style={css.successIcon}>✅</div>
            <div style={css.successText}>Form Submitted Successfully!</div>
            <div style={css.successSubtext}>
              Thank you, {formData.personal.name}. Your information has been recorded.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const stepTitles = ["Personal Information", "Address Details", "Confirmation"];

  return (
    <div style={css.container}>
      <div style={css.title}>Registration Wizard</div>
      <div style={css.card}>
        <StepIndicator currentStep={currentStep} />
        <h3 style={{ fontSize: "18px", color: "#333", marginBottom: "20px" }}>
          Step {currentStep}: {stepTitles[currentStep - 1]}
        </h3>

        {currentStep === 1 && (
          <StepPersonal data={formData.personal} errors={errors} onChange={handlePersonalChange} />
        )}
        {currentStep === 2 && (
          <StepAddress data={formData.address} errors={errors} onChange={handleAddressChange} />
        )}
        {currentStep === 3 && <StepConfirmation data={formData} />}

        <div style={css.buttonRow}>
          {currentStep > 1 ? (
            <button style={css.secondaryButton} onClick={handleBack}>
              ← Back
            </button>
          ) : (
            <div />
          )}
          {currentStep < 3 ? (
            <button style={css.primaryButton} onClick={handleNext}>
              Next →
            </button>
          ) : (
            <button style={css.primaryButton} onClick={handleSubmit}>
              Submit ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FormWizard;
