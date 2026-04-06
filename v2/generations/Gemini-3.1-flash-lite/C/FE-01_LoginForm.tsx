import React, { useState } from 'react';

// [L]TS[S]React[F]SFC[Y]TW[D]NOX[M]MOB[DT]MOCK[O]CODE
export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const validate = () => {
    if (!email.includes('@')) return 'Bad Email';
    if (!password) return 'Empty Pwd';
    return null;
  };

  return (
    <div className="p-4 bg-white rounded shadow-md">
      <input 
        className="block w-full mb-2 p-2 border" 
        value={email} onChange={e => setEmail(e.target.value)} 
      />
      <input 
        className="block w-full mb-2 p-2 border" 
        type="password"
        value={password} onChange={e => setPassword(e.target.value)} 
      />
      {error && <div className="text-red-500">{error}</div>}
      <button 
        className="bg-blue-500 text-white p-2"
        onClick={() => setError(validate() || '')}
      >Login</button>
    </div>
  );
}
