import React, { useState } from "react";

interface TodoItem {
  id: number;
  content: string;
  finished: boolean;
}

type FilterMode = "all" | "open" | "closed";

export default function TodoList() {
  const [list, setList] = useState<TodoItem[]>([
    { id: 1, content: "买菜", finished: false },
    { id: 2, content: "读书", finished: true },
    { id: 3, content: "跑步", finished: false },
  ]);
  const [text, setText] = useState("");
  const [mode, setMode] = useState<FilterMode>("all");

  const addNew = () => {
    const s = text.trim();
    if (!s) return;
    setList([...list, { id: Date.now(), content: s, finished: false }]);
    setText("");
  };

  const markDone = (id: number) => {
    setList(list.map(item => item.id === id ? { ...item, finished: !item.finished } : item));
  };

  const erase = (id: number) => {
    setList(list.filter(item => item.id !== id));
  };

  const shown = list.filter(item => {
    if (mode === "open") return !item.finished;
    if (mode === "closed") return item.finished;
    return true;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-pink-50 p-4 flex justify-center">
      <div className="w-full max-w-md bg-white/80 backdrop-blur rounded-2xl shadow-lg p-6 space-y-4">
        <h1 className="text-xl font-bold text-gray-800 text-center">待办事项</h1>
        <div className="flex gap-2">
          <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === "Enter" && addNew()}
            placeholder="新增任务..." className="flex-1 rounded-xl border border-gray-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
          <button onClick={addNew} className="rounded-xl bg-violet-500 px-4 py-2 text-sm text-white font-medium hover:bg-violet-600">添加</button>
        </div>
        <div className="flex gap-2 justify-center">
          {([["all", "全部"], ["open", "未完成"], ["closed", "已完成"]] as [FilterMode, string][]).map(([val, label]) => (
            <button key={val} onClick={() => setMode(val)}
              className={`rounded-full px-3 py-1 text-xs ${mode === val ? "bg-violet-500 text-white" : "bg-gray-100 text-gray-500"}`}>{label}</button>
          ))}
        </div>
        <ul className="space-y-2">
          {shown.map(item => (
            <li key={item.id} className="flex items-center gap-3 rounded-xl bg-white p-3 shadow-sm">
              <input type="checkbox" checked={item.finished} onChange={() => markDone(item.id)} className="h-4 w-4 accent-violet-500" />
              <span className={`flex-1 text-sm ${item.finished ? "line-through text-gray-400" : "text-gray-700"}`}>{item.content}</span>
              <button onClick={() => erase(item.id)} className="text-gray-300 hover:text-red-500 text-sm">删除</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
