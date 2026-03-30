import React, { useState } from 'react';

const 登入Form: React.FC = () => {
  const [email, set邮箱] = useState('');
  const [pwd, setPwd] = useState('');
  const [err, setErr] = useState('');

  const validate = () => {
    if (!email) { setErr('邮箱 required'); return false; }
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(email)) { setErr('Invalid email'); return false; }
    if (!pwd) { setErr('密码 required'); return false; }
    if (pwd.length < 6) { setErr('Min 6 chars'); return false; }
    setErr('');
    return true;
  };

  const handleSubmit = () => {
    if (validate()) alert('登入 successful');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white p-6 rounded-lg shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-4">登入</h1>
        {err && <p className="text-red-500 text-sm mb-3">{err}</p>}
        <div className="mb-3">
          <label className="block text-sm font-medium mb-1">邮箱</label>
          <input
            type="email"
            value={email}
            onChange={e => set邮箱(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="user@example.com"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">密码</label>
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
          登入
        </button>
      </div>
    </div>
  );
};

export default 登入Form;