import React, { useState } from 'react';

const TodoList: React.FC = () => {
  const [list, setList] = useState<{ id: number; val: string; end: boolean }[]>([]);
  const [val, setVal] = useState('');
  const [tab, setTab] = useState('ALL');

  const add = () => {
    if (!val) return;
    setList([...list, { id: Date.now(), val, end: false }]);
    setVal('');
  };

  const del = (id: number) => setList(list.filter((i) => i.id !== id));
  const tog = (id: number) => setList(list.map((i) => (i.id === id ? { ...i, end: !i.end } : i)));

  const show = list.filter((i) => {
    if (tab === 'ACT') return !i.end;
    if (tab === 'FIN') return i.end;
    return true;
  });

  return (
    <div className="max-w-md mx-auto p-4 font-sans text-sm">
      <div className="flex border rounded-lg overflow-hidden mb-4">
        <input value={val} onChange={(e) => setVal(e.target.value)} className="flex-1 p-2 outline-none" placeholder="Task" />
        <button onClick={add} className="px-4 bg-blue-600 text-white">Add</button>
      </div>
      <div className="flex gap-4 mb-4 text-xs font-bold text-gray-500 border-b pb-2">
        {['ALL', 'ACT', 'FIN'].map((t) => (
          <span key={t} onClick={() => setTab(t)} className={`cursor-pointer ${tab === t ? 'text-blue-600 border-b border-blue-600' : ''}`}>{t}</span>
        ))}
      </div>
      <div className="space-y-2">
        {show.map((i) => (
          <div key={i.id} className="flex items-center justify-between p-2 bg-gray-50 rounded border">
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={i.end} onChange={() => tog(i.id)} />
              <span className={i.end ? 'line-through text-gray-400' : ''}>{i.val}</span>
            </div>
            <button onClick={() => del(i.id)} className="text-gray-400 hover:text-red-500">Del</button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TodoList;
