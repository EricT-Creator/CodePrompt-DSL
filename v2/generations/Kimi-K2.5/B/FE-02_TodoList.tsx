import React, { useState } from 'react';

interface TodoItem {
  id: number;
  text: string;
  completed: boolean;
  createdAt: number;
}

interface TodoManager {
  items: TodoItem[];
  add: (text: string) => void;
  remove: (id: number) => void;
  toggle: (id: number) => void;
  filter: (status: 'all' | 'active' | 'completed') => TodoItem[];
}

export default function TodoList() {
  const [todos, setTodos] = useState<TodoItem[]>([
    { id: 1, text: 'Study TypeScript', completed: false, createdAt: Date.now() },
    { id: 2, text: 'Practice React hooks', completed: true, createdAt: Date.now() - 1000 },
    { id: 3, text: 'Review code', completed: false, createdAt: Date.now() - 2000 }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [currentFilter, setCurrentFilter] = useState<'all' | 'active' | 'completed'>('all');

  const manager: TodoManager = {
    items: todos,
    add: (text: string) => {
      if (text.trim()) {
        setTodos(prev => [...prev, {
          id: Date.now(),
          text: text.trim(),
          completed: false,
          createdAt: Date.now()
        }]);
      }
    },
    remove: (id: number) => {
      setTodos(prev => prev.filter(t => t.id !== id));
    },
    toggle: (id: number) => {
      setTodos(prev => prev.map(t => 
        t.id === id ? { ...t, completed: !t.completed } : t
      ));
    },
    filter: (status) => {
      if (status === 'active') return todos.filter(t => !t.completed);
      if (status === 'completed') return todos.filter(t => t.completed);
      return todos;
    }
  };

  const filteredItems = manager.filter(currentFilter);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-4">
      <div className="max-w-lg mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Task Manager</h1>
        <p className="text-gray-500 mb-6">Organize your work efficiently</p>
        
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                manager.add(inputValue);
                setInputValue('');
              }
            }}
            className="flex-1 px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            placeholder="What needs to be done?"
          />
          <button
            onClick={() => {
              manager.add(inputValue);
              setInputValue('');
            }}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all font-semibold"
          >
            Add
          </button>
        </div>

        <div className="flex gap-2 mb-6 bg-gray-100 p-1 rounded-lg">
          {(['all', 'active', 'completed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setCurrentFilter(f)}
              className={`flex-1 py-2 rounded-md text-sm font-medium capitalize transition-all ${
                currentFilter === f 
                  ? 'bg-white text-purple-600 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <ul className="space-y-3">
          {filteredItems.map((todo) => (
            <li
              key={todo.id}
              className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-gray-100 hover:shadow-sm transition-shadow"
            >
              <button
                onClick={() => manager.toggle(todo.id)}
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                  todo.completed 
                    ? 'bg-green-500 border-green-500 text-white' 
                    : 'border-gray-300 hover:border-purple-500'
                }`}
              >
                {todo.completed && '✓'}
              </button>
              <span className={`flex-1 ${todo.completed ? 'line-through text-gray-400' : 'text-gray-700'}`}>
                {todo.text}
              </span>
              <button
                onClick={() => manager.remove(todo.id)}
                className="text-gray-400 hover:text-red-500 transition-colors p-1"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>

        {filteredItems.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <p className="text-lg">No tasks here</p>
            <p className="text-sm">Add a new task to get started</p>
          </div>
        )}

        <div className="mt-6 pt-4 border-t border-gray-100 text-sm text-gray-500 flex justify-between">
          <span>{todos.filter(t => !t.completed).length} items left</span>
          <span>{todos.filter(t => t.completed).length} completed</span>
        </div>
      </div>
    </div>
  );
}
