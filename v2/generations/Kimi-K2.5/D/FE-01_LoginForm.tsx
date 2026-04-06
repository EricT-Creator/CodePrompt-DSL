import React, { useState } from 'react';

export default function 登入表() {
  const [邮址, 设邮址] = useState('');
  const [密码, 设密码] = useState('');
  const [误告, 设误告] = useState<{ 邮误?: string; 密误?: string }>({});

  const 验邮 = (邮: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(邮);

  const 呈表 = (e: React.FormEvent) => {
    e.preventDefault();
    const 新误: { 邮误?: string; 密误?: string } = {};

    if (!邮址) 新误.邮误 = '邮址必填';
    else if (!验邮(邮址)) 新误.邮误 = '邮址格式有误';
    if (!密码) 新误.密误 = '密码必填';

    设误告(新误);
    if (Object.keys(新误).length === 0) console.log('登入:', { 邮址, 密码 });
  };

  return (
    <div className="min-h-screen bg-stone-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-lg p-6 border border-stone-200">
        <h2 className="text-2xl font-bold text-stone-800 mb-6 text-center">登入</h2>
        <form onSubmit={呈表} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">邮址</label>
            <input
              type="email"
              value={邮址}
              onChange={(e) => 设邮址(e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-amber-600 ${
                误告.邮误 ? 'border-red-500' : 'border-stone-300'
              }`}
              placeholder="请输入邮址"
            />
            {误告.邮误 && <p className="mt-1 text-sm text-red-600">{误告.邮误}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">密码</label>
            <input
              type="password"
              value={密码}
              onChange={(e) => 设密码(e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-amber-600 ${
                误告.密误 ? 'border-red-500' : 'border-stone-300'
              }`}
              placeholder="请输入密码"
            />
            {误告.密误 && <p className="mt-1 text-sm text-red-600">{误告.密误}</p>}
          </div>
          <button
            type="submit"
            className="w-full bg-amber-700 text-white py-2 px-4 rounded-md hover:bg-amber-800 focus:outline-none focus:ring-2 focus:ring-amber-600 transition-colors"
          >
            登入
          </button>
        </form>
      </div>
    </div>
  );
}
