import React, { FormEvent, useMemo, useState } from "react";

type Todo = {
  id: number;
  text: string;
  done: boolean;
};

type FilterKey = "all" | "active" | "done";

const sampleTodos: Todo[] = [
  { id: 11, text: "Read the experiment runbook", done: true },
  { id: 12, text: "Generate the current task set", done: false },
  { id: 13, text: "Append log entries", done: false },
];

export default function TodoList() {
  const [todos, setTodos] = useState<Todo[]>(sampleTodos);
  const [text, setText] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");

  const shown = useMemo(() => {
    if (filter === "active") {
      return todos.filter((todo) => !todo.done);
    }
    if (filter === "done") {
      return todos.filter((todo) => todo.done);
    }
    return todos;
  }, [filter, todos]);

  const addTodo = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = text.trim();
    if (!value) {
      return;
    }
    setTodos((previous) => [...previous, { id: Date.now(), text: value, done: false }]);
    setText("");
  };

  return (
    <div className="min-h-screen bg-amber-50 px-4 py-8">
      <div className="mx-auto w-full max-w-xl rounded-3xl bg-white p-6 shadow-lg shadow-amber-100">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Todo board</h1>
            <p className="mt-2 text-sm text-slate-500">Add tasks, mark them done, remove them, and filter the list.</p>
          </div>
          <div className="rounded-2xl bg-amber-100 px-4 py-3 text-sm text-amber-800">
            {todos.filter((todo) => !todo.done).length} remaining
          </div>
        </div>

        <form onSubmit={addTodo} className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <input
            type="text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Write a new todo"
            className="rounded-2xl border border-amber-200 px-4 py-3 text-sm outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-100"
          />
          <button type="submit" className="rounded-2xl bg-amber-500 px-5 py-3 text-sm font-semibold text-white hover:bg-amber-600">
            Add item
          </button>
        </form>

        <div className="mt-5 flex flex-wrap gap-2">
          {[
            { key: "all", label: "All" },
            { key: "active", label: "Active" },
            { key: "done", label: "Completed" },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setFilter(option.key as FilterKey)}
              className={`rounded-full px-4 py-2 text-sm font-medium ${
                filter === option.key ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="mt-6 space-y-3">
          {shown.map((todo) => (
            <div key={todo.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
              <button
                type="button"
                onClick={() =>
                  setTodos((previous) =>
                    previous.map((entry) =>
                      entry.id === todo.id ? { ...entry, done: !entry.done } : entry
                    )
                  )
                }
                className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs ${
                  todo.done ? "border-emerald-500 bg-emerald-500 text-white" : "border-slate-300 text-transparent"
                }`}
                aria-label={todo.done ? "Mark as active" : "Mark as completed"}
              >
                ✓
              </button>
              <div className={`flex-1 text-sm ${todo.done ? "text-slate-400 line-through" : "text-slate-800"}`}>{todo.text}</div>
              <button
                type="button"
                onClick={() => setTodos((previous) => previous.filter((entry) => entry.id !== todo.id))}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Delete
              </button>
            </div>
          ))}
        </div>

        {shown.length === 0 && (
          <div className="mt-6 rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">No tasks to show.</div>
        )}
      </div>
    </div>
  );
}
