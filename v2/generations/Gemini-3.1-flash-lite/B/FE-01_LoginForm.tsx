import React, { useState } from 'react';

// Constraint: { "framework": "React", "language": "TypeScript", "style": "tailwind" }
export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes('@')) {
      setError('Invalid email');
      return;
    }
    if (!password) {
      setError('Password required');
      return;
    }
    setError('');
    alert('Logged in!');
  };

  return (
    <div className="max-w-xs mx-auto p-4 bg-gray-100 rounded shadow">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <input 
          type="email" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="p-2 border border-gray-300 rounded"
        />
        <input 
          type="password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="p-2 border border-gray-300 rounded"
        />
        {error && <span className="text-red-500 text-sm">{error}</span>}
        <button type="submit" className="bg-blue-600 text-white p-2 rounded">Submit</button>
      </form>
    </div>
  );
}
