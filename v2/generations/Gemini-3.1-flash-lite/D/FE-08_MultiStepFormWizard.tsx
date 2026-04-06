import React, { useState } from 'react';

const MultiStepFormWizard = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({ name: '', email: '', street: '', city: '', zip: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (step === 1) {
      if (!formData.name) newErrors.name = 'Name required';
      if (!formData.email.includes('@')) newErrors.email = 'Invalid email';
    } else if (step === 2) {
      if (!formData.street || !formData.city || !formData.zip) newErrors.address = 'All fields required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const next = () => { if (validate()) setStep(s => s + 1); };
  const prev = () => setStep(s => s - 1);
  const submit = () => { console.log(formData); alert('Submitted'); };

  return (
    <div style={{ padding: '20px' }}>
      {step === 1 && (
        <div>
          <input placeholder="Name" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} />
          <input placeholder="Email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} />
          {errors.name && <span>{errors.name}</span>}
          {errors.email && <span>{errors.email}</span>}
          <button onClick={next}>Next</button>
        </div>
      )}
      {step === 2 && (
        <div>
          <input placeholder="Street" value={formData.street} onChange={e => setFormData({ ...formData, street: e.target.value })} />
          <input placeholder="City" value={formData.city} onChange={e => setFormData({ ...formData, city: e.target.value })} />
          <input placeholder="Zip" value={formData.zip} onChange={e => setFormData({ ...formData, zip: e.target.value })} />
          {errors.address && <span>{errors.address}</span>}
          <button onClick={prev}>Back</button>
          <button onClick={next}>Next</button>
        </div>
      )}
      {step === 3 && (
        <div>
          <p>Confirm: {formData.name}</p>
          <button onClick={prev}>Back</button>
          <button onClick={submit}>Submit</button>
        </div>
      )}
    </div>
  );
};

export default MultiStepFormWizard;
