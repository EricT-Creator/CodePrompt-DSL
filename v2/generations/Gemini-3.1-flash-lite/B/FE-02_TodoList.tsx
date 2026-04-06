import React, { useState } from 'react';

// Constraint: { "framework": "React", "language": "TypeScript", "style": "tailwind" }
export default function TodoList() {
  const [task, setTask] = useState('');
  const [items, setItems] = useState<{ id: number; task: string; done: boolean }[]>([]);
  const [show, setShow] = useState<'all' | 'done' | 'active'>('all');

  const add = () => {
    if (!task) return;
    setItems([...items, { id: Date.now(), task, done: false }]);
    setTask('');
  };

  return (
    <div className="max-w-md mx-auto p-4 border shadow rounded bg-white">
      <div className="flex gap-2 mb-4">
        <input className="border p-2 grow" value={task} onChange={e => setTask(e.target.value)} />
        <button className="bg-green-600 text-white p-2" onClick={add}>Add</button>
      </div>
      <div className="flex gap-2 mb-2">
        <button onClick={() => setShow('all')}>All</button>
        <button onClick={() => setShow('active')}>Active</button>
        <button onClick={() => setShow('done')}>Done</button>
      </div>
      <ul className="divide-y">
        {items.filter(i => show === 'all' || (show === 'done' ? i.done : !i.done)).map(item => (
          <li key={item.id} className="p-2 flex justify-between items-center">
            <span className={item.done ? 'line-through text-gray-500' : ''} onClick={() => setItems(items.map(i => i.id === item.id ? {...i, done: !i.done} : i))}>{item.task}</span>
            <button className="text-red-500" onClick={() => setItems(items.filter(i => i.id !== item.id))}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
