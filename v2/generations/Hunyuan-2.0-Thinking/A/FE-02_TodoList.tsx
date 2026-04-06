import React, { useState } from 'react';

export default function TodoList() {
  const [todos, setTodos] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [filter, setFilter] = useState('all');

  const addTodo = () => {
    if (inputValue.trim()) {
      setTodos([...todos, { id: Date.now(), text: inputValue.trim(), completed: false }]);
      setInputValue('');
    }
  };

  const deleteTodo = (id) => {
    setTodos(todos.filter(todo => todo.id !== id));
  };

  const toggleTodo = (id) => {
    setTodos(todos.map(todo => todo.id === id ? { ...todo, completed: !todo.completed } : todo));
  };

  const filteredTodos = todos.filter(todo => {
    if (filter === 'active') return !todo.completed;
    if (filter === 'completed') return todo.completed;
    return true;
  });

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
      <div className="flex mb-4">
        <input type="text" value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && addTodo()} className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500" placeholder="Add new task" />
        <button onClick={addTodo} className="px-4 py-2 bg-indigo-600 text-white rounded-r-md hover:bg-indigo-700">Add</button>
      </div>
      <div className="flex gap-2 mb-4">
        {['all', 'active', 'completed'].map(f => (
          <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 rounded ${filter === f ? 'bg-indigo-600 text-white' : 'bg-gray-200'}`}>{f}</button>
        ))}
      </div>
      <ul className="space-y-2">
        {filteredTodos.map(todo => (
          <li key={todo.id} className="flex items-center justify-between p-2 border rounded">
            <span className={`flex-1 ${todo.completed ? 'line-through text-gray-500' : ''}`} onClick={() => toggleTodo(todo.id)}>{todo.text}</span>
            <button onClick={() => deleteTodo(todo.id)} className="ml-2 text-red-600 hover:text-red-800">Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}