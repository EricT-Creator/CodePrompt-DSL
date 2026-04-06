import React, { FormEvent, useReducer } from "react";

type Mode = "all" | "active" | "completed";

type Todo = {
  id: number;
  label: string;
  completed: boolean;
};

type State = {
  draft: string;
  mode: Mode;
  todos: Todo[];
};

type Action =
  | { type: "setDraft"; value: string }
  | { type: "setMode"; value: Mode }
  | { type: "addTodo" }
  | { type: "toggleTodo"; id: number }
  | { type: "deleteTodo"; id: number };

const initialState: State = {
  draft: "",
  mode: "all",
  todos: [
    { id: 1, label: "Inspect generated outputs", completed: false },
    { id: 2, label: "Tag retry cases", completed: false },
    { id: 3, label: "Archive pilot notes", completed: true },
  ],
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "setDraft":
      return { ...state, draft: action.value };
    case "setMode":
      return { ...state, mode: action.value };
    case "addTodo": {
      const label = state.draft.trim();
      if (!label) {
        return state;
      }
      return {
        ...state,
        draft: "",
        todos: [{ id: Date.now(), label, completed: false }, ...state.todos],
      };
    }
    case "toggleTodo":
      return {
        ...state,
        todos: state.todos.map((todo) =>
          todo.id === action.id ? { ...todo, completed: !todo.completed } : todo
        ),
      };
    case "deleteTodo":
      return { ...state, todos: state.todos.filter((todo) => todo.id !== action.id) };
    default:
      return state;
  }
}

export default function TodoList() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const visible = state.todos.filter((todo) => {
    if (state.mode === "active") {
      return !todo.completed;
    }
    if (state.mode === "completed") {
      return todo.completed;
    }
    return true;
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    dispatch({ type: "addTodo" });
  };

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-8 text-zinc-100">
      <section className="mx-auto max-w-xl rounded-3xl bg-zinc-900 p-6 ring-1 ring-white/10">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Todo List</h1>
            <p className="mt-2 text-sm text-zinc-400">Track tasks with add, delete, complete, and filter controls.</p>
          </div>
          <div className="rounded-2xl bg-cyan-500/10 px-4 py-3 text-sm text-cyan-300">
            {state.todos.filter((todo) => !todo.completed).length} active tasks
          </div>
        </div>

        <form className="flex flex-col gap-3 sm:flex-row" onSubmit={submit}>
          <input
            value={state.draft}
            onChange={(event) => dispatch({ type: "setDraft", value: event.target.value })}
            placeholder="Create a task"
            className="flex-1 rounded-2xl border border-zinc-700 bg-zinc-950 px-4 py-3 text-sm outline-none focus:border-cyan-400"
          />
          <button type="submit" className="rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-zinc-950 hover:bg-cyan-300">
            Add Todo
          </button>
        </form>

        <div className="mt-5 flex flex-wrap gap-2">
          {(["all", "active", "completed"] as Mode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => dispatch({ type: "setMode", value: mode })}
              className={`rounded-full px-4 py-2 text-sm ${
                state.mode === mode ? "bg-white text-zinc-950" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>

        <ul className="mt-6 space-y-3">
          {visible.map((todo) => (
            <li key={todo.id} className="flex items-center gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/40 px-4 py-3">
              <button
                type="button"
                onClick={() => dispatch({ type: "toggleTodo", id: todo.id })}
                className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                  todo.completed ? "border-cyan-400 bg-cyan-400 text-zinc-950" : "border-zinc-500"
                }`}
              >
                {todo.completed ? "✓" : ""}
              </button>
              <span className={`flex-1 text-sm ${todo.completed ? "line-through text-zinc-500" : "text-zinc-100"}`}>
                {todo.label}
              </span>
              <button
                type="button"
                onClick={() => dispatch({ type: "deleteTodo", id: todo.id })}
                className="rounded-xl bg-rose-500/15 px-3 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/25"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>

        {visible.length === 0 && (
          <div className="mt-6 rounded-2xl border border-dashed border-zinc-700 px-4 py-6 text-center text-sm text-zinc-500">
            No items match the current filter.
          </div>
        )}
      </section>
    </main>
  );
}
