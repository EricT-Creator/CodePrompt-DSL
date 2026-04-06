import React, { useState } from 'react';

interface 任务 {
  id: number;
  标题: string;
  完成: boolean;
}

const 待办列表 = () => {
  const [列表, set列表] = useState<任务[]>([]);
  const [输入, set输入] = useState('');
  const [筛选, set筛选] = useState<'全部' | '未完' | '已完'>('全部');

  const 添加 = () => {
    if (输入.trim()) {
      set列表([...列表, { id: Date.now(), 标题: 输入, 完成: false }]);
      set输入('');
    }
  };

  const 切换 = (id: number) => {
    set列表(列表.map(t => t.id === id ? { ...t, 完成: !t.完成 } : t));
  };

  const 删除 = (id: number) => {
    set列表(列表.filter(t => t.id !== id));
  };

  const 显示 = 筛选 === '全部' ? 列表 : 筛选 === '未完' ? 列表.filter(t => !t.完成) : 列表.filter(t => t.完成);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-md mx-auto bg-white rounded shadow p-4">
        <h1 className="text-xl font-bold mb-4">待办</h1>

        <div className="flex gap-2 mb-4">
          <input
            value={输入}
            onChange={(e) => set输入(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && 添加()}
            placeholder="新任务"
            className="flex-1 px-2 py-1 border rounded"
          />
          <button onClick={添加} className="bg-blue-600 text-white px-3 py-1 rounded">
            加
          </button>
        </div>

        <div className="flex gap-2 mb-4">
          {(['全部', '未完', '已完'] as const).map(f => (
            <button
              key={f}
              onClick={() => set筛选(f)}
              className={`px-2 py-1 rounded ${筛选 === f ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          {显示.map(t => (
            <div key={t.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
              <input
                type="checkbox"
                checked={t.完成}
                onChange={() => 切换(t.id)}
              />
              <span className={t.完成 ? 'line-through text-gray-500' : ''}>{t.标题}</span>
              <button
                onClick={() => 删除(t.id)}
                className="ml-auto text-red-600 text-sm"
              >
                删
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default 待办列表;