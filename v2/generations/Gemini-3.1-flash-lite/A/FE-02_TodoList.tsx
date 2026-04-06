import React, { useState } from 'react';

export default function TodoList() {
  const [todos, setTodos] = useState<{ id: number; text: string; completed: boolean }[]>([]);
  const [text, setText] = useState('');
  const [filter, setFilter] = useState<'all' | 'completed' | 'active'>('all');

  const add = () => {
    if (!text) return;
    setTodos([...todos, { id: Date.now(), text, completed: false }]);
    setText('');
  };

  const toggle = (id: number) => {
    setTodos(todos.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const remove = (id: number) => {
    setTodos(todos.filter(t => t.id !== id));
  };

  const filtered = todos.filter(t => {
    if (filter === 'completed') return t.completed;
    if (filter === 'active') return !t.completed;
    return true;
  });

  return (
    <div className="p-4 bg-white shadow rounded">
      <div className="flex mb-4">
        <input value={text} onChange={e => setText(e.target.value)} className="border p-2 flex-grow" />
        <button onClick={add} className="bg-green-500 text-white p-2">Add</button>
      </div>
      <div className="flex gap-2 mb-4">
        <button onClick={() => setFilter('all')}>All</button>
        <button onClick={() => setFilter('active')}>Active</button>
        <button onClick={() => setFilter('completed')}>Completed</button>
      </div>
      <ul>
        {filtered.map(t => (
          <li key={t.id} className="flex justify-between border-b p-2">
            <span onClick={() => toggle(t.id)} className={t.completed ? 'line-through' : ''}>{t.text}</span>
            <button onClick={() => remove(t.id)} className="text-red-500">Del</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
