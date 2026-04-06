import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailErr, setEmailErr] = useState('');
  const [passwordErr, setPasswordErr] = useState('');

  const validate = (e: React.FormEvent) => {
    e.preventDefault();
    let ok = true;
    if (!email.includes('@')) {
      setEmailErr('格式不正确');
      ok = false;
    } else {
      setEmailErr('');
    }
    if (!password) {
      setPasswordErr('不可为空');
      ok = false;
    } else {
      setPasswordErr('');
    }
    if (ok) {
      alert('登入成功');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <div className="bg-white p-8 rounded-2xl shadow-lg w-full max-w-sm">
        <h2 className="text-center text-2xl font-semibold mb-8">登入</h2>
        <form onSubmit={validate}>
          <div className="mb-4">
            <label className="block mb-2 text-sm text-gray-600">邮箱</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-400 outline-none transition"
            />
            {emailErr && <p className="mt-1 text-xs text-red-500">{emailErr}</p>}
          </div>
          <div className="mb-8">
            <label className="block mb-2 text-sm text-gray-600">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-400 outline-none transition"
            />
            {passwordErr && <p className="mt-1 text-xs text-red-500">{passwordErr}</p>}
          </div>
          <button
            type="submit"
            className="w-full p-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 active:scale-95 transition-all shadow-md"
          >
            登入
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginForm;
