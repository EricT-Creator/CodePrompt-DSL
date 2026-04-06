import React, { useState } from 'react';

interface TodoItem {
  id: number;
  text: string;
  done: boolean;
}

const TodoList: React.FC = () => {
  const [items, setItems] = useState<TodoItem[]>([]);
  const [text, setText] = useState('');
  const [view, setView] = useState<'all' | 'todo' | 'done'>('all');

  const addItem = () => {
    if (text.trim()) {
      setItems([...items, { id: Date.now(), text: text.trim(), done: false }]);
      setText('');
    }
  };

  const removeItem = (id: number) => {
    setItems(items.filter(item => item.id !== id));
  };

  const toggleItem = (id: number) => {
    setItems(items.map(item =>
      item.id === id ? { ...item, done: !item.done } : item
    ));
  };

  const visibleItems = items.filter(item => {
    if (view === 'todo') return !item.done;
    if (view === 'done') return item.done;
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="max-w-xl mx-auto">
        <div className="bg-gray-800 rounded-xl shadow-2xl overflow-hidden">
          <div className="px-6 py-8 border-b border-gray-700">
            <h1 className="text-3xl font-bold text-white mb-6">Todo List</h1>
            
            <div className="flex gap-3">
              <input
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addItem()}
                className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="Add a new todo..."
              />
              <button
                onClick={addItem}
                className="px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-gray-800 transition"
              >
                Add
              </button>
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-750 border-b border-gray-700">
            <div className="flex gap-2">
              {[
                { key: 'all', label: 'All' },
                { key: 'todo', label: 'Active' },
                { key: 'done', label: 'Completed' },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setView(key as 'all' | 'todo' | 'done')}
                  className={`px-4 py-2 rounded-lg font-medium transition ${
                    view === key
                      ? 'bg-green-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="p-6">
            {visibleItems.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No items to display</p>
            ) : (
              <ul className="space-y-3">
                {visibleItems.map(item => (
                  <li
                    key={item.id}
                    className="flex items-center gap-4 p-4 bg-gray-700 rounded-lg hover:bg-gray-650 transition"
                  >
                    <input
                      type="checkbox"
                      checked={item.done}
                      onChange={() => toggleItem(item.id)}
                      className="w-5 h-5 text-green-600 bg-gray-600 border-gray-500 rounded focus:ring-2 focus:ring-green-500 focus:ring-offset-gray-700"
                    />
                    <span
                      className={`flex-1 ${
                        item.done ? 'line-through text-gray-500' : 'text-gray-200'
                      }`}
                    >
                      {item.text}
                    </span>
                    <button
                      onClick={() => removeItem(item.id)}
                      className="text-red-400 hover:text-red-300 font-medium focus:outline-none transition"
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TodoList;
