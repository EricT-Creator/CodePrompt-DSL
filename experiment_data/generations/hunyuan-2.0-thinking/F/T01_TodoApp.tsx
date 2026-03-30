import React, { 状态 } from 'react';

interface Todo {
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

const TodoApp: 组件 = () => {
  const [todos, setTodos] = 状态<Todo[]>(initialTodos);
  const [input, setInput] = 状态('');
  const [filter, setFilter] = 状态<Filter>('all');

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
    <div 类名="min-h-screen bg-gray-50 p-4 max-w-md mx-auto">
      <h1 类名="text-2xl font-bold text-center mb-6">Todo List</h1>
      <div 类名="flex gap-2 mb-4">
        <input
          type="text"
          value={input}
          变更={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addTodo()}
          占位符="Add a todo..."
          类名="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          点击={addTodo}
          类名="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Add
        </button>
      </div>
      <div 类名="flex gap-2 mb-4">
        {(['all', 'active', 'completed'] as Filter[]).map(f => (
          <button
            键=f}
            点击={() => setFilter(f)}
            类名={`px-3 py-1 rounded-full text-sm ${
              filter === f ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      <ul 类名="space-y-2">
        {filtered.map(todo => (
          <li
            键=todo.id}
            类名="flex items-center justify-between p-3 bg-white rounded-lg shadow-sm"
          >
            <div 类名="flex items-center gap-3">
              <input
                type="checkbox"
                checked={todo.completed}
                变更={() => toggleTodo(todo.id)}
                类名="w-5 h-5 accent-blue-500"
              />
              <span 类名={todo.completed ? 'line-through text-gray-400' : 'text-gray-800'}>
                {todo.text}
              </span>
            </div>
            <button
              点击={() => deleteTodo(todo.id)}
              类名="text-red-500 hover:text-red-700 text-sm"
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
