import React, { useState } from "react";

type FilterType = "all" | "active" | "done";

interface Task {
  id: number;
  title: string;
  completed: boolean;
}

export default function TodoList() {
  const [tasks, setTasks] = useState<Task[]>([
    { id: 1, title: "Learn TypeScript", completed: false },
    { id: 2, title: "Build a project", completed: false },
    { id: 3, title: "Write tests", completed: true },
  ]);
  const [newTask, setNewTask] = useState("");
  const [view, setView] = useState<FilterType>("all");

  const handleAdd = () => {
    if (!newTask.trim()) return;
    setTasks([...tasks, { id: Date.now(), title: newTask.trim(), completed: false }]);
    setNewTask("");
  };

  const handleToggle = (id: number) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const handleRemove = (id: number) => {
    setTasks(tasks.filter(t => t.id !== id));
  };

  const visible = tasks.filter(t => {
    if (view === "active") return !t.completed;
    if (view === "done") return t.completed;
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-100 flex items-start justify-center pt-10 px-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow p-6">
        <h1 className="text-xl font-bold text-slate-800 mb-4">My Tasks</h1>
        <div className="flex gap-2 mb-4">
          <input value={newTask} onChange={e => setNewTask(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleAdd()}
            placeholder="New task..." className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          <button onClick={handleAdd} className="bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-600">Add</button>
        </div>
        <div className="flex gap-2 mb-4">
          {(["all", "active", "done"] as FilterType[]).map(f => (
            <button key={f} onClick={() => setView(f)}
              className={`px-3 py-1 rounded-md text-xs font-medium capitalize ${view === f ? "bg-indigo-500 text-white" : "bg-slate-100 text-slate-600"}`}>{f}</button>
          ))}
        </div>
        <div className="space-y-2">
          {visible.map(task => (
            <div key={task.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <input type="checkbox" checked={task.completed} onChange={() => handleToggle(task.id)} className="h-4 w-4 rounded" />
              <span className={`flex-1 text-sm ${task.completed ? "line-through text-slate-400" : "text-slate-700"}`}>{task.title}</span>
              <button onClick={() => handleRemove(task.id)} className="text-red-500 text-xs hover:underline">Remove</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
