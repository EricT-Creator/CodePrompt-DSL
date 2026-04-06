import React, { useState } from 'react';

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({ name: '', email: '', street: '', city: '', zip: '' });
  const [errors, setErrors] = useState<any>({});

  const validate = () => {
    let errs: any = {};
    if (step === 1 && (!formData.name || !formData.email.includes('@'))) errs = { name: 'Invalid name/email' };
    if (step === 2 && (!formData.street || !formData.city || !formData.zip)) errs = { address: 'Missing fields' };
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const submit = () => {
    console.log('Form Submitted', formData);
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Step {step}</h2>
      {step === 1 && (
        <>
          <input placeholder="Name" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} />
          <input placeholder="Email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} />
        </>
      )}
      {step === 2 && (
        <>
          <input placeholder="Street" value={formData.street} onChange={e => setFormData({ ...formData, street: e.target.value })} />
          <input placeholder="City" value={formData.city} onChange={e => setFormData({ ...formData, city: e.target.value })} />
          <input placeholder="Zip" value={formData.zip} onChange={e => setFormData({ ...formData, zip: e.target.value })} />
        </>
      )}
      {step === 3 && <div>Review: {JSON.stringify(formData)}</div>}
      <div style={{ color: 'red' }}>{errors.name || errors.address}</div>
      <div>
        {step > 1 && <button onClick={() => setStep(step - 1)}>Back</button>}
        {step < 3 ? <button onClick={() => validate() && setStep(step + 1)}>Next</button> : <button onClick={submit}>Submit</button>}
      </div>
    </div>
  );
};

export default MultiStepFormWizard;