import React, { useReducer, useCallback } from "react";

// ─── Types ───

type Step = "personal" | "address" | "confirmation";

interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface Address {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: Address;
}

interface ValidationRule {
  required?: boolean;
  minLength?: number;
  pattern?: RegExp;
  patternMessage?: string;
}

interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

interface WizardState {
  currentStep: Step;
  formData: FormData;
  stepValidation: Record<Step, boolean>;
  touched: Record<string, boolean>;
  errors: Record<string, string>;
  submitted: boolean;
}

type WizardAction =
  | { type: "SET_FIELD"; step: "personal" | "address"; field: string; value: string }
  | { type: "TOUCH_FIELD"; field: string }
  | { type: "MARK_STEP_TOUCHED"; step: Step }
  | { type: "VALIDATE_STEP"; step: Step; isValid: boolean; errors: Record<string, string> }
  | { type: "NEXT_STEP" }
  | { type: "PREV_STEP" }
  | { type: "SUBMIT" };

// ─── CSS (plain CSS via inline objects, no Tailwind) ───

const css: Record<string, React.CSSProperties> = {
  wrapper: {
    fontFamily: "system-ui, sans-serif",
    maxWidth: 560,
    margin: "40px auto",
    padding: 24,
    background: "#fff",
    borderRadius: 8,
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
  },
  stepIndicator: {
    display: "flex",
    justifyContent: "center",
    gap: 8,
    marginBottom: 28,
  },
  stepItem: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 13,
    color: "#999",
  },
  stepItemActive: {
    color: "#1890ff",
    fontWeight: 600,
  },
  stepItemComplete: {
    color: "#52c41a",
  },
  stepNumber: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "2px solid #d9d9d9",
    fontSize: 13,
    fontWeight: 600,
  },
  stepNumberActive: {
    borderColor: "#1890ff",
    background: "#1890ff",
    color: "#fff",
  },
  stepNumberComplete: {
    borderColor: "#52c41a",
    background: "#52c41a",
    color: "#fff",
  },
  connector: {
    width: 40,
    height: 2,
    background: "#e8e8e8",
    alignSelf: "center" as const,
  },
  connectorActive: {
    background: "#52c41a",
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    marginBottom: 20,
  },
  field: {
    marginBottom: 16,
  },
  label: {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    marginBottom: 4,
    color: "#333",
  },
  input: {
    width: "100%",
    padding: "8px 12px",
    border: "1px solid #d9d9d9",
    borderRadius: 4,
    fontSize: 14,
    boxSizing: "border-box" as const,
    outline: "none",
  },
  inputError: {
    borderColor: "#ff4d4f",
  },
  errorText: {
    fontSize: 12,
    color: "#ff4d4f",
    marginTop: 4,
  },
  btnRow: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: 24,
  },
  btnPrimary: {
    padding: "8px 24px",
    background: "#1890ff",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
  },
  btnSecondary: {
    padding: "8px 24px",
    background: "#fff",
    color: "#333",
    border: "1px solid #d9d9d9",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 14,
  },
  btnDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
  },
  summaryRow: {
    padding: "8px 0",
    borderBottom: "1px solid #f0f0f0",
    display: "flex",
    justifyContent: "space-between",
    fontSize: 14,
  },
  summaryLabel: {
    color: "#666",
    fontWeight: 600,
  },
  successBox: {
    textAlign: "center" as const,
    padding: 40,
  },
  successIcon: {
    fontSize: 48,
    color: "#52c41a",
    marginBottom: 16,
  },
};

// ─── Validation engine ───

const personalRules: Record<string, ValidationRule> = {
  name: { required: true, minLength: 2, pattern: /^[a-zA-Z\s]+$/, patternMessage: "Alphabetic characters only" },
  email: { required: true, pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, patternMessage: "Invalid email format" },
  phone: { required: true, pattern: /^[\d\s\-\(\)\+]{10,}$/, patternMessage: "Invalid phone format" },
};

const addressRules: Record<string, ValidationRule> = {
  street: { required: true, minLength: 5 },
  city: { required: true, minLength: 2 },
  state: { required: true, pattern: /^[A-Za-z]{2}$/, patternMessage: "2-letter state code" },
  zip: { required: true, pattern: /^\d{5}(-\d{4})?$/, patternMessage: "5-digit or 5+4 zip code" },
};

function validateField(value: string, rule: ValidationRule): string | null {
  if (rule.required && !value.trim()) return "This field is required";
  if (rule.minLength && value.length < rule.minLength) return `Minimum ${rule.minLength} characters required`;
  if (rule.pattern && !rule.pattern.test(value)) return rule.patternMessage || "Invalid format";
  return null;
}

function validateStep(step: Step, formData: FormData): ValidationResult {
  const rules = step === "personal" ? personalRules : step === "address" ? addressRules : {};
  const data = step === "personal" ? formData.personal : step === "address" ? formData.address : {};
  const errors: Record<string, string> = {};

  for (const [field, rule] of Object.entries(rules)) {
    const value = (data as Record<string, string>)[field] || "";
    const error = validateField(value, rule);
    if (error) errors[field] = error;
  }

  return { isValid: Object.keys(errors).length === 0, errors };
}

// ─── Reducer ───

const STEP_ORDER: Step[] = ["personal", "address", "confirmation"];

const initialFormData: FormData = {
  personal: { name: "", email: "", phone: "" },
  address: { street: "", city: "", state: "", zip: "" },
};

const initialState: WizardState = {
  currentStep: "personal",
  formData: initialFormData,
  stepValidation: { personal: false, address: false, confirmation: true },
  touched: {},
  errors: {},
  submitted: false,
};

function reducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_FIELD": {
      const stepData = { ...state.formData[action.step], [action.field]: action.value };
      const newFormData = { ...state.formData, [action.step]: stepData };
      // re-validate touched fields
      const validation = validateStep(state.currentStep, newFormData);
      const touchedErrors: Record<string, string> = {};
      for (const [k, v] of Object.entries(validation.errors)) {
        if (state.touched[k]) touchedErrors[k] = v;
      }
      return {
        ...state,
        formData: newFormData,
        errors: touchedErrors,
        stepValidation: {
          ...state.stepValidation,
          [state.currentStep]: validation.isValid,
        },
      };
    }

    case "TOUCH_FIELD":
      return { ...state, touched: { ...state.touched, [action.field]: true } };

    case "MARK_STEP_TOUCHED": {
      const rules = action.step === "personal" ? personalRules : addressRules;
      const touched = { ...state.touched };
      for (const key of Object.keys(rules)) touched[key] = true;
      const validation = validateStep(action.step, state.formData);
      return { ...state, touched, errors: validation.errors };
    }

    case "VALIDATE_STEP":
      return {
        ...state,
        stepValidation: { ...state.stepValidation, [action.step]: action.isValid },
        errors: action.errors,
      };

    case "NEXT_STEP": {
      const idx = STEP_ORDER.indexOf(state.currentStep);
      if (idx < STEP_ORDER.length - 1) {
        return { ...state, currentStep: STEP_ORDER[idx + 1], errors: {} };
      }
      return state;
    }

    case "PREV_STEP": {
      const idx = STEP_ORDER.indexOf(state.currentStep);
      if (idx > 0) {
        return { ...state, currentStep: STEP_ORDER[idx - 1], errors: {} };
      }
      return state;
    }

    case "SUBMIT":
      return { ...state, submitted: true };

    default:
      return state;
  }
}

// ─── Step Components ───

const PersonalStep: React.FC<{
  data: PersonalInfo;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  onChange: (field: string, value: string) => void;
  onBlur: (field: string) => void;
}> = ({ data, errors, touched, onChange, onBlur }) => {
  const fields: { key: keyof PersonalInfo; label: string; placeholder: string; type?: string }[] = [
    { key: "name", label: "Full Name", placeholder: "John Doe" },
    { key: "email", label: "Email Address", placeholder: "john@example.com", type: "email" },
    { key: "phone", label: "Phone Number", placeholder: "+1 (555) 123-4567", type: "tel" },
  ];
  return (
    <div>
      <div style={css.title}>Personal Information</div>
      {fields.map((f) => (
        <div key={f.key} style={css.field}>
          <label style={css.label}>{f.label}</label>
          <input
            style={{
              ...css.input,
              ...(touched[f.key] && errors[f.key] ? css.inputError : {}),
            }}
            type={f.type || "text"}
            value={data[f.key]}
            placeholder={f.placeholder}
            onChange={(e) => onChange(f.key, e.target.value)}
            onBlur={() => onBlur(f.key)}
          />
          {touched[f.key] && errors[f.key] && (
            <div style={css.errorText}>{errors[f.key]}</div>
          )}
        </div>
      ))}
    </div>
  );
};

const AddressStep: React.FC<{
  data: Address;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  onChange: (field: string, value: string) => void;
  onBlur: (field: string) => void;
}> = ({ data, errors, touched, onChange, onBlur }) => {
  const fields: { key: keyof Address; label: string; placeholder: string }[] = [
    { key: "street", label: "Street Address", placeholder: "123 Main St" },
    { key: "city", label: "City", placeholder: "Springfield" },
    { key: "state", label: "State", placeholder: "CA" },
    { key: "zip", label: "ZIP Code", placeholder: "90210" },
  ];
  return (
    <div>
      <div style={css.title}>Address</div>
      {fields.map((f) => (
        <div key={f.key} style={css.field}>
          <label style={css.label}>{f.label}</label>
          <input
            style={{
              ...css.input,
              ...(touched[f.key] && errors[f.key] ? css.inputError : {}),
            }}
            value={data[f.key]}
            placeholder={f.placeholder}
            onChange={(e) => onChange(f.key, e.target.value)}
            onBlur={() => onBlur(f.key)}
          />
          {touched[f.key] && errors[f.key] && (
            <div style={css.errorText}>{errors[f.key]}</div>
          )}
        </div>
      ))}
    </div>
  );
};

const ConfirmationStep: React.FC<{ data: FormData }> = ({ data }) => {
  const rows = [
    { label: "Name", value: data.personal.name },
    { label: "Email", value: data.personal.email },
    { label: "Phone", value: data.personal.phone },
    { label: "Street", value: data.address.street },
    { label: "City", value: data.address.city },
    { label: "State", value: data.address.state },
    { label: "ZIP", value: data.address.zip },
  ];
  return (
    <div>
      <div style={css.title}>Confirmation</div>
      <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
        Please review your information before submitting.
      </p>
      {rows.map((r) => (
        <div key={r.label} style={css.summaryRow}>
          <span style={css.summaryLabel}>{r.label}</span>
          <span>{r.value || "—"}</span>
        </div>
      ))}
    </div>
  );
};

// ─── Step Indicator ───

const StepIndicator: React.FC<{ currentStep: Step; validation: Record<Step, boolean> }> = ({
  currentStep,
  validation,
}) => {
  const stepLabels: Record<Step, string> = {
    personal: "Personal",
    address: "Address",
    confirmation: "Confirm",
  };
  const currentIdx = STEP_ORDER.indexOf(currentStep);

  return (
    <div style={css.stepIndicator}>
      {STEP_ORDER.map((step, idx) => {
        const isActive = idx === currentIdx;
        const isComplete = idx < currentIdx || (validation[step] && idx <= currentIdx);
        return (
          <React.Fragment key={step}>
            {idx > 0 && (
              <div
                style={{
                  ...css.connector,
                  ...(idx <= currentIdx ? css.connectorActive : {}),
                }}
              />
            )}
            <div
              style={{
                ...css.stepItem,
                ...(isActive ? css.stepItemActive : {}),
                ...(isComplete && !isActive ? css.stepItemComplete : {}),
              }}
            >
              <div
                style={{
                  ...css.stepNumber,
                  ...(isActive ? css.stepNumberActive : {}),
                  ...(isComplete && !isActive ? css.stepNumberComplete : {}),
                }}
              >
                {isComplete && !isActive ? "✓" : idx + 1}
              </div>
              <span>{stepLabels[step]}</span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ─── Main Component ───

const FormWizard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleChange = useCallback(
    (field: string, value: string) => {
      const step = state.currentStep === "personal" ? "personal" : "address";
      dispatch({ type: "SET_FIELD", step, field, value });
    },
    [state.currentStep]
  );

  const handleBlur = useCallback((field: string) => {
    dispatch({ type: "TOUCH_FIELD", field });
  }, []);

  const handleNext = useCallback(() => {
    const validation = validateStep(state.currentStep, state.formData);
    if (!validation.isValid) {
      dispatch({ type: "MARK_STEP_TOUCHED", step: state.currentStep });
      dispatch({
        type: "VALIDATE_STEP",
        step: state.currentStep,
        isValid: false,
        errors: validation.errors,
      });
      return;
    }
    dispatch({
      type: "VALIDATE_STEP",
      step: state.currentStep,
      isValid: true,
      errors: {},
    });
    dispatch({ type: "NEXT_STEP" });
  }, [state.currentStep, state.formData]);

  const handleBack = useCallback(() => {
    dispatch({ type: "PREV_STEP" });
  }, []);

  const handleSubmit = useCallback(() => {
    dispatch({ type: "SUBMIT" });
  }, []);

  const isFirstStep = state.currentStep === "personal";
  const isLastStep = state.currentStep === "confirmation";

  if (state.submitted) {
    return (
      <div style={css.wrapper}>
        <div style={css.successBox}>
          <div style={css.successIcon}>✅</div>
          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            Form Submitted!
          </div>
          <div style={{ color: "#666" }}>
            Thank you, {state.formData.personal.name}. Your information has been received.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={css.wrapper}>
      <StepIndicator currentStep={state.currentStep} validation={state.stepValidation} />

      {state.currentStep === "personal" && (
        <PersonalStep
          data={state.formData.personal}
          errors={state.errors}
          touched={state.touched}
          onChange={handleChange}
          onBlur={handleBlur}
        />
      )}
      {state.currentStep === "address" && (
        <AddressStep
          data={state.formData.address}
          errors={state.errors}
          touched={state.touched}
          onChange={handleChange}
          onBlur={handleBlur}
        />
      )}
      {state.currentStep === "confirmation" && (
        <ConfirmationStep data={state.formData} />
      )}

      <div style={css.btnRow}>
        {!isFirstStep ? (
          <button style={css.btnSecondary} onClick={handleBack}>
            ← Back
          </button>
        ) : (
          <div />
        )}
        {isLastStep ? (
          <button style={css.btnPrimary} onClick={handleSubmit}>
            Submit
          </button>
        ) : (
          <button style={css.btnPrimary} onClick={handleNext}>
            Next →
          </button>
        )}
      </div>
    </div>
  );
};

export default FormWizard;
