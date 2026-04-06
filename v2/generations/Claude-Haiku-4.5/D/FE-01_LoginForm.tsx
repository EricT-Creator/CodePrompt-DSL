import React, { useState } from 'react';

const LoginForm = () => {
  const [邮箱, set邮箱] = useState('');
  const [密码, set密码] = useState('');
  const [错误, set错误] = useState<{ 邮箱?: string; 密码?: string }>({});

  const 校验邮箱 = (邮: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(邮);
  };

  const 处理提交 = (e: React.FormEvent) => {
    e.preventDefault();
    const 新错误: { 邮箱?: string; 密码?: string } = {};

    if (!校验邮箱(邮箱)) {
      新错误.邮箱 = '邮箱格式不正确';
    }

    if (!密码) {
      新错误.密码 = '密码不能为空';
    }

    set错误(新错误);

    if (Object.keys(新错误).length === 0) {
      console.log('登入成功');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={处理提交} className="bg-white shadow p-8 rounded-lg w-full max-w-sm">
        <h2 className="text-2xl font-bold mb-6">登入</h2>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">邮箱</label>
          <input
            type="email"
            value={邮箱}
            onChange={(e) => set邮箱(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:border-blue-500"
          />
          {错误.邮箱 && <span className="text-red-600 text-sm block mt-1">{错误.邮箱}</span>}
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">密码</label>
          <input
            type="password"
            value={密码}
            onChange={(e) => set密码(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:border-blue-500"
          />
          {错误.密码 && <span className="text-red-600 text-sm block mt-1">{错误.密码}</span>}
        </div>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          登入
        </button>
      </form>
    </div>
  );
};

export default LoginForm;