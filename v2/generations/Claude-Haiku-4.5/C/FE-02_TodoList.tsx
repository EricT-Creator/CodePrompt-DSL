import React, { useState } from 'react';

interface Task {
  id: number;
  name: string;
  finished: boolean;
}

const TodoList = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [input, setInput] = useState('');
  const [view, setView] = useState<'all' | 'open' | 'closed'>('all');

  const add = () => {
    if (input.trim()) {
      setTasks([...tasks, { id: Date.now(), name: input, finished: false }]);
      setInput('');
    }
  };

  const toggle = (id: number) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, finished: !t.finished } : t));
  };

  const remove = (id: number) => {
    setTasks(tasks.filter(t => t.id !== id));
  };

  const shown = view === 'all' ? tasks : view === 'open' ? tasks.filter(t => !t.finished) : tasks.filter(t => t.finished);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-md mx-auto bg-white rounded shadow p-4">
        <h1 className="text-xl font-bold mb-4">Tasks</h1>

        <div className="flex gap-1 mb-4">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="Task"
            className="flex-1 px-2 py-1 border rounded text-sm"
          />
          <button onClick={add} className="bg-green-600 text-white px-3 py-1 rounded text-sm">
            +
          </button>
        </div>

        <div className="flex gap-2 mb-4 text-sm">
          {(['all', 'open', 'closed'] as const).map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-2 py-1 rounded ${view === v ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            >
              {v}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          {shown.map(t => (
            <div key={t.id} className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded">
              <input type="checkbox" checked={t.finished} onChange={() => toggle(t.id)} />
              <span className={t.finished ? 'line-through text-gray-500' : ''}>{t.name}</span>
              <button onClick={() => remove(t.id)} className="ml-auto text-red-500 text-sm">
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TodoList;