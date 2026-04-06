import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  completed: boolean;
}

export default function TodoApp() {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: 'Buy groceries', completed: false },
    { id: 2, text: 'Walk the dog', completed: true },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const handleAddTodo = () => {
    if (inputValue.trim() !== '') {
      const newTodo: Todo = {
        id: Date.now(),
        text: inputValue.trim(),
        completed: false,
      };
      setTodos([...todos, newTodo]);
      setInputValue('');
    }
  };

  const handleDeleteTodo = (id: number) => {
    setTodos(todos.filter((todo) => todo.id !== id));
  };

  const handleToggleTodo = (id: number) => {
    setTodos(
      todos.map((todo) =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
    );
  };

  const filteredTodos = todos.filter((todo) => {
    if (filter === 'active') return !todo.completed;
    if (filter === 'completed') return todo.completed;
    return true;
  });

  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-gray-100 p-4 font-sans">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold text-center text-gray-800 mb-6">Todo List</h1>

        <div className="flex mb-4">
          <input
            type="text"
            className="flex-grow shadow appearance-none border rounded-l py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
            placeholder="Add new task..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddTodo()}
          />
          <button
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-r focus:outline-none focus:shadow-outline"
            onClick={handleAddTodo}
          >
            Add
          </button>
        </div>

        <div className="flex justify-center space-x-4 mb-6">
          <button
            className={`px-3 py-1 rounded text-sm font-medium ${filter === 'all' ? 'bg-gray-200 text-gray-800' : 'text-gray-600 hover:bg-gray-100'}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`px-3 py-1 rounded text-sm font-medium ${filter === 'active' ? 'bg-gray-200 text-gray-800' : 'text-gray-600 hover:bg-gray-100'}`}
            onClick={() => setFilter('active')}
          >
            Active
          </button>
          <button
            className={`px-3 py-1 rounded text-sm font-medium ${filter === 'completed' ? 'bg-gray-200 text-gray-800' : 'text-gray-600 hover:bg-gray-100'}`}
            onClick={() => setFilter('completed')}
          >
            Completed
          </button>
        </div>

        <ul className="space-y-3">
          {filteredTodos.map((todo) => (
            <li
              key={todo.id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-md border border-gray-200 hover:shadow-sm transition-shadow duration-200"
            >
              <div className="flex items-center flex-grow overflow-hidden">
                <input
                  type="checkbox"
                  className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer mr-3"
                  checked={todo.completed}
                  onChange={() => handleToggleTodo(todo.id)}
                />
                <span
                  className={`text-gray-800 truncate ${todo.completed ? 'line-through text-gray-400' : ''}`}
                >
                  {todo.text}
                </span>
              </div>
              <button
                className="ml-2 text-red-500 hover:text-red-700 focus:outline-none font-medium"
                onClick={() => handleDeleteTodo(todo.id)}
              >
                Delete
              </button>
            </li>
          ))}
          {filteredTodos.length === 0 && (
            <div className="text-center text-gray-500 py-4 italic">No tasks found.</div>
          )}
        </ul>
      </div>
    </div>
  );
}
