import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  completed: boolean;
}

const TodoList: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: 'Learn React', completed: true },
    { id: 2, text: 'Build a todo app', completed: false },
    { id: 3, text: 'Write documentation', completed: false },
  ]);
  const [newTodo, setNewTodo] = useState<string>('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const addTodo = () => {
    if (newTodo.trim() === '') return;
    const newTodoItem: Todo = {
      id: todos.length + 1,
      text: newTodo.trim(),
      completed: false,
    };
    setTodos([...todos, newTodoItem]);
    setNewTodo('');
  };

  const deleteTodo = (id: number) => {
    setTodos(todos.filter(todo => todo.id !== id));
  };

  const toggleTodo = (id: number) => {
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

  const activeCount = todos.filter(todo => !todo.completed).length;

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
        <header className="mb-10 text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Todo List</h1>
          <p className="text-gray-600">Manage your tasks efficiently</p>
        </header>

        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          {/* Add new todo */}
          <div className="flex gap-3 mb-10">
            <input
              type="text"
              value={newTodo}
              onChange={(e) => setNewTodo(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTodo()}
              placeholder="What needs to be done?"
              className="flex-1 px-5 py-3 text-lg border-2 border-gray-300 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
            <button
              onClick={addTodo}
              className="px-8 bg-blue-600 text-white font-bold text-lg rounded-xl hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 transition-colors"
            >
              Add
            </button>
          </div>

          {/* Filter buttons */}
          <div className="flex gap-2 mb-8">
            <button
              onClick={() => setFilter('all')}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${filter === 'all' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              All ({todos.length})
            </button>
            <button
              onClick={() => setFilter('active')}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${filter === 'active' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Active ({activeCount})
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${filter === 'completed' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Completed ({todos.length - activeCount})
            </button>
          </div>

          {/* Todo list */}
          <div className="space-y-4">
            {filteredTodos.length === 0 ? (
              <div className="text-center py-10 text-gray-500">
                <p className="text-xl">No todos to show</p>
                <p className="mt-2">Try changing the filter or adding a new task</p>
              </div>
            ) : (
              filteredTodos.map(todo => (
                <div
                  key={todo.id}
                  className="flex items-center gap-4 p-5 border-2 border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={todo.completed}
                    onChange={() => toggleTodo(todo.id)}
                    className="h-6 w-6 text-blue-600 focus:ring-blue-500"
                  />
                  <span
                    className={`flex-1 text-lg ${todo.completed ? 'line-through text-gray-500' : 'text-gray-800'}`}
                  >
                    {todo.text}
                  </span>
                  <button
                    onClick={() => deleteTodo(todo.id)}
                    className="px-4 py-2 bg-red-100 text-red-700 font-medium rounded-lg hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-300 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 bg-blue-50 rounded-xl">
              <p className="text-2xl font-bold text-blue-700">{todos.length}</p>
              <p className="text-gray-600 mt-1">Total</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl">
              <p className="text-2xl font-bold text-green-700">{activeCount}</p>
              <p className="text-gray-600 mt-1">Active</p>
            </div>
            <div className="p-4 bg-purple-50 rounded-xl">
              <p className="text-2xl font-bold text-purple-700">{todos.length - activeCount}</p>
              <p className="text-gray-600 mt-1">Completed</p>
            </div>
          </div>
        </div>

        <footer className="mt-8 text-center text-gray-500 text-sm">
          <p>Mock todo application with CRUD operations and filtering</p>
        </footer>
      </div>
    </div>
  );
};

export default TodoList;