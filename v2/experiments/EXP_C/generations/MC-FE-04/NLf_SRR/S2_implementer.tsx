import React, { useState, useCallback } from "react";

// ── Inline CSS ─────────────────────────────────────────────────────────
const css = `
  .wizard { max-width:560px; margin:40px auto; font-family:system-ui,sans-serif; }
  .stepBar { display:flex; margin-bottom:32px; }
  .stepItem { flex:1; text-align:center; position:relative; }
  .stepCircle { width:36px; height:36px; border-radius:50%; border:2px solid #ddd; display:inline-flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; background:#fff; color:#999; position:relative; z-index:1; }
  .stepCircleActive { border-color:#4a90d9; color:#4a90d9; }
  .stepCircleDone { border-color:#43a047; background:#43a047; color:#fff; }
  .stepLabel { display:block; font-size:12px; color:#999; margin-top:6px; }
  .stepLabelActive { color:#4a90d9; font-weight:600; }
  .stepLine { position:absolute; top:18px; left:50%; width:100%; height:2px; background:#ddd; z-index:0; }
  .stepLineDone { background:#43a047; }
  .card { background:#fff; border:1px solid #e0e0e0; border-radius:12px; padding:28px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
  .title { font-size:20px; font-weight:700; color:#333; margin-bottom:20px; }
  .field { margin-bottom:16px; }
  .label { display:block; font-size:13px; font-weight:600; color:#555; margin-bottom:4px; }
  .input { width:100%; padding:10px 12px; border:1px solid #ddd; border-radius:6px; font-size:14px; box-sizing:border-box; outline:none; }
  .input:focus { border-color:#4a90d9; }
  .inputError { border-color:#e53935; }
  .errorMsg { color:#e53935; font-size:12px; margin-top:2px; }
  .navRow { display:flex; justify-content:space-between; margin-top:24px; }
  .btn { padding:10px 24px; border:none; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; }
  .btnPrimary { background:#4a90d9; color:#fff; }
  .btnPrimary:hover { background:#3a7bc8; }
  .btnSecondary { background:#e0e0e0; color:#555; }
  .btnSecondary:hover { background:#d0d0d0; }
  .btnSubmit { background:#43a047; color:#fff; }
  .btnSubmit:hover { background:#388e3c; }
  .reviewGroup { margin-bottom:16px; }
  .reviewLabel { font-size:12px; color:#888; }
  .reviewValue { font-size:15px; color:#333; font-weight:500; }
  .successBox { text-align:center; padding:40px 0; }
  .successIcon { font-size:48px; margin-bottom:12px; }
  .successText { font-size:18px; color:#43a047; font-weight:700; }
`;

// ── Types ──────────────────────────────────────────────────────────────
interface PersonalInfo { name: string; email: string; phone: string; }
interface AddressInfo { street: string; city: string; state: string; zip: string; }
type Errors = Record<string, string>;

// ── Validation ─────────────────────────────────────────────────────────
function validatePersonal(d: PersonalInfo): Errors {
  const e: Errors = {};
  if (!d.name.trim()) e.name = "Name is required";
  else if (d.name.trim().length < 2) e.name = "Name must be at least 2 characters";
  else if (!/^[a-zA-Z\s]+$/.test(d.name.trim())) e.name = "Name must contain only letters";
  if (!d.email.trim()) e.email = "Email is required";
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.email.trim())) e.email = "Invalid email format";
  if (!d.phone.trim()) e.phone = "Phone is required";
  else if (!/^[\d\s\-+()]{10,20}$/.test(d.phone.trim())) e.phone = "Invalid phone number";
  return e;
}

function validateAddress(d: AddressInfo): Errors {
  const e: Errors = {};
  if (!d.street.trim()) e.street = "Street is required";
  else if (d.street.trim().length < 5) e.street = "Street must be at least 5 characters";
  if (!d.city.trim()) e.city = "City is required";
  else if (d.city.trim().length < 2) e.city = "City must be at least 2 characters";
  if (!d.state.trim()) e.state = "State is required";
  else if (!/^[A-Z]{2}$/.test(d.state.trim())) e.state = "Enter a valid 2-letter state code (e.g. CA)";
  if (!d.zip.trim()) e.zip = "ZIP is required";
  else if (!/^\d{5}(-\d{4})?$/.test(d.zip.trim())) e.zip = "Enter a valid ZIP (e.g. 12345)";
  return e;
}

// ── Input helper ───────────────────────────────────────────────────────
function FormInput({
  label,
  value,
  error,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="field">
      <label className="label">{label}</label>
      <input
        className={`input ${error ? "inputError" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {error && <div className="errorMsg">{error}</div>}
    </div>
  );
}

// ── Step Indicator ─────────────────────────────────────────────────────
function StepIndicator({ step }: { step: number }) {
  const labels = ["Personal Info", "Address", "Confirm"];
  return (
    <div className="stepBar">
      {labels.map((lbl, i) => {
        const n = i + 1;
        const done = step > n;
        const active = step === n;
        return (
          <div key={n} className="stepItem">
            {i < labels.length - 1 && <div className={`stepLine ${done ? "stepLineDone" : ""}`} />}
            <div className={`stepCircle ${done ? "stepCircleDone" : active ? "stepCircleActive" : ""}`}>
              {done ? "✓" : n}
            </div>
            <span className={`stepLabel ${active ? "stepLabelActive" : ""}`}>{lbl}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────
export default function FormWizard() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [personal, setPersonal] = useState<PersonalInfo>({ name: "", email: "", phone: "" });
  const [address, setAddress] = useState<AddressInfo>({ street: "", city: "", state: "", zip: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const updatePersonal = useCallback((key: keyof PersonalInfo, val: string) => {
    setPersonal((p) => ({ ...p, [key]: val }));
    setErrors((e) => { const c = { ...e }; delete c[key]; return c; });
  }, []);

  const updateAddress = useCallback((key: keyof AddressInfo, val: string) => {
    setAddress((a) => ({ ...a, [key]: val }));
    setErrors((e) => { const c = { ...e }; delete c[key]; return c; });
  }, []);

  const goNext = () => {
    if (step === 1) {
      const errs = validatePersonal(personal);
      if (Object.keys(errs).length) { setErrors(errs); return; }
      setErrors({});
      setStep(2);
    } else if (step === 2) {
      const errs = validateAddress(address);
      if (Object.keys(errs).length) { setErrors(errs); return; }
      setErrors({});
      setStep(3);
    }
  };

  const goBack = () => {
    if (step === 2) setStep(1);
    else if (step === 3) setStep(2);
  };

  const handleSubmit = () => {
    const e1 = validatePersonal(personal);
    const e2 = validateAddress(address);
    const allErrs = { ...e1, ...e2 };
    if (Object.keys(allErrs).length) { setErrors(allErrs); setStep(1); return; }
    setSubmitting(true);
    setTimeout(() => { setSubmitting(false); setSubmitted(true); }, 1200);
  };

  if (submitted) {
    return (
      <>
        <style>{css}</style>
        <div className="wizard">
          <StepIndicator step={4} />
          <div className="card successBox">
            <div className="successIcon">✅</div>
            <div className="successText">Submitted Successfully!</div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{css}</style>
      <div className="wizard">
        <StepIndicator step={step} />
        <div className="card">
          {step === 1 && (
            <>
              <div className="title">Personal Information</div>
              <FormInput label="Full Name" value={personal.name} error={errors.name} onChange={(v) => updatePersonal("name", v)} placeholder="John Doe" />
              <FormInput label="Email" value={personal.email} error={errors.email} onChange={(v) => updatePersonal("email", v)} placeholder="john@example.com" />
              <FormInput label="Phone" value={personal.phone} error={errors.phone} onChange={(v) => updatePersonal("phone", v)} placeholder="+1 (555) 123-4567" />
            </>
          )}
          {step === 2 && (
            <>
              <div className="title">Address Information</div>
              <FormInput label="Street" value={address.street} error={errors.street} onChange={(v) => updateAddress("street", v)} placeholder="123 Main St" />
              <FormInput label="City" value={address.city} error={errors.city} onChange={(v) => updateAddress("city", v)} placeholder="San Francisco" />
              <FormInput label="State" value={address.state} error={errors.state} onChange={(v) => updateAddress("state", v.toUpperCase())} placeholder="CA" />
              <FormInput label="ZIP Code" value={address.zip} error={errors.zip} onChange={(v) => updateAddress("zip", v)} placeholder="94102" />
            </>
          )}
          {step === 3 && (
            <>
              <div className="title">Review & Confirm</div>
              <div className="reviewGroup"><div className="reviewLabel">Name</div><div className="reviewValue">{personal.name}</div></div>
              <div className="reviewGroup"><div className="reviewLabel">Email</div><div className="reviewValue">{personal.email}</div></div>
              <div className="reviewGroup"><div className="reviewLabel">Phone</div><div className="reviewValue">{personal.phone}</div></div>
              <div className="reviewGroup"><div className="reviewLabel">Street</div><div className="reviewValue">{address.street}</div></div>
              <div className="reviewGroup"><div className="reviewLabel">City</div><div className="reviewValue">{address.city}, {address.state} {address.zip}</div></div>
            </>
          )}
          <div className="navRow">
            {step > 1 ? <button className="btn btnSecondary" onClick={goBack}>← Back</button> : <span />}
            {step < 3 && <button className="btn btnPrimary" onClick={goNext}>Next →</button>}
            {step === 3 && (
              <button className="btn btnSubmit" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Submitting…" : "Submit ✓"}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
