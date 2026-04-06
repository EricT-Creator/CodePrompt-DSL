import React, { useMemo, useState } from "react";

type FormValues = {
  name: string;
  email: string;
  street: string;
  city: string;
  zip: string;
};

type ErrorMap = Partial<Record<keyof FormValues, string>>;

const initialValues: FormValues = {
  name: "",
  email: "",
  street: "",
  city: "",
  zip: "",
};

const styles = `
  .wizard-page {
    min-height: 100vh;
    background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
    padding: 28px 16px;
    box-sizing: border-box;
    font-family: Arial, Helvetica, sans-serif;
    color: #0f172a;
  }

  .wizard-shell {
    max-width: 760px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-radius: 24px;
    box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
    overflow: hidden;
  }

  .wizard-header {
    padding: 24px 24px 12px;
    border-bottom: 1px solid #e2e8f0;
  }

  .wizard-title {
    margin: 0 0 8px;
    font-size: 30px;
  }

  .wizard-subtitle {
    margin: 0;
    font-size: 14px;
    line-height: 1.6;
    color: #475569;
  }

  .wizard-steps {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    padding: 18px 24px 0;
  }

  .wizard-step {
    border: 1px solid #cbd5e1;
    border-radius: 16px;
    padding: 12px;
    background: #f8fafc;
  }

  .wizard-step.active {
    border-color: #2563eb;
    background: #eff6ff;
  }

  .wizard-step-index {
    width: 28px;
    height: 28px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #dbeafe;
    color: #1d4ed8;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .wizard-step-label {
    font-size: 14px;
    font-weight: 700;
    margin: 0 0 4px;
  }

  .wizard-step-note {
    margin: 0;
    color: #64748b;
    font-size: 12px;
    line-height: 1.5;
  }

  .wizard-body {
    padding: 24px;
  }

  .wizard-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px 16px;
  }

  .wizard-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .wizard-field.full {
    grid-column: span 2;
  }

  .wizard-label {
    font-size: 14px;
    font-weight: 700;
    color: #334155;
  }

  .wizard-input {
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 14px;
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }

  .wizard-input:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
  }

  .wizard-input.error {
    border-color: #dc2626;
    background: #fef2f2;
  }

  .wizard-error {
    margin: 0;
    color: #dc2626;
    font-size: 12px;
    line-height: 1.5;
  }

  .wizard-review {
    display: grid;
    gap: 12px;
  }

  .review-card {
    border: 1px solid #dbeafe;
    border-radius: 16px;
    padding: 16px;
    background: #f8fafc;
  }

  .review-title {
    margin: 0 0 10px;
    font-size: 16px;
    color: #1d4ed8;
  }

  .review-row {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 0;
    border-bottom: 1px dashed #cbd5e1;
    font-size: 14px;
  }

  .review-row:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  .wizard-actions {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 0 24px 24px;
  }

  .action-left,
  .action-right {
    display: flex;
    gap: 12px;
  }

  .wizard-button {
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 12px 18px;
    background: #ffffff;
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: background 120ms ease, border-color 120ms ease, transform 120ms ease;
  }

  .wizard-button:hover {
    background: #eff6ff;
    border-color: #60a5fa;
    transform: translateY(-1px);
  }

  .wizard-button.primary {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
  }

  .wizard-button.primary:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
  }

  @media (max-width: 720px) {
    .wizard-steps,
    .wizard-grid {
      grid-template-columns: 1fr;
    }

    .wizard-field.full {
      grid-column: span 1;
    }

    .wizard-actions {
      flex-direction: column;
    }

    .action-left,
    .action-right {
      width: 100%;
    }

    .wizard-button {
      flex: 1;
    }
  }
`;

function validateStep(step: number, values: FormValues): ErrorMap {
  const errors: ErrorMap = {};

  if (step === 0) {
    if (values.name.trim().length < 2) {
      errors.name = "Name must contain at least 2 characters.";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
      errors.email = "Please enter a valid email address.";
    }
  }

  if (step === 1) {
    if (!values.street.trim()) {
      errors.street = "Street is required.";
    }
    if (!values.city.trim()) {
      errors.city = "City is required.";
    }
    if (!/^[A-Za-z0-9\-\s]{4,10}$/.test(values.zip.trim())) {
      errors.zip = "ZIP must be 4-10 letters, numbers, spaces, or dashes.";
    }
  }

  return errors;
}

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<FormValues>(initialValues);
  const [errors, setErrors] = useState<ErrorMap>({});

  const steps = useMemo(
    () => [
      { label: "Personal", note: "Name and email" },
      { label: "Address", note: "Street, city, ZIP" },
      { label: "Review", note: "Confirm and submit" },
    ],
    [],
  );

  const updateField = (key: keyof FormValues, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const goNext = () => {
    const stepErrors = validateStep(step, values);
    setErrors(stepErrors);
    if (Object.keys(stepErrors).length > 0) {
      return;
    }
    setStep((current) => Math.min(current + 1, steps.length - 1));
  };

  const goBack = () => {
    setStep((current) => Math.max(current - 1, 0));
  };

  const handleSubmit = () => {
    const stepOneErrors = validateStep(0, values);
    const stepTwoErrors = validateStep(1, values);
    const nextErrors = { ...stepOneErrors, ...stepTwoErrors };
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    console.log("Wizard submission", values);
    alert("Form submitted. Check the console for the payload.");
  };

  return (
    <div className="wizard-page">
      <style>{styles}</style>
      <div className="wizard-shell">
        <div className="wizard-header">
          <h1 className="wizard-title">Multi-Step Form Wizard</h1>
          <p className="wizard-subtitle">
            Step-by-step validation happens at runtime, data stays intact when navigating back, and the
            final review step submits the collected values to the console.
          </p>
        </div>

        <div className="wizard-steps">
          {steps.map((item, index) => (
            <div key={item.label} className={`wizard-step ${step === index ? "active" : ""}`}>
              <div className="wizard-step-index">{index + 1}</div>
              <p className="wizard-step-label">{item.label}</p>
              <p className="wizard-step-note">{item.note}</p>
            </div>
          ))}
        </div>

        <div className="wizard-body">
          {step === 0 ? (
            <div className="wizard-grid">
              <div className="wizard-field">
                <label className="wizard-label" htmlFor="name">
                  Name
                </label>
                <input
                  id="name"
                  className={`wizard-input ${errors.name ? "error" : ""}`}
                  value={values.name}
                  onChange={(event) => updateField("name", event.currentTarget.value)}
                  placeholder="Ada Lovelace"
                />
                {errors.name ? <p className="wizard-error">{errors.name}</p> : null}
              </div>

              <div className="wizard-field">
                <label className="wizard-label" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  className={`wizard-input ${errors.email ? "error" : ""}`}
                  value={values.email}
                  onChange={(event) => updateField("email", event.currentTarget.value)}
                  placeholder="ada@example.com"
                />
                {errors.email ? <p className="wizard-error">{errors.email}</p> : null}
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="wizard-grid">
              <div className="wizard-field full">
                <label className="wizard-label" htmlFor="street">
                  Street
                </label>
                <input
                  id="street"
                  className={`wizard-input ${errors.street ? "error" : ""}`}
                  value={values.street}
                  onChange={(event) => updateField("street", event.currentTarget.value)}
                  placeholder="123 Research Avenue"
                />
                {errors.street ? <p className="wizard-error">{errors.street}</p> : null}
              </div>

              <div className="wizard-field">
                <label className="wizard-label" htmlFor="city">
                  City
                </label>
                <input
                  id="city"
                  className={`wizard-input ${errors.city ? "error" : ""}`}
                  value={values.city}
                  onChange={(event) => updateField("city", event.currentTarget.value)}
                  placeholder="London"
                />
                {errors.city ? <p className="wizard-error">{errors.city}</p> : null}
              </div>

              <div className="wizard-field">
                <label className="wizard-label" htmlFor="zip">
                  ZIP
                </label>
                <input
                  id="zip"
                  className={`wizard-input ${errors.zip ? "error" : ""}`}
                  value={values.zip}
                  onChange={(event) => updateField("zip", event.currentTarget.value)}
                  placeholder="12345"
                />
                {errors.zip ? <p className="wizard-error">{errors.zip}</p> : null}
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="wizard-review">
              <div className="review-card">
                <h2 className="review-title">Personal</h2>
                <div className="review-row">
                  <strong>Name</strong>
                  <span>{values.name || "-"}</span>
                </div>
                <div className="review-row">
                  <strong>Email</strong>
                  <span>{values.email || "-"}</span>
                </div>
              </div>

              <div className="review-card">
                <h2 className="review-title">Address</h2>
                <div className="review-row">
                  <strong>Street</strong>
                  <span>{values.street || "-"}</span>
                </div>
                <div className="review-row">
                  <strong>City</strong>
                  <span>{values.city || "-"}</span>
                </div>
                <div className="review-row">
                  <strong>ZIP</strong>
                  <span>{values.zip || "-"}</span>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="wizard-actions">
          <div className="action-left">
            {step > 0 ? (
              <button type="button" className="wizard-button" onClick={goBack}>
                Back
              </button>
            ) : null}
          </div>
          <div className="action-right">
            {step < steps.length - 1 ? (
              <button type="button" className="wizard-button primary" onClick={goNext}>
                Next
              </button>
            ) : (
              <button type="button" className="wizard-button primary" onClick={handleSubmit}>
                Submit
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
