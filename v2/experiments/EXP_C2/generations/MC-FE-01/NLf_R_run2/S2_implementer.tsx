import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ─── Types ───────────────────────────────────────────────────────────────

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  order: number;
  lastMovedBy: string;
  version: number;
}

interface PendingOperation {
  opId: string;
  kind: 'add' | 'move' | 'reorder';
  taskId: string;
  createdAt: number;
}

interface ConflictRecord {
  taskId: string;
  otherUser: string;
  message: string;
}

interface State {
  tasks: Record<string, Task>;
  columns: { todo: string[]; inProgress: string[]; done: string[] };
  me: string;
  onlineUsers: string[];
  pendingOps: PendingOperation[];
  conflicts: ConflictRecord[];
}

type Act =
  | { type: 'CREATE_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; dest: ColumnId; idx: number }
  | { type: 'REORDER_TASK'; taskId: string; idx: number }
  | { type: 'RECEIVE_REMOTE'; tasks: Record<string, Task>; columns: State['columns'] }
  | { type: 'FLAG_CONFLICT'; cr: ConflictRecord }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'OP_CONFIRMED'; opId: string }
  | { type: 'OP_REJECTED'; opId: string }
  | { type: 'UPDATE_PEERS'; peers: string[] };

function newId(): string {
  return Math.random().toString(36).slice(2, 9) + Date.now().toString(36);
}

// ─── Mock Server ─────────────────────────────────────────────────────────

const fakeServer = {
  store: { tasks: {} as Record<string, Task>, cols: { todo: [] as string[], inProgress: [] as string[], done: [] as string[] } },
  history: [] as { opId: string; taskId: string; user: string; ts: number }[],
  outbox: [] as Act[],
};

function serverProcess(op: PendingOperation, userId: string) {
  const t = Date.now();
  const hit = fakeServer.history.find((h) => h.taskId === op.taskId && t - h.ts < 2000 && h.user !== userId);
  if (hit) {
    fakeServer.outbox.push({ type: 'FLAG_CONFLICT', cr: { taskId: op.taskId, otherUser: hit.user, message: 'Concurrent edit' } });
  }
  fakeServer.history.push({ opId: op.opId, taskId: op.taskId, user: userId, ts: t });
  fakeServer.outbox.push({ type: 'OP_CONFIRMED', opId: op.opId });
}

function serverBot() {
  const ids = Object.keys(fakeServer.store.tasks);
  if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const task = fakeServer.store.tasks[tid];
  if (!task) return;
  const options: ColumnId[] = (['todo', 'inProgress', 'done'] as ColumnId[]).filter((c) => c !== task.column);
  const to = options[Math.floor(Math.random() * options.length)];
  fakeServer.store.cols[task.column] = fakeServer.store.cols[task.column].filter((x) => x !== tid);
  fakeServer.store.cols[to].push(tid);
  fakeServer.store.tasks[tid] = { ...task, column: to, lastMovedBy: 'alice', version: task.version + 1 };
  fakeServer.history.push({ opId: newId(), taskId: tid, user: 'alice', ts: Date.now() });
  fakeServer.outbox.push({ type: 'RECEIVE_REMOTE', tasks: { ...fakeServer.store.tasks }, columns: { ...fakeServer.store.cols } });
}

function serverDrain(): Act[] {
  const q = [...fakeServer.outbox];
  fakeServer.outbox = [];
  return q;
}

// ─── Reducer ─────────────────────────────────────────────────────────────

function reducer(state: State, action: Act): State {
  switch (action.type) {
    case 'CREATE_TASK': {
      const id = newId();
      const t: Task = { id, text: action.text, column: 'todo', order: 0, lastMovedBy: state.me, version: 1 };
      const cols = { ...state.columns, todo: [id, ...state.columns.todo] };
      fakeServer.store.tasks[id] = t;
      fakeServer.store.cols = { ...cols };
      const op: PendingOperation = { opId: newId(), kind: 'add', taskId: id, createdAt: Date.now() };
      setTimeout(() => serverProcess(op, state.me), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [id]: t }, columns: cols, pendingOps: [...state.pendingOps, op] };
    }
    case 'MOVE_TASK': {
      const { taskId, dest, idx } = action;
      const t = state.tasks[taskId];
      if (!t) return state;
      const from = state.columns[t.column].filter((x) => x !== taskId);
      const to = t.column === dest ? from : [...state.columns[dest]];
      if (t.column === dest) from.splice(idx, 0, taskId);
      else to.splice(idx, 0, taskId);
      const ut = { ...t, column: dest, lastMovedBy: state.me, version: t.version + 1 };
      const cols = { ...state.columns, [t.column]: from, [dest]: t.column === dest ? from : to };
      fakeServer.store.tasks[taskId] = ut;
      fakeServer.store.cols = { ...cols };
      const op: PendingOperation = { opId: newId(), kind: 'move', taskId, createdAt: Date.now() };
      setTimeout(() => serverProcess(op, state.me), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [taskId]: ut }, columns: cols, pendingOps: [...state.pendingOps, op] };
    }
    case 'REORDER_TASK': {
      const { taskId, idx } = action;
      const t = state.tasks[taskId];
      if (!t) return state;
      const list = state.columns[t.column].filter((x) => x !== taskId);
      list.splice(idx, 0, taskId);
      const cols = { ...state.columns, [t.column]: list };
      fakeServer.store.cols = { ...cols };
      const op: PendingOperation = { opId: newId(), kind: 'reorder', taskId, createdAt: Date.now() };
      setTimeout(() => serverProcess(op, state.me), 300 + Math.random() * 500);
      return { ...state, columns: cols, pendingOps: [...state.pendingOps, op] };
    }
    case 'RECEIVE_REMOTE':
      return { ...state, tasks: action.tasks, columns: action.columns };
    case 'FLAG_CONFLICT':
      return { ...state, conflicts: [...state.conflicts, action.cr] };
    case 'DISMISS_CONFLICT':
      return { ...state, conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId) };
    case 'OP_CONFIRMED':
      return { ...state, pendingOps: state.pendingOps.filter((o) => o.opId !== action.opId) };
    case 'OP_REJECTED':
      return { ...state, pendingOps: state.pendingOps.filter((o) => o.opId !== action.opId) };
    case 'UPDATE_PEERS':
      return { ...state, onlineUsers: action.peers };
    default:
      return state;
  }
}

const initState: State = {
  tasks: {},
  columns: { todo: [], inProgress: [], done: [] },
  me: 'user-' + newId().slice(0, 4),
  onlineUsers: [],
  pendingOps: [],
  conflicts: [],
};

// ─── Sub-Components ──────────────────────────────────────────────────────

function BoardHeader({ me, peers }: { me: string; peers: string[] }) {
  return (
    <div className={styles.header}>
      <h1>Collaborative Todo Board</h1>
      <div className={styles.users}>
        <span>{me}</span>
        {peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}
      </div>
    </div>
  );
}

function TaskCard({ task, startDrag }: { task: Task; startDrag: (e: React.DragEvent, id: string) => void }) {
  const [dragging, setDragging] = useState(false);
  return (
    <div
      className={`${styles.card} ${dragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={(e) => { setDragging(true); startDrag(e, task.id); }}
      onDragEnd={() => setDragging(false)}
    >
      <div className={styles.cardText}>{task.text}</div>
      <div className={styles.cardMeta}>{task.lastMovedBy} · v{task.version}</div>
    </div>
  );
}

function AddTaskForm({ dispatch }: { dispatch: React.Dispatch<Act> }) {
  const [val, setVal] = useState('');
  return (
    <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (val.trim()) { dispatch({ type: 'CREATE_TASK', text: val.trim() }); setVal(''); } }}>
      <input className={styles.taskInput} value={val} onChange={(e) => setVal(e.target.value)} placeholder="Add task..." />
      <button className={styles.addBtn} type="submit">+</button>
    </form>
  );
}

function ColumnPanel({ cid, label, ids, tasks, dispatch }: { cid: ColumnId; label: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Act> }) {
  const ref = useRef<HTMLDivElement>(null);
  const onOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const tid = e.dataTransfer.getData('text/plain');
    if (!tid || !tasks[tid]) return;
    let pos = ids.length;
    if (ref.current) {
      const cards = ref.current.querySelectorAll('[data-c]');
      for (let i = 0; i < cards.length; i++) {
        const r = cards[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height / 2) { pos = i; break; }
      }
    }
    if (tasks[tid].column === cid) dispatch({ type: 'REORDER_TASK', taskId: tid, idx: pos });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, dest: cid, idx: pos });
  }, [cid, ids, tasks, dispatch]);
  const dragStart = useCallback((e: React.DragEvent, id: string) => { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move'; }, []);

  return (
    <div className={styles.column} onDragOver={onOver} onDrop={onDrop} ref={ref}>
      <h2 className={styles.columnTitle}>{label}</h2>
      {cid === 'todo' && <AddTaskForm dispatch={dispatch} />}
      <div className={styles.cardList}>
        {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-c><TaskCard task={t} startDrag={dragStart} /></div> : null; })}
      </div>
    </div>
  );
}

function ConflictAlert({ items, tasks, dispatch }: { items: ConflictRecord[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Act> }) {
  if (!items.length) return null;
  return (
    <div className={styles.conflictToast}>
      {items.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; moved by {c.otherUser}</span>
          <button onClick={() => dispatch({ type: 'DISMISS_CONFLICT', taskId: c.taskId })}>Dismiss</button>
        </div>
      ))}
    </div>
  );
}

// ─── Root ────────────────────────────────────────────────────────────────

const COL_CFG: { id: ColumnId; label: string }[] = [
  { id: 'todo', label: 'Todo' },
  { id: 'inProgress', label: 'In Progress' },
  { id: 'done', label: 'Done' },
];

function CollaborativeBoard() {
  const [state, dispatch] = useReducer(reducer, initState);

  useEffect(() => {
    const p = setInterval(() => serverDrain().forEach((a) => dispatch(a)), 500);
    const r = setInterval(() => setTimeout(serverBot, Math.random() * 2500), 5000);
    dispatch({ type: 'UPDATE_PEERS', peers: ['alice'] });
    return () => { clearInterval(p); clearInterval(r); };
  }, []);

  return (
    <div className={styles.app}>
      <BoardHeader me={state.me} peers={state.onlineUsers} />
      <div className={styles.board}>
        {COL_CFG.map((c) => <ColumnPanel key={c.id} cid={c.id} label={c.label} ids={state.columns[c.id]} tasks={state.tasks} dispatch={dispatch} />)}
      </div>
      <ConflictAlert items={state.conflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default CollaborativeBoard;
