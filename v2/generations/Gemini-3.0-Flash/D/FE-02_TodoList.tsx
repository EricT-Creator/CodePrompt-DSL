import React, { useState } from 'react';

interface 项 {
  号: number;
  文: string;
  毕: boolean;
}

const 待办页: React.FC = () => {
  const [列, 设列] = useState<项[]>([]);
  const [词, 设词] = useState('');
  const [筛, 设筛] = useState<'全' | '未' | '已'>('全');

  const 增 = () => {
    if (!词.trim()) return;
    设列([...列, { 号: Date.now(), 文: 词, 毕: false }]);
    设词('');
  };

  const 删 = (号: number) => 设列(列.filter((i) => i.号 !== 号));
  const 切换 = (号: number) => 设列(列.map((i) => (i.号 === 号 ? { ...i, 毕: !i.毕 } : i)));

  const 示 = 列.filter((i) => {
    if (筛 === '未') return !i.毕;
    if (筛 === '已') return i.毕;
    return true;
  });

  return (
    <div className="p-8 max-w-md mx-auto text-sm">
      <h1 className="text-xl font-bold mb-4">待办事项</h1>
      <div className="flex mb-4">
        <input value={词} onChange={(e) => 设词(e.target.value)} className="flex-1 p-2 border border-gray-300 rounded-l-md outline-none" />
        <button onClick={增} className="bg-indigo-500 text-white px-4 rounded-r-md">增</button>
      </div>
      <div className="flex gap-4 mb-4 text-gray-500">
        {(['全', '未', '已'] as const).map((s) => (
          <span key={s} onClick={() => 设筛(s)} className={`cursor-pointer ${筛 === s ? 'text-indigo-600 font-bold' : ''}`}>{s}</span>
        ))}
      </div>
      <div className="space-y-2">
        {示.map((i) => (
          <div key={i.号} className="flex justify-between items-center p-3 bg-white border rounded shadow-sm">
            <div className="flex items-center gap-3">
              <input type="checkbox" checked={i.毕} onChange={() => 切换(i.号)} />
              <span className={i.毕 ? 'line-through text-gray-400' : ''}>{i.文}</span>
            </div>
            <button onClick={() => 删(i.号)} className="text-red-400">删</button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default 待办页;
