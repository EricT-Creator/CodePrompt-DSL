import React, { useEffect, useMemo, useState } from 'react';

const STYLE_ID = 'fe08-multi-step-form-wizard-styles';

type PersonalInfo = {
  name: string;
  email: string;
};

type AddressInfo = {
  street: string;
  city: string;
  zip: string;
};

type FormState = {
  personal: PersonalInfo;
  address: AddressInfo;
};

type Errors = Partial<Record<'name' | 'email' | 'street' | 'city' | 'zip', string>>;

function ensureStyles() {
  if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) {
    return;
  }
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .wizardShell {
      max-width: 640px;
      margin: 28px auto;
      padding: 28px;
      border-radius: 20px;
      border: 1px solid #d7deea;
      background: #ffffff;
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
      font-family: Arial, Helvetica, sans-serif;
      color: #102a43;
    }
    .wizardTitle {
      margin: 0 0 6px;
      font-size: 30px;
      font-weight: 700;
    }
    .wizardSubtitle {
      margin: 0 0 24px;
      font-size: 14px;
      color: #52667a;
    }
    .wizardSteps {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-bottom: 24px;
    }
    .wizardStep {
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid #d9e2ec;
      background: #f8fbff;
    }
    .wizardStep--active {
      border-color: #2563eb;
      background: #dbeafe;
    }
    .wizardStep--done {
      border-color: #16a34a;
      background: #dcfce7;
    }
    .wizardStepIndex {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      background: #102a43;
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 10px;
    }
    .wizardStepLabel {
      display: block;
      font-size: 13px;
      font-weight: 700;
      color: #102a43;
    }
    .wizardPanel {
      padding: 22px;
      border-radius: 16px;
      border: 1px solid #e7edf5;
      background: #fbfdff;
    }
    .wizardSectionTitle {
      margin: 0 0 18px;
      font-size: 20px;
      font-weight: 700;
    }
    .wizardField {
      margin-bottom: 16px;
    }
    .wizardField:last-child {
      margin-bottom: 0;
    }
    .wizardLabel {
      display: block;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 700;
      color: #243b53;
    }
    .wizardInput {
      width: 100%;
      padding: 12px 14px;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      background: #ffffff;
      color: #102a43;
      font-size: 14px;
      box-sizing: border-box;
      transition: border-color 160ms ease, box-shadow 160ms ease;
    }
    .wizardInput:focus {
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }
    .wizardInput--error {
      border-color: #dc2626;
      background: #fff5f5;
    }
    .wizardError {
      display: block;
      margin-top: 6px;
      font-size: 12px;
      color: #b91c1c;
    }
    .wizardReviewGroup {
      padding: 16px;
      margin-bottom: 14px;
      border-radius: 14px;
      background: #ffffff;
      border: 1px solid #e7edf5;
    }
    .wizardReviewTitle {
      margin: 0 0 10px;
      font-size: 14px;
      font-weight: 700;
      color: #243b53;
    }
    .wizardReviewRow {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 8px 0;
      border-bottom: 1px solid #edf2f7;
      font-size: 13px;
    }
    .wizardReviewRow:last-child {
      border-bottom: 0;
      padding-bottom: 0;
    }
    .wizardActions {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-top: 22px;
    }
    .wizardButton {
      min-width: 112px;
      padding: 12px 16px;
      border-radius: 12px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      color: #243b53;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
    }
    .wizardButton:hover {
      border-color: #2563eb;
    }
    .wizardButton--primary {
      border-color: #2563eb;
      background: #2563eb;
      color: #ffffff;
    }
    .wizardButton--submit {
      border-color: #16a34a;
      background: #16a34a;
      color: #ffffff;
    }
    .wizardSuccess {
      padding: 22px;
      border-radius: 16px;
      border: 1px solid #bbf7d0;
      background: #f0fdf4;
      color: #166534;
      line-height: 1.6;
    }
  `;
  document.head.appendChild(style);
}

function validateEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState<FormState>({
    personal: { name: '', email: '' },
    address: { street: '', city: '', zip: '' },
  });
  const [errors, setErrors] = useState<Errors>({});

  useEffect(() => {
    ensureStyles();
  }, []);

  const steps = useMemo(() => ['Personal', 'Address', 'Review'], []);

  const updatePersonal = (field: keyof PersonalInfo, value: string) => {
    setForm((current) => ({ ...current, personal: { ...current.personal, [field]: value } }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const updateAddress = (field: keyof AddressInfo, value: string) => {
    setForm((current) => ({ ...current, address: { ...current.address, [field]: value } }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const validateCurrentStep = () => {
    const nextErrors: Errors = {};

    if (step === 0) {
      if (!form.personal.name.trim()) {
        nextErrors.name = 'Name is required.';
      }
      if (!form.personal.email.trim()) {
        nextErrors.email = 'Email is required.';
      } else if (!validateEmail(form.personal.email)) {
        nextErrors.email = 'Enter a valid email address.';
      }
    }

    if (step === 1) {
      if (!form.address.street.trim()) {
        nextErrors.street = 'Street is required.';
      }
      if (!form.address.city.trim()) {
        nextErrors.city = 'City is required.';
      }
      if (!form.address.zip.trim()) {
        nextErrors.zip = 'ZIP is required.';
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const goNext = () => {
    if (validateCurrentStep()) {
      setStep((current) => Math.min(current + 1, 2));
    }
  };

  const submit = () => {
    console.log('Wizard submitted:', form);
    setSubmitted(true);
  };

  return (
    <section className="wizardShell" aria-label="Multi-step form wizard">
      <h2 className="wizardTitle">Profile Setup Wizard</h2>
      <p className="wizardSubtitle">Three steps with manual validation, back and next navigation, and preserved form data.</p>

      <div className="wizardSteps">
        {steps.map((label, index) => {
          const className = [
            'wizardStep',
            step === index ? 'wizardStep--active' : '',
            step > index || submitted ? 'wizardStep--done' : '',
          ]
            .filter(Boolean)
            .join(' ');
          return (
            <div key={label} className={className}>
              <span className="wizardStepIndex">{step > index || submitted ? '✓' : index + 1}</span>
              <span className="wizardStepLabel">{label}</span>
            </div>
          );
        })}
      </div>

      {!submitted && (
        <div className="wizardPanel">
          {step === 0 && (
            <>
              <h3 className="wizardSectionTitle">Personal details</h3>
              <div className="wizardField">
                <label className="wizardLabel" htmlFor="wizard-name">Name</label>
                <input
                  id="wizard-name"
                  className={`wizardInput ${errors.name ? 'wizardInput--error' : ''}`}
                  type="text"
                  value={form.personal.name}
                  onChange={(event) => updatePersonal('name', event.target.value)}
                />
                {errors.name ? <span className="wizardError">{errors.name}</span> : null}
              </div>
              <div className="wizardField">
                <label className="wizardLabel" htmlFor="wizard-email">Email</label>
                <input
                  id="wizard-email"
                  className={`wizardInput ${errors.email ? 'wizardInput--error' : ''}`}
                  type="email"
                  value={form.personal.email}
                  onChange={(event) => updatePersonal('email', event.target.value)}
                />
                {errors.email ? <span className="wizardError">{errors.email}</span> : null}
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <h3 className="wizardSectionTitle">Address</h3>
              <div className="wizardField">
                <label className="wizardLabel" htmlFor="wizard-street">Street</label>
                <input
                  id="wizard-street"
                  className={`wizardInput ${errors.street ? 'wizardInput--error' : ''}`}
                  type="text"
                  value={form.address.street}
                  onChange={(event) => updateAddress('street', event.target.value)}
                />
                {errors.street ? <span className="wizardError">{errors.street}</span> : null}
              </div>
              <div className="wizardField">
                <label className="wizardLabel" htmlFor="wizard-city">City</label>
                <input
                  id="wizard-city"
                  className={`wizardInput ${errors.city ? 'wizardInput--error' : ''}`}
                  type="text"
                  value={form.address.city}
                  onChange={(event) => updateAddress('city', event.target.value)}
                />
                {errors.city ? <span className="wizardError">{errors.city}</span> : null}
              </div>
              <div className="wizardField">
                <label className="wizardLabel" htmlFor="wizard-zip">ZIP</label>
                <input
                  id="wizard-zip"
                  className={`wizardInput ${errors.zip ? 'wizardInput--error' : ''}`}
                  type="text"
                  value={form.address.zip}
                  onChange={(event) => updateAddress('zip', event.target.value)}
                />
                {errors.zip ? <span className="wizardError">{errors.zip}</span> : null}
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h3 className="wizardSectionTitle">Review and submit</h3>
              <div className="wizardReviewGroup">
                <h4 className="wizardReviewTitle">Personal</h4>
                <div className="wizardReviewRow"><span>Name</span><strong>{form.personal.name}</strong></div>
                <div className="wizardReviewRow"><span>Email</span><strong>{form.personal.email}</strong></div>
              </div>
              <div className="wizardReviewGroup">
                <h4 className="wizardReviewTitle">Address</h4>
                <div className="wizardReviewRow"><span>Street</span><strong>{form.address.street}</strong></div>
                <div className="wizardReviewRow"><span>City</span><strong>{form.address.city}</strong></div>
                <div className="wizardReviewRow"><span>ZIP</span><strong>{form.address.zip}</strong></div>
              </div>
            </>
          )}

          <div className="wizardActions">
            <button type="button" className="wizardButton" disabled={step === 0} onClick={() => setStep((current) => Math.max(current - 1, 0))}>
              Back
            </button>
            {step < 2 ? (
              <button type="button" className="wizardButton wizardButton--primary" onClick={goNext}>
                Next
              </button>
            ) : (
              <button type="button" className="wizardButton wizardButton--submit" onClick={submit}>
                Submit
              </button>
            )}
          </div>
        </div>
      )}

      {submitted && (
        <div className="wizardSuccess">
          <strong>Submitted.</strong> The collected data was sent to <code>console.log</code>. Use Back/refresh if you want to enter a different record.
        </div>
      )}
    </section>
  );
}
