import React, { useCallback, useMemo, useState } from "react";

interface Task {
  id: number;
  label: string;
  completed: boolean;
}

type View = "all" | "pending" | "completed";

export default function TodoList() {
  const [tasks, setTasks] = useState<Task[]>([
    { id: 1, label: "Verify prompt template tokens", completed: false },
    { id: 2, label: "Update experiment log", completed: true },
    { id: 3, label: "Run pilot on two models", completed: false },
  ]);
  const [newTask, setNewTask] = useState("");
  const [view, setView] = useState<View>("all");

  const displayed = useMemo(() => {
    if (view === "pending") return tasks.filter((t) => !t.completed);
    if (view === "completed") return tasks.filter((t) => t.completed);
    return tasks;
  }, [tasks, view]);

  const add = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const val = newTask.trim();
      if (!val) return;
      setTasks((prev) => [
        { id: Date.now(), label: val, completed: false },
        ...prev,
      ]);
      setNewTask("");
    },
    [newTask]
  );

  const toggle = (id: number) =>
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );

  const remove = (id: number) =>
    setTasks((prev) => prev.filter((t) => t.id !== id));

  const pendingCount = tasks.filter((t) => !t.completed).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8">
      <div className="mx-auto max-w-md bg-white rounded-2xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h1 className="text-xl font-bold text-slate-800">Tasks</h1>
          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
            {pendingCount} active
          </span>
        </div>

        <form onSubmit={add} className="flex gap-2 mb-5">
          <input
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            placeholder="New task…"
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-200"
          />
          <button
            type="submit"
            className="bg-teal-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition"
          >
            Add
          </button>
        </form>

        <div className="flex gap-1 mb-4">
          {(["all", "pending", "completed"] as View[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={`text-xs px-3 py-1.5 rounded-full capitalize font-medium ${
                view === v
                  ? "bg-teal-600 text-white"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {v}
            </button>
          ))}
        </div>

        <ul className="divide-y divide-slate-100">
          {displayed.map((task) => (
            <li key={task.id} className="flex items-center gap-3 py-3">
              <button
                type="button"
                onClick={() => toggle(task.id)}
                className={`w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center ${
                  task.completed
                    ? "bg-teal-600 border-teal-600 text-white"
                    : "border-slate-300"
                }`}
                aria-label={task.completed ? "Mark incomplete" : "Mark complete"}
              >
                {task.completed && (
                  <svg viewBox="0 0 12 12" className="w-3 h-3" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                )}
              </button>
              <span
                className={`flex-1 text-sm ${
                  task.completed ? "line-through text-slate-400" : "text-slate-700"
                }`}
              >
                {task.label}
              </span>
              <button
                type="button"
                onClick={() => remove(task.id)}
                className="text-xs text-rose-400 hover:text-rose-600 font-medium"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>

        {displayed.length === 0 && (
          <p className="text-center text-sm text-slate-400 py-8">No tasks match the filter</p>
        )}
      </div>
    </div>
  );
}
