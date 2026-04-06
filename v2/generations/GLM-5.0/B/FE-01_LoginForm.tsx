import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [validationErrors, setValidationErrors] = useState<{ email?: string; password?: string }>({});

  const constraints = {
    email: {
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      message: 'Invalid email format'
    },
    password: {
      minLength: 1,
      message: 'Password cannot be empty'
    }
  };

  const validateField = (field: string, value: string): string | undefined => {
    if (field === 'email') {
      if (!constraints.email.pattern.test(value)) {
        return constraints.email.message;
      }
    }
    if (field === 'password') {
      if (value.trim().length < constraints.password.minLength) {
        return constraints.password.message;
      }
    }
    return undefined;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errors: { email?: string; password?: string } = {};

    const emailError = validateField('email', formData.email);
    if (emailError) errors.email = emailError;

    const passwordError = validateField('password', formData.password);
    if (passwordError) errors.password = passwordError;

    setValidationErrors(errors);

    if (Object.keys(errors).length === 0) {
      console.log('Form submitted successfully', formData);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-white rounded-xl shadow-lg p-8 space-y-6"
      >
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-800">Sign In</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-slate-700 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
              placeholder="email@example.com"
            />
            {validationErrors.email && (
              <p className="mt-2 text-sm text-rose-600 font-medium">{validationErrors.email}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-semibold text-slate-700 mb-2">
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
              placeholder="••••••••"
            />
            {validationErrors.password && (
              <p className="mt-2 text-sm text-rose-600 font-medium">{validationErrors.password}</p>
            )}
          </div>
        </div>

        <button
          type="submit"
          className="w-full bg-indigo-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-200"
        >
          Sign In
        </button>
      </form>
    </div>
  );
};

export default LoginForm;
