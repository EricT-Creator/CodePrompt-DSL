import React, { useState, useMemo } from "react";

interface TodoItem {
  id: number;
  text: string;
  completed: boolean;
}

type FilterMode = "all" | "active" | "completed";

const initialTodos: TodoItem[] = [
  { id: 1, text: "Review experiment design", completed: false },
  { id: 2, text: "Set up project structure", completed: true },
  { id: 3, text: "Write task definitions", completed: false },
];

export default function TodoList() {
  const [todos, setTodos] = useState<TodoItem[]>(initialTodos);
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState<FilterMode>("all");

  const filteredTodos = useMemo(() => {
    switch (filter) {
      case "active":
        return todos.filter((t) => !t.completed);
      case "completed":
        return todos.filter((t) => t.completed);
      default:
        return todos;
    }
  }, [todos, filter]);

  const addTodo = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    setTodos((prev) => [
      ...prev,
      { id: Date.now(), text: trimmed, completed: false },
    ]);
    setInput("");
  };

  const toggleTodo = (id: number) => {
    setTodos((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  };

  const deleteTodo = (id: number) => {
    setTodos((prev) => prev.filter((t) => t.id !== id));
  };

  const activeCount = todos.filter((t) => !t.completed).length;

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-lg bg-white rounded-2xl shadow-md p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Todo List</h1>
        <p className="text-sm text-gray-500 mb-6">
          {activeCount} task{activeCount !== 1 ? "s" : ""} remaining
        </p>

        <form onSubmit={addTodo} className="flex gap-2 mb-6">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Add a new task..."
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-200"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          >
            Add
          </button>
        </form>

        <div className="flex gap-1 mb-4">
          {(["all", "active", "completed"] as FilterMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setFilter(mode)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize transition ${
                filter === mode
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>

        <ul className="space-y-2">
          {filteredTodos.map((todo) => (
            <li
              key={todo.id}
              className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 bg-gray-50"
            >
              <button
                type="button"
                onClick={() => toggleTodo(todo.id)}
                className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition ${
                  todo.completed
                    ? "bg-blue-600 border-blue-600"
                    : "border-gray-300 hover:border-blue-400"
                }`}
              >
                {todo.completed && (
                  <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
              <span
                className={`flex-1 text-sm ${
                  todo.completed ? "line-through text-gray-400" : "text-gray-800"
                }`}
              >
                {todo.text}
              </span>
              <button
                type="button"
                onClick={() => deleteTodo(todo.id)}
                className="text-xs text-red-400 hover:text-red-600 font-medium transition"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>

        {filteredTodos.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-8">No tasks to show</p>
        )}
      </div>
    </div>
  );
}
