import React, { useReducer } from 'react';

interface FormData {
  personalInfo: {
    name: string;
    email: string;
  };
  address: {
    street: string;
    city: string;
    zipCode: string;
  };
}

interface FormErrors {
  personalInfo: {
    name: string;
    email: string;
  };
  address: {
    street: string;
    city: string;
    zipCode: string;
  };
}

interface FormState {
  currentStep: number;
  formData: FormData;
  errors: FormErrors;
}

type Action =
  | { type: 'SET_STEP'; step: number }
  | { type: 'UPDATE_PERSONAL_INFO'; field: keyof FormData['personalInfo']; value: string }
  | { type: 'UPDATE_ADDRESS'; field: keyof FormData['address']; value: string }
  | { type: 'VALIDATE_STEP' };

const initialState: FormState = {
  currentStep: 1,
  formData: {
    personalInfo: {
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
    personalInfo: {
      name: '',
      email: '',
    },
    address: {
      street: '',
      city: '',
      zipCode: '',
    },
  },
};

const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const validateZipCode = (zipCode: string): boolean => {
  const zipCodeRegex = /^\d{5}(-\d{4})?$/;
  return zipCodeRegex.test(zipCode);
};

const formReducer = (state: FormState, action: Action): FormState => {
  switch (action.type) {
    case 'SET_STEP': {
      return {
        ...state,
        currentStep: action.step,
      };
    }

    case 'UPDATE_PERSONAL_INFO': {
      return {
        ...state,
        formData: {
          ...state.formData,
          personalInfo: {
            ...state.formData.personalInfo,
            [action.field]: action.value,
          },
        },
        errors: {
          ...state.errors,
          personalInfo: {
            ...state.errors.personalInfo,
            [action.field]: '',
          },
        },
      };
    }

    case 'UPDATE_ADDRESS': {
      return {
        ...state,
        formData: {
          ...state.formData,
          address: {
            ...state.formData.address,
            [action.field]: action.value,
          },
        },
        errors: {
          ...state.errors,
          address: {
            ...state.errors.address,
            [action.field]: '',
          },
        },
      };
    }

    case 'VALIDATE_STEP': {
      const newErrors = { ...state.errors };

      if (state.currentStep === 1) {
        // Validate personal info
        if (!state.formData.personalInfo.name.trim()) {
          newErrors.personalInfo.name = 'Name is required';
        }

        if (!state.formData.personalInfo.email.trim()) {
          newErrors.personalInfo.email = 'Email is required';
        } else if (!validateEmail(state.formData.personalInfo.email)) {
          newErrors.personalInfo.email = 'Invalid email format';
        }
      }

      if (state.currentStep === 2) {
        // Validate address
        if (!state.formData.address.street.trim()) {
          newErrors.address.street = 'Street is required';
        }

        if (!state.formData.address.city.trim()) {
          newErrors.address.city = 'City is required';
        }

        if (!state.formData.address.zipCode.trim()) {
          newErrors.address.zipCode = 'ZIP Code is required';
        } else if (!validateZipCode(state.formData.address.zipCode)) {
          newErrors.address.zipCode = 'Invalid ZIP Code format (e.g., 12345 or 12345-6789)';
        }
      }

      return {
        ...state,
        errors: newErrors,
      };
    }

    default:
      return state;
  }
};

const MultiStepFormWizard: React.FC = () => {
  const [state, dispatch] = useReducer(formReducer, initialState);

  const handleNext = () => {
    // Validate current step
    dispatch({ type: 'VALIDATE_STEP' });

    // Check if there are any errors
    let hasErrors = false;
    if (state.currentStep === 1) {
      hasErrors = Object.values(state.errors.personalInfo).some(error => error !== '');
    } else if (state.currentStep === 2) {
      hasErrors = Object.values(state.errors.address).some(error => error !== '');
    }

    if (!hasErrors && state.currentStep < 3) {
      dispatch({ type: 'SET_STEP', step: state.currentStep + 1 });
    }
  };

  const handleBack = () => {
    if (state.currentStep > 1) {
      dispatch({ type: 'SET_STEP', step: state.currentStep - 1 });
    }
  };

  const handleSubmit = () => {
    console.log('Form submitted with data:', state.formData);
    alert('Form submitted successfully! Check console for data.');
  };

  const renderStep1 = () => (
    <div style={styles.stepContainer}>
      <h3 style={styles.stepTitle}>Step 1: Personal Information</h3>
      
      <div style={styles.formGroup}>
        <label style={styles.label} htmlFor="name">
          Full Name *
        </label>
        <input
          id="name"
          type="text"
          value={state.formData.personalInfo.name}
          onChange={(e) => dispatch({ 
            type: 'UPDATE_PERSONAL_INFO', 
            field: 'name', 
            value: e.target.value 
          })}
          style={{
            ...styles.input,
            borderColor: state.errors.personalInfo.name ? '#dc3545' : '#ddd',
          }}
        />
        {state.errors.personalInfo.name && (
          <div style={styles.error}>{state.errors.personalInfo.name}</div>
        )}
      </div>

      <div style={styles.formGroup}>
        <label style={styles.label} htmlFor="email">
          Email Address *
        </label>
        <input
          id="email"
          type="email"
          value={state.formData.personalInfo.email}
          onChange={(e) => dispatch({ 
            type: 'UPDATE_PERSONAL_INFO', 
            field: 'email', 
            value: e.target.value 
          })}
          style={{
            ...styles.input,
            borderColor: state.errors.personalInfo.email ? '#dc3545' : '#ddd',
          }}
          placeholder="user@example.com"
        />
        {state.errors.personalInfo.email && (
          <div style={styles.error}>{state.errors.personalInfo.email}</div>
        )}
      </div>

      <div style={styles.note}>
        * Required fields
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div style={styles.stepContainer}>
      <h3 style={styles.stepTitle}>Step 2: Address Information</h3>
      
      <div style={styles.formGroup}>
        <label style={styles.label} htmlFor="street">
          Street Address *
        </label>
        <input
          id="street"
          type="text"
          value={state.formData.address.street}
          onChange={(e) => dispatch({ 
            type: 'UPDATE_ADDRESS', 
            field: 'street', 
            value: e.target.value 
          })}
          style={{
            ...styles.input,
            borderColor: state.errors.address.street ? '#dc3545' : '#ddd',
          }}
          placeholder="123 Main St"
        />
        {state.errors.address.street && (
          <div style={styles.error}>{state.errors.address.street}</div>
        )}
      </div>

      <div style={styles.formGroup}>
        <label style={styles.label} htmlFor="city">
          City *
        </label>
        <input
          id="city"
          type="text"
          value={state.formData.address.city}
          onChange={(e) => dispatch({ 
            type: 'UPDATE_ADDRESS', 
            field: 'city', 
            value: e.target.value 
          })}
          style={{
            ...styles.input,
            borderColor: state.errors.address.city ? '#dc3545' : '#ddd',
          }}
          placeholder="New York"
        />
        {state.errors.address.city && (
          <div style={styles.error}>{state.errors.address.city}</div>
        )}
      </div>

      <div style={styles.formGroup}>
        <label style={styles.label} htmlFor="zipCode">
          ZIP Code *
        </label>
        <input
          id="zipCode"
          type="text"
          value={state.formData.address.zipCode}
          onChange={(e) => dispatch({ 
            type: 'UPDATE_ADDRESS', 
            field: 'zipCode', 
            value: e.target.value 
          })}
          style={{
            ...styles.input,
            borderColor: state.errors.address.zipCode ? '#dc3545' : '#ddd',
          }}
          placeholder="12345 or 12345-6789"
        />
        {state.errors.address.zipCode && (
          <div style={styles.error}>{state.errors.address.zipCode}</div>
        )}
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div style={styles.stepContainer}>
      <h3 style={styles.stepTitle}>Step 3: Review & Confirm</h3>
      
      <div style={styles.reviewContainer}>
        <div style={styles.reviewSection}>
          <h4 style={styles.reviewSectionTitle}>Personal Information</h4>
          <div style={styles.reviewItem}>
            <strong>Name:</strong> {state.formData.personalInfo.name || 'Not provided'}
          </div>
          <div style={styles.reviewItem}>
            <strong>Email:</strong> {state.formData.personalInfo.email || 'Not provided'}
          </div>
        </div>

        <div style={styles.reviewSection}>
          <h4 style={styles.reviewSectionTitle}>Address Information</h4>
          <div style={styles.reviewItem}>
            <strong>Street:</strong> {state.formData.address.street || 'Not provided'}
          </div>
          <div style={styles.reviewItem}>
            <strong>City:</strong> {state.formData.address.city || 'Not provided'}
          </div>
          <div style={styles.reviewItem}>
            <strong>ZIP Code:</strong> {state.formData.address.zipCode || 'Not provided'}
          </div>
        </div>
      </div>

      <div style={styles.confirmationNote}>
        Please review all information above before submitting. Once submitted, this data will be logged to the console.
      </div>
    </div>
  );

  const renderProgress = () => (
    <div style={styles.progressContainer}>
      <div style={styles.progressSteps}>
        {[1, 2, 3].map((step) => (
          <div key={step} style={styles.progressStep}>
            <div
              style={{
                ...styles.progressCircle,
                backgroundColor: state.currentStep >= step ? '#007bff' : '#e9ecef',
                color: state.currentStep >= step ? '#fff' : '#666',
              }}
            >
              {step}
            </div>
            <div style={styles.progressLabel}>
              {step === 1 && 'Personal Info'}
              {step === 2 && 'Address'}
              {step === 3 && 'Review'}
            </div>
          </div>
        ))}
      </div>
      <div style={styles.progressLine} />
    </div>
  );

  const renderButtons = () => (
    <div style={styles.buttonContainer}>
      {state.currentStep > 1 && (
        <button
          onClick={handleBack}
          style={styles.secondaryButton}
        >
          Back
        </button>
      )}
      
      {state.currentStep < 3 ? (
        <button
          onClick={handleNext}
          style={styles.primaryButton}
        >
          Next
        </button>
      ) : (
        <button
          onClick={handleSubmit}
          style={styles.submitButton}
        >
          Submit Form
        </button>
      )}
    </div>
  );

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Multi-Step Form Wizard</h2>
      
      {renderProgress()}
      
      <div style={styles.formContainer}>
        {state.currentStep === 1 && renderStep1()}
        {state.currentStep === 2 && renderStep2()}
        {state.currentStep === 3 && renderStep3()}
      </div>
      
      {renderButtons()}
      
      <div style={styles.footer}>
        <div style={styles.footerInfo}>
          <div>Current Step: {state.currentStep} of 3</div>
          <div>Data preserved when navigating back</div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '30px',
    fontFamily: 'Arial, sans-serif',
  },
  title: {
    textAlign: 'center' as const,
    color: '#333',
    marginBottom: '30px',
    fontSize: '28px',
  },
  progressContainer: {
    position: 'relative' as const,
    marginBottom: '40px',
  },
  progressSteps: {
    display: 'flex' as const,
    justifyContent: 'space-between' as const,
    position: 'relative' as const,
    zIndex: 2,
  },
  progressStep: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    alignItems: 'center' as const,
  },
  progressCircle: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    fontWeight: 'bold' as const,
    fontSize: '18px',
    transition: 'all 0.3s ease',
  },
  progressLabel: {
    marginTop: '8px',
    fontSize: '14px',
    color: '#666',
    textAlign: 'center' as const,
  },
  progressLine: {
    position: 'absolute' as const,
    top: '20px',
    left: '20px',
    right: '20px',
    height: '2px',
    backgroundColor: '#e9ecef',
    zIndex: 1,
  },
  formContainer: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    padding: '30px',
    border: '1px solid #e9ecef',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
    marginBottom: '30px',
  },
  stepContainer: {
    minHeight: '300px',
  },
  stepTitle: {
    color: '#333',
    marginBottom: '30px',
    paddingBottom: '15px',
    borderBottom: '2px solid #007bff',
  },
  formGroup: {
    marginBottom: '25px',
  },
  label: {
    display: 'block' as const,
    marginBottom: '8px',
    color: '#555',
    fontWeight: 'bold' as const,
    fontSize: '14px',
  },
  input: {
    width: '100%',
    padding: '12px 15px',
    borderRadius: '6px',
    border: '1px solid #ddd',
    fontSize: '16px',
    transition: 'border-color 0.3s',
  },
  error: {
    color: '#dc3545',
    fontSize: '14px',
    marginTop: '5px',
  },
  note: {
    fontSize: '14px',
    color: '#666',
    fontStyle: 'italic' as const,
    marginTop: '20px',
  },
  reviewContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    padding: '20px',
  },
  reviewSection: {
    marginBottom: '25px',
  },
  reviewSectionTitle: {
    color: '#495057',
    marginBottom: '15px',
    borderBottom: '1px solid #dee2e6',
    paddingBottom: '8px',
  },
  reviewItem: {
    marginBottom: '10px',
    color: '#6c757d',
  },
  confirmationNote: {
    backgroundColor: '#d1ecf1',
    color: '#0c5460',
    padding: '15px',
    borderRadius: '6px',
    marginTop: '20px',
    fontSize: '14px',
    border: '1px solid #bee5eb',
  },
  buttonContainer: {
    display: 'flex' as const,
    justifyContent: 'space-between' as const,
    alignItems: 'center' as const,
    padding: '0 10px',
  },
  primaryButton: {
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    padding: '12px 30px',
    borderRadius: '6px',
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'background-color 0.3s',
  },
  secondaryButton: {
    backgroundColor: '#6c757d',
    color: 'white',
    border: 'none',
    padding: '12px 30px',
    borderRadius: '6px',
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'background-color 0.3s',
  },
  submitButton: {
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    padding: '12px 30px',
    borderRadius: '6px',
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'background-color 0.3s',
  },
  footer: {
    marginTop: '30px',
    paddingTop: '20px',
    borderTop: '1px solid #e9ecef',
  },
  footerInfo: {
    display: 'flex' as const,
    justifyContent: 'space-between' as const,
    fontSize: '14px',
    color: '#666',
  },
};

export default MultiStepFormWizard;