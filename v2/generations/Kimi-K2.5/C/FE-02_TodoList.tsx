import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  done: boolean;
}

export default function TodoList() {
  const [items, setItems] = useState<Todo[]>([
    { id: 1, text: 'Read documentation', done: false },
    { id: 2, text: 'Write tests', done: true },
    { id: 3, text: 'Fix bugs', done: false }
  ]);
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'done'>('all');

  const add = () => {
    if (input.trim()) {
      setItems([...items, { id: Date.now(), text: input.trim(), done: false }]);
      setInput('');
    }
  };

  const toggle = (id: number) => {
    setItems(items.map(i => i.id === id ? { ...i, done: !i.done } : i));
  };

  const remove = (id: number) => {
    setItems(items.filter(i => i.id !== id));
  };

  const visible = items.filter(i => {
    if (filter === 'active') return !i.done;
    if (filter === 'done') return i.done;
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-900 p-4">
      <div className="max-w-md mx-auto">
        <h1 className="text-3xl font-bold text-white mb-6">Tasks</h1>
        
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            placeholder="New task..."
          />
          <button
            onClick={add}
            className="px-5 py-3 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors font-medium"
          >
            +
          </button>
        </div>

        <div className="flex gap-2 mb-4">
          {(['all', 'active', 'done'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-md text-sm capitalize ${
                filter === f ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <ul className="space-y-2">
          {visible.map(t => (
            <li key={t.id} className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg">
              <input
                type="checkbox"
                checked={t.done}
                onChange={() => toggle(t.id)}
                className="w-5 h-5 rounded border-slate-600 text-cyan-600 focus:ring-cyan-500"
              />
              <span className={`flex-1 ${t.done ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                {t.text}
              </span>
              <button
                onClick={() => remove(t.id)}
                className="text-slate-500 hover:text-red-400"
              >
                ×
              </button>
            </li>
          ))}
        </ul>

        {visible.length === 0 && (
          <p className="text-center text-slate-500 py-8">No tasks</p>
        )}
      </div>
    </div>
  );
}
