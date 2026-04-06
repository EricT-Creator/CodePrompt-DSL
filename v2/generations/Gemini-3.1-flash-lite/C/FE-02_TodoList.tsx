import React, { useState } from 'react';

// [L]TS[S]React[F]SFC[Y]TW[D]NOX[M]MOB[DT]MOCK[O]CODE
export default function TodoList() {
  const [list, setList] = useState<{ id: number; task: string; done: boolean }[]>([]);
  const [val, setVal] = useState('');

  const add = () => {
    setList([...list, { id: Date.now(), task: val, done: false }]);
    setVal('');
  };

  return (
    <div className="p-4 bg-gray-100 rounded">
      <input className="border p-2" value={val} onChange={e => setVal(e.target.value)} />
      <button className="bg-green-500 text-white p-2" onClick={add}>Add</button>
      <ul className="mt-4">
        {list.map(i => (
          <li key={i.id} className="flex justify-between p-2 border-b">
            <span className={i.done ? 'line-through' : ''} onClick={() => setList(list.map(item => item.id === i.id ? {...item, done: !item.done} : item))}>{i.task}</span>
            <button className="text-red-500" onClick={() => setList(list.filter(item => item.id !== i.id))}>X</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
