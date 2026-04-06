import React, { useState, useCallback } from "react";

interface PersonalInfo {
  name: string;
  email: string;
}

interface AddressInfo {
  street: string;
  city: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

interface FieldErrors {
  [key: string]: string;
}

const initialFormData: FormData = {
  personal: { name: "", email: "" },
  address: { street: "", city: "", zip: "" },
};

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateStep(step: number, data: FormData): FieldErrors {
  const errors: FieldErrors = {};
  if (step === 0) {
    if (!data.personal.name.trim()) errors.name = "Name is required";
    if (!data.personal.email.trim()) {
      errors.email = "Email is required";
    } else if (!validateEmail(data.personal.email)) {
      errors.email = "Invalid email format";
    }
  }
  if (step === 1) {
    if (!data.address.street.trim()) errors.street = "Street is required";
    if (!data.address.city.trim()) errors.city = "City is required";
    if (!data.address.zip.trim()) errors.zip = "Zip code is required";
  }
  return errors;
}

const STEPS = ["Personal Info", "Address", "Confirm & Submit"];

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const updatePersonal = useCallback((field: keyof PersonalInfo, value: string) => {
    setFormData((prev) => ({
      ...prev,
      personal: { ...prev.personal, [field]: value },
    }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const updateAddress = useCallback((field: keyof AddressInfo, value: string) => {
    setFormData((prev) => ({
      ...prev,
      address: { ...prev.address, [field]: value },
    }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const handleNext = useCallback(() => {
    const validation = validateStep(step, formData);
    if (Object.keys(validation).length > 0) {
      setErrors(validation);
      return;
    }
    setErrors({});
    setStep((s) => s + 1);
  }, [step, formData]);

  const handleBack = useCallback(() => {
    setErrors({});
    setStep((s) => s - 1);
  }, []);

  const handleSubmit = useCallback(() => {
    console.log("Form submitted:", formData);
    setSubmitted(true);
  }, [formData]);

  if (submitted) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h2 style={styles.successTitle}>✅ Submitted Successfully!</h2>
          <p style={styles.successText}>Your data has been logged to the console.</p>
          <button
            style={styles.primaryBtn}
            onClick={() => {
              setSubmitted(false);
              setStep(0);
              setFormData(initialFormData);
            }}
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Multi-Step Form</h2>
        <div style={styles.stepper}>
          {STEPS.map((label, i) => (
            <div key={label} style={styles.stepItem}>
              <div
                style={{
                  ...styles.stepCircle,
                  ...(i <= step ? styles.stepCircleActive : {}),
                }}
              >
                {i < step ? "✓" : i + 1}
              </div>
              <span
                style={{
                  ...styles.stepLabel,
                  ...(i <= step ? { color: "#3498db", fontWeight: 600 } : {}),
                }}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  style={{
                    ...styles.stepLine,
                    ...(i < step ? { backgroundColor: "#3498db" } : {}),
                  }}
                />
              )}
            </div>
          ))}
        </div>

        {step === 0 && (
          <div style={styles.formSection}>
            <label style={styles.label}>Name *</label>
            <input
              style={{
                ...styles.input,
                ...(errors.name ? styles.inputError : {}),
              }}
              value={formData.personal.name}
              onChange={(e) => updatePersonal("name", e.target.value)}
              placeholder="Enter your full name"
            />
            {errors.name && <span style={styles.errorText}>{errors.name}</span>}

            <label style={styles.label}>Email *</label>
            <input
              style={{
                ...styles.input,
                ...(errors.email ? styles.inputError : {}),
              }}
              value={formData.personal.email}
              onChange={(e) => updatePersonal("email", e.target.value)}
              placeholder="your@email.com"
              type="email"
            />
            {errors.email && <span style={styles.errorText}>{errors.email}</span>}
          </div>
        )}

        {step === 1 && (
          <div style={styles.formSection}>
            <label style={styles.label}>Street *</label>
            <input
              style={{
                ...styles.input,
                ...(errors.street ? styles.inputError : {}),
              }}
              value={formData.address.street}
              onChange={(e) => updateAddress("street", e.target.value)}
              placeholder="123 Main St"
            />
            {errors.street && <span style={styles.errorText}>{errors.street}</span>}

            <label style={styles.label}>City *</label>
            <input
              style={{
                ...styles.input,
                ...(errors.city ? styles.inputError : {}),
              }}
              value={formData.address.city}
              onChange={(e) => updateAddress("city", e.target.value)}
              placeholder="New York"
            />
            {errors.city && <span style={styles.errorText}>{errors.city}</span>}

            <label style={styles.label}>Zip Code *</label>
            <input
              style={{
                ...styles.input,
                ...(errors.zip ? styles.inputError : {}),
              }}
              value={formData.address.zip}
              onChange={(e) => updateAddress("zip", e.target.value)}
              placeholder="10001"
            />
            {errors.zip && <span style={styles.errorText}>{errors.zip}</span>}
          </div>
        )}

        {step === 2 && (
          <div style={styles.formSection}>
            <h3 style={styles.reviewTitle}>Review Your Information</h3>
            <div style={styles.reviewGroup}>
              <h4 style={styles.reviewSubtitle}>Personal Info</h4>
              <p style={styles.reviewItem}>
                <strong>Name:</strong> {formData.personal.name}
              </p>
              <p style={styles.reviewItem}>
                <strong>Email:</strong> {formData.personal.email}
              </p>
            </div>
            <div style={styles.reviewGroup}>
              <h4 style={styles.reviewSubtitle}>Address</h4>
              <p style={styles.reviewItem}>
                <strong>Street:</strong> {formData.address.street}
              </p>
              <p style={styles.reviewItem}>
                <strong>City:</strong> {formData.address.city}
              </p>
              <p style={styles.reviewItem}>
                <strong>Zip:</strong> {formData.address.zip}
              </p>
            </div>
          </div>
        )}

        <div style={styles.buttonRow}>
          {step > 0 && (
            <button style={styles.secondaryBtn} onClick={handleBack}>
              ← Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          {step < 2 ? (
            <button style={styles.primaryBtn} onClick={handleNext}>
              Next →
            </button>
          ) : (
            <button style={styles.submitBtn} onClick={handleSubmit}>
              Submit ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "520px",
    margin: "40px auto",
    fontFamily: "system-ui, -apple-system, sans-serif",
    padding: "0 16px",
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: "12px",
    padding: "32px",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
  },
  title: {
    textAlign: "center",
    color: "#333",
    marginBottom: "24px",
  },
  stepper: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: "28px",
    gap: "4px",
  },
  stepItem: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  stepCircle: {
    width: "30px",
    height: "30px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "13px",
    fontWeight: 600,
    backgroundColor: "#e0e0e0",
    color: "#999",
    flexShrink: 0,
  },
  stepCircleActive: {
    backgroundColor: "#3498db",
    color: "#fff",
  },
  stepLabel: {
    fontSize: "12px",
    color: "#999",
    whiteSpace: "nowrap",
  },
  stepLine: {
    width: "30px",
    height: "2px",
    backgroundColor: "#e0e0e0",
    margin: "0 4px",
  },
  formSection: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    marginBottom: "20px",
  },
  label: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#555",
    marginTop: "8px",
  },
  input: {
    padding: "10px 14px",
    border: "1px solid #ddd",
    borderRadius: "6px",
    fontSize: "15px",
    outline: "none",
    transition: "border-color 0.2s",
  },
  inputError: {
    borderColor: "#e74c3c",
  },
  errorText: {
    fontSize: "12px",
    color: "#e74c3c",
  },
  buttonRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginTop: "8px",
  },
  primaryBtn: {
    padding: "10px 24px",
    backgroundColor: "#3498db",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "15px",
    cursor: "pointer",
    fontWeight: 600,
  },
  secondaryBtn: {
    padding: "10px 24px",
    backgroundColor: "#f0f0f0",
    color: "#555",
    border: "1px solid #ddd",
    borderRadius: "6px",
    fontSize: "15px",
    cursor: "pointer",
  },
  submitBtn: {
    padding: "10px 24px",
    backgroundColor: "#2ecc71",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "15px",
    cursor: "pointer",
    fontWeight: 600,
  },
  successTitle: {
    textAlign: "center",
    color: "#2ecc71",
  },
  successText: {
    textAlign: "center",
    color: "#666",
  },
  reviewTitle: {
    color: "#333",
    marginBottom: "12px",
  },
  reviewGroup: {
    marginBottom: "12px",
    padding: "12px",
    backgroundColor: "#f9f9f9",
    borderRadius: "6px",
  },
  reviewSubtitle: {
    color: "#555",
    marginBottom: "6px",
    fontSize: "14px",
  },
  reviewItem: {
    color: "#333",
    margin: "4px 0",
    fontSize: "14px",
  },
};

export default MultiStepFormWizard;
