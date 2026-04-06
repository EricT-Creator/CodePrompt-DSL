import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailErr, setEmailErr] = useState('');
  const [passwordErr, setPasswordErr] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    let valid = true;

    if (!email) {
      setEmailErr('Email required');
      valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailErr('Format invalid');
      valid = false;
    } else {
      setEmailErr('');
    }

    if (!password) {
      setPasswordErr('Password required');
      valid = false;
    } else {
      setPasswordErr('');
    }

    if (valid) {
      alert('Sign in success');
    }
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-100 p-4">
      <div className="w-full max-w-md bg-white p-8 rounded-lg shadow-xl">
        <h1 className="text-xl font-bold text-center mb-6">Account Login</h1>
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm mb-1">Email</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full p-2 border rounded focus:ring-1 outline-none ${emailErr ? 'border-red-500 ring-red-500' : 'border-gray-300 ring-blue-500'}`}
            />
            {emailErr && <span className="text-xs text-red-500">{emailErr}</span>}
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full p-2 border rounded focus:ring-1 outline-none ${passwordErr ? 'border-red-500 ring-red-500' : 'border-gray-300 ring-blue-500'}`}
            />
            {passwordErr && <span className="text-xs text-red-500">{passwordErr}</span>}
          </div>
          <button type="submit" className="bg-black text-white py-2 rounded hover:opacity-90 transition">
            Log In
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginForm;
