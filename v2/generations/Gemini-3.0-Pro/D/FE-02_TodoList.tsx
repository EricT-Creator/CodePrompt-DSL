import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  completed: boolean;
}

export default function TodoApp() {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: '学习 React', completed: false },
    { id: 2, text: '学习 TypeScript', completed: true },
  ]);
  const [inputText, setInputText] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const handleAddTodo = () => {
    if (inputText.trim() !== '') {
      setTodos([...todos, { id: Date.now(), text: inputText.trim(), completed: false }]);
      setInputText('');
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
    <div className="flex flex-col items-center min-h-screen bg-gray-100 p-4 font-sans">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold text-center text-gray-800 mb-6">待办事项</h1>

        <div className="flex mb-4">
          <input
            type="text"
            className="flex-grow shadow appearance-none border rounded-l w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
            placeholder="添加新任务..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddTodo()}
          />
          <button
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-r focus:outline-none focus:shadow-outline"
            onClick={handleAddTodo}
          >
            添加
          </button>
        </div>

        <div className="flex justify-center space-x-4 mb-6">
          <button
            className={`px-4 py-1 rounded-full text-sm font-medium transition-colors ${filter === 'all' ? 'bg-blue-100 text-blue-800' : 'text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setFilter('all')}
          >
            全部
          </button>
          <button
            className={`px-4 py-1 rounded-full text-sm font-medium transition-colors ${filter === 'active' ? 'bg-blue-100 text-blue-800' : 'text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setFilter('active')}
          >
            未完成
          </button>
          <button
            className={`px-4 py-1 rounded-full text-sm font-medium transition-colors ${filter === 'completed' ? 'bg-blue-100 text-blue-800' : 'text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setFilter('completed')}
          >
            已完成
          </button>
        </div>

        <ul className="space-y-3">
          {filteredTodos.map((todo) => (
            <li
              key={todo.id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-md border border-gray-200 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-center flex-grow overflow-hidden pr-3">
                <input
                  type="checkbox"
                  className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer mr-3 shrink-0"
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
                className="text-red-500 hover:text-red-700 focus:outline-none shrink-0"
                onClick={() => handleDeleteTodo(todo.id)}
              >
                删除
              </button>
            </li>
          ))}
          {filteredTodos.length === 0 && (
            <div className="text-center text-gray-500 py-4 italic">暂无任务</div>
          )}
        </ul>
      </div>
    </div>
  );
}
