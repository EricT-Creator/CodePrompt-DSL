import React, { useState, useReducer } from "react";

type Item = { id: number; text: string; done: boolean };
type Show = "all" | "todo" | "done";

type Action =
  | { type: "add"; text: string }
  | { type: "toggle"; id: number }
  | { type: "remove"; id: number };

function reducer(state: Item[], action: Action): Item[] {
  switch (action.type) {
    case "add":
      return [...state, { id: Date.now(), text: action.text, done: false }];
    case "toggle":
      return state.map((i) =>
        i.id === action.id ? { ...i, done: !i.done } : i
      );
    case "remove":
      return state.filter((i) => i.id !== action.id);
    default:
      return state;
  }
}

const initial: Item[] = [
  { id: 1, text: "阅读实验手册", done: true },
  { id: 2, text: "完成代码生成", done: false },
  { id: 3, text: "记录执行日志", done: false },
];

export default function TodoList() {
  const [items, dispatch] = useReducer(reducer, initial);
  const [input, setInput] = useState("");
  const [show, setShow] = useState<Show>("all");

  const list =
    show === "all"
      ? items
      : show === "todo"
      ? items.filter((i) => !i.done)
      : items.filter((i) => i.done);

  const onAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const t = input.trim();
    if (!t) return;
    dispatch({ type: "add", text: t });
    setInput("");
  };

  return (
    <div className="min-h-screen bg-gray-100 px-4 py-8">
      <div className="mx-auto max-w-md bg-white rounded-xl shadow p-5">
        <h1 className="text-lg font-bold text-gray-800 mb-4">待办事项</h1>

        <form onSubmit={onAdd} className="flex gap-2 mb-4">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="新增任务…"
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-blue-700"
          >
            添加
          </button>
        </form>

        <div className="flex gap-2 mb-4">
          {([
            { key: "all", label: "全部" },
            { key: "todo", label: "待完成" },
            { key: "done", label: "已完成" },
          ] as { key: Show; label: string }[]).map((opt) => (
            <button
              key={opt.key}
              type="button"
              onClick={() => setShow(opt.key)}
              className={`text-xs px-3 py-1 rounded-full font-medium ${
                show === opt.key
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <ul className="space-y-2">
          {list.map((item) => (
            <li
              key={item.id}
              className="flex items-center gap-3 p-2 rounded-md border border-gray-100"
            >
              <input
                type="checkbox"
                checked={item.done}
                onChange={() => dispatch({ type: "toggle", id: item.id })}
                className="h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              <span
                className={`flex-1 text-sm ${
                  item.done ? "line-through text-gray-400" : "text-gray-700"
                }`}
              >
                {item.text}
              </span>
              <button
                type="button"
                onClick={() => dispatch({ type: "remove", id: item.id })}
                className="text-xs text-red-400 hover:text-red-600"
              >
                删除
              </button>
            </li>
          ))}
        </ul>

        {list.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-6">暂无任务</p>
        )}

        <p className="text-xs text-gray-400 text-right mt-3">
          剩余 {items.filter((i) => !i.done).length} 项
        </p>
      </div>
    </div>
  );
}
