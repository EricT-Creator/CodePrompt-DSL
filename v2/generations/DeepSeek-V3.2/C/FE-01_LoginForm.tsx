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

    // Validate email format
    if (!email.trim()) {
      setEmailError('Email is required');
      isValid = false;
    } else if (!validateEmail(email)) {
      setEmailError('Invalid email format');
      isValid = false;
    } else {
      setEmailError('');
    }

    // Validate password non-empty
    if (!password.trim()) {
      setPasswordError('Password is required');
      isValid = false;
    } else {
      setPasswordError('');
    }

    if (isValid) {
      // Mock login action
      console.log('Login attempt:', { email, password: '***' });
      alert('Login successful (mock)');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 p-4">
      <div className="max-w-sm w-full bg-white rounded-2xl shadow-2xl p-8">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-black text-gray-900 mb-2">Login</h1>
          <p className="text-gray-600">Enter your credentials</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          <div>
            <label htmlFor="email" className="block text-sm font-bold text-gray-800 mb-3">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full px-5 py-4 border-2 rounded-xl text-lg focus:outline-none transition-all ${emailError ? 'border-red-400 focus:border-red-500' : 'border-gray-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-100'}`}
              placeholder="user@example.com"
            />
            {emailError && (
              <div className="mt-3 px-4 py-2 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700 font-medium">{emailError}</p>
              </div>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-bold text-gray-800 mb-3">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full px-5 py-4 border-2 rounded-xl text-lg focus:outline-none transition-all ${passwordError ? 'border-red-400 focus:border-red-500' : 'border-gray-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-100'}`}
              placeholder="••••••••"
            />
            {passwordError && (
              <div className="mt-3 px-4 py-2 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700 font-medium">{passwordError}</p>
              </div>
            )}
          </div>

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-xl font-extrabold py-5 px-6 rounded-xl hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-4 focus:ring-blue-300 focus:ring-offset-2 transform hover:-translate-y-1 transition-all duration-300 shadow-xl hover:shadow-2xl"
          >
            Continue
          </button>
        </form>

        <div className="mt-12 pt-8 border-t border-gray-200 text-center">
          <p className="text-gray-500 text-sm">Mock login interface with validation</p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;