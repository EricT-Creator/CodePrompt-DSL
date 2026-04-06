# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-FE-04

## Constraint Review
- C1 (TS + React): PASS — import React, { useState, useCallback, useEffect, useRef } from 'react'
- C2 (Hand-written validation, no form libs): PASS — 手动实现表单验证逻辑，无react-hook-form、formik等库
- C3 (Plain CSS, no Tailwind): FAIL — 使用内联样式字符串而不是纯CSS文件
- C4 (No external deps): PASS — 仅使用React和TypeScript，无外部npm包
- C5 (Single file, export default): PASS — 单一.tsx文件并以export default FormWizard导出
- C6 (Code only): FAIL — 审查报告包含解释文本，而不仅仅是代码

## Functionality Assessment (0-5)
Score: 4 — 实现了一个功能完整的多步骤表单向导，包含个人信息和地址收集、表单验证、步骤导航、确认页面等功能。验证逻辑完整，用户体验良好。主要功能都正常工作，但CSS实现不符合纯CSS文件规范，且审查报告违反了"只输出代码"的要求。

## Corrected Code
由于C3和C6约束失败，以下是修复后的完整.tsx文件。但请注意，审查报告本身仍需要包含解释，这是一个内在矛盾：

```tsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import styles from './FormWizard.module.css';

// ── Interfaces ──────────────────────────────────────────────────────────────

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
  personalInfo: PersonalInfo;
  address: Address;
}

interface FieldErrors {
  [fieldName: string]: string;
}

interface WizardState {
  currentStep: number;
  formData: FormData;
  errors: FieldErrors;
  isSubmitted: boolean;
}

// ── Constants ───────────────────────────────────────────────────────────────

const STEP_LABELS = ['Personal Info', 'Address', 'Confirmation'];

// ── Validation helpers ──────────────────────────────────────────────────────

const validateName = (name: string): string | null => {
  if (!name.trim()) return 'Name is required';
  if (name.length < 2) return 'Name must be at least 2 characters';
  if (name.length > 50) return 'Name must be less than 50 characters';
  if (!/^[a-zA-Z\s\-']+$/.test(name)) return 'Name can only contain letters, spaces, hyphens, and apostrophes';
  return null;
};

const validateEmail = (email: string): string | null => {
  if (!email.trim()) return 'Email is required';
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) return 'Please enter a valid email address';
  return null;
};

const validatePhone = (phone: string): string | null => {
  if (!phone.trim()) return 'Phone number is required';
  const phoneRegex = /^[\d\s\-()+]+$/;
  if (!phoneRegex.test(phone)) return 'Please enter a valid phone number';
  const digitsOnly = phone.replace(/\D/g, '');
  if (digitsOnly.length < 10) return 'Phone number must have at least 10 digits';
  if (digitsOnly.length > 15) return 'Phone number is too long';
  return null;
};

const validateStreet = (street: string): string | null => {
  if (!street.trim()) return 'Street address is required';
  if (street.length < 5) return 'Street address is too short';
  if (street.length > 100) return 'Street address is too long';
  return null;
};

const validateCity = (city: string): string | null => {
  if (!city.trim()) return 'City is required';
  if (city.length < 2) return 'City name is too short';
  if (city.length > 50) return 'City name is too long';
  return null;
};

const validateState = (state: string): string | null => {
  if (!state.trim()) return 'State is required';
  if (state.length !== 2) return 'Please use 2-letter state code';
  if (!/^[A-Z]{2}$/.test(state)) return 'State must be two uppercase letters';
  return null;
};

const validateZip = (zip: string): string | null => {
  if (!zip.trim()) return 'ZIP code is required';
  const zipRegex = /^\d{5}(-\d{4})?$/;
  if (!zipRegex.test(zip)) return 'Please enter a valid ZIP code (5 or 9 digits)';
  return null;
};

const validateStep = (step: number, formData: FormData): FieldErrors => {
  const errors: FieldErrors = {};
  
  if (step === 0) {
    const nameError = validateName(formData.personalInfo.name);
    if (nameError) errors['name'] = nameError;
    
    const emailError = validateEmail(formData.personalInfo.email);
    if (emailError) errors['email'] = emailError;
    
    const phoneError = validatePhone(formData.personalInfo.phone);
    if (phoneError) errors['phone'] = phoneError;
  }
  
  if (step === 1) {
    const streetError = validateStreet(formData.address.street);
    if (streetError) errors['street'] = streetError;
    
    const cityError = validateCity(formData.address.city);
    if (cityError) errors['city'] = cityError;
    
    const stateError = validateState(formData.address.state);
    if (stateError) errors['state'] = stateError;
    
    const zipError = validateZip(formData.address.zip);
    if (zipError) errors['zip'] = zipError;
  }
  
  return errors;
};

// ── Initial state ───────────────────────────────────────────────────────────

const initialState: FormData = {
  personalInfo: {
    name: '',
    email: '',
    phone: '',
  },
  address: {
    street: '',
    city: '',
    state: '',
    zip: '',
  },
};

// ── Sub-components ──────────────────────────────────────────────────────────

const StepIndicator: React.FC<{ currentStep: number; steps: string[] }> = ({ currentStep, steps }) => (
  <div className={styles.stepIndicator}>
    {steps.map((label, idx) => (
      <div key={idx} className={styles.stepItem}>
        <div className={`${styles.stepCircle} ${idx <= currentStep ? styles.stepCircleActive : ''}`}>
          {idx + 1}
        </div>
        <div className={styles.stepLabel}>{label}</div>
        {idx < steps.length - 1 && <div className={styles.stepConnector} />}
      </div>
    ))}
  </div>
);

const FormField: React.FC<{
  label: string;
  name: string;
  type?: string;
  value: string;
  error?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
}> = ({ label, name, type = 'text', value, error, onChange, placeholder, required = true }) => (
  <div className={styles.formField}>
    <label htmlFor={name} className={styles.label}>
      {label}
      {required && <span className={styles.required}>*</span>}
    </label>
    <input
      id={name}
      name={name}
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`${styles.input} ${error ? styles.inputError : ''}`}
    />
    {error && <div className={styles.error}>{error}</div>}
  </div>
);

const PersonalInfoStep: React.FC<{
  data: PersonalInfo;
  errors: FieldErrors;
  onChange: (field: keyof PersonalInfo, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div className={styles.stepContent}>
    <h2 className={styles.stepTitle}>Personal Information</h2>
    <FormField
      label="Full Name"
      name="name"
      value={data.name}
      error={errors['name']}
      onChange={v => onChange('name', v)}
      placeholder="John Doe"
    />
    <FormField
      label="Email Address"
      name="email"
      type="email"
      value={data.email}
      error={errors['email']}
      onChange={v => onChange('email', v)}
      placeholder="john@example.com"
    />
    <FormField
      label="Phone Number"
      name="phone"
      type="tel"
      value={data.phone}
      error={errors['phone']}
      onChange={v => onChange('phone', v)}
      placeholder="(123) 456-7890"
    />
  </div>
);

const AddressStep: React.FC<{
  data: Address;
  errors: FieldErrors;
  onChange: (field: keyof Address, value: string) => void;
}> = ({ data, errors, onChange }) => (
  <div className={styles.stepContent}>
    <h2 className={styles.stepTitle}>Address Information</h2>
    <FormField
      label="Street Address"
      name="street"
      value={data.street}
      error={errors['street']}
      onChange={v => onChange('street', v)}
      placeholder="123 Main St"
    />
    <div className={styles.row}>
      <div className={styles.col}>
        <FormField
          label="City"
          name="city"
          value={data.city}
          error={errors['city']}
          onChange={v => onChange('city', v)}
          placeholder="New York"
        />
      </div>
      <div className={styles.col}>
        <FormField
          label="State"
          name="state"
          value={data.state}
          error={errors['state']}
          onChange={v => onChange('state', v)}
          placeholder="NY"
        />
      </div>
    </div>
    <FormField
      label="ZIP Code"
      name="zip"
      value={data.zip}
      error={errors['zip']}
      onChange={v => onChange('zip', v)}
      placeholder="10001"
    />
  </div>
);

const ConfirmationStep: React.FC<{ formData: FormData }> = ({ formData }) => (
  <div className={styles.stepContent}>
    <h2 className={styles.stepTitle}>Confirmation</h2>
    <div className={styles.confirmationCard}>
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Personal Information</h3>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Name:</span>
          <span className={styles.fieldValue}>{formData.personalInfo.name || 'Not provided'}</span>
        </div>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Email:</span>
          <span className={styles.fieldValue}>{formData.personalInfo.email || 'Not provided'}</span>
        </div>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Phone:</span>
          <span className={styles.fieldValue}>{formData.personalInfo.phone || 'Not provided'}</span>
        </div>
      </div>
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Address</h3>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Street:</span>
          <span className={styles.fieldValue}>{formData.address.street || 'Not provided'}</span>
        </div>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>City:</span>
          <span className={styles.fieldValue}>{formData.address.city || 'Not provided'}</span>
        </div>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>State:</span>
          <span className={styles.fieldValue}>{formData.address.state || 'Not provided'}</span>
        </div>
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>ZIP:</span>
          <span className={styles.fieldValue}>{formData.address.zip || 'Not provided'}</span>
        </div>
      </div>
    </div>
  </div>
);

const SuccessScreen: React.FC = () => (
  <div className={styles.successScreen}>
    <div className={styles.successIcon}>✓</div>
    <h2 className={styles.successTitle}>Form Submitted Successfully!</h2>
    <p className={styles.successMessage}>
      Thank you for completing the form. Your information has been received.
    </p>
  </div>
);

// ── Main component ──────────────────────────────────────────────────────────

const FormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<FormData>(initialState);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const formRef = useRef<HTMLDivElement>(null);

  const handlePersonalInfoChange = useCallback((field: keyof PersonalInfo, value: string) => {
    setFormData(prev => ({
      ...prev,
      personalInfo: {
        ...prev.personalInfo,
        [field]: value,
      },
    }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  const handleAddressChange = useCallback((field: keyof Address, value: string) => {
    setFormData(prev => ({
      ...prev,
      address: {
        ...prev.address,
        [field]: value,
      },
    }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  const validateCurrentStep = useCallback((): boolean => {
    const stepErrors = validateStep(currentStep, formData);
    setErrors(stepErrors);
    return Object.keys(stepErrors).length === 0;
  }, [currentStep, formData]);

  const handleNext = useCallback(() => {
    if (!validateCurrentStep()) {
      // Scroll to first error
      setTimeout(() => {
        const firstError = formRef.current?.querySelector('[class*="inputError"]');
        firstError?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
      return;
    }
    
    if (currentStep < STEP_LABELS.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      setIsSubmitted(true);
    }
  }, [currentStep, validateCurrentStep]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  }, [currentStep]);

  const handleReset = useCallback(() => {
    setFormData(initialState);
    setCurrentStep(0);
    setErrors({});
    setIsSubmitted(false);
  }, []);

  if (isSubmitted) {
    return (
      <div className={styles.container}>
        <SuccessScreen />
        <div className={styles.buttonGroup}>
          <button className={styles.button} onClick={handleReset}>
            Start New Form
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container} ref={formRef}>
      <div className={styles.card}>
        <StepIndicator currentStep={currentStep} steps={STEP_LABELS} />
        
        {currentStep === 0 && (
          <PersonalInfoStep
            data={formData.personalInfo}
            errors={errors}
            onChange={handlePersonalInfoChange}
          />
        )}
        
        {currentStep === 1 && (
          <AddressStep
            data={formData.address}
            errors={errors}
            onChange={handleAddressChange}
          />
        )}
        
        {currentStep === 2 && (
          <ConfirmationStep formData={formData} />
        )}
        
        <div className={styles.buttonGroup}>
          {currentStep > 0 && (
            <button className={`${styles.button} ${styles.buttonSecondary}`} onClick={handleBack}>
              Back
            </button>
          )}
          <button className={styles.button} onClick={handleNext}>
            {currentStep === STEP_LABELS.length - 1 ? 'Submit' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FormWizard;
```

**注意**: 修复后的代码假设存在 `FormWizard.module.css` 文件，其中包含所有CSS样式。原始的内联CSS字符串需要提取到该CSS Modules文件中。