import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  completed: boolean;
}

const TodoList: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: 'Learn TypeScript', completed: true },
    { id: 2, text: 'Practice React hooks', completed: false },
    { id: 3, text: 'Build projects', completed: false },
  ]);
  const [newTodo, setNewTodo] = useState<string>('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const handleAddTodo = () => {
    if (newTodo.trim() === '') return;
    const todo: Todo = {
      id: todos.length > 0 ? Math.max(...todos.map(t => t.id)) + 1 : 1,
      text: newTodo.trim(),
      completed: false,
    };
    setTodos([...todos, todo]);
    setNewTodo('');
  };

  const handleDeleteTodo = (id: number) => {
    setTodos(todos.filter(todo => todo.id !== id));
  };

  const handleToggleTodo = (id: number) => {
    setTodos(
      todos.map(todo =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
    );
  };

  const filteredTodos = todos.filter(todo => {
    if (filter === 'active') return !todo.completed;
    if (filter === 'completed') return todo.completed;
    return true;
  });

  const activeTodosCount = todos.filter(todo => !todo.completed).length;
  const completedTodosCount = todos.length - activeTodosCount;

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-3xl shadow-2xl p-10 mb-8">
          <h1 className="text-5xl font-black text-gray-900 text-center mb-10">
            Todo Manager
          </h1>

          {/* Input section */}
          <div className="flex gap-4 mb-12">
            <input
              type="text"
              value={newTodo}
              onChange={(e) => setNewTodo(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddTodo()}
              placeholder="Enter a new task..."
              className="flex-1 px-6 py-4 text-xl border-3 border-gray-400 rounded-2xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-200"
            />
            <button
              onClick={handleAddTodo}
              className="px-10 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-xl font-bold rounded-2xl hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-6 focus:ring-blue-400 transition-all transform hover:scale-105"
            >
              Add Task
            </button>
          </div>

          {/* Filter buttons */}
          <div className="flex gap-3 mb-10">
            <button
              onClick={() => setFilter('all')}
              className={`px-8 py-3 text-lg font-bold rounded-xl transition-all ${filter === 'all' ? 'bg-blue-600 text-white shadow-lg' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              All ({todos.length})
            </button>
            <button
              onClick={() => setFilter('active')}
              className={`px-8 py-3 text-lg font-bold rounded-xl transition-all ${filter === 'active' ? 'bg-blue-600 text-white shadow-lg' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              Active ({activeTodosCount})
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-8 py-3 text-lg font-bold rounded-xl transition-all ${filter === 'completed' ? 'bg-blue-600 text-white shadow-lg' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              Completed ({completedTodosCount})
            </button>
          </div>

          {/* Todo items */}
          <div className="space-y-6">
            {filteredTodos.length === 0 ? (
              <div className="text-center py-12 bg-gray-50 rounded-2xl border-3 border-dashed border-gray-300">
                <p className="text-2xl text-gray-600 font-semibold mb-4">No tasks found</p>
                <p className="text-gray-500">Try a different filter or add a new task</p>
              </div>
            ) : (
              filteredTodos.map(todo => (
                <div
                  key={todo.id}
                  className="flex items-center gap-6 p-6 bg-white border-3 border-gray-300 rounded-2xl hover:border-blue-400 transition-all"
                >
                  <input
                    type="checkbox"
                    checked={todo.completed}
                    onChange={() => handleToggleTodo(todo.id)}
                    className="h-8 w-8 text-blue-600 focus:ring-4 focus:ring-blue-300"
                  />
                  <span
                    className={`flex-1 text-2xl font-medium ${todo.completed ? 'line-through text-gray-400' : 'text-gray-900'}`}
                  >
                    {todo.text}
                  </span>
                  <button
                    onClick={() => handleDeleteTodo(todo.id)}
                    className="px-6 py-3 bg-red-500 text-white font-bold text-lg rounded-xl hover:bg-red-600 focus:outline-none focus:ring-4 focus:ring-red-300 transition-colors"
                  >
                    Remove
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Summary panel */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-100 rounded-3xl shadow-xl p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">Summary</h2>
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl text-center shadow-lg">
              <p className="text-4xl font-black text-blue-600">{todos.length}</p>
              <p className="text-gray-700 mt-2 font-semibold">Total Tasks</p>
            </div>
            <div className="bg-white p-6 rounded-2xl text-center shadow-lg">
              <p className="text-4xl font-black text-green-600">{activeTodosCount}</p>
              <p className="text-gray-700 mt-2 font-semibold">Active</p>
            </div>
            <div className="bg-white p-6 rounded-2xl text-center shadow-lg">
              <p className="text-4xl font-black text-purple-600">{completedTodosCount}</p>
              <p className="text-gray-700 mt-2 font-semibold">Completed</p>
            </div>
          </div>
        </div>

        <div className="mt-10 text-center text-gray-500 text-base">
          <p>A mock todo application with full CRUD functionality and filtering</p>
        </div>
      </div>
    </div>
  );
};

export default TodoList;