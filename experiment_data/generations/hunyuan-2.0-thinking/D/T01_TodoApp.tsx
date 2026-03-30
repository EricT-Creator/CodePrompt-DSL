import React, { useState } from 'react';

interface TodoProps {
  id: number;
  text: string;
  completed: boolean;
}

const initialTodos: Todo[] = [
  { id: 1, text: 'Buy groceries', completed: false },
  { id: 2, text: 'Walk the dog', completed: true },
  { id: 3, text: 'Read a book', completed: false },
];

type Filter = 'all' | 'active' | 'completed';

const TodoApp: React.FunctionalComponent = () => {
  const [todos, setTodos] = useState<Todo[]>(initialTodos);
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<Filter>('all');

  const addTodo = () => {
    if (input.trim() === '') return;
    setTodos([...todos, { id: Date.now(), text: input.trim(), completed: false }]);
    setInput('');
  };

  const deleteTodo = (id: number) => {
    setTodos(todos.filter(t => t.id !== id));
  };

  const toggleTodo = (id: number) => {
    setTodos(todos.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const filtered = todos.filter(t => {
    if (filter === 'active') return !t.completed;
    if (filter === 'completed') return t.completed;
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50 p-4 max-w-md mx-auto">
      <h1 className="text-2xl font-bold text-center mb-6">Todo List</h1>
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addTodo()}
          placeholder="Add a todo..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={addTodo}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Add
        </button>
      </div>
      <div className="flex gap-2 mb-4">
        {(['all', 'active', 'completed'] as Filter[]).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-sm ${
              filter === f ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      <ul className="space-y-2">
        {filtered.map(todo => (
          <li
            key={todo.id}
            className="flex items-center justify-between p-3 bg-white rounded-lg shadow-sm"
          >
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={todo.completed}
                onChange={() => toggleTodo(todo.id)}
                className="w-5 h-5 accent-blue-500"
              />
              <span className={todo.completed ? 'line-through text-gray-400' : 'text-gray-800'}>
                {todo.text}
              </span>
            </div>
            <button
              onClick={() => deleteTodo(todo.id)}
              className="text-red-500 hover:text-red-700 text-sm"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TodoApp;
