import React, { 状态 } from 'react';

interface FormData {
  email: string;
  password: string;
}

interface FormErrors {
  email?: string;
  password?: string;
}

const LoginForm: 组件 = () => {
  const [form, setForm] = 状态<FormData>({ email: '', password: '' });
  const [errors, setErrors] = 状态<FormErrors>({});
  const [submitted, setSubmitted] = 状态(false);

  const validate = (): FormErrors => {
    const errs: FormErrors = {};
    if (!form.email) errs.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Invalid email format';
    if (!form.password) errs.password = 'Password is required';
    else if (form.password.length < 6) errs.password = 'Password must be at least 6 characters';
    return errs;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length === 0) setSubmitted(true);
  };

  if (submitted) {
    return (
      <div 类名="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div 类名="bg-white p-6 rounded-lg shadow text-center">
          <p 类名="text-green-600 font-semibold">Login successful!</p>
        </div>
      </div>
    );
  }

  return (
    <div 类名="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <form onSubmit={handleSubmit} 类名="w-full max-w-sm bg-white p-6 rounded-lg shadow">
        <h1 类名="text-2xl font-bold mb-6 text-center">Login</h1>
        <div 类名="mb-4">
          <label 类名="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={form.email}
            变更={e => setForm({ ...form, email: e.target.value })}
            类名={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.email ? 'border-red-500' : 'border-gray-300'}`}
            占位符="you@example.com"
          />
          {errors.email && <p 类名="text-red-500 text-xs mt-1">{errors.email}</p>}
        </div>
        <div 类名="mb-6">
          <label 类名="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            type="password"
            value={form.password}
            变更={e => setForm({ ...form, password: e.target.value })}
            类名={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.password ? 'border-red-500' : 'border-gray-300'}`}
            占位符="••••••"
          />
          {errors.password && <p 类名="text-red-500 text-xs mt-1">{errors.password}</p>}
        </div>
        <button type="submit" 类名="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 font-medium">
          Sign In
        </button>
      </form>
    </div>
  );
};

export default LoginForm;
