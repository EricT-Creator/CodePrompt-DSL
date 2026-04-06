import React, { useState } from "react";

interface Todo {
  id: number;
  text: string;
  done: boolean;
}

export default function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: "Buy groceries", done: false },
    { id: 2, text: "Read a book", done: true },
    { id: 3, text: "Walk the dog", done: false },
  ]);
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "completed">("all");

  const addTodo = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setTodos((prev) => [...prev, { id: Date.now(), text: trimmed, done: false }]);
    setInput("");
  };

  const toggleTodo = (id: number) => {
    setTodos((prev) => prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));
  };

  const deleteTodo = (id: number) => {
    setTodos((prev) => prev.filter((t) => t.id !== id));
  };

  const filtered = todos.filter((t) => {
    if (filter === "active") return !t.done;
    if (filter === "completed") return t.done;
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50 p-4 flex flex-col items-center">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-4 text-center">Todo List</h1>
        <div className="flex gap-2 mb-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addTodo()}
            placeholder="Add a new task..."
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button onClick={addTodo} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
            Add
          </button>
        </div>
        <div className="flex gap-1 mb-3">
          {(["all", "active", "completed"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded-full ${filter === f ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-600"}`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <ul className="space-y-2">
          {filtered.map((todo) => (
            <li key={todo.id} className="flex items-center gap-2 bg-white rounded-lg p-3 shadow-sm">
              <input type="checkbox" checked={todo.done} onChange={() => toggleTodo(todo.id)} className="h-4 w-4" />
              <span className={`flex-1 text-sm ${todo.done ? "line-through text-gray-400" : "text-gray-700"}`}>{todo.text}</span>
              <button onClick={() => deleteTodo(todo.id)} className="text-red-400 hover:text-red-600 text-xs">Delete</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
