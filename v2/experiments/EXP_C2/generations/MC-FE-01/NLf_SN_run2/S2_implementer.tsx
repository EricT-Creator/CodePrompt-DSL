import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ─── Type Definitions ────────────────────────────────────────────────────

type ColumnKey = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnKey;
  rank: number;
  editor: string;
  version: number;
}

interface WriteOp { wid: string; type: 'add' | 'move' | 'reorder'; taskId: string; ts: number; }
interface ConflictMsg { taskId: string; otherUser: string; info: string; }

interface KanbanState {
  tasks: Record<string, Task>;
  lists: Record<ColumnKey, string[]>;
  myId: string;
  activePeers: string[];
  pendingWrites: WriteOp[];
  conflictMessages: ConflictMsg[];
}

type KAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; destCol: ColumnKey; pos: number }
  | { type: 'REORDER'; taskId: string; pos: number }
  | { type: 'REMOTE_EVENT'; tasks: Record<string, Task>; lists: Record<ColumnKey, string[]> }
  | { type: 'SHOW_CONFLICT'; msg: ConflictMsg }
  | { type: 'HIDE_CONFLICT'; taskId: string }
  | { type: 'WRITE_OK'; wid: string }
  | { type: 'WRITE_FAIL'; wid: string }
  | { type: 'SET_PEERS'; peers: string[] };

function makeUid(): string { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36); }

// ─── Simulated Backend ───────────────────────────────────────────────────

const backend = {
  store: { tasks: {} as Record<string, Task>, cols: { todo: [] as string[], inProgress: [] as string[], done: [] as string[] } },
  opLog: [] as { wid: string; taskId: string; user: string; ts: number }[],
  events: [] as KAction[],
};

function beProcess(w: WriteOp, user: string) {
  const now = Date.now();
  const clash = backend.opLog.find((o) => o.taskId === w.taskId && now - o.ts < 2000 && o.user !== user);
  if (clash) backend.events.push({ type: 'SHOW_CONFLICT', msg: { taskId: w.taskId, otherUser: clash.user, info: 'Concurrent edit' } });
  backend.opLog.push({ wid: w.wid, taskId: w.taskId, user, ts: now });
  backend.events.push({ type: 'WRITE_OK', wid: w.wid });
}

function beSimulate() {
  const ids = Object.keys(backend.store.tasks);
  if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const t = backend.store.tasks[tid]; if (!t) return;
  const dest: ColumnKey = (['todo', 'inProgress', 'done'] as ColumnKey[]).filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  backend.store.cols[t.column] = backend.store.cols[t.column].filter((x) => x !== tid);
  backend.store.cols[dest].push(tid);
  backend.store.tasks[tid] = { ...t, column: dest, editor: 'ghost', version: t.version + 1 };
  backend.opLog.push({ wid: makeUid(), taskId: tid, user: 'ghost', ts: Date.now() });
  backend.events.push({ type: 'REMOTE_EVENT', tasks: { ...backend.store.tasks }, lists: { ...backend.store.cols } });
}

function beFlush(): KAction[] { const q = [...backend.events]; backend.events = []; return q; }

// ─── Reducer ─────────────────────────────────────────────────────────────

function kanbanReducer(state: KanbanState, action: KAction): KanbanState {
  switch (action.type) {
    case 'ADD_TASK': {
      const nid = makeUid();
      const t: Task = { id: nid, text: action.text, column: 'todo', rank: 0, editor: state.myId, version: 1 };
      const ls = { ...state.lists, todo: [nid, ...state.lists.todo] };
      backend.store.tasks[nid] = t; backend.store.cols = { ...ls };
      const w: WriteOp = { wid: makeUid(), type: 'add', taskId: nid, ts: Date.now() };
      setTimeout(() => beProcess(w, state.myId), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [nid]: t }, lists: ls, pendingWrites: [...state.pendingWrites, w] };
    }
    case 'MOVE_TASK': {
      const { taskId, destCol, pos } = action;
      const tk = state.tasks[taskId]; if (!tk) return state;
      const src = state.lists[tk.column].filter((x) => x !== taskId);
      const dst = tk.column === destCol ? src : [...state.lists[destCol]];
      if (tk.column === destCol) src.splice(pos, 0, taskId); else dst.splice(pos, 0, taskId);
      const ut = { ...tk, column: destCol, editor: state.myId, version: tk.version + 1 };
      const ls = { ...state.lists, [tk.column]: src, [destCol]: tk.column === destCol ? src : dst };
      backend.store.tasks[taskId] = ut; backend.store.cols = { ...ls };
      const w: WriteOp = { wid: makeUid(), type: 'move', taskId, ts: Date.now() };
      setTimeout(() => beProcess(w, state.myId), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [taskId]: ut }, lists: ls, pendingWrites: [...state.pendingWrites, w] };
    }
    case 'REORDER': {
      const { taskId, pos } = action;
      const tk = state.tasks[taskId]; if (!tk) return state;
      const l = state.lists[tk.column].filter((x) => x !== taskId); l.splice(pos, 0, taskId);
      const ls = { ...state.lists, [tk.column]: l };
      backend.store.cols = { ...ls };
      const w: WriteOp = { wid: makeUid(), type: 'reorder', taskId, ts: Date.now() };
      setTimeout(() => beProcess(w, state.myId), 300 + Math.random() * 500);
      return { ...state, lists: ls, pendingWrites: [...state.pendingWrites, w] };
    }
    case 'REMOTE_EVENT': return { ...state, tasks: action.tasks, lists: action.lists };
    case 'SHOW_CONFLICT': return { ...state, conflictMessages: [...state.conflictMessages, action.msg] };
    case 'HIDE_CONFLICT': return { ...state, conflictMessages: state.conflictMessages.filter((c) => c.taskId !== action.taskId) };
    case 'WRITE_OK': return { ...state, pendingWrites: state.pendingWrites.filter((w) => w.wid !== action.wid) };
    case 'WRITE_FAIL': return { ...state, pendingWrites: state.pendingWrites.filter((w) => w.wid !== action.wid) };
    case 'SET_PEERS': return { ...state, activePeers: action.peers };
    default: return state;
  }
}

const initialState: KanbanState = { tasks: {}, lists: { todo: [], inProgress: [], done: [] }, myId: 'me-' + makeUid().slice(0, 4), activePeers: [], pendingWrites: [], conflictMessages: [] };

// ─── Components ──────────────────────────────────────────────────────────

function BoardHeader({ myId, peers }: { myId: string; peers: string[] }) {
  return <div className={styles.header}><h1>Collaborative Todo Board</h1><div className={styles.users}><span>{myId}</span>{peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}</div></div>;
}

function TaskItem({ task, onStart }: { task: Task; onStart: (e: React.DragEvent, id: string) => void }) {
  const [d, sd] = useState(false);
  return <div className={`${styles.card} ${d ? styles.cardDragging : ''}`} draggable="true" onDragStart={(e) => { sd(true); onStart(e, task.id); }} onDragEnd={() => sd(false)}>
    <div className={styles.cardText}>{task.text}</div><div className={styles.cardMeta}>{task.editor} · v{task.version}</div>
  </div>;
}

function TaskForm({ dispatch }: { dispatch: React.Dispatch<KAction> }) {
  const [v, sv] = useState('');
  return <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (v.trim()) { dispatch({ type: 'ADD_TASK', text: v.trim() }); sv(''); } }}>
    <input className={styles.taskInput} value={v} onChange={(e) => sv(e.target.value)} placeholder="Create task..." /><button className={styles.addBtn} type="submit">Add</button>
  </form>;
}

function ColumnPanel({ ck, label, ids, tasks, dispatch }: { ck: ColumnKey; label: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<KAction> }) {
  const ref = useRef<HTMLDivElement>(null);
  const over = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);
  const drop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); const tid = e.dataTransfer.getData('text/plain');
    if (!tid || !tasks[tid]) return; let p = ids.length;
    if (ref.current) { const els = ref.current.querySelectorAll('[data-ti]'); for (let i = 0; i < els.length; i++) { const r = els[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { p = i; break; } } }
    if (tasks[tid].column === ck) dispatch({ type: 'REORDER', taskId: tid, pos: p }); else dispatch({ type: 'MOVE_TASK', taskId: tid, destCol: ck, pos: p });
  }, [ck, ids, tasks, dispatch]);
  const ds = useCallback((e: React.DragEvent, id: string) => { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move'; }, []);
  return <div className={styles.column} onDragOver={over} onDrop={drop} ref={ref}>
    <h2 className={styles.columnTitle}>{label}</h2>{ck === 'todo' && <TaskForm dispatch={dispatch} />}
    <div className={styles.cardList}>{ids.map((i) => { const t = tasks[i]; return t ? <div key={i} data-ti><TaskItem task={t} onStart={ds} /></div> : null; })}</div>
  </div>;
}

function ConflictToast({ msgs, tasks, dispatch }: { msgs: ConflictMsg[]; tasks: Record<string, Task>; dispatch: React.Dispatch<KAction> }) {
  if (!msgs.length) return null;
  return <div className={styles.conflictToast}>{msgs.map((m) => <div key={m.taskId} className={styles.conflictItem}>
    <span>Conflict: &quot;{tasks[m.taskId]?.text ?? m.taskId}&quot; by {m.otherUser}</span>
    <button onClick={() => dispatch({ type: 'HIDE_CONFLICT', taskId: m.taskId })}>Dismiss</button>
  </div>)}</div>;
}

// ─── Root ────────────────────────────────────────────────────────────────

const COLUMNS: { k: ColumnKey; l: string }[] = [{ k: 'todo', l: 'Todo' }, { k: 'inProgress', l: 'In Progress' }, { k: 'done', l: 'Done' }];

function KanbanBoard() {
  const [s, d] = useReducer(kanbanReducer, initialState);
  useEffect(() => {
    const t1 = setInterval(() => beFlush().forEach((a) => d(a)), 500);
    const t2 = setInterval(() => setTimeout(beSimulate, Math.random() * 2500), 5000);
    d({ type: 'SET_PEERS', peers: ['ghost'] });
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);
  return <div className={styles.app}>
    <BoardHeader myId={s.myId} peers={s.activePeers} />
    <div className={styles.board}>{COLUMNS.map((c) => <ColumnPanel key={c.k} ck={c.k} label={c.l} ids={s.lists[c.k]} tasks={s.tasks} dispatch={d} />)}</div>
    <ConflictToast msgs={s.conflictMessages} tasks={s.tasks} dispatch={d} />
  </div>;
}

export default KanbanBoard;
