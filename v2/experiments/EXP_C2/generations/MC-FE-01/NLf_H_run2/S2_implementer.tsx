import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ═══ Type System ════════════════════════════════════════════════════════════

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  position: number;
  movedBy: string;
  version: number;
}

interface WriteOp { wid: string; type: 'add' | 'move' | 'reorder'; taskId: string; ts: number; }
interface ConflictMsg { taskId: string; otherUser: string; info: string; }

interface Store {
  tasks: Record<string, Task>;
  lists: Record<ColumnId, string[]>;
  myId: string;
  activePeers: string[];
  pendingWrites: WriteOp[];
  conflictMessages: ConflictMsg[];
}

type StoreAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toCol: ColumnId; toIdx: number }
  | { type: 'REORDER'; taskId: string; toIdx: number }
  | { type: 'REMOTE_EVENT'; tasks: Record<string, Task>; lists: Record<ColumnId, string[]> }
  | { type: 'SHOW_CONFLICT'; msg: ConflictMsg }
  | { type: 'HIDE_CONFLICT'; taskId: string }
  | { type: 'WRITE_OK'; wid: string }
  | { type: 'WRITE_FAIL'; wid: string }
  | { type: 'SET_PEERS'; peers: string[] };

function id(): string { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36); }

// ═══ Simulated Server ══════════════════════════════════════════════════════

const SimServer = {
  data: { tasks: {} as Record<string, Task>, cols: { todo: [] as string[], inProgress: [] as string[], done: [] as string[] } },
  log: [] as { wid: string; taskId: string; user: string; ts: number }[],
  events: [] as StoreAction[],
};

function simSubmit(w: WriteOp, user: string) {
  const n = Date.now();
  const conflict = SimServer.log.find((l) => l.taskId === w.taskId && n - l.ts < 2000 && l.user !== user);
  if (conflict) SimServer.events.push({ type: 'SHOW_CONFLICT', msg: { taskId: w.taskId, otherUser: conflict.user, info: 'Concurrent move' } });
  SimServer.log.push({ wid: w.wid, taskId: w.taskId, user, ts: n });
  SimServer.events.push({ type: 'WRITE_OK', wid: w.wid });
}

function simRemote() {
  const all = Object.keys(SimServer.data.tasks);
  if (!all.length) return;
  const tid = all[Math.floor(Math.random() * all.length)];
  const t = SimServer.data.tasks[tid];
  if (!t) return;
  const dest: ColumnId = (['todo', 'inProgress', 'done'] as ColumnId[]).filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  SimServer.data.cols[t.column] = SimServer.data.cols[t.column].filter((x) => x !== tid);
  SimServer.data.cols[dest].push(tid);
  SimServer.data.tasks[tid] = { ...t, column: dest, movedBy: 'peer-eve', version: t.version + 1 };
  SimServer.log.push({ wid: id(), taskId: tid, user: 'peer-eve', ts: Date.now() });
  SimServer.events.push({ type: 'REMOTE_EVENT', tasks: { ...SimServer.data.tasks }, lists: { ...SimServer.data.cols } });
}

function simFlush(): StoreAction[] { const e = [...SimServer.events]; SimServer.events = []; return e; }

// ═══ Reducer ═══════════════════════════════════════════════════════════════

function storeReducer(state: Store, action: StoreAction): Store {
  switch (action.type) {
    case 'ADD_TASK': {
      const tid = id();
      const task: Task = { id: tid, text: action.text, column: 'todo', position: 0, movedBy: state.myId, version: 1 };
      const lists = { ...state.lists, todo: [tid, ...state.lists.todo] };
      SimServer.data.tasks[tid] = task; SimServer.data.cols = { ...lists };
      const w: WriteOp = { wid: id(), type: 'add', taskId: tid, ts: Date.now() };
      setTimeout(() => simSubmit(w, state.myId), 350 + Math.random() * 400);
      return { ...state, tasks: { ...state.tasks, [tid]: task }, lists, pendingWrites: [...state.pendingWrites, w] };
    }
    case 'MOVE_TASK': {
      const { taskId, toCol, toIdx } = action;
      const t = state.tasks[taskId]; if (!t) return state;
      const src = state.lists[t.column].filter((x) => x !== taskId);
      const dst = t.column === toCol ? src : [...state.lists[toCol]];
      if (t.column === toCol) src.splice(toIdx, 0, taskId); else dst.splice(toIdx, 0, taskId);
      const ut = { ...t, column: toCol, movedBy: state.myId, version: t.version + 1 };
      const lists = { ...state.lists, [t.column]: src, [toCol]: t.column === toCol ? src : dst };
      SimServer.data.tasks[taskId] = ut; SimServer.data.cols = { ...lists };
      const w: WriteOp = { wid: id(), type: 'move', taskId, ts: Date.now() };
      setTimeout(() => simSubmit(w, state.myId), 350 + Math.random() * 400);
      return { ...state, tasks: { ...state.tasks, [taskId]: ut }, lists, pendingWrites: [...state.pendingWrites, w] };
    }
    case 'REORDER': {
      const { taskId, toIdx } = action;
      const t = state.tasks[taskId]; if (!t) return state;
      const l = state.lists[t.column].filter((x) => x !== taskId); l.splice(toIdx, 0, taskId);
      const lists = { ...state.lists, [t.column]: l };
      SimServer.data.cols = { ...lists };
      const w: WriteOp = { wid: id(), type: 'reorder', taskId, ts: Date.now() };
      setTimeout(() => simSubmit(w, state.myId), 350 + Math.random() * 400);
      return { ...state, lists, pendingWrites: [...state.pendingWrites, w] };
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

const initial: Store = { tasks: {}, lists: { todo: [], inProgress: [], done: [] }, myId: 'u-' + id().slice(0, 4), activePeers: [], pendingWrites: [], conflictMessages: [] };

// ═══ Components ════════════════════════════════════════════════════════════

function BoardTitle({ me, peers }: { me: string; peers: string[] }) {
  return (
    <div className={styles.header}><h1>Collaborative Todo Board</h1>
      <div className={styles.users}><span>{me}</span>{peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}</div>
    </div>
  );
}

function TaskItem({ task, onStart }: { task: Task; onStart: (e: React.DragEvent, id: string) => void }) {
  const [d, sd] = useState(false);
  return (
    <div className={`${styles.card} ${d ? styles.cardDragging : ''}`} draggable="true"
      onDragStart={(e) => { sd(true); onStart(e, task.id); }} onDragEnd={() => sd(false)}>
      <div className={styles.cardText}>{task.text}</div>
      <div className={styles.cardMeta}>{task.movedBy} · v{task.version}</div>
    </div>
  );
}

function TaskForm({ dispatch }: { dispatch: React.Dispatch<StoreAction> }) {
  const [v, sv] = useState('');
  return (
    <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (v.trim()) { dispatch({ type: 'ADD_TASK', text: v.trim() }); sv(''); } }}>
      <input className={styles.taskInput} value={v} onChange={(e) => sv(e.target.value)} placeholder="New task..." />
      <button className={styles.addBtn} type="submit">Add</button>
    </form>
  );
}

function ColumnPanel({ col, title, ids, tasks, dispatch }: { col: ColumnId; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<StoreAction> }) {
  const ref = useRef<HTMLDivElement>(null);
  const over = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);
  const drop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const tid = e.dataTransfer.getData('text/plain');
    if (!tid || !tasks[tid]) return;
    let idx = ids.length;
    if (ref.current) { const els = ref.current.querySelectorAll('[data-item]'); for (let i = 0; i < els.length; i++) { const r = els[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { idx = i; break; } } }
    if (tasks[tid].column === col) dispatch({ type: 'REORDER', taskId: tid, toIdx: idx });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, toCol: col, toIdx: idx });
  }, [col, ids, tasks, dispatch]);
  const start = useCallback((e: React.DragEvent, tid: string) => { e.dataTransfer.setData('text/plain', tid); e.dataTransfer.effectAllowed = 'move'; }, []);

  return (
    <div className={styles.column} onDragOver={over} onDrop={drop} ref={ref}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {col === 'todo' && <TaskForm dispatch={dispatch} />}
      <div className={styles.cardList}>
        {ids.map((i) => { const t = tasks[i]; return t ? <div key={i} data-item><TaskItem task={t} onStart={start} /></div> : null; })}
      </div>
    </div>
  );
}

function ConflictToast({ msgs, tasks, dispatch }: { msgs: ConflictMsg[]; tasks: Record<string, Task>; dispatch: React.Dispatch<StoreAction> }) {
  if (!msgs.length) return null;
  return (
    <div className={styles.conflictToast}>
      {msgs.map((m) => (
        <div key={m.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[m.taskId]?.text ?? m.taskId}&quot; by {m.otherUser}</span>
          <button onClick={() => dispatch({ type: 'HIDE_CONFLICT', taskId: m.taskId })}>OK</button>
        </div>
      ))}
    </div>
  );
}

// ═══ Root ═══════════════════════════════════════════════════════════════════

const COLS: { id: ColumnId; title: string }[] = [{ id: 'todo', title: 'Todo' }, { id: 'inProgress', title: 'In Progress' }, { id: 'done', title: 'Done' }];

function KanbanBoard() {
  const [s, d] = useReducer(storeReducer, initial);
  useEffect(() => {
    const p = setInterval(() => simFlush().forEach((a) => d(a)), 500);
    const r = setInterval(() => setTimeout(simRemote, Math.random() * 2000), 5500);
    d({ type: 'SET_PEERS', peers: ['peer-eve'] });
    return () => { clearInterval(p); clearInterval(r); };
  }, []);

  return (
    <div className={styles.app}>
      <BoardTitle me={s.myId} peers={s.activePeers} />
      <div className={styles.board}>
        {COLS.map((c) => <ColumnPanel key={c.id} col={c.id} title={c.title} ids={s.lists[c.id]} tasks={s.tasks} dispatch={d} />)}
      </div>
      <ConflictToast msgs={s.conflictMessages} tasks={s.tasks} dispatch={d} />
    </div>
  );
}

export default KanbanBoard;
