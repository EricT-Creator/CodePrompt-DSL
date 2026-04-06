import React, { useState } from 'react';

interface 待办项 {
  编号: number;
  内容: string;
  已毕: boolean;
}

export default function 待办页() {
  const [待办列, 设待办列] = useState<待办项[]>([
    { 编号: 1, 内容: '读书', 已毕: false },
    { 编号: 2, 内容: '写字', 已毕: true },
    { 编号: 3, 内容: '买菜', 已毕: false }
  ]);
  const [输入, 设输入] = useState('');
  const [筛状, 设筛状] = useState<'全部' | '未完' | '已毕'>('全部');

  const 增项 = () => {
    if (输入.trim()) {
      设待办列([...待办列, { 编号: Date.now(), 内容: 输入.trim(), 已毕: false }]);
      设输入('');
    }
  };

  const 切毕 = (编号: number) => {
    设待办列(待办列.map(项 => 项.编号 === 编号 ? { ...项, 已毕: !项.已毕 } : 项));
  };

  const 删项 = (编号: number) => {
    设待办列(待办列.filter(项 => 项.编号 !== 编号));
  };

  const 显列 = 待办列.filter(项 => {
    if (筛状 === '未完') return !项.已毕;
    if (筛状 === '已毕') return 项.已毕;
    return true;
  });

  return (
    <div className="min-h-screen bg-stone-100 p-4">
      <div className="max-w-md mx-auto">
        <h1 className="text-3xl font-bold text-stone-800 mb-6 text-center">待办</h1>
        
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={输入}
            onChange={(e) => 设输入(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && 增项()}
            className="flex-1 px-4 py-3 bg-white border border-stone-300 rounded-lg text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-600"
            placeholder="新增事项..."
          />
          <button
            onClick={增项}
            className="px-5 py-3 bg-amber-700 text-white rounded-lg hover:bg-amber-800 transition-colors font-medium"
          >
            增
          </button>
        </div>

        <div className="flex gap-2 mb-4 justify-center">
          {(['全部', '未完', '已毕'] as const).map(状 => (
            <button
              key={状}
              onClick={() => 设筛状(状)}
              className={`px-4 py-1 rounded-md text-sm ${
                筛状 === 状 ? 'bg-amber-700 text-white' : 'bg-white text-stone-600 hover:bg-stone-200'
              }`}
            >
              {状}
            </button>
          ))}
        </div>

        <ul className="space-y-2">
          {显列.map(项 => (
            <li key={项.编号} className="flex items-center gap-3 p-3 bg-white rounded-lg shadow-sm">
              <input
                type="checkbox"
                checked={项.已毕}
                onChange={() => 切毕(项.编号)}
                className="w-5 h-5 rounded border-stone-300 text-amber-700 focus:ring-amber-600"
              />
              <span className={`flex-1 ${项.已毕 ? 'line-through text-stone-400' : 'text-stone-800'}`}>
                {项.内容}
              </span>
              <button
                onClick={() => 删项(项.编号)}
                className="text-stone-400 hover:text-red-600"
              >
                删
              </button>
            </li>
          ))}
        </ul>

        {显列.length === 0 && (
          <p className="text-center text-stone-400 py-8">无事项</p>
        )}
      </div>
    </div>
  );
}
