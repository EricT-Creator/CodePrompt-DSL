import React, { useState } from "react";

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

const containerStyle: React.CSSProperties = {
  maxWidth: 520,
  margin: "40px auto",
  fontFamily: "system-ui, -apple-system, sans-serif",
  padding: 24,
  border: "1px solid #e0e0e0",
  borderRadius: 10,
  backgroundColor: "#fff",
  boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
};

const stepIndicatorStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: 8,
  marginBottom: 28,
};

const stepDotStyle = (active: boolean, completed: boolean): React.CSSProperties => ({
  width: 36,
  height: 36,
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: 14,
  fontWeight: 600,
  backgroundColor: active ? "#1a1a2e" : completed ? "#2ecc71" : "#e0e0e0",
  color: active || completed ? "#fff" : "#999",
  transition: "all 0.2s",
});

const stepLineStyle: React.CSSProperties = {
  width: 40,
  height: 2,
  backgroundColor: "#e0e0e0",
  alignSelf: "center",
};

const titleStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 600,
  marginBottom: 20,
  color: "#1a1a2e",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 14,
  fontWeight: 500,
  marginBottom: 6,
  color: "#333",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  fontSize: 14,
  border: "1px solid #d0d0d0",
  borderRadius: 6,
  boxSizing: "border-box",
  outline: "none",
  transition: "border-color 0.15s",
};

const inputErrorStyle: React.CSSProperties = {
  ...inputStyle,
  borderColor: "#e74c3c",
};

const errorTextStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#e74c3c",
  marginTop: 4,
};

const fieldGroupStyle: React.CSSProperties = {
  marginBottom: 16,
};

const btnRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: 24,
};

const btnPrimaryStyle: React.CSSProperties = {
  padding: "10px 24px",
  fontSize: 14,
  fontWeight: 600,
  backgroundColor: "#1a1a2e",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  cursor: "pointer",
};

const btnSecondaryStyle: React.CSSProperties = {
  padding: "10px 24px",
  fontSize: 14,
  fontWeight: 600,
  backgroundColor: "#fff",
  color: "#1a1a2e",
  border: "1px solid #1a1a2e",
  borderRadius: 6,
  cursor: "pointer",
};

const reviewRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  padding: "10px 0",
  borderBottom: "1px solid #f0f0f0",
  fontSize: 14,
};

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateStep1(data: PersonalInfo): FieldErrors {
  const errors: FieldErrors = {};
  if (!data.name.trim()) errors.name = "Name is required";
  if (!data.email.trim()) errors.email = "Email is required";
  else if (!validateEmail(data.email)) errors.email = "Invalid email format";
  return errors;
}

function validateStep2(data: AddressInfo): FieldErrors {
  const errors: FieldErrors = {};
  if (!data.street.trim()) errors.street = "Street is required";
  if (!data.city.trim()) errors.city = "City is required";
  if (!data.zip.trim()) errors.zip = "ZIP code is required";
  else if (!/^\d{5}(-\d{4})?$/.test(data.zip.trim())) errors.zip = "Invalid ZIP (use 12345 or 12345-6789)";
  return errors;
}

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState<FormData>({
    personal: { name: "", email: "" },
    address: { street: "", city: "", zip: "" },
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const updatePersonal = (field: keyof PersonalInfo, value: string) => {
    setFormData((prev) => ({
      ...prev,
      personal: { ...prev.personal, [field]: value },
    }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const updateAddress = (field: keyof AddressInfo, value: string) => {
    setFormData((prev) => ({
      ...prev,
      address: { ...prev.address, [field]: value },
    }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const goNext = () => {
    if (step === 0) {
      const errs = validateStep1(formData.personal);
      if (Object.keys(errs).length > 0) {
        setErrors(errs);
        return;
      }
    } else if (step === 1) {
      const errs = validateStep2(formData.address);
      if (Object.keys(errs).length > 0) {
        setErrors(errs);
        return;
      }
    }
    setErrors({});
    setStep((s) => s + 1);
  };

  const goBack = () => {
    setErrors({});
    setStep((s) => s - 1);
  };

  const handleSubmit = () => {
    console.log("Form submitted:", formData);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
          <h2 style={{ fontSize: 22, color: "#2ecc71", marginBottom: 8 }}>Submitted!</h2>
          <p style={{ color: "#666", fontSize: 14 }}>Data logged to console.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={stepIndicatorStyle}>
        {[1, 2, 3].map((n, i) => (
          <React.Fragment key={n}>
            {i > 0 && <div style={stepLineStyle} />}
            <div style={stepDotStyle(step === i, step > i)}>
              {step > i ? "✓" : n}
            </div>
          </React.Fragment>
        ))}
      </div>

      {step === 0 && (
        <div>
          <h3 style={titleStyle}>Personal Information</h3>
          <div style={fieldGroupStyle}>
            <label style={labelStyle}>Name</label>
            <input
              style={errors.name ? inputErrorStyle : inputStyle}
              value={formData.personal.name}
              onChange={(e) => updatePersonal("name", e.target.value)}
              placeholder="John Doe"
            />
            {errors.name && <div style={errorTextStyle}>{errors.name}</div>}
          </div>
          <div style={fieldGroupStyle}>
            <label style={labelStyle}>Email</label>
            <input
              style={errors.email ? inputErrorStyle : inputStyle}
              value={formData.personal.email}
              onChange={(e) => updatePersonal("email", e.target.value)}
              placeholder="john@example.com"
            />
            {errors.email && <div style={errorTextStyle}>{errors.email}</div>}
          </div>
        </div>
      )}

      {step === 1 && (
        <div>
          <h3 style={titleStyle}>Address</h3>
          <div style={fieldGroupStyle}>
            <label style={labelStyle}>Street</label>
            <input
              style={errors.street ? inputErrorStyle : inputStyle}
              value={formData.address.street}
              onChange={(e) => updateAddress("street", e.target.value)}
              placeholder="123 Main St"
            />
            {errors.street && <div style={errorTextStyle}>{errors.street}</div>}
          </div>
          <div style={fieldGroupStyle}>
            <label style={labelStyle}>City</label>
            <input
              style={errors.city ? inputErrorStyle : inputStyle}
              value={formData.address.city}
              onChange={(e) => updateAddress("city", e.target.value)}
              placeholder="Springfield"
            />
            {errors.city && <div style={errorTextStyle}>{errors.city}</div>}
          </div>
          <div style={fieldGroupStyle}>
            <label style={labelStyle}>ZIP Code</label>
            <input
              style={errors.zip ? inputErrorStyle : inputStyle}
              value={formData.address.zip}
              onChange={(e) => updateAddress("zip", e.target.value)}
              placeholder="12345"
            />
            {errors.zip && <div style={errorTextStyle}>{errors.zip}</div>}
          </div>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3 style={titleStyle}>Review & Submit</h3>
          <div style={{ backgroundColor: "#f9f9fb", padding: 16, borderRadius: 8, marginBottom: 8 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: "#888", marginBottom: 8, textTransform: "uppercase" }}>
              Personal
            </div>
            <div style={reviewRowStyle}>
              <span style={{ color: "#666" }}>Name</span>
              <span style={{ fontWeight: 500 }}>{formData.personal.name}</span>
            </div>
            <div style={reviewRowStyle}>
              <span style={{ color: "#666" }}>Email</span>
              <span style={{ fontWeight: 500 }}>{formData.personal.email}</span>
            </div>
          </div>
          <div style={{ backgroundColor: "#f9f9fb", padding: 16, borderRadius: 8 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: "#888", marginBottom: 8, textTransform: "uppercase" }}>
              Address
            </div>
            <div style={reviewRowStyle}>
              <span style={{ color: "#666" }}>Street</span>
              <span style={{ fontWeight: 500 }}>{formData.address.street}</span>
            </div>
            <div style={reviewRowStyle}>
              <span style={{ color: "#666" }}>City</span>
              <span style={{ fontWeight: 500 }}>{formData.address.city}</span>
            </div>
            <div style={{ ...reviewRowStyle, borderBottom: "none" }}>
              <span style={{ color: "#666" }}>ZIP</span>
              <span style={{ fontWeight: 500 }}>{formData.address.zip}</span>
            </div>
          </div>
        </div>
      )}

      <div style={btnRowStyle}>
        {step > 0 ? (
          <button style={btnSecondaryStyle} onClick={goBack}>
            ← Back
          </button>
        ) : (
          <div />
        )}
        {step < 2 ? (
          <button style={btnPrimaryStyle} onClick={goNext}>
            Next →
          </button>
        ) : (
          <button style={{ ...btnPrimaryStyle, backgroundColor: "#2ecc71" }} onClick={handleSubmit}>
            Submit ✓
          </button>
        )}
      </div>
    </div>
  );
}
