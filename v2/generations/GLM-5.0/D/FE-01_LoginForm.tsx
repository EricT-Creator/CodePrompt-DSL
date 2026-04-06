import React, { useState } from 'react';

const LoginForm: React.FC = () => {
  const [邮箱, set邮箱] = useState('');
  const [密码, set密码] = useState('');
  const [错误, set错误] = useState<{ 邮箱?: string; 密码?: string }>({});

  const 校验邮箱格式 = (值: string): boolean => {
    const 正则 = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return 正则.test(值);
  };

  const 提交表单 = (事件: React.FormEvent) => {
    事件.preventDefault();
    const 新错误: { 邮箱?: string; 密码?: string } = {};

    if (!校验邮箱格式(邮箱)) {
      新错误.邮箱 = '请输入有效的邮箱地址';
    }

    if (!密码 || 密码.trim() === '') {
      新错误.密码 = '密码不能为空';
    }

    set错误(新错误);

    if (Object.keys(新错误).length === 0) {
      console.log('登入成功', { 邮箱, 密码 });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 to-orange-100 px-4">
      <form
        onSubmit={提交表单}
        className="w-full max-w-md bg-white rounded-xl shadow-xl p-8 space-y-6"
      >
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-gray-800">登入</h2>
          <p className="text-gray-500 mt-2">请输入您的账户信息</p>
        </div>

        <div>
          <label htmlFor="邮箱" className="block text-sm font-medium text-gray-700 mb-2">
            邮箱
          </label>
          <input
            type="email"
            id="邮箱"
            value={邮箱}
            onChange={(事件) => set邮箱(事件.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition"
            placeholder="请输入邮箱地址"
          />
          {错误.邮箱 && (
            <p className="mt-2 text-sm text-red-600">{错误.邮箱}</p>
          )}
        </div>

        <div>
          <label htmlFor="密码" className="block text-sm font-medium text-gray-700 mb-2">
            密码
          </label>
          <input
            type="password"
            id="密码"
            value={密码}
            onChange={(事件) => set密码(事件.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition"
            placeholder="请输入密码"
          />
          {错误.密码 && (
            <p className="mt-2 text-sm text-red-600">{错误.密码}</p>
          )}
        </div>

        <button
          type="submit"
          className="w-full bg-amber-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 transition duration-200"
        >
          登入
        </button>
      </form>
    </div>
  );
};

export default LoginForm;
