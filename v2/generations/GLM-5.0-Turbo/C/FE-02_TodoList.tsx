import React, { useState } from "react";

type View = "all" | "pending" | "finished";

interface Item {
  key: number;
  label: string;
  checked: boolean;
}

export default function TodoList() {
  const [items, setItems] = useState<Item[]>([
    { key: 1, label: "Pick up milk", checked: false },
    { key: 2, label: "Clean room", checked: true },
    { key: 3, label: "Call dentist", checked: false },
  ]);
  const [draft, setDraft] = useState("");
  const [view, setView] = useState<View>("all");

  const add = () => {
    const t = draft.trim();
    if (!t) return;
    setItems([...items, { key: Date.now(), label: t, checked: false }]);
    setDraft("");
  };

  const toggle = (k: number) => setItems(items.map(i => i.key === k ? { ...i, checked: !i.checked } : i));
  const remove = (k: number) => setItems(items.filter(i => i.key !== k));

  const list = items.filter(i => {
    if (view === "pending") return !i.checked;
    if (view === "finished") return i.checked;
    return true;
  });

  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-50 p-4">
      <div className="w-full max-w-sm space-y-4">
        <h1 className="text-lg font-bold text-zinc-800">Todos</h1>
        <div className="flex gap-2">
          <input value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => e.key === "Enter" && add()}
            placeholder="What needs to be done?" className="flex-1 rounded border border-zinc-300 px-3 py-2 text-sm" />
          <button onClick={add} className="rounded bg-zinc-800 px-3 py-2 text-sm text-white hover:bg-zinc-700">+</button>
        </div>
        <div className="flex gap-1">
          {(["all", "pending", "finished"] as View[]).map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`rounded px-2 py-0.5 text-xs capitalize ${view === v ? "bg-zinc-800 text-white" : "bg-zinc-200 text-zinc-600"}`}>{v}</button>
          ))}
        </div>
        <ul className="space-y-1.5">
          {list.map(i => (
            <li key={i.key} className="flex items-center gap-2 rounded bg-white p-2.5 shadow-sm">
              <input type="checkbox" checked={i.checked} onChange={() => toggle(i.key)} className="h-3.5 w-3.5" />
              <span className={`flex-1 text-sm ${i.checked ? "text-zinc-400 line-through" : "text-zinc-700"}`}>{i.label}</span>
              <button onClick={() => remove(i.key)} className="text-zinc-300 hover:text-red-500 text-xs">✕</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
