import React, { useState } from 'react';

interface Task {
  id: string;
  title: string;
  status: 'pending' | 'completed';
  createdAt: Date;
}

type FilterType = 'all' | 'pending' | 'completed';

const TodoList: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');

  const taskManager = {
    create: (title: string) => {
      if (title.trim()) {
        const newTask: Task = {
          id: `task-${Date.now()}`,
          title: title.trim(),
          status: 'pending',
          createdAt: new Date(),
        };
        setTasks(prev => [...prev, newTask]);
        setNewTaskTitle('');
      }
    },

    delete: (taskId: string) => {
      setTasks(prev => prev.filter(task => task.id !== taskId));
    },

    toggleStatus: (taskId: string) => {
      setTasks(prev =>
        prev.map(task =>
          task.id === taskId
            ? { ...task, status: task.status === 'pending' ? 'completed' : 'pending' }
            : task
        )
      );
    },

    getFiltered: (filter: FilterType) => {
      return tasks.filter(task => {
        if (filter === 'pending') return task.status === 'pending';
        if (filter === 'completed') return task.status === 'completed';
        return true;
      });
    },
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      taskManager.create(newTaskTitle);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 py-8 px-4">
      <div className="max-w-lg mx-auto">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
            <h1 className="text-2xl font-bold text-white">Task Manager</h1>
          </div>

          <div className="p-6">
            <div className="flex gap-3 mb-6">
              <input
                type="text"
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-indigo-500 focus:outline-none transition"
                placeholder="What needs to be done?"
              />
              <button
                onClick={() => taskManager.create(newTaskTitle)}
                className="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition"
              >
                Add
              </button>
            </div>

            <div className="flex gap-2 mb-6">
              {(['all', 'pending', 'completed'] as FilterType[]).map((filterType) => (
                <button
                  key={filterType}
                  onClick={() => setActiveFilter(filterType)}
                  className={`px-4 py-2 rounded-lg font-medium transition ${
                    activeFilter === filterType
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {filterType.charAt(0).toUpperCase() + filterType.slice(1)}
                </button>
              ))}
            </div>

            <div className="space-y-3">
              {taskManager.getFiltered(activeFilter).map(task => (
                <div
                  key={task.id}
                  className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                >
                  <input
                    type="checkbox"
                    checked={task.status === 'completed'}
                    onChange={() => taskManager.toggleStatus(task.id)}
                    className="w-5 h-5 text-indigo-600 rounded focus:ring-2 focus:ring-indigo-500"
                  />
                  <span
                    className={`flex-1 ${
                      task.status === 'completed'
                        ? 'line-through text-gray-400'
                        : 'text-gray-800'
                    }`}
                  >
                    {task.title}
                  </span>
                  <button
                    onClick={() => taskManager.delete(task.id)}
                    className="text-red-500 hover:text-red-700 font-medium focus:outline-none transition"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            {tasks.length === 0 && (
              <p className="text-center text-gray-400 mt-6">No tasks yet. Add one above!</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TodoList;
