import React, { useState, useCallback } from 'react';

interface FormData {
  name: string;
  email: string;
  street: string;
  city: string;
  zipcode: string;
}

interface Errors {
  name?: string;
  email?: string;
  street?: string;
  city?: string;
  zipcode?: string;
}

const initialFormData: FormData = {
  name: '',
  email: '',
  street: '',
  city: '',
  zipcode: '',
};

export default function MultiStepFormWizard() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validateStep1 = (): boolean => {
    const newErrors: Errors = {};
    if (!formData.name.trim()) {
      newErrors.name = '姓名必填';
    }
    if (!formData.email.trim()) {
      newErrors.email = '邮箱必填';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = '邮箱格式不正确';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = (): boolean => {
    const newErrors: Errors = {};
    if (!formData.street.trim()) {
      newErrors.street = '街道必填';
    }
    if (!formData.city.trim()) {
      newErrors.city = '城市必填';
    }
    if (!formData.zipcode.trim()) {
      newErrors.zipcode = '邮编必填';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = useCallback(() => {
    if (step === 1 && validateStep1()) {
      setStep(2);
      setErrors({});
    } else if (step === 2 && validateStep2()) {
      setStep(3);
      setErrors({});
    }
  }, [step, formData]);

  const handleBack = useCallback(() => {
    if (step > 1) {
      setStep(step - 1);
      setErrors({});
    }
  }, [step]);

  const handleSubmit = useCallback(() => {
    console.log('提交的数据:', formData);
    setSubmitted(true);
  }, [formData]);

  const handleChange = useCallback((field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  }, [errors]);

  const styles: { [key: string]: React.CSSProperties } = {
    container: {
      maxWidth: '500px',
      margin: '0 auto',
      padding: '30px',
      fontFamily: 'Arial, sans-serif',
    },
    title: {
      textAlign: 'center',
      marginBottom: '30px',
    },
    progressBar: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '30px',
    },
    stepIndicator: {
      width: '40px',
      height: '40px',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 'bold',
    },
    stepActive: {
      backgroundColor: '#2196f3',
      color: '#fff',
    },
    stepInactive: {
      backgroundColor: '#e0e0e0',
      color: '#666',
    },
    stepCompleted: {
      backgroundColor: '#4caf50',
      color: '#fff',
    },
    formGroup: {
      marginBottom: '20px',
    },
    label: {
      display: 'block',
      marginBottom: '8px',
      fontWeight: 'bold',
    },
    input: {
      width: '100%',
      padding: '12px',
      border: '1px solid #ddd',
      borderRadius: '4px',
      fontSize: '16px',
      boxSizing: 'border-box',
    },
    inputError: {
      borderColor: '#f44336',
    },
    errorText: {
      color: '#f44336',
      fontSize: '14px',
      marginTop: '5px',
    },
    buttonGroup: {
      display: 'flex',
      justifyContent: 'space-between',
      marginTop: '30px',
    },
    button: {
      padding: '12px 30px',
      border: 'none',
      borderRadius: '4px',
      fontSize: '16px',
      cursor: 'pointer',
    },
    buttonPrimary: {
      backgroundColor: '#2196f3',
      color: '#fff',
    },
    buttonSecondary: {
      backgroundColor: '#e0e0e0',
      color: '#333',
    },
    summary: {
      backgroundColor: '#f5f5f5',
      padding: '20px',
      borderRadius: '8px',
      marginBottom: '20px',
    },
    summaryItem: {
      marginBottom: '10px',
      padding: '10px',
      backgroundColor: '#fff',
      borderRadius: '4px',
    },
    successMessage: {
      textAlign: 'center',
      padding: '40px',
      backgroundColor: '#e8f5e9',
      borderRadius: '8px',
    },
  };

  if (submitted) {
    return (
      <div style={styles.container}>
        <div style={styles.successMessage}>
          <h2>提交成功!</h2>
          <p>您的信息已成功提交，请查看控制台输出。</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>三步表单向导</h2>
      <div style={styles.progressBar}>
        {[1, 2, 3].map(s => (
          <div
            key={s}
            style={{
              ...styles.stepIndicator,
              ...(s === step ? styles.stepActive : s < step ? styles.stepCompleted : styles.stepInactive),
            }}
          >
            {s < step ? '✓' : s}
          </div>
        ))}
      </div>

      {step === 1 && (
        <div>
          <h3>第一步: 个人信息</h3>
          <div style={styles.formGroup}>
            <label style={styles.label}>姓名 *</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => handleChange('name', e.target.value)}
              style={{ ...styles.input, ...(errors.name ? styles.inputError : {}) }}
              placeholder="请输入姓名"
            />
            {errors.name && <div style={styles.errorText}>{errors.name}</div>}
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>邮箱 *</label>
            <input
              type="email"
              value={formData.email}
              onChange={e => handleChange('email', e.target.value)}
              style={{ ...styles.input, ...(errors.email ? styles.inputError : {}) }}
              placeholder="请输入邮箱"
            />
            {errors.email && <div style={styles.errorText}>{errors.email}</div>}
          </div>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3>第二步: 地址信息</h3>
          <div style={styles.formGroup}>
            <label style={styles.label}>街道 *</label>
            <input
              type="text"
              value={formData.street}
              onChange={e => handleChange('street', e.target.value)}
              style={{ ...styles.input, ...(errors.street ? styles.inputError : {}) }}
              placeholder="请输入街道"
            />
            {errors.street && <div style={styles.errorText}>{errors.street}</div>}
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>城市 *</label>
            <input
              type="text"
              value={formData.city}
              onChange={e => handleChange('city', e.target.value)}
              style={{ ...styles.input, ...(errors.city ? styles.inputError : {}) }}
              placeholder="请输入城市"
            />
            {errors.city && <div style={styles.errorText}>{errors.city}</div>}
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>邮编 *</label>
            <input
              type="text"
              value={formData.zipcode}
              onChange={e => handleChange('zipcode', e.target.value)}
              style={{ ...styles.input, ...(errors.zipcode ? styles.inputError : {}) }}
              placeholder="请输入邮编"
            />
            {errors.zipcode && <div style={styles.errorText}>{errors.zipcode}</div>}
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <h3>第三步: 确认信息</h3>
          <div style={styles.summary}>
            <div style={styles.summaryItem}>
              <strong>姓名:</strong> {formData.name}
            </div>
            <div style={styles.summaryItem}>
              <strong>邮箱:</strong> {formData.email}
            </div>
            <div style={styles.summaryItem}>
              <strong>街道:</strong> {formData.street}
            </div>
            <div style={styles.summaryItem}>
              <strong>城市:</strong> {formData.city}
            </div>
            <div style={styles.summaryItem}>
              <strong>邮编:</strong> {formData.zipcode}
            </div>
          </div>
        </div>
      )}

      <div style={styles.buttonGroup}>
        {step > 1 ? (
          <button style={{ ...styles.button, ...styles.buttonSecondary }} onClick={handleBack}>
            上一步
          </button>
        ) : (
          <div />
        )}
        {step < 3 ? (
          <button style={{ ...styles.button, ...styles.buttonPrimary }} onClick={handleNext}>
            下一步
          </button>
        ) : (
          <button style={{ ...styles.button, ...styles.buttonPrimary }} onClick={handleSubmit}>
            提交
          </button>
        )}
      </div>
    </div>
  );
}
