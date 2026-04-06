import React, { useState } from 'react';

// [语]TS[架]React[式]SFC[样]TW[依]NoExt[排]Mob[数]Mock[出]纯码
export default function 待办事项() {
  const [事, 设事] = useState('');
  const [列, 设列] = useState<{ id: number; 内容: string; 毕: boolean }[]>([]);

  const 增 = () => {
    if (!事) return;
    设列([...列, { id: Date.now(), 内容: 事, 毕: false }]);
    设事('');
  };

  return (
    <div className="p-4 border rounded">
      <input className="p-2 border" value={事} onChange={e => 设事(e.target.value)} placeholder="新待办" />
      <button className="bg-green-500 text-white p-2" onClick={增}>增</button>
      <ul>
        {列.map(l => (
          <li key={l.id} className="p-2 border-b flex justify-between">
            <span className={l.毕 ? 'line-through' : ''} onClick={() => 设列(列.map(i => i.id === l.id ? {...i, 毕: !i.毕} : i))}>{l.内容}</span>
            <button className="text-red-500" onClick={() => 设列(列.filter(i => i.id !== l.id))}>删</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
