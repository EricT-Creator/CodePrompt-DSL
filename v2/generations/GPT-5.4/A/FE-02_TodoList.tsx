import React, { FormEvent, useMemo, useState } from "react";

type Filter = "all" | "active" | "completed";

type Todo = {
  id: number;
  text: string;
  completed: boolean;
};

const initialTodos: Todo[] = [
  { id: 1, text: "Outline experiment sections", completed: false },
  { id: 2, text: "Review task coverage", completed: true },
  { id: 3, text: "Prepare baseline prompts", completed: false },
];

export default function TodoList() {
  const [todos, setTodos] = useState<Todo[]>(initialTodos);
  const [draft, setDraft] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const visibleTodos = useMemo(() => {
    if (filter === "active") {
      return todos.filter((todo) => !todo.completed);
    }

    if (filter === "completed") {
      return todos.filter((todo) => todo.completed);
    }

    return todos;
  }, [filter, todos]);

  const handleAdd = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = draft.trim();

    if (!text) {
      return;
    }

    setTodos((previous) => [
      { id: Date.now(), text, completed: false },
      ...previous,
    ]);
    setDraft("");
  };

  const activeCount = todos.filter((todo) => !todo.completed).length;

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto w-full max-w-xl rounded-3xl bg-white p-6 shadow-xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-violet-600">Task manager</p>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">Todo list</h1>
            <p className="mt-2 text-sm text-slate-500">Add, remove, complete, and filter your tasks.</p>
          </div>
          <div className="rounded-2xl bg-violet-50 px-4 py-3 text-right text-sm text-violet-700">
            <div className="font-semibold">{activeCount}</div>
            <div>active items</div>
          </div>
        </div>

        <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleAdd}>
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add a new task"
            className="flex-1 rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />
          <button
            type="submit"
            className="rounded-2xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-700"
          >
            Add task
          </button>
        </form>

        <div className="mt-5 flex flex-wrap gap-2">
          {(["all", "active", "completed"] as Filter[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                filter === item ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </div>

        <ul className="mt-6 space-y-3">
          {visibleTodos.map((todo) => (
            <li key={todo.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 p-4">
              <button
                type="button"
                onClick={() =>
                  setTodos((previous) =>
                    previous.map((item) =>
                      item.id === todo.id ? { ...item, completed: !item.completed } : item
                    )
                  )
                }
                className={`flex h-5 w-5 items-center justify-center rounded-full border transition ${
                  todo.completed ? "border-violet-600 bg-violet-600 text-white" : "border-slate-300"
                }`}
                aria-label={`Mark ${todo.text} as ${todo.completed ? "active" : "completed"}`}
              >
                {todo.completed ? "✓" : ""}
              </button>
              <span className={`flex-1 text-sm ${todo.completed ? "text-slate-400 line-through" : "text-slate-700"}`}>
                {todo.text}
              </span>
              <button
                type="button"
                onClick={() => setTodos((previous) => previous.filter((item) => item.id !== todo.id))}
                className="rounded-xl bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-600 transition hover:bg-rose-100"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>

        {visibleTodos.length === 0 && (
          <div className="mt-6 rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500">
            No tasks match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
}
