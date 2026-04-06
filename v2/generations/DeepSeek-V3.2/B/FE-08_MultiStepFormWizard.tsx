import React, { useState } from 'react';
import './MultiStepFormWizard.css';

interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface AddressInfo {
  street: string;
  city: string;
  zipCode: string;
  country: string;
}

type Step = 1 | 2 | 3;

const MultiStepFormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [personalInfo, setPersonalInfo] = useState<PersonalInfo>({
    name: '',
    email: '',
    phone: '',
  });
  const [addressInfo, setAddressInfo] = useState<AddressInfo>({
    street: '',
    city: '',
    zipCode: '',
    country: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!personalInfo.name.trim()) {
      newErrors.name = '姓名不能为空';
    } else if (personalInfo.name.trim().length < 2) {
      newErrors.name = '姓名至少需要2个字符';
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!personalInfo.email.trim()) {
      newErrors.email = '邮箱不能为空';
    } else if (!emailRegex.test(personalInfo.email)) {
      newErrors.email = '请输入有效的邮箱地址';
    }

    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    if (!personalInfo.phone.trim()) {
      newErrors.phone = '电话号码不能为空';
    } else if (!phoneRegex.test(personalInfo.phone.replace(/\s+/g, ''))) {
      newErrors.phone = '请输入有效的电话号码';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!addressInfo.street.trim()) {
      newErrors.street = '街道地址不能为空';
    }

    if (!addressInfo.city.trim()) {
      newErrors.city = '城市不能为空';
    }

    if (!addressInfo.zipCode.trim()) {
      newErrors.zipCode = '邮政编码不能为空';
    } else if (!/^\d{5,6}$/.test(addressInfo.zipCode)) {
      newErrors.zipCode = '请输入5-6位数字的邮政编码';
    }

    if (!addressInfo.country.trim()) {
      newErrors.country = '国家不能为空';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (currentStep === 1) {
      if (!validateStep1()) return;
    } else if (currentStep === 2) {
      if (!validateStep2()) return;
    }

    if (currentStep < 3) {
      setCurrentStep((prev) => (prev + 1) as Step);
      setErrors({});
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as Step);
      setErrors({});
    }
  };

  const handleSubmit = () => {
    const allData = {
      personalInfo,
      addressInfo,
    };
    console.log('提交的数据:', allData);
    alert('表单提交成功！数据已打印到控制台。');
  };

  const handlePersonalInfoChange = (field: keyof PersonalInfo, value: string) => {
    setPersonalInfo((prev) => ({
      ...prev,
      [field]: value,
    }));
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleAddressInfoChange = (field: keyof AddressInfo, value: string) => {
    setAddressInfo((prev) => ({
      ...prev,
      [field]: value,
    }));
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const renderStep1 = () => (
    <div className="form-step">
      <h3>第一步：个人信息</h3>
      <div className="form-group">
        <label htmlFor="name">姓名 *</label>
        <input
          id="name"
          type="text"
          value={personalInfo.name}
          onChange={(e) => handlePersonalInfoChange('name', e.target.value)}
          className={errors.name ? 'error' : ''}
        />
        {errors.name && <span className="error-message">{errors.name}</span>}
      </div>
      <div className="form-group">
        <label htmlFor="email">邮箱 *</label>
        <input
          id="email"
          type="email"
          value={personalInfo.email}
          onChange={(e) => handlePersonalInfoChange('email', e.target.value)}
          className={errors.email ? 'error' : ''}
        />
        {errors.email && <span className="error-message">{errors.email}</span>}
      </div>
      <div className="form-group">
        <label htmlFor="phone">电话 *</label>
        <input
          id="phone"
          type="tel"
          value={personalInfo.phone}
          onChange={(e) => handlePersonalInfoChange('phone', e.target.value)}
          className={errors.phone ? 'error' : ''}
        />
        {errors.phone && <span className="error-message">{errors.phone}</span>}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="form-step">
      <h3>第二步：地址信息</h3>
      <div className="form-group">
        <label htmlFor="street">街道地址 *</label>
        <input
          id="street"
          type="text"
          value={addressInfo.street}
          onChange={(e) => handleAddressInfoChange('street', e.target.value)}
          className={errors.street ? 'error' : ''}
        />
        {errors.street && <span className="error-message">{errors.street}</span>}
      </div>
      <div className="form-group">
        <label htmlFor="city">城市 *</label>
        <input
          id="city"
          type="text"
          value={addressInfo.city}
          onChange={(e) => handleAddressInfoChange('city', e.target.value)}
          className={errors.city ? 'error' : ''}
        />
        {errors.city && <span className="error-message">{errors.city}</span>}
      </div>
      <div className="form-group">
        <label htmlFor="zipCode">邮政编码 *</label>
        <input
          id="zipCode"
          type="text"
          value={addressInfo.zipCode}
          onChange={(e) => handleAddressInfoChange('zipCode', e.target.value)}
          className={errors.zipCode ? 'error' : ''}
        />
        {errors.zipCode && <span className="error-message">{errors.zipCode}</span>}
      </div>
      <div className="form-group">
        <label htmlFor="country">国家 *</label>
        <input
          id="country"
          type="text"
          value={addressInfo.country}
          onChange={(e) => handleAddressInfoChange('country', e.target.value)}
          className={errors.country ? 'error' : ''}
        />
        {errors.country && <span className="error-message">{errors.country}</span>}
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="form-step">
      <h3>第三步：确认信息</h3>
      <div className="summary">
        <h4>个人信息</h4>
        <p><strong>姓名:</strong> {personalInfo.name}</p>
        <p><strong>邮箱:</strong> {personalInfo.email}</p>
        <p><strong>电话:</strong> {personalInfo.phone}</p>

        <h4>地址信息</h4>
        <p><strong>街道地址:</strong> {addressInfo.street}</p>
        <p><strong>城市:</strong> {addressInfo.city}</p>
        <p><strong>邮政编码:</strong> {addressInfo.zipCode}</p>
        <p><strong>国家:</strong> {addressInfo.country}</p>
      </div>
    </div>
  );

  return (
    <div className="multi-step-form-wizard">
      <div className="wizard-header">
        <h2>多步表单向导</h2>
        <div className="step-indicator">
          <div className={`step ${currentStep >= 1 ? 'active' : ''}`}>
            <span className="step-number">1</span>
            <span className="step-label">个人信息</span>
          </div>
          <div className={`step-line ${currentStep >= 2 ? 'active' : ''}`}></div>
          <div className={`step ${currentStep >= 2 ? 'active' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-label">地址信息</span>
          </div>
          <div className={`step-line ${currentStep >= 3 ? 'active' : ''}`}></div>
          <div className={`step ${currentStep >= 3 ? 'active' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-label">确认</span>
          </div>
        </div>
      </div>

      <div className="wizard-content">
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
      </div>

      <div className="wizard-footer">
        <div className="button-group">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 1}
            className="back-button"
          >
            上一步
          </button>
          {currentStep < 3 ? (
            <button
              type="button"
              onClick={handleNext}
              className="next-button"
            >
              下一步
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              className="submit-button"
            >
              提交
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MultiStepFormWizard;