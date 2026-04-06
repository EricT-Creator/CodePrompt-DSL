import React, { useState, useCallback } from 'react';

/* ===== 三步表单向导 ===== */

interface PersonalInfo {
  name: string;
  email: string;
}

interface AddressInfo {
  street: string;
  city: string;
  zip: string;
}

type FormErrors = Record<string, string>;

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateZip(zip: string): boolean {
  return /^\d{5,6}$/.test(zip);
}

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [personal, setPersonal] = useState<PersonalInfo>({ name: '', email: '' });
  const [address, setAddress] = useState<AddressInfo>({ street: '', city: '', zip: '' });
  const [errors, setErrors] = useState<FormErrors>({});

  const updatePersonal = useCallback((field: keyof PersonalInfo, value: string) => {
    setPersonal((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const updateAddress = useCallback((field: keyof AddressInfo, value: string) => {
    setAddress((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const validateStep1 = useCallback((): boolean => {
    const errs: FormErrors = {};
    if (!personal.name.trim()) errs.name = '姓名为必填项';
    if (!personal.email.trim()) errs.email = '邮箱为必填项';
    else if (!validateEmail(personal.email)) errs.email = '邮箱格式不正确';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }, [personal]);

  const validateStep2 = useCallback((): boolean => {
    const errs: FormErrors = {};
    if (!address.street.trim()) errs.street = '街道为必填项';
    if (!address.city.trim()) errs.city = '城市为必填项';
    if (!address.zip.trim()) errs.zip = '邮编为必填项';
    else if (!validateZip(address.zip)) errs.zip = '邮编格式不正确（5-6位数字）';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }, [address]);

  const handleNext = useCallback(() => {
    if (step === 1 && validateStep1()) setStep(2);
    else if (step === 2 && validateStep2()) setStep(3);
  }, [step, validateStep1, validateStep2]);

  const handleBack = useCallback(() => {
    if (step === 2) setStep(1);
    else if (step === 3) setStep(2);
  }, [step]);

  const handleSubmit = useCallback(() => {
    console.log('表单提交数据:', { personal, address });
    alert('提交成功！数据已输出到控制台。');
  }, [personal, address]);

  const inputStyle = (hasError: boolean): React.CSSProperties => ({
    width: '100%',
    padding: '10px 14px',
    border: hasError ? '2px solid #e74c3c' : '1px solid #d0d5dd',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
    boxSizing: 'border-box' as const,
    fontFamily: 'inherit',
    background: hasError ? '#fef5f5' : '#fff',
  });

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: '#555',
    marginBottom: '6px',
  };

  const errorStyle: React.CSSProperties = {
    fontSize: '12px',
    color: '#e74c3c',
    marginTop: '4px',
  };

  const btnStyle = (primary: boolean, disabled?: boolean): React.CSSProperties => ({
    padding: '10px 24px',
    border: primary ? 'none' : '1px solid #d0d5dd',
    borderRadius: '8px',
    background: disabled ? '#e0e0e0' : primary ? '#4a90d9' : '#fff',
    color: disabled ? '#999' : primary ? '#fff' : '#555',
    fontSize: '14px',
    fontWeight: 500,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.15s ease',
  });

  const renderStepIndicator = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0', marginBottom: '32px' }}>
      {[
        { num: 1, label: '个人信息' },
        { num: 2, label: '地址信息' },
        { num: 3, label: '确认提交' },
      ].map((s, idx) => (
        <React.Fragment key={s.num}>
          {idx > 0 && (
            <div style={{ flex: '0 0 40px', height: '2px', background: step > s.num ? '#4a90d9' : '#e0e0e0', margin: '0 8px' }} />
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              fontWeight: 600,
              background: step >= s.num ? '#4a90d9' : '#e8eaed',
              color: step >= s.num ? '#fff' : '#999',
              transition: 'all 0.2s ease',
            }}>
              {step > s.num ? '✓' : s.num}
            </div>
            <span style={{ fontSize: '14px', fontWeight: step === s.num ? 600 : 400, color: step >= s.num ? '#333' : '#999' }}>
              {s.label}
            </span>
          </div>
        </React.Fragment>
      ))}
    </div>
  );

  const renderStep1 = () => (
    <div>
      <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>个人信息</h3>
      <div style={{ marginBottom: '20px' }}>
        <label style={labelStyle}>姓名 <span style={{ color: '#e74c3c' }}>*</span></label>
        <input
          style={inputStyle(!!errors.name)}
          placeholder="请输入姓名"
          value={personal.name}
          onChange={(e) => updatePersonal('name', e.target.value)}
        />
        {errors.name && <div style={errorStyle}>{errors.name}</div>}
      </div>
      <div>
        <label style={labelStyle}>邮箱 <span style={{ color: '#e74c3c' }}>*</span></label>
        <input
          style={inputStyle(!!errors.email)}
          type="email"
          placeholder="请输入邮箱"
          value={personal.email}
          onChange={(e) => updatePersonal('email', e.target.value)}
        />
        {errors.email && <div style={errorStyle}>{errors.email}</div>}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div>
      <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>地址信息</h3>
      <div style={{ marginBottom: '20px' }}>
        <label style={labelStyle}>街道 <span style={{ color: '#e74c3c' }}>*</span></label>
        <input
          style={inputStyle(!!errors.street)}
          placeholder="请输入街道地址"
          value={address.street}
          onChange={(e) => updateAddress('street', e.target.value)}
        />
        {errors.street && <div style={errorStyle}>{errors.street}</div>}
      </div>
      <div style={{ display: 'flex', gap: '16px' }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>城市 <span style={{ color: '#e74c3c' }}>*</span></label>
          <input
            style={inputStyle(!!errors.city)}
            placeholder="请输入城市"
            value={address.city}
            onChange={(e) => updateAddress('city', e.target.value)}
          />
          {errors.city && <div style={errorStyle}>{errors.city}</div>}
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>邮编 <span style={{ color: '#e74c3c' }}>*</span></label>
          <input
            style={inputStyle(!!errors.zip)}
            placeholder="请输入邮编"
            value={address.zip}
            onChange={(e) => updateAddress('zip', e.target.value)}
          />
          {errors.zip && <div style={errorStyle}>{errors.zip}</div>}
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div>
      <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>确认信息</h3>
      <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '20px', border: '1px solid #e8eaed' }}>
        <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>个人信息</h4>
        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', color: '#888', width: '60px' }}>姓名:</span>
            <span style={{ fontSize: '14px', color: '#333', fontWeight: 500 }}>{personal.name || '—'}</span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span style={{ fontSize: '14px', color: '#888', width: '60px' }}>邮箱:</span>
            <span style={{ fontSize: '14px', color: '#333', fontWeight: 500 }}>{personal.email || '—'}</span>
          </div>
        </div>

        <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>地址信息</h4>
        <div>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', color: '#888', width: '60px' }}>街道:</span>
            <span style={{ fontSize: '14px', color: '#333', fontWeight: 500 }}>{address.street || '—'}</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', color: '#888', width: '60px' }}>城市:</span>
            <span style={{ fontSize: '14px', color: '#333', fontWeight: 500 }}>{address.city || '—'}</span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span style={{ fontSize: '14px', color: '#888', width: '60px' }}>邮编:</span>
            <span style={{ fontSize: '14px', color: '#333', fontWeight: 500 }}>{address.zip || '—'}</span>
          </div>
        </div>
      </div>
    </div>
  );

  const steps: Record<number, () => React.ReactNode> = {
    1: renderStep1,
    2: renderStep2,
    3: renderStep3,
  };

  return (
    <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', maxWidth: '520px', margin: '40px auto', padding: '0 16px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px', color: '#1a1a1a' }}>三步表单向导</h2>
      <p style={{ fontSize: '13px', color: '#888', marginBottom: '24px' }}>请依次填写信息，带 <span style={{ color: '#e74c3c' }}>*</span> 为必填项</p>

      <div style={{ background: '#fff', border: '1px solid #e8eaed', borderRadius: '12px', padding: '28px' }}>
        {renderStepIndicator()}
        {steps[step]()}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '32px', paddingTop: '20px', borderTop: '1px solid #f0f0f0' }}>
          {step > 1 ? (
            <button style={btnStyle(false)} onClick={handleBack}>← 上一步</button>
          ) : (
            <div />
          )}
          {step < 3 ? (
            <button style={btnStyle(true)} onClick={handleNext}>下一步 →</button>
          ) : (
            <button style={btnStyle(true)} onClick={handleSubmit}>✓ 提交</button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MultiStepFormWizard;
