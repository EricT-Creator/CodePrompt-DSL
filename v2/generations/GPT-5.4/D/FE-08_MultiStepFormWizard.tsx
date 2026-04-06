import React, { FormEvent, useMemo, useState } from "react";

type FormData = {
  name: string;
  email: string;
  street: string;
  city: string;
  zip: string;
};

type FormErrors = Partial<Record<keyof FormData, string>>;

const initialData: FormData = {
  name: "",
  email: "",
  street: "",
  city: "",
  zip: "",
};

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(initialData);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const css = `
    * {
      box-sizing: border-box;
    }

    .wizard-page {
      min-height: 100vh;
      padding: 32px 16px;
      background: linear-gradient(180deg, #f4f7fb 0%, #eef2ff 100%);
      font-family: Arial, Helvetica, sans-serif;
      color: #16213a;
    }

    .wizard-shell {
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 24px;
      border: 1px solid #d8e1f2;
      box-shadow: 0 24px 64px rgba(20, 40, 90, 0.12);
      overflow: hidden;
    }

    .wizard-header {
      padding: 28px 28px 22px;
      border-bottom: 1px solid #e7ecf5;
    }

    .wizard-title {
      margin: 0;
      font-size: 30px;
      font-weight: 700;
    }

    .wizard-subtitle {
      margin: 10px 0 0;
      color: #5c6983;
      line-height: 1.6;
    }

    .wizard-progress {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 20px;
    }

    .wizard-progress-item {
      border-radius: 16px;
      padding: 12px 14px;
      border: 1px solid #d9e1f0;
      background: #f7f9fc;
      color: #627089;
      font-weight: 700;
      font-size: 14px;
    }

    .wizard-progress-item--active {
      border-color: #4661df;
      background: #eaf0ff;
      color: #2341c8;
    }

    .wizard-form {
      padding: 28px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .wizard-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }

    .wizard-field {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .wizard-field--full {
      grid-column: 1 / -1;
    }

    .wizard-label {
      font-weight: 700;
      color: #2f3c57;
    }

    .wizard-input {
      width: 100%;
      border: 1px solid #d5deef;
      border-radius: 14px;
      padding: 12px 14px;
      font-size: 15px;
      color: #1f2a44;
      transition: border-color 0.16s ease, box-shadow 0.16s ease;
    }

    .wizard-input:focus {
      outline: none;
      border-color: #4b67e3;
      box-shadow: 0 0 0 4px rgba(75, 103, 227, 0.12);
    }

    .wizard-input--error {
      border-color: #dc2626;
      background: #fff7f7;
    }

    .wizard-error {
      margin: 0;
      font-size: 13px;
      color: #dc2626;
    }

    .wizard-summary {
      display: grid;
      gap: 12px;
      padding: 20px;
      border-radius: 18px;
      background: #f7f9fd;
      border: 1px solid #dce4f2;
    }

    .wizard-summary-row {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      border-bottom: 1px dashed #d8e1f1;
      padding-bottom: 10px;
    }

    .wizard-summary-row:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }

    .wizard-actions {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      padding-top: 8px;
    }

    .wizard-button {
      appearance: none;
      border: 1px solid #d5deef;
      background: #ffffff;
      color: #32405c;
      border-radius: 14px;
      padding: 12px 18px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.16s ease;
    }

    .wizard-button:hover {
      border-color: #7a94e8;
      background: #eff4ff;
    }

    .wizard-button--primary {
      border-color: #4661df;
      background: #4661df;
      color: #ffffff;
    }

    .wizard-button--primary:hover {
      background: #3752d3;
      border-color: #3752d3;
    }

    .wizard-success {
      padding: 0 28px 28px;
      color: #15803d;
      font-weight: 700;
    }

    @media (max-width: 640px) {
      .wizard-grid {
        grid-template-columns: 1fr;
      }
    }
  `;

  const stepLabels = useMemo(() => ["个人信息", "地址信息", "确认提交"], []);

  const validateCurrentStep = (currentStep: number): FormErrors => {
    const nextErrors: FormErrors = {};

    if (currentStep === 1) {
      if (!formData.name.trim()) {
        nextErrors.name = "姓名为必填项";
      }
      if (!formData.email.trim()) {
        nextErrors.email = "邮箱为必填项";
      } else if (!validateEmail(formData.email.trim())) {
        nextErrors.email = "请输入有效的邮箱地址";
      }
    }

    if (currentStep === 2) {
      if (!formData.street.trim()) {
        nextErrors.street = "街道为必填项";
      }
      if (!formData.city.trim()) {
        nextErrors.city = "城市为必填项";
      }
      if (!formData.zip.trim()) {
        nextErrors.zip = "邮编为必填项";
      }
    }

    return nextErrors;
  };

  const updateField = (field: keyof FormData, value: string) => {
    setFormData((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const goNext = () => {
    const nextErrors = validateCurrentStep(step);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }
    setStep((current) => Math.min(3, current + 1));
  };

  const goBack = () => {
    setStep((current) => Math.max(1, current - 1));
    setSubmitted(false);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const firstErrors = validateCurrentStep(1);
    const secondErrors = validateCurrentStep(2);
    const nextErrors = { ...firstErrors, ...secondErrors };
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      setStep(firstErrors.name || firstErrors.email ? 1 : 2);
      return;
    }

    console.log({ ...formData });
    setSubmitted(true);
  };

  return (
    <div className="wizard-page">
      <style>{css}</style>
      <div className="wizard-shell">
        <div className="wizard-header">
          <h1 className="wizard-title">三步表单向导</h1>
          <p className="wizard-subtitle">
            第一步填写个人信息，第二步补充地址信息，第三步确认后提交。后退时会保留已填写的数据。
          </p>
          <div className="wizard-progress">
            {stepLabels.map((label, index) => (
              <div
                key={label}
                className={[
                  "wizard-progress-item",
                  step === index + 1 ? "wizard-progress-item--active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {index + 1}. {label}
              </div>
            ))}
          </div>
        </div>

        <form className="wizard-form" onSubmit={handleSubmit}>
          {step === 1 && (
            <div className="wizard-grid">
              <div className="wizard-field wizard-field--full">
                <label className="wizard-label" htmlFor="name">
                  姓名
                </label>
                <input
                  id="name"
                  className={[
                    "wizard-input",
                    errors.name ? "wizard-input--error" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  value={formData.name}
                  onChange={(event) => updateField("name", event.currentTarget.value)}
                  placeholder="请输入姓名"
                />
                {errors.name ? <p className="wizard-error">{errors.name}</p> : null}
              </div>

              <div className="wizard-field wizard-field--full">
                <label className="wizard-label" htmlFor="email">
                  邮箱
                </label>
                <input
                  id="email"
                  className={[
                    "wizard-input",
                    errors.email ? "wizard-input--error" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  value={formData.email}
                  onChange={(event) => updateField("email", event.currentTarget.value)}
                  placeholder="name@example.com"
                />
                {errors.email ? <p className="wizard-error">{errors.email}</p> : null}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="wizard-grid">
              <div className="wizard-field wizard-field--full">
                <label className="wizard-label" htmlFor="street">
                  街道
                </label>
                <input
                  id="street"
                  className={[
                    "wizard-input",
                    errors.street ? "wizard-input--error" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  value={formData.street}
                  onChange={(event) => updateField("street", event.currentTarget.value)}
                  placeholder="请输入街道地址"
                />
                {errors.street ? <p className="wizard-error">{errors.street}</p> : null}
              </div>

              <div className="wizard-field">
                <label className="wizard-label" htmlFor="city">
                  城市
                </label>
                <input
                  id="city"
                  className={[
                    "wizard-input",
                    errors.city ? "wizard-input--error" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  value={formData.city}
                  onChange={(event) => updateField("city", event.currentTarget.value)}
                  placeholder="请输入城市"
                />
                {errors.city ? <p className="wizard-error">{errors.city}</p> : null}
              </div>

              <div className="wizard-field">
                <label className="wizard-label" htmlFor="zip">
                  邮编
                </label>
                <input
                  id="zip"
                  className={[
                    "wizard-input",
                    errors.zip ? "wizard-input--error" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  value={formData.zip}
                  onChange={(event) => updateField("zip", event.currentTarget.value)}
                  placeholder="请输入邮编"
                />
                {errors.zip ? <p className="wizard-error">{errors.zip}</p> : null}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="wizard-summary">
              <div className="wizard-summary-row">
                <strong>姓名</strong>
                <span>{formData.name || "-"}</span>
              </div>
              <div className="wizard-summary-row">
                <strong>邮箱</strong>
                <span>{formData.email || "-"}</span>
              </div>
              <div className="wizard-summary-row">
                <strong>街道</strong>
                <span>{formData.street || "-"}</span>
              </div>
              <div className="wizard-summary-row">
                <strong>城市</strong>
                <span>{formData.city || "-"}</span>
              </div>
              <div className="wizard-summary-row">
                <strong>邮编</strong>
                <span>{formData.zip || "-"}</span>
              </div>
            </div>
          )}

          <div className="wizard-actions">
            <button type="button" className="wizard-button" onClick={goBack} disabled={step === 1}>
              上一步
            </button>

            {step < 3 ? (
              <button type="button" className="wizard-button wizard-button--primary" onClick={goNext}>
                下一步
              </button>
            ) : (
              <button type="submit" className="wizard-button wizard-button--primary">
                确认并提交
              </button>
            )}
          </div>
        </form>

        {submitted ? <div className="wizard-success">提交成功，完整数据已输出到 console.log。</div> : null}
      </div>
    </div>
  );
}
