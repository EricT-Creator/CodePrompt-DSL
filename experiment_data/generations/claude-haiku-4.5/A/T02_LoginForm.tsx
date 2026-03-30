import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [pwd, setPwd] = useState('');
  const [err, setErr] = useState('');

  const validate = () => {
    if (!email) { setErr('Email required'); return false; }
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(email)) { setErr('Invalid email'); return false; }
    if (!pwd) { setErr('Password required'); return false; }
    if (pwd.length < 6) { setErr('Min 6 chars'); return false; }
    setErr('');
    return true;
  };

  const handleSubmit = () => {
    if (validate()) alert('Login successful');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white p-6 rounded-lg shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-4">Login</h1>
        {err && <p className="text-red-500 text-sm mb-3">{err}</p>}
        <div className="mb-3">
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="your@email.com"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Password</label>
          <input
            type="password"
            value={pwd}
            onChange={e => setPwd(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••"
          />
        </div>
        <button
          onClick={handleSubmit}
          className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 font-medium"
        >
          Sign In
        </button>
      </div>
    </div>
  );
};

export default LoginForm;