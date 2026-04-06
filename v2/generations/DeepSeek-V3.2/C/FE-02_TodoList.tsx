import React, { useState } from 'react';

interface TodoItem {
  id: number;
  title: string;
  done: boolean;
}

const TodoList: React.FC = () => {
  const [items, setItems] = useState<TodoItem[]>([
    { id: 1, title: 'Setup project', done: true },
    { id: 2, title: 'Implement UI', done: true },
    { id: 3, title: 'Add tests', done: false },
    { id: 4, title: 'Write docs', done: false },
  ]);
  const [input, setInput] = useState<string>('');
  const [viewMode, setViewMode] = useState<'all' | 'pending' | 'done'>('all');

  const addItem = () => {
    if (!input.trim()) return;
    const newItem: TodoItem = {
      id: items.length > 0 ? Math.max(...items.map(i => i.id)) + 1 : 1,
      title: input.trim(),
      done: false,
    };
    setItems([...items, newItem]);
    setInput('');
  };

  const removeItem = (id: number) => {
    setItems(items.filter(item => item.id !== id));
  };

  const toggleDone = (id: number) => {
    setItems(items.map(item => 
      item.id === id ? { ...item, done: !item.done } : item
    ));
  };

  const filteredItems = items.filter(item => {
    if (viewMode === 'pending') return !item.done;
    if (viewMode === 'done') return item.done;
    return true;
  });

  const pendingCount = items.filter(item => !item.done).length;
  const doneCount = items.filter(item => item.done).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-100 to-gray-300 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-3xl shadow-3xl p-12 mb-10">
          <header className="text-center mb-16">
            <h1 className="text-6xl font-extrabold text-gray-900 mb-6">
              Task Manager
            </h1>
            <p className="text-2xl text-gray-600">Organize your work efficiently</p>
          </header>

          {/* Input area */}
          <div className="flex gap-5 mb-16">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addItem()}
              placeholder="What's your next task?"
              className="flex-1 px-8 py-6 text-2xl border-4 border-gray-400 rounded-3xl focus:outline-none focus:border-blue-500 focus:ring-8 focus:ring-blue-200"
            />
            <button
              onClick={addItem}
              className="px-12 py-6 bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-2xl font-black rounded-3xl hover:from-emerald-600 hover:to-teal-700 focus:outline-none focus:ring-8 focus:ring-emerald-300 transition-all duration-300 transform hover:scale-105 shadow-2xl hover:shadow-3xl"
            >
              ADD
            </button>
          </div>

          {/* View controls */}
          <div className="flex gap-4 justify-center mb-12">
            <button
              onClick={() => setViewMode('all')}
              className={`px-10 py-4 text-xl font-black rounded-2xl transition-all ${viewMode === 'all' ? 'bg-blue-600 text-white shadow-xl' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              All ({items.length})
            </button>
            <button
              onClick={() => setViewMode('pending')}
              className={`px-10 py-4 text-xl font-black rounded-2xl transition-all ${viewMode === 'pending' ? 'bg-blue-600 text-white shadow-xl' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              Pending ({pendingCount})
            </button>
            <button
              onClick={() => setViewMode('done')}
              className={`px-10 py-4 text-xl font-black rounded-2xl transition-all ${viewMode === 'done' ? 'bg-blue-600 text-white shadow-xl' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              Done ({doneCount})
            </button>
          </div>

          {/* Task list */}
          <div className="space-y-8">
            {filteredItems.length === 0 ? (
              <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-gray-100 rounded-3xl border-4 border-dashed border-gray-400">
                <div className="text-4xl text-gray-500 mb-6">📝</div>
                <p className="text-3xl text-gray-700 font-bold mb-4">No tasks to display</p>
                <p className="text-xl text-gray-600">Adjust the filter or create a new task</p>
              </div>
            ) : (
              filteredItems.map(item => (
                <div
                  key={item.id}
                  className={`flex items-center gap-8 p-8 border-4 rounded-3xl transition-all ${item.done ? 'bg-green-50 border-green-300' : 'bg-white border-gray-300 hover:border-blue-400'}`}
                >
                  <input
                    type="checkbox"
                    checked={item.done}
                    onChange={() => toggleDone(item.id)}
                    className="h-10 w-10 text-green-600 focus:ring-6 focus:ring-green-400"
                  />
                  <span
                    className={`flex-1 text-3xl font-bold ${item.done ? 'line-through text-gray-500' : 'text-gray-900'}`}
                  >
                    {item.title}
                  </span>
                  <button
                    onClick={() => removeItem(item.id)}
                    className="px-8 py-4 bg-gradient-to-r from-red-500 to-rose-600 text-white text-xl font-black rounded-2xl hover:from-red-600 hover:to-rose-700 focus:outline-none focus:ring-6 focus:ring-red-300 transition-all transform hover:scale-110 shadow-lg hover:shadow-xl"
                  >
                    DELETE
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Dashboard */}
        <div className="bg-gradient-to-r from-gray-900 to-black text-white rounded-3xl shadow-3xl p-12">
          <h2 className="text-4xl font-black text-center mb-10">PROGRESS DASHBOARD</h2>
          <div className="grid grid-cols-3 gap-8">
            <div className="bg-gradient-to-br from-blue-500 to-blue-700 p-10 rounded-3xl text-center shadow-2xl">
              <p className="text-6xl font-black mb-4">{items.length}</p>
              <p className="text-2xl font-bold">TOTAL</p>
            </div>
            <div className="bg-gradient-to-br from-amber-500 to-amber-700 p-10 rounded-3xl text-center shadow-2xl">
              <p className="text-6xl font-black mb-4">{pendingCount}</p>
              <p className="text-2xl font-bold">PENDING</p>
            </div>
            <div className="bg-gradient-to-br from-green-500 to-green-700 p-10 rounded-3xl text-center shadow-2xl">
              <p className="text-6xl font-black mb-4">{doneCount}</p>
              <p className="text-2xl font-bold">DONE</p>
            </div>
          </div>
          <div className="mt-10 pt-8 border-t-2 border-gray-700 text-center">
            <p className="text-xl text-gray-400">Mock todo application with full functionality</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TodoList;