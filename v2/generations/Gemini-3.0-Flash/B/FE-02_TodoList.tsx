import React, { useState } from 'react';

interface Todo {
  id: string;
  task: string;
  done: boolean;
}

const TodoList: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([
    { id: '1', task: 'Review Code', done: false },
    { id: '2', task: 'Update Docs', done: true },
  ]);
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const addItem = () => {
    if (!input.trim()) return;
    setTodos([...todos, { id: Date.now().toString(), task: input, done: false }]);
    setInput('');
  };

  const deleteItem = (id: string) => {
    setTodos(todos.filter(t => t.id !== id));
  };

  const toggleItem = (id: string) => {
    setTodos(todos.map(t => t.id === id ? { ...t, done: !t.done } : t));
  };

  const filtered = todos.filter(t => {
    if (filter === 'active') return !t.done;
    if (filter === 'completed') return t.done;
    return true;
  });

  return (
    <div className="p-6 max-w-md mx-auto bg-gray-50 min-h-screen">
      <h1 className="text-xl font-bold mb-4">Tasks</h1>
      <div className="flex gap-2 mb-4">
        <input 
          className="flex-1 p-2 border rounded"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="New task..."
        />
        <button onClick={addItem} className="bg-blue-500 text-white px-4 py-2 rounded">Add</button>
      </div>
      <div className="flex gap-2 mb-4 text-sm">
        {(['all', 'active', 'completed'] as const).map(f => (
          <button 
            key={f} 
            onClick={() => setFilter(f)}
            className={`px-2 py-1 rounded ${filter === f ? 'bg-blue-200' : 'bg-white border'}`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      <ul className="bg-white border rounded divide-y">
        {filtered.map(t => (
          <li key={t.id} className="p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={t.done} onChange={() => toggleItem(t.id)} />
              <span className={t.done ? 'line-through text-gray-400' : ''}>{t.task}</span>
            </div>
            <button onClick={() => deleteItem(t.id)} className="text-red-500">×</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TodoList;
