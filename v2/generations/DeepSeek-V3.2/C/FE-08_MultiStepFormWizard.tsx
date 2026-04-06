import React, { useReducer, useState } from 'react';

type FormData = {
  personal: {
    name: string;
    email: string;
  };
  address: {
    street: string;
    city: string;
    zipCode: string;
  };
};

type FormErrors = {
  personal: {
    name?: string;
    email?: string;
  };
  address: {
    street?: string;
    city?: string;
    zipCode?: string;
  };
};

type Step = 1 | 2 | 3;

type Action =
  | { type: 'SET_PERSONAL_DATA'; data: Partial<FormData['personal']> }
  | { type: 'SET_ADDRESS_DATA'; data: Partial<FormData['address']> }
  | { type: 'SET_STEP'; step: Step }
  | { type: 'SET_ERRORS'; errors: Partial<FormErrors> }
  | { type: 'RESET_FORM' };

interface State {
  step: Step;
  data: FormData;
  errors: FormErrors;
  isSubmitting: boolean;
}

const initialState: State = {
  step: 1,
  data: {
    personal: {
      name: '',
      email: '',
    },
    address: {
      street: '',
      city: '',
      zipCode: '',
    },
  },
  errors: {
    personal: {},
    address: {},
  },
  isSubmitting: false,
};

function formReducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_PERSONAL_DATA':
      return {
        ...state,
        data: {
          ...state.data,
          personal: {
            ...state.data.personal,
            ...action.data,
          },
        },
        errors: {
          ...state.errors,
          personal: {},
        },
      };
    
    case 'SET_ADDRESS_DATA':
      return {
        ...state,
        data: {
          ...state.data,
          address: {
            ...state.data.address,
            ...action.data,
          },
        },
        errors: {
          ...state.errors,
          address: {},
        },
      };
    
    case 'SET_STEP':
      return {
        ...state,
        step: action.step,
      };
    
    case 'SET_ERRORS':
      return {
        ...state,
        errors: {
          personal: { ...state.errors.personal, ...action.errors.personal },
          address: { ...state.errors.address, ...action.errors.address },
        },
      };
    
    case 'RESET_FORM':
      return initialState;
    
    default:
      return state;
  }
}

const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const validatePersonalData = (data: FormData['personal']): FormErrors['personal'] => {
  const errors: FormErrors['personal'] = {};
  
  if (!data.name.trim()) {
    errors.name = '姓名不能为空';
  } else if (data.name.trim().length < 2) {
    errors.name = '姓名至少需要2个字符';
  }
  
  if (!data.email.trim()) {
    errors.email = '邮箱不能为空';
  } else if (!validateEmail(data.email)) {
    errors.email = '请输入有效的邮箱地址';
  }
  
  return errors;
};

const validateAddressData = (data: FormData['address']): FormErrors['address'] => {
  const errors: FormErrors['address'] = {};
  
  if (!data.street.trim()) {
    errors.street = '街道地址不能为空';
  }
  
  if (!data.city.trim()) {
    errors.city = '城市不能为空';
  }
  
  if (!data.zipCode.trim()) {
    errors.zipCode = '邮政编码不能为空';
  } else if (!/^\d{5,6}$/.test(data.zipCode)) {
    errors.zipCode = '请输入5-6位数字的邮政编码';
  }
  
  return errors;
};

const MultiStepFormWizard: React.FC = () => {
  const [state, dispatch] = useReducer(formReducer, initialState);
  const [submissionLog, setSubmissionLog] = useState<string[]>([]);
  
  const handlePersonalChange = (field: keyof FormData['personal'], value: string) => {
    dispatch({ 
      type: 'SET_PERSONAL_DATA', 
      data: { [field]: value } 
    });
  };
  
  const handleAddressChange = (field: keyof FormData['address'], value: string) => {
    dispatch({ 
      type: 'SET_ADDRESS_DATA', 
      data: { [field]: value } 
    });
  };
  
  const goToStep = (step: Step) => {
    dispatch({ type: 'SET_STEP', step });
  };
  
  const nextStep = () => {
    if (state.step === 1) {
      const personalErrors = validatePersonalData(state.data.personal);
      
      if (Object.keys(personalErrors).length > 0) {
        dispatch({ 
          type: 'SET_ERRORS', 
          errors: { personal: personalErrors } 
        });
        return;
      }
      
      goToStep(2);
    } else if (state.step === 2) {
      const addressErrors = validateAddressData(state.data.address);
      
      if (Object.keys(addressErrors).length > 0) {
        dispatch({ 
          type: 'SET_ERRORS', 
          errors: { address: addressErrors } 
        });
        return;
      }
      
      goToStep(3);
    }
  };
  
  const prevStep = () => {
    if (state.step === 2) {
      goToStep(1);
    } else if (state.step === 3) {
      goToStep(2);
    }
  };
  
  const handleSubmit = () => {
    const personalErrors = validatePersonalData(state.data.personal);
    const addressErrors = validateAddressData(state.data.address);
    
    const allErrors = { personal: personalErrors, address: addressErrors };
    const hasErrors = Object.keys(personalErrors).length > 0 || 
                     Object.keys(addressErrors).length > 0;
    
    if (hasErrors) {
      dispatch({ type: 'SET_ERRORS', errors: allErrors });
      goToStep(1);
      return;
    }
    
    const timestamp = new Date().toLocaleString();
    const logEntry = `[${timestamp}] 表单提交成功:\n` +
      `个人信息 - 姓名: ${state.data.personal.name}, 邮箱: ${state.data.personal.email}\n` +
      `地址信息 - 街道: ${state.data.address.street}, 城市: ${state.data.address.city}, 邮编: ${state.data.address.zipCode}`;
    
    console.log(logEntry);
    setSubmissionLog(prev => [logEntry, ...prev.slice(0, 4)]);
    
    dispatch({ type: 'RESET_FORM' });
  };
  
  const resetForm = () => {
    dispatch({ type: 'RESET_FORM' });
    setSubmissionLog([]);
  };
  
  const renderStep = () => {
    switch (state.step) {
      case 1:
        return (
          <div className="form-step">
            <h3>步骤 1: 个人信息</h3>
            <p className="step-description">请填写您的姓名和邮箱地址</p>
            
            <div className="form-group">
              <label htmlFor="name">姓名 *</label>
              <input
                id="name"
                type="text"
                value={state.data.personal.name}
                onChange={(e) => handlePersonalChange('name', e.target.value)}
                className={state.errors.personal.name ? 'error' : ''}
                placeholder="请输入您的姓名"
              />
              {state.errors.personal.name && (
                <div className="error-message">{state.errors.personal.name}</div>
              )}
            </div>
            
            <div className="form-group">
              <label htmlFor="email">邮箱 *</label>
              <input
                id="email"
                type="email"
                value={state.data.personal.email}
                onChange={(e) => handlePersonalChange('email', e.target.value)}
                className={state.errors.personal.email ? 'error' : ''}
                placeholder="example@email.com"
              />
              {state.errors.personal.email && (
                <div className="error-message">{state.errors.personal.email}</div>
              )}
            </div>
          </div>
        );
      
      case 2:
        return (
          <div className="form-step">
            <h3>步骤 2: 地址信息</h3>
            <p className="step-description">请填写您的详细地址</p>
            
            <div className="form-group">
              <label htmlFor="street">街道地址 *</label>
              <input
                id="street"
                type="text"
                value={state.data.address.street}
                onChange={(e) => handleAddressChange('street', e.target.value)}
                className={state.errors.address.street ? 'error' : ''}
                placeholder="请输入街道地址"
              />
              {state.errors.address.street && (
                <div className="error-message">{state.errors.address.street}</div>
              )}
            </div>
            
            <div className="form-group">
              <label htmlFor="city">城市 *</label>
              <input
                id="city"
                type="text"
                value={state.data.address.city}
                onChange={(e) => handleAddressChange('city', e.target.value)}
                className={state.errors.address.city ? 'error' : ''}
                placeholder="请输入城市"
              />
              {state.errors.address.city && (
                <div className="error-message">{state.errors.address.city}</div>
              )}
            </div>
            
            <div className="form-group">
              <label htmlFor="zipCode">邮政编码 *</label>
              <input
                id="zipCode"
                type="text"
                value={state.data.address.zipCode}
                onChange={(e) => handleAddressChange('zipCode', e.target.value)}
                className={state.errors.address.zipCode ? 'error' : ''}
                placeholder="5-6位数字"
              />
              {state.errors.address.zipCode && (
                <div className="error-message">{state.errors.address.zipCode}</div>
              )}
            </div>
          </div>
        );
      
      case 3:
        return (
          <div className="form-step review-step">
            <h3>步骤 3: 确认信息</h3>
            <p className="step-description">请确认您的信息是否正确</p>
            
            <div className="review-section">
              <h4>个人信息</h4>
              <div className="review-item">
                <span className="review-label">姓名:</span>
                <span className="review-value">{state.data.personal.name}</span>
              </div>
              <div className="review-item">
                <span className="review-label">邮箱:</span>
                <span className="review-value">{state.data.personal.email}</span>
              </div>
            </div>
            
            <div className="review-section">
              <h4>地址信息</h4>
              <div className="review-item">
                <span className="review-label">街道:</span>
                <span className="review-value">{state.data.address.street}</span>
              </div>
              <div className="review-item">
                <span className="review-label">城市:</span>
                <span className="review-value">{state.data.address.city}</span>
              </div>
              <div className="review-item">
                <span className="review-label">邮编:</span>
                <span className="review-value">{state.data.address.zipCode}</span>
              </div>
            </div>
            
            <div className="review-hint">
              ✅ 信息已正确填写，点击"提交"完成表单
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };
  
  const isFirstStep = state.step === 1;
  const isLastStep = state.step === 3;
  
  return (
    <div className="wizard-container">
      <h2>多步表单向导</h2>
      
      <div className="progress-indicator">
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${(state.step - 1) * 50}%` }}
          />
        </div>
        
        <div className="step-dots">
          {[1, 2, 3].map((stepNum) => (
            <div 
              key={stepNum}
              className={`step-dot ${stepNum === state.step ? 'active' : ''} ${stepNum < state.step ? 'completed' : ''}`}
              onClick={() => stepNum <= state.step && goToStep(stepNum as Step)}
            >
              <span className="step-number">{stepNum}</span>
              <span className="step-label">
                {stepNum === 1 ? '个人信息' : stepNum === 2 ? '地址信息' : '确认'}
              </span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="form-wrapper">
        {renderStep()}
        
        <div className="form-actions">
          <div className="action-buttons">
            {!isFirstStep && (
              <button
                type="button"
                className="action-button prev-button"
                onClick={prevStep}
              >
                ← 上一步
              </button>
            )}
            
            {!isLastStep ? (
              <button
                type="button"
                className="action-button next-button"
                onClick={nextStep}
              >
                下一步 →
              </button>
            ) : (
              <button
                type="button"
                className="action-button submit-button"
                onClick={handleSubmit}
              >
                提交表单
              </button>
            )}
          </div>
          
          <button
            type="button"
            className="reset-button"
            onClick={resetForm}
          >
            重置表单
          </button>
        </div>
      </div>
      
      {submissionLog.length > 0 && (
        <div className="submission-log">
          <h4>最近提交记录 (控制台输出)</h4>
          <div className="log-content">
            {submissionLog.map((log, index) => (
              <div key={index} className="log-entry">
                <pre>{log}</pre>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .wizard-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }
        
        h2 {
          color: #333;
          text-align: center;
          margin-bottom: 30px;
        }
        
        .progress-indicator {
          margin-bottom: 30px;
        }
        
        .progress-bar {
          height: 4px;
          background: #e0e0e0;
          border-radius: 2px;
          margin-bottom: 15px;
          position: relative;
        }
        
        .progress-fill {
          height: 100%;
          background: #1976d2;
          border-radius: 2px;
          transition: width 0.3s ease;
        }
        
        .step-dots {
          display: flex;
          justify-content: space-between;
          position: relative;
        }
        
        .step-dot {
          display: flex;
          flex-direction: column;
          align-items: center;
          cursor: pointer;
          position: relative;
          z-index: 1;
        }
        
        .step-dot.completed {
          cursor: pointer;
        }
        
        .step-number {
          width: 30px;
          height: 30px;
          border-radius: 50%;
          background: #e0e0e0;
          color: #666;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          margin-bottom: 5px;
          transition: all 0.3s ease;
        }
        
        .step-dot.active .step-number {
          background: #1976d2;
          color: white;
          transform: scale(1.1);
        }
        
        .step-dot.completed .step-number {
          background: #4caf50;
          color: white;
        }
        
        .step-label {
          font-size: 12px;
          color: #666;
          font-weight: 500;
          white-space: nowrap;
        }
        
        .form-wrapper {
          background: white;
          border-radius: 8px;
          padding: 25px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .form-step {
          min-height: 300px;
        }
        
        .form-step h3 {
          color: #333;
          margin-bottom: 8px;
        }
        
        .step-description {
          color: #666;
          margin-bottom: 25px;
          font-size: 14px;
        }
        
        .form-group {
          margin-bottom: 20px;
        }
        
        .form-group label {
          display: block;
          margin-bottom: 6px;
          font-weight: 500;
          color: #555;
          font-size: 14px;
        }
        
        .form-group input {
          width: 100%;
          padding: 12px 15px;
          border: 2px solid #e0e0e0;
          border-radius: 4px;
          font-size: 15px;
          transition: border-color 0.2s;
        }
        
        .form-group input:focus {
          outline: none;
          border-color: #1976d2;
        }
        
        .form-group input.error {
          border-color: #f44336;
        }
        
        .error-message {
          color: #f44336;
          font-size: 12px;
          margin-top: 5px;
        }
        
        .review-step {
          min-height: 250px;
        }
        
        .review-section {
          margin-bottom: 25px;
        }
        
        .review-section h4 {
          color: #333;
          margin-bottom: 10px;
          font-size: 16px;
          border-bottom: 1px solid #f0f0f0;
          padding-bottom: 5px;
        }
        
        .review-item {
          display: flex;
          margin-bottom: 8px;
          padding: 5px 0;
        }
        
        .review-label {
          width: 80px;
          font-weight: 500;
          color: #666;
          font-size: 14px;
        }
        
        .review-value {
          flex: 1;
          color: #333;
          font-size: 14px;
        }
        
        .review-hint {
          background: #e8f5e9;
          color: #2e7d32;
          padding: 10px 15px;
          border-radius: 4px;
          font-size: 14px;
          margin-top: 20px;
        }
        
        .form-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #f0f0f0;
        }
        
        .action-buttons {
          display: flex;
          gap: 10px;
        }
        
        .action-button {
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .prev-button {
          background: #f5f5f5;
          color: #666;
        }
        
        .prev-button:hover {
          background: #e0e0e0;
        }
        
        .next-button, .submit-button {
          background: #1976d2;
          color: white;
        }
        
        .next-button:hover, .submit-button:hover {
          background: #1565c0;
        }
        
        .reset-button {
          padding: 8px 16px;
          background: transparent;
          color: #f44336;
          border: 1px solid #f44336;
          border-radius: 4px;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .reset-button:hover {
          background: #f44336;
          color: white;
        }
        
        .submission-log {
          margin-top: 30px;
          background: #f8f9fa;
          border-radius: 8px;
          padding: 20px;
        }
        
        .submission-log h4 {
          color: #333;
          margin-bottom: 15px;
          font-size: 15px;
        }
        
        .log-content {
          max-height: 200px;
          overflow-y: auto;
          font-size: 12px;
        }
        
        .log-entry {
          background: white;
          padding: 10px;
          border-radius: 4px;
          margin-bottom: 10px;
          border: 1px solid #e0e0e0;
        }
        
        .log-entry pre {
          margin: 0;
          white-space: pre-wrap;
          word-wrap: break-word;
          font-family: 'Courier New', monospace;
          color: #333;
          font-size: 11px;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
};

export default MultiStepFormWizard;