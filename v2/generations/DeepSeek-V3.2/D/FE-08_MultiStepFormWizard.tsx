import React, { useState } from 'react';

interface PersonalInfo {
  name: string;
  email: string;
}

interface AddressInfo {
  street: string;
  city: string;
  postalCode: string;
}

interface FormData {
  personalInfo: PersonalInfo;
  addressInfo: AddressInfo;
}

interface ValidationErrors {
  personalInfo?: {
    name?: string;
    email?: string;
  };
  addressInfo?: {
    street?: string;
    city?: string;
    postalCode?: string;
  };
}

const MultiStepFormWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [formData, setFormData] = useState<FormData>({
    personalInfo: {
      name: '',
      email: ''
    },
    addressInfo: {
      street: '',
      city: '',
      postalCode: ''
    }
  });
  
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  
  const validatePersonalInfo = (): boolean => {
    const errors: ValidationErrors['personalInfo'] = {};
    
    if (!formData.personalInfo.name.trim()) {
      errors.name = '姓名不能为空';
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formData.personalInfo.email) {
      errors.email = '邮箱不能为空';
    } else if (!emailRegex.test(formData.personalInfo.email)) {
      errors.email = '邮箱格式不正确';
    }
    
    setValidationErrors(prev => ({
      ...prev,
      personalInfo: errors
    }));
    
    return Object.keys(errors).length === 0;
  };
  
  const validateAddressInfo = (): boolean => {
    const errors: ValidationErrors['addressInfo'] = {};
    
    if (!formData.addressInfo.street.trim()) {
      errors.street = '街道不能为空';
    }
    
    if (!formData.addressInfo.city.trim()) {
      errors.city = '城市不能为空';
    }
    
    if (!formData.addressInfo.postalCode.trim()) {
      errors.postalCode = '邮编不能为空';
    }
    
    setValidationErrors(prev => ({
      ...prev,
      addressInfo: errors
    }));
    
    return Object.keys(errors).length === 0;
  };
  
  const handlePersonalInfoChange = (field: keyof PersonalInfo, value: string) => {
    setFormData(prev => ({
      ...prev,
      personalInfo: {
        ...prev.personalInfo,
        [field]: value
      }
    }));
    
    if (validationErrors.personalInfo?.[field]) {
      setValidationErrors(prev => ({
        ...prev,
        personalInfo: {
          ...prev.personalInfo,
          [field]: undefined
        }
      }));
    }
  };
  
  const handleAddressInfoChange = (field: keyof AddressInfo, value: string) => {
    setFormData(prev => ({
      ...prev,
      addressInfo: {
        ...prev.addressInfo,
        [field]: value
      }
    }));
    
    if (validationErrors.addressInfo?.[field]) {
      setValidationErrors(prev => ({
        ...prev,
        addressInfo: {
          ...prev.addressInfo,
          [field]: undefined
        }
      }));
    }
  };
  
  const goToStep = (step: 1 | 2 | 3) => {
    setCurrentStep(step);
  };
  
  const handleNextStep = () => {
    if (currentStep === 1) {
      if (validatePersonalInfo()) {
        setCurrentStep(2);
      }
    } else if (currentStep === 2) {
      if (validateAddressInfo()) {
        setCurrentStep(3);
      }
    }
  };
  
  const handlePrevStep = () => {
    if (currentStep === 2) {
      setCurrentStep(1);
    } else if (currentStep === 3) {
      setCurrentStep(2);
    }
  };
  
  const handleSubmit = () => {
    const allValid = validatePersonalInfo() && validateAddressInfo();
    
    if (allValid) {
      console.log('提交的表单数据:', formData);
      alert('表单提交成功！请在控制台查看数据。');
    } else {
      alert('请先修正表单中的错误');
    }
  };
  
  const renderStepIndicator = () => {
    const steps = [
      { number: 1, label: '个人信息' },
      { number: 2, label: '地址信息' },
      { number: 3, label: '确认提交' }
    ];
    
    return (
      <div style={styles.stepIndicator}>
        {steps.map(step => (
          <React.Fragment key={step.number}>
            <div
              style={{
                ...styles.stepCircle,
                ...(step.number === currentStep ? styles.activeStepCircle : {}),
                ...(step.number < currentStep ? styles.completedStepCircle : {})
              }}
            >
              {step.number < currentStep ? '✓' : step.number}
            </div>
            <div
              style={{
                ...styles.stepLabel,
                ...(step.number === currentStep ? styles.activeStepLabel : {})
              }}
            >
              {step.label}
            </div>
            {step.number < 3 && <div style={styles.stepConnector} />}
          </React.Fragment>
        ))}
      </div>
    );
  };
  
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div style={styles.stepContent}>
            <h3 style={styles.stepTitle}>第一步：个人信息</h3>
            <p style={styles.stepDescription}>请填写您的个人信息，带*的为必填项</p>
            
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>
                姓名 <span style={styles.requiredStar}>*</span>
              </label>
              <input
                type="text"
                value={formData.personalInfo.name}
                onChange={(e) => handlePersonalInfoChange('name', e.target.value)}
                style={{
                  ...styles.formInput,
                  ...(validationErrors.personalInfo?.name ? styles.errorInput : {})
                }}
                placeholder="请输入您的姓名"
              />
              {validationErrors.personalInfo?.name && (
                <div style={styles.errorMessage}>{validationErrors.personalInfo.name}</div>
              )}
            </div>
            
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>
                邮箱 <span style={styles.requiredStar}>*</span>
              </label>
              <input
                type="email"
                value={formData.personalInfo.email}
                onChange={(e) => handlePersonalInfoChange('email', e.target.value)}
                style={{
                  ...styles.formInput,
                  ...(validationErrors.personalInfo?.email ? styles.errorInput : {})
                }}
                placeholder="example@domain.com"
              />
              {validationErrors.personalInfo?.email && (
                <div style={styles.errorMessage}>{validationErrors.personalInfo.email}</div>
              )}
            </div>
            
            <div style={styles.helpText}>
              <p>邮箱将用于接收重要通知，请确保输入正确。</p>
            </div>
          </div>
        );
      
      case 2:
        return (
          <div style={styles.stepContent}>
            <h3 style={styles.stepTitle}>第二步：地址信息</h3>
            <p style={styles.stepDescription}>请填写您的邮寄地址</p>
            
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>
                街道地址 <span style={styles.requiredStar}>*</span>
              </label>
              <input
                type="text"
                value={formData.addressInfo.street}
                onChange={(e) => handleAddressInfoChange('street', e.target.value)}
                style={{
                  ...styles.formInput,
                  ...(validationErrors.addressInfo?.street ? styles.errorInput : {})
                }}
                placeholder="例如：人民路123号"
              />
              {validationErrors.addressInfo?.street && (
                <div style={styles.errorMessage}>{validationErrors.addressInfo.street}</div>
              )}
            </div>
            
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>
                城市 <span style={styles.requiredStar}>*</span>
              </label>
              <input
                type="text"
                value={formData.addressInfo.city}
                onChange={(e) => handleAddressInfoChange('city', e.target.value)}
                style={{
                  ...styles.formInput,
                  ...(validationErrors.addressInfo?.city ? styles.errorInput : {})
                }}
                placeholder="例如：北京市"
              />
              {validationErrors.addressInfo?.city && (
                <div style={styles.errorMessage}>{validationErrors.addressInfo.city}</div>
              )}
            </div>
            
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>
                邮政编码 <span style={styles.requiredStar}>*</span>
              </label>
              <input
                type="text"
                value={formData.addressInfo.postalCode}
                onChange={(e) => handleAddressInfoChange('postalCode', e.target.value)}
                style={{
                  ...styles.formInput,
                  ...(validationErrors.addressInfo?.postalCode ? styles.errorInput : {})
                }}
                placeholder="例如：100000"
              />
              {validationErrors.addressInfo?.postalCode && (
                <div style={styles.errorMessage}>{validationErrors.addressInfo.postalCode}</div>
              )}
            </div>
            
            <div style={styles.helpText}>
              <p>地址将用于邮寄文件和物品，请确保准确无误。</p>
            </div>
          </div>
        );
      
      case 3:
        return (
          <div style={styles.stepContent}>
            <h3 style={styles.stepTitle}>第三步：确认信息</h3>
            <p style={styles.stepDescription}>请确认您的信息是否正确</p>
            
            <div style={styles.reviewSection}>
              <h4 style={styles.reviewTitle}>个人信息</h4>
              <div style={styles.reviewItem}>
                <span style={styles.reviewLabel}>姓名：</span>
                <span style={styles.reviewValue}>{formData.personalInfo.name || '未填写'}</span>
              </div>
              <div style={styles.reviewItem}>
                <span style={styles.reviewLabel}>邮箱：</span>
                <span style={styles.reviewValue}>{formData.personalInfo.email || '未填写'}</span>
              </div>
              
              <div style={styles.editLinkContainer}>
                <button
                  type="button"
                  onClick={() => goToStep(1)}
                  style={styles.editLink}
                >
                  修改个人信息
                </button>
              </div>
            </div>
            
            <div style={styles.reviewSection}>
              <h4 style={styles.reviewTitle}>地址信息</h4>
              <div style={styles.reviewItem}>
                <span style={styles.reviewLabel}>街道：</span>
                <span style={styles.reviewValue}>{formData.addressInfo.street || '未填写'}</span>
              </div>
              <div style={styles.reviewItem}>
                <span style={styles.reviewLabel}>城市：</span>
                <span style={styles.reviewValue}>{formData.addressInfo.city || '未填写'}</span>
              </div>
              <div style={styles.reviewItem}>
                <span style={styles.reviewLabel}>邮编：</span>
                <span style={styles.reviewValue}>{formData.addressInfo.postalCode || '未填写'}</span>
              </div>
              
              <div style={styles.editLinkContainer}>
                <button
                  type="button"
                  onClick={() => goToStep(2)}
                  style={styles.editLink}
                >
                  修改地址信息
                </button>
              </div>
            </div>
            
            <div style={styles.confirmationText}>
              <p>请仔细核对以上信息，确认无误后点击"提交"按钮。</p>
              <p>提交后系统将保存您的信息并发送确认通知。</p>
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };
  
  return (
    <div style={styles.container}>
      <h2 style={styles.header}>多步表单向导</h2>
      
      {renderStepIndicator()}
      
      <div style={styles.formContainer}>
        {renderStepContent()}
        
        <div style={styles.navigationButtons}>
          {currentStep > 1 && (
            <button
              type="button"
              onClick={handlePrevStep}
              style={styles.prevButton}
            >
              上一步
            </button>
          )}
          
          {currentStep < 3 ? (
            <button
              type="button"
              onClick={handleNextStep}
              style={styles.nextButton}
            >
              下一步
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              style={styles.submitButton}
            >
              提交表单
            </button>
          )}
        </div>
      </div>
      
      <div style={styles.progressInfo}>
        <div style={styles.progressBar}>
          <div 
            style={{
              ...styles.progressFill,
              width: `${(currentStep - 1) / 2 * 100}%`
            }}
          />
        </div>
        <div style={styles.progressText}>
          步骤 {currentStep} / 3 • 完成 {Math.round((currentStep - 1) / 2 * 100)}%
        </div>
      </div>
      
      <div style={styles.footer}>
        <p style={styles.footerText}>
          提示：您可以随时点击步骤指示器或使用上一步/下一步按钮在不同步骤间切换。
          所有填写的数据将自动保存，切换步骤不会丢失。
        </p>
      </div>
    </div>
  );
};

const styles = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '800px',
    margin: '0 auto',
    padding: '30px',
    backgroundColor: '#f9f9f9',
    borderRadius: '12px',
    boxShadow: '0 6px 30px rgba(0,0,0,0.08)'
  } as React.CSSProperties,
  
  header: {
    textAlign: 'center' as const,
    color: '#2c3e50',
    marginBottom: '30px',
    fontSize: '32px',
    fontWeight: 'bold' as const
  } as React.CSSProperties,
  
  stepIndicator: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '40px',
    position: 'relative' as const
  } as React.CSSProperties,
  
  stepCircle: {
    width: '50px',
    height: '50px',
    borderRadius: '50%',
    backgroundColor: '#e0e0e0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
    fontWeight: 'bold' as const,
    color: '#666',
    zIndex: 2,
    transition: 'all 0.3s ease'
  } as React.CSSProperties,
  
  activeStepCircle: {
    backgroundColor: '#3498db',
    color: 'white',
    boxShadow: '0 0 0 5px rgba(52, 152, 219, 0.2)'
  } as React.CSSProperties,
  
  completedStepCircle: {
    backgroundColor: '#2ecc71',
    color: 'white'
  } as React.CSSProperties,
  
  stepLabel: {
    position: 'absolute' as const,
    top: '60px',
    textAlign: 'center' as const,
    width: '100px',
    left: '-25px',
    color: '#999',
    fontSize: '14px',
    fontWeight: '500' as const
  } as React.CSSProperties,
  
  activeStepLabel: {
    color: '#3498db',
    fontWeight: 'bold' as const
  } as React.CSSProperties,
  
  stepConnector: {
    flex: 1,
    height: '3px',
    backgroundColor: '#e0e0e0',
    margin: '0 10px'
  } as React.CSSProperties,
  
  formContainer: {
    backgroundColor: 'white',
    padding: '30px',
    borderRadius: '10px',
    boxShadow: '0 4px 15px rgba(0,0,0,0.05)',
    marginBottom: '30px'
  } as React.CSSProperties,
  
  stepContent: {
    minHeight: '300px'
  } as React.CSSProperties,
  
  stepTitle: {
    color: '#2c3e50',
    marginBottom: '10px',
    fontSize: '22px',
    fontWeight: '600' as const
  } as React.CSSProperties,
  
  stepDescription: {
    color: '#7f8c8d',
    marginBottom: '25px',
    fontSize: '15px'
  } as React.CSSProperties,
  
  formGroup: {
    marginBottom: '25px'
  } as React.CSSProperties,
  
  formLabel: {
    display: 'block',
    marginBottom: '8px',
    color: '#34495e',
    fontSize: '16px',
    fontWeight: '500' as const
  } as React.CSSProperties,
  
  requiredStar: {
    color: '#e74c3c'
  } as React.CSSProperties,
  
  formInput: {
    width: '100%',
    padding: '12px 15px',
    fontSize: '16px',
    border: '2px solid #ddd',
    borderRadius: '6px',
    transition: 'border-color 0.3s ease',
    boxSizing: 'border-box' as const
  } as React.CSSProperties,
  
  errorInput: {
    borderColor: '#e74c3c',
    backgroundColor: '#fff9f9'
  } as React.CSSProperties,
  
  errorMessage: {
    color: '#e74c3c',
    fontSize: '14px',
    marginTop: '6px'
  } as React.CSSProperties,
  
  helpText: {
    marginTop: '25px',
    padding: '15px',
    backgroundColor: '#f8f9fa',
    borderRadius: '6px',
    borderLeft: '4px solid #3498db'
  } as React.CSSProperties,
  
  reviewSection: {
    marginBottom: '30px',
    padding: '20px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px'
  } as React.CSSProperties,
  
  reviewTitle: {
    color: '#2c3e50',
    marginBottom: '15px',
    fontSize: '18px',
    fontWeight: '600' as const
  } as React.CSSProperties,
  
  reviewItem: {
    display: 'flex',
    marginBottom: '10px',
    padding: '8px 0'
  } as React.CSSProperties,
  
  reviewLabel: {
    color: '#7f8c8d',
    width: '100px',
    fontWeight: '500' as const
  } as React.CSSProperties,
  
  reviewValue: {
    color: '#2c3e50',
    flex: 1,
    fontWeight: '500' as const
  } as React.CSSProperties,
  
  editLinkContainer: {
    marginTop: '15px',
    textAlign: 'right' as const
  } as React.CSSProperties,
  
  editLink: {
    background: 'none',
    border: 'none',
    color: '#3498db',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500' as const,
    padding: '5px 10px',
    textDecoration: 'underline'
  } as React.CSSProperties,
  
  confirmationText: {
    color: '#666',
    lineHeight: '1.6',
    fontSize: '15px'
  } as React.CSSProperties,
  
  navigationButtons: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '30px',
    paddingTop: '25px',
    borderTop: '1px solid #eee'
  } as React.CSSProperties,
  
  prevButton: {
    padding: '12px 30px',
    fontSize: '16px',
    backgroundColor: '#f8f9fa',
    color: '#495057',
    border: '2px solid #dee2e6',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500' as const,
    transition: 'all 0.2s ease'
  } as React.CSSProperties,
  
  nextButton: {
    padding: '12px 30px',
    fontSize: '16px',
    backgroundColor: '#3498db',
    color: 'white',
    border: '2px solid #2980b9',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500' as const,
    transition: 'all 0.2s ease',
    marginLeft: 'auto'
  } as React.CSSProperties,
  
  submitButton: {
    padding: '12px 40px',
    fontSize: '16px',
    backgroundColor: '#2ecc71',
    color: 'white',
    border: '2px solid #27ae60',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500' as const,
    transition: 'all 0.2s ease',
    marginLeft: 'auto'
  } as React.CSSProperties,
  
  progressInfo: {
    marginBottom: '20px'
  } as React.CSSProperties,
  
  progressBar: {
    height: '8px',
    backgroundColor: '#e0e0e0',
    borderRadius: '4px',
    marginBottom: '10px',
    overflow: 'hidden' as const
  } as React.CSSProperties,
  
  progressFill: {
    height: '100%',
    backgroundColor: '#3498db',
    transition: 'width 0.5s ease'
  } as React.CSSProperties,
  
  progressText: {
    textAlign: 'center' as const,
    color: '#7f8c8d',
    fontSize: '14px'
  } as React.CSSProperties,
  
  footer: {
    marginTop: '20px',
    padding: '15px',
    backgroundColor: '#f0f7ff',
    borderRadius: '8px',
    borderLeft: '4px solid #3498db'
  } as React.CSSProperties,
  
  footerText: {
    color: '#666',
    fontSize: '14px',
    lineHeight: '1.6',
    margin: 0
  } as React.CSSProperties
};

export default MultiStepFormWizard;