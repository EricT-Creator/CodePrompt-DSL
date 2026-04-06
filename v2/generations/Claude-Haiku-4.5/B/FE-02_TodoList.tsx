import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  done: boolean;
}

const TodoList = () => {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [newTodo, setNewTodo] = useState('');
  const [status, setStatus] = useState<'all' | 'pending' | 'done'>('all');

  const add = () => {
    if (newTodo.trim()) {
      setTodos([...todos, { id: Date.now(), text: newTodo, done: false }]);
      setNewTodo('');
    }
  };

  const toggle = (id: number) => {
    setTodos(todos.map(t => t.id === id ? { ...t, done: !t.done } : t));
  };

  const remove = (id: number) => {
    setTodos(todos.filter(t => t.id !== id));
  };

  const display = status === 'all' ? todos : status === 'pending' ? todos.filter(t => !t.done) : todos.filter(t => t.done);

  return (
    <div className="min-h-screen bg-white p-4">
      <div className="max-w-md mx-auto">
        <h1 className="text-2xl font-bold mb-4">Todos</h1>

        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newTodo}
            onChange={(e) => setNewTodo(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && add()}
            placeholder="New task"
            className="flex-1 px-3 py-2 border rounded"
          />
          <button onClick={add} className="bg-blue-600 text-white px-4 py-2 rounded">
            Add
          </button>
        </div>

        <div className="flex gap-2 mb-4">
          {(['all', 'pending', 'done'] as const).map(s => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`px-3 py-1 rounded ${status === s ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            >
              {s}
            </button>
          ))}
        </div>

        {display.map(todo => (
          <div key={todo.id} className="flex items-center gap-2 p-2 border-b">
            <input
              type="checkbox"
              checked={todo.done}
              onChange={() => toggle(todo.id)}
            />
            <span className={todo.done ? 'line-through' : ''}>{todo.text}</span>
            <button onClick={() => remove(todo.id)} className="ml-auto text-red-600">
              X
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TodoList;