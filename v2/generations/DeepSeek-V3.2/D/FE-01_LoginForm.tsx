import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [emailError, setEmailError] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let isValid = true;

    // 校邮之格式
    if (!email.trim()) {
      setEmailError('邮不可空');
      isValid = false;
    } else if (!validateEmail(email)) {
      setEmailError('邮之格式不合');
      isValid = false;
    } else {
      setEmailError('');
    }

    // 验密之非空
    if (!password.trim()) {
      setPasswordError('密不可空');
      isValid = false;
    } else {
      setPasswordError('');
    }

    if (isValid) {
      // 模拟登入
      console.log('登入尝试:', { email, password: '***' });
      alert('登入功成');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-xl p-10">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-black text-gray-900 mb-4">登入</h1>
          <p className="text-gray-600">输入邮密以登入</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-10">
          <div>
            <label htmlFor="email" className="block text-lg font-bold text-gray-800 mb-4">
              邮址
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full px-6 py-5 border-3 text-xl rounded-2xl focus:outline-none transition-all ${emailError ? 'border-red-400 focus:border-red-500 bg-red-50' : 'border-gray-300 focus:border-green-500 focus:ring-4 focus:ring-green-100'}`}
              placeholder="you@example.com"
            />
            {emailError && (
              <div className="mt-4 px-5 py-3 bg-red-100 border-2 border-red-300 rounded-xl">
                <p className="text-red-800 font-bold text-lg">{emailError}</p>
              </div>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-lg font-bold text-gray-800 mb-4">
              密
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full px-6 py-5 border-3 text-xl rounded-2xl focus:outline-none transition-all ${passwordError ? 'border-red-400 focus:border-red-500 bg-red-50' : 'border-gray-300 focus:border-green-500 focus:ring-4 focus:ring-green-100'}`}
              placeholder="••••••••"
            />
            {passwordError && (
              <div className="mt-4 px-5 py-3 bg-red-100 border-2 border-red-300 rounded-xl">
                <p className="text-red-800 font-bold text-lg">{passwordError}</p>
              </div>
            )}
          </div>

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white text-2xl font-black py-6 px-8 rounded-2xl hover:from-green-600 hover:to-emerald-700 focus:outline-none focus:ring-6 focus:ring-green-300 focus:ring-offset-4 transform hover:scale-105 transition-all duration-300 shadow-2xl hover:shadow-3xl"
          >
            登入
          </button>
        </form>

        <div className="mt-16 pt-10 border-t-2 border-gray-300 text-center">
          <p className="text-gray-500 text-base">模拟登入表含验证</p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;