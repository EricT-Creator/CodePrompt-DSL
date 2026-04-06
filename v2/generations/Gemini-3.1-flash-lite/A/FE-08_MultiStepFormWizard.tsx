import React, { useState } from 'react';

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState(1);
  const [data, setData] = useState({ name: '', email: '', street: '', city: '', zip: '' });
  const [errors, setErrors] = useState<string[]>([]);

  const validate = () => {
    let newErrors: string[] = [];
    if (step === 1) {
      if (!data.name) newErrors.push('Name is required');
      if (!/^\S+@\S+\.\S+$/.test(data.email)) newErrors.push('Email is invalid');
    } else if (step === 2) {
      if (!data.street || !data.city || !data.zip) newErrors.push('All address fields are required');
    }
    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const nextStep = () => { if (validate()) setStep(step + 1); };
  const prevStep = () => setStep(step - 1);

  return (
    <div style={{ padding: '20px' }}>
      {step === 1 && (
        <div>
          <h3>Personal Info</h3>
          <input value={data.name} onChange={(e) => setData({...data, name: e.target.value})} placeholder="Name" />
          <input value={data.email} onChange={(e) => setData({...data, email: e.target.value})} placeholder="Email" />
        </div>
      )}
      {step === 2 && (
        <div>
          <h3>Address</h3>
          <input value={data.street} onChange={(e) => setData({...data, street: e.target.value})} placeholder="Street" />
          <input value={data.city} onChange={(e) => setData({...data, city: e.target.value})} placeholder="City" />
          <input value={data.zip} onChange={(e) => setData({...data, zip: e.target.value})} placeholder="Zip Code" />
        </div>
      )}
      {step === 3 && (
        <div>
          <h3>Review</h3>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
      {errors.length > 0 && <div style={{ color: 'red' }}>{errors.join(', ')}</div>}
      <button disabled={step === 1} onClick={prevStep}>Back</button>
      {step < 3 ? <button onClick={nextStep}>Next</button> : <button onClick={() => console.log(data)}>Submit</button>}
    </div>
  );
};

export default MultiStepFormWizard;
