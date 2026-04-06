import React, { FormEvent, useMemo, useState } from "react";

type TodoItem = {
  id: number;
  title: string;
  done: boolean;
};

type ViewMode = "all" | "open" | "done";

const seedTodos: TodoItem[] = [
  { id: 101, title: "Collect benchmark feedback", done: false },
  { id: 102, title: "Draft evaluation notes", done: true },
];

export default function TodoList() {
  const [items, setItems] = useState<TodoItem[]>(seedTodos);
  const [inputValue, setInputValue] = useState("");
  const [view, setView] = useState<ViewMode>("all");

  const filteredItems = useMemo(() => {
    switch (view) {
      case "open":
        return items.filter((item) => !item.done);
      case "done":
        return items.filter((item) => item.done);
      default:
        return items;
    }
  }, [items, view]);

  const submitNewItem = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = inputValue.trim();
    if (!title) {
      return;
    }

    setItems((previous) => [{ id: Date.now(), title, done: false }, ...previous]);
    setInputValue("");
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Todo workspace</h1>
            <p className="mt-2 text-sm text-slate-500">Manage tasks with add, delete, complete, and filter actions.</p>
          </div>
          <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {items.filter((item) => !item.done).length} open / {items.length} total
          </div>
        </div>

        <form onSubmit={submitNewItem} className="mt-6 grid gap-3 sm:grid-cols-[1fr_auto]">
          <input
            type="text"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            placeholder="Add a todo item"
            className="rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
          />
          <button type="submit" className="rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-700">
            Add
          </button>
        </form>

        <div className="mt-5 flex gap-2">
          {[
            { key: "all", label: "All" },
            { key: "open", label: "Active" },
            { key: "done", label: "Completed" },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setView(option.key as ViewMode)}
              className={`rounded-full px-4 py-2 text-sm ${
                view === option.key ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="mt-6 space-y-3">
          {filteredItems.map((item) => (
            <div key={item.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
              <input
                type="checkbox"
                checked={item.done}
                onChange={() =>
                  setItems((previous) =>
                    previous.map((entry) =>
                      entry.id === item.id ? { ...entry, done: !entry.done } : entry
                    )
                  )
                }
                className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
              />
              <div className={`flex-1 text-sm ${item.done ? "text-slate-400 line-through" : "text-slate-700"}`}>{item.title}</div>
              <button
                type="button"
                onClick={() => setItems((previous) => previous.filter((entry) => entry.id !== item.id))}
                className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        {filteredItems.length === 0 && (
          <div className="mt-6 rounded-2xl bg-slate-100 px-4 py-6 text-center text-sm text-slate-500">
            No todos in this view.
          </div>
        )}
      </div>
    </div>
  );
}
