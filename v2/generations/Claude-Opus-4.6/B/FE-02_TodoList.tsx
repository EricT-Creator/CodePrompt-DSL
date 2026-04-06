import React, { useState } from "react";

type Todo = {
  id: number;
  title: string;
  done: boolean;
};

type Filter = "all" | "active" | "done";

const seed: Todo[] = [
  { id: 1, title: "Outline the paper introduction", done: false },
  { id: 2, title: "Collect baseline measurements", done: true },
];

export default function TodoList() {
  const [todos, setTodos] = useState<Todo[]>(seed);
  const [draft, setDraft] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const visible =
    filter === "all"
      ? todos
      : filter === "active"
      ? todos.filter((t) => !t.done)
      : todos.filter((t) => t.done);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setTodos((prev) => [...prev, { id: Date.now(), title: text, done: false }]);
    setDraft("");
  };

  const toggle = (id: number) =>
    setTodos((prev) =>
      prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t))
    );

  const remove = (id: number) =>
    setTodos((prev) => prev.filter((t) => t.id !== id));

  return (
    <div className="min-h-screen bg-slate-50 p-4">
      <div className="mx-auto max-w-xl bg-white rounded-xl shadow p-6">
        <h1 className="text-xl font-bold text-slate-900 mb-4">Todo List</h1>

        <form onSubmit={handleAdd} className="flex gap-2 mb-5">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="What needs to be done?"
            className="flex-1 border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-indigo-700"
          >
            Add
          </button>
        </form>

        <div className="flex gap-2 mb-4 border-b border-slate-200 pb-3">
          {(["all", "active", "done"] as Filter[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 rounded-full font-medium ${
                filter === f
                  ? "bg-indigo-100 text-indigo-700"
                  : "text-slate-500 hover:bg-slate-100"
              }`}
            >
              {f === "done" ? "Completed" : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          {visible.map((todo) => (
            <div
              key={todo.id}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={todo.done}
                onChange={() => toggle(todo.id)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span
                className={`flex-1 text-sm ${
                  todo.done ? "line-through text-slate-400" : "text-slate-700"
                }`}
              >
                {todo.title}
              </span>
              <button
                type="button"
                onClick={() => remove(todo.id)}
                className="text-xs text-slate-400 hover:text-red-500"
              >
                Remove
              </button>
            </div>
          ))}
          {visible.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-6">
              Nothing here yet.
            </p>
          )}
        </div>

        <div className="mt-4 text-xs text-slate-400 text-right">
          {todos.filter((t) => !t.done).length} item(s) left
        </div>
      </div>
    </div>
  );
}
