import React, { useMemo, useState } from "react";

type FormData = {
  name: string;
  email: string;
  street: string;
  city: string;
  zipCode: string;
};

type Errors = Partial<Record<keyof FormData, string>>;

const initialData: FormData = {
  name: "",
  email: "",
  street: "",
  city: "",
  zipCode: "",
};

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function MultiStepFormWizard(): JSX.Element {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(initialData);
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);

  const progress = useMemo(() => `${Math.round((step / 3) * 100)}%`, [step]);

  const updateField = (field: keyof FormData, value: string) => {
    setFormData((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setSubmitted(false);
  };

  const validateStep = (currentStep: number): boolean => {
    const nextErrors: Errors = {};

    if (currentStep === 1) {
      if (!formData.name.trim()) {
        nextErrors.name = "Name is required.";
      }
      if (!formData.email.trim()) {
        nextErrors.email = "Email is required.";
      } else if (!validateEmail(formData.email)) {
        nextErrors.email = "Please enter a valid email address.";
      }
    }

    if (currentStep === 2) {
      if (!formData.street.trim()) {
        nextErrors.street = "Street is required.";
      }
      if (!formData.city.trim()) {
        nextErrors.city = "City is required.";
      }
      if (!formData.zipCode.trim()) {
        nextErrors.zipCode = "ZIP code is required.";
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep((current) => Math.min(current + 1, 3));
    }
  };

  const handleBack = () => {
    setStep((current) => Math.max(current - 1, 1));
  };

  const handleSubmit = () => {
    if (!validateStep(1) || !validateStep(2)) {
      setStep(!validateStep(1) ? 1 : 2);
      return;
    }

    console.log("Submitted form data:", formData);
    setSubmitted(true);
  };

  return (
    <div className="wizard-root">
      <style>{`
        .wizard-root {
          min-height: 100%;
          background: linear-gradient(180deg, #f8fafc 0%, #e0f2fe 100%);
          padding: 24px;
          font-family: Arial, Helvetica, sans-serif;
          color: #0f172a;
        }
        .wizard-card {
          max-width: 760px;
          margin: 0 auto;
          background: #ffffff;
          border-radius: 20px;
          border: 1px solid #dbeafe;
          box-shadow: 0 24px 50px rgba(15, 23, 42, 0.08);
          overflow: hidden;
        }
        .wizard-header {
          padding: 28px 28px 18px;
          border-bottom: 1px solid #e2e8f0;
        }
        .wizard-header h1 {
          margin: 0 0 10px;
          font-size: 30px;
        }
        .wizard-header p {
          margin: 0;
          color: #475569;
          line-height: 1.6;
        }
        .wizard-progress-track {
          margin-top: 18px;
          height: 10px;
          border-radius: 999px;
          background: #e2e8f0;
          overflow: hidden;
        }
        .wizard-progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #2563eb, #0ea5e9);
          transition: width 0.2s ease;
        }
        .wizard-steps {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          padding: 18px 28px 0;
        }
        .wizard-step {
          border-radius: 14px;
          border: 1px solid #cbd5e1;
          padding: 14px;
          background: #f8fafc;
          font-size: 14px;
        }
        .wizard-step.active {
          border-color: #60a5fa;
          background: #dbeafe;
        }
        .wizard-body {
          padding: 28px;
          display: grid;
          gap: 18px;
        }
        .field-group {
          display: grid;
          gap: 8px;
        }
        .field-group label {
          font-weight: 700;
          color: #334155;
        }
        .field-group input {
          border: 1px solid #cbd5e1;
          border-radius: 12px;
          padding: 12px 14px;
          font-size: 15px;
          transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }
        .field-group input:focus {
          outline: none;
          border-color: #2563eb;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
        }
        .field-group .error {
          color: #dc2626;
          font-size: 13px;
        }
        .review-grid {
          display: grid;
          gap: 12px;
        }
        .review-item {
          border: 1px solid #dbeafe;
          border-radius: 14px;
          padding: 14px 16px;
          background: #f8fbff;
        }
        .review-item strong {
          display: block;
          margin-bottom: 6px;
          color: #1e3a8a;
        }
        .wizard-footer {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding: 0 28px 28px;
        }
        .button {
          border: none;
          border-radius: 12px;
          padding: 12px 18px;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
          transition: transform 0.15s ease, opacity 0.15s ease;
        }
        .button:hover {
          transform: translateY(-1px);
        }
        .button.secondary {
          background: #e2e8f0;
          color: #0f172a;
        }
        .button.primary {
          background: linear-gradient(90deg, #2563eb, #0ea5e9);
          color: #ffffff;
        }
        .success-message {
          margin: 0 28px 24px;
          padding: 14px 16px;
          border-radius: 14px;
          background: #ecfdf5;
          border: 1px solid #86efac;
          color: #166534;
          font-weight: 700;
        }
        @media (max-width: 640px) {
          .wizard-root {
            padding: 16px;
          }
          .wizard-steps {
            grid-template-columns: 1fr;
          }
          .wizard-footer {
            flex-direction: column;
          }
          .button {
            width: 100%;
          }
        }
      `}</style>

      <div className="wizard-card">
        <div className="wizard-header">
          <h1>Multi-Step Form Wizard</h1>
          <p>Complete each step in order. Validation happens before you can move forward.</p>
          <div className="wizard-progress-track" aria-hidden="true">
            <div className="wizard-progress-fill" style={{ width: progress }} />
          </div>
        </div>

        <div className="wizard-steps">
          <div className={`wizard-step ${step === 1 ? "active" : ""}`.trim()}>
            <strong>Step 1</strong>
            <div>Personal info</div>
          </div>
          <div className={`wizard-step ${step === 2 ? "active" : ""}`.trim()}>
            <strong>Step 2</strong>
            <div>Address</div>
          </div>
          <div className={`wizard-step ${step === 3 ? "active" : ""}`.trim()}>
            <strong>Step 3</strong>
            <div>Review &amp; confirm</div>
          </div>
        </div>

        <div className="wizard-body">
          {step === 1 ? (
            <>
              <div className="field-group">
                <label htmlFor="name">Name</label>
                <input
                  id="name"
                  value={formData.name}
                  onChange={(event) => updateField("name", event.target.value)}
                  placeholder="Enter your full name"
                />
                {errors.name ? <span className="error">{errors.name}</span> : null}
              </div>
              <div className="field-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  value={formData.email}
                  onChange={(event) => updateField("email", event.target.value)}
                  placeholder="name@example.com"
                />
                {errors.email ? <span className="error">{errors.email}</span> : null}
              </div>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <div className="field-group">
                <label htmlFor="street">Street</label>
                <input
                  id="street"
                  value={formData.street}
                  onChange={(event) => updateField("street", event.target.value)}
                  placeholder="123 Main Street"
                />
                {errors.street ? <span className="error">{errors.street}</span> : null}
              </div>
              <div className="field-group">
                <label htmlFor="city">City</label>
                <input
                  id="city"
                  value={formData.city}
                  onChange={(event) => updateField("city", event.target.value)}
                  placeholder="City"
                />
                {errors.city ? <span className="error">{errors.city}</span> : null}
              </div>
              <div className="field-group">
                <label htmlFor="zipCode">ZIP Code</label>
                <input
                  id="zipCode"
                  value={formData.zipCode}
                  onChange={(event) => updateField("zipCode", event.target.value)}
                  placeholder="ZIP Code"
                />
                {errors.zipCode ? <span className="error">{errors.zipCode}</span> : null}
              </div>
            </>
          ) : null}

          {step === 3 ? (
            <div className="review-grid">
              <div className="review-item">
                <strong>Name</strong>
                <span>{formData.name || "—"}</span>
              </div>
              <div className="review-item">
                <strong>Email</strong>
                <span>{formData.email || "—"}</span>
              </div>
              <div className="review-item">
                <strong>Street</strong>
                <span>{formData.street || "—"}</span>
              </div>
              <div className="review-item">
                <strong>City</strong>
                <span>{formData.city || "—"}</span>
              </div>
              <div className="review-item">
                <strong>ZIP Code</strong>
                <span>{formData.zipCode || "—"}</span>
              </div>
            </div>
          ) : null}
        </div>

        {submitted ? <div className="success-message">Submitted. Check the console for the full payload.</div> : null}

        <div className="wizard-footer">
          <button type="button" className="button secondary" onClick={handleBack} disabled={step === 1}>
            Back
          </button>
          {step < 3 ? (
            <button type="button" className="button primary" onClick={handleNext}>
              Next
            </button>
          ) : (
            <button type="button" className="button primary" onClick={handleSubmit}>
              Confirm &amp; Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
