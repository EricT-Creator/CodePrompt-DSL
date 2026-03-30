import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  done: boolean;
}

const TodoApp: React.FC = () => {
  const [todos, set待办] = useState<Todo[]>([
    { id: 1, text: 'Buy groceries', done: false },
    { id: 2, text: 'Walk the dog', done: true },
    { id: 3, text: 'Read a book', done: false },
  ]);
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'done'>('all');

  const add = () => {
    if (!input.trim()) return;
    set待办([...todos, { id: Date.now(), text: input, done: false }]);
    setInput('');
  };

  const del = (id: number) => set待办(todos.filter(t => t.id !== id));
  const toggle = (id: number) => set待办(todos.map(t => t.id === id ? { ...t, done: !t.done } : t));

  const filtered = todos.filter(t => 
    filter === 'all' ? true : filter === 'active' ? !t.done : t.done
  );

  return (
    <div className="min-h-screen bg-slate-100 p-3 max-w-md mx-auto">
      <h1 className="text-xl font-bold mb-4">待办</h1>
      <div className="flex gap-1 mb-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="输入待办..."
          className="flex-1 px-2 py-1 border rounded text-sm"
        />
        <button onClick={add} className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
          增
        </button>
      </div>
      <div className="flex gap-1 mb-3">
        {(['all', 'active', 'done'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-sm rounded ${filter === f ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}
          >
            {f}
          </button>
        ))}
      </div>
      <ul className="space-y-1">
        {filtered.map(t => (
          <li key={t.id} className="flex items-center gap-2 p-2 bg-white rounded">
            <input type="checkbox" checked={t.done} onChange={() => toggle(t.id)} />
            <span className={t.done ? 'line-through text-gray-400' : ''}>{t.text}</span>
            <button onClick={() => del(t.id)} className="ml-auto text-xs text-red-500">删</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TodoApp;