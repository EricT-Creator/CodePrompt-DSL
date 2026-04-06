import React, { useState } from 'react';

const MultiStepFormWizard: React.FC = () => {
  const [step, setStep] = useState(1);
  const [data, setData] = useState({ name: '', email: '', street: '', city: '', zip: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (step === 1) {
      if (!data.name) newErrors.name = 'Required';
      if (!data.email.includes('@')) newErrors.email = 'Invalid';
    } else if (step === 2) {
      if (!data.street) newErrors.street = 'Required';
      if (!data.city) newErrors.city = 'Required';
      if (!data.zip) newErrors.zip = 'Required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const next = () => {
    if (validate()) setStep(s => s + 1);
  };

  const back = () => setStep(s => s - 1);

  const submit = () => {
    console.log('Submitted:', data);
    alert('Submitted!');
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h3>Step {step} of 3</h3>
      {step === 1 && (
        <div>
          <input placeholder="Name" value={data.name} onChange={e => setData({...data, name: e.target.value})} />
          {errors.name && <p style={{color: 'red'}}>{errors.name}</p>}
          <input placeholder="Email" value={data.email} onChange={e => setData({...data, email: e.target.value})} />
          {errors.email && <p style={{color: 'red'}}>{errors.email}</p>}
        </div>
      )}
      {step === 2 && (
        <div>
          <input placeholder="Street" value={data.street} onChange={e => setData({...data, street: e.target.value})} />
          {errors.street && <p style={{color: 'red'}}>{errors.street}</p>}
          <input placeholder="City" value={data.city} onChange={e => setData({...data, city: e.target.value})} />
          {errors.city && <p style={{color: 'red'}}>{errors.city}</p>}
          <input placeholder="Zip" value={data.zip} onChange={e => setData({...data, zip: e.target.value})} />
          {errors.zip && <p style={{color: 'red'}}>{errors.zip}</p>}
        </div>
      )}
      {step === 3 && (
        <div>
          <p>Name: {data.name}</p>
          <p>Email: {data.email}</p>
          <p>Address: {data.street}, {data.city}, {data.zip}</p>
        </div>
      )}
      <div style={{ marginTop: '20px' }}>
        {step > 1 && <button onClick={back}>Back</button>}
        {step < 3 && <button onClick={next}>Next</button>}
        {step === 3 && <button onClick={submit}>Submit</button>}
      </div>
    </div>
  );
};

export default MultiStepFormWizard;
