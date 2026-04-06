import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ── Types ────────────────────────────────────────────────────────────────────

type ColumnKey = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnKey;
  order: number;
  lastEditor: string;
  version: number;
}

interface AppState {
  tasks: Record<string, Task>;
  columns: Record<ColumnKey, string[]>;
  userId: string;
  peers: string[];
  pendingOps: LocalOp[];
  activeConflicts: Conflict[];
}

interface LocalOp {
  id: string;
  kind: 'add' | 'move' | 'reorder';
  taskId: string;
  ts: number;
}

interface Conflict {
  taskId: string;
  otherUser: string;
  description: string;
}

type AppAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; targetCol: ColumnKey; pos: number }
  | { type: 'REORDER'; taskId: string; pos: number }
  | { type: 'REMOTE_CHANGE'; tasks: Record<string, Task>; columns: Record<ColumnKey, string[]> }
  | { type: 'CONFLICT'; conflict: Conflict }
  | { type: 'CLEAR_CONFLICT'; taskId: string }
  | { type: 'ACK'; opId: string }
  | { type: 'NACK'; opId: string };

function makeId(): string {
  return (Math.random().toString(36) + Date.now().toString(36)).slice(2, 14);
}

// ── Mock Backend ─────────────────────────────────────────────────────────────

const mockBackend = {
  data: { tasks: {} as Record<string, Task>, cols: { todo: [], inProgress: [], done: [] } as Record<ColumnKey, string[]> },
  log: [] as { opId: string; taskId: string; user: string; ts: number }[],
  queue: [] as AppAction[],
};

function backendProcess(op: LocalOp, user: string) {
  const now = Date.now();
  const clash = mockBackend.log.find((l) => l.taskId === op.taskId && now - l.ts < 2000 && l.user !== user);
  if (clash) {
    mockBackend.queue.push({ type: 'CONFLICT', conflict: { taskId: op.taskId, otherUser: clash.user, description: `Both moved task ${op.taskId}` } });
  }
  mockBackend.log.push({ opId: op.id, taskId: op.taskId, user, ts: now });
  mockBackend.queue.push({ type: 'ACK', opId: op.id });
}

function backendSimulate() {
  const keys = Object.keys(mockBackend.data.tasks);
  if (!keys.length) return;
  const tid = keys[Math.floor(Math.random() * keys.length)];
  const t = mockBackend.data.tasks[tid];
  if (!t) return;
  const allCols: ColumnKey[] = ['todo', 'inProgress', 'done'];
  const dest = allCols.filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  mockBackend.data.cols[t.column] = mockBackend.data.cols[t.column].filter((i) => i !== tid);
  mockBackend.data.cols[dest].push(tid);
  mockBackend.data.tasks[tid] = { ...t, column: dest, lastEditor: 'remote-bob', version: t.version + 1 };
  mockBackend.log.push({ opId: makeId(), taskId: tid, user: 'remote-bob', ts: Date.now() });
  mockBackend.queue.push({ type: 'REMOTE_CHANGE', tasks: { ...mockBackend.data.tasks }, columns: { ...mockBackend.data.cols } });
}

function backendFlush(): AppAction[] {
  const out = [...mockBackend.queue];
  mockBackend.queue = [];
  return out;
}

// ── Reducer ──────────────────────────────────────────────────────────────────

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = makeId();
      const task: Task = { id, text: action.text, column: 'todo', order: 0, lastEditor: state.userId, version: 1 };
      const cols = { ...state.columns, todo: [id, ...state.columns.todo] };
      mockBackend.data.tasks[id] = task;
      mockBackend.data.cols = { ...cols };
      const op: LocalOp = { id: makeId(), kind: 'add', taskId: id, ts: Date.now() };
      setTimeout(() => backendProcess(op, state.userId), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [id]: task }, columns: cols, pendingOps: [...state.pendingOps, op] };
    }
    case 'MOVE_TASK': {
      const { taskId, targetCol, pos } = action;
      const task = state.tasks[taskId];
      if (!task) return state;
      const srcList = state.columns[task.column].filter((i) => i !== taskId);
      const dstList = task.column === targetCol ? srcList : [...state.columns[targetCol]];
      if (task.column === targetCol) srcList.splice(pos, 0, taskId);
      else dstList.splice(pos, 0, taskId);
      const upd = { ...task, column: targetCol, lastEditor: state.userId, version: task.version + 1 };
      const cols = { ...state.columns, [task.column]: srcList, [targetCol]: task.column === targetCol ? srcList : dstList };
      mockBackend.data.tasks[taskId] = upd;
      mockBackend.data.cols = { ...cols };
      const op: LocalOp = { id: makeId(), kind: 'move', taskId, ts: Date.now() };
      setTimeout(() => backendProcess(op, state.userId), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [taskId]: upd }, columns: cols, pendingOps: [...state.pendingOps, op] };
    }
    case 'REORDER': {
      const { taskId, pos } = action;
      const task = state.tasks[taskId];
      if (!task) return state;
      const list = state.columns[task.column].filter((i) => i !== taskId);
      list.splice(pos, 0, taskId);
      const cols = { ...state.columns, [task.column]: list };
      mockBackend.data.cols = { ...cols };
      const op: LocalOp = { id: makeId(), kind: 'reorder', taskId, ts: Date.now() };
      setTimeout(() => backendProcess(op, state.userId), 300 + Math.random() * 500);
      return { ...state, columns: cols, pendingOps: [...state.pendingOps, op] };
    }
    case 'REMOTE_CHANGE':
      return { ...state, tasks: action.tasks, columns: action.columns };
    case 'CONFLICT':
      return { ...state, activeConflicts: [...state.activeConflicts, action.conflict] };
    case 'CLEAR_CONFLICT':
      return { ...state, activeConflicts: state.activeConflicts.filter((c) => c.taskId !== action.taskId) };
    case 'ACK':
      return { ...state, pendingOps: state.pendingOps.filter((o) => o.id !== action.opId) };
    case 'NACK':
      return { ...state, pendingOps: state.pendingOps.filter((o) => o.id !== action.opId) };
    default:
      return state;
  }
}

const defaultState: AppState = {
  tasks: {},
  columns: { todo: [], inProgress: [], done: [] },
  userId: 'me-' + makeId().slice(0, 5),
  peers: [],
  pendingOps: [],
  activeConflicts: [],
};

// ── Subcomponents ────────────────────────────────────────────────────────────

function Header({ userId, peers }: { userId: string; peers: string[] }) {
  return (
    <div className={styles.header}>
      <h1>Collaborative Todo Board</h1>
      <div className={styles.users}>
        <span>{userId}</span>
        {peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}
      </div>
    </div>
  );
}

function Card({ task, onDragStart }: { task: Task; onDragStart: (e: React.DragEvent, id: string) => void }) {
  const [d, setD] = useState(false);
  return (
    <div className={`${styles.card} ${d ? styles.cardDragging : ''}`} draggable="true"
      onDragStart={(e) => { setD(true); onDragStart(e, task.id); }}
      onDragEnd={() => setD(false)}>
      <div className={styles.cardText}>{task.text}</div>
      <div className={styles.cardMeta}>{task.lastEditor} · v{task.version}</div>
    </div>
  );
}

function NewTaskInput({ dispatch }: { dispatch: React.Dispatch<AppAction> }) {
  const [v, sv] = useState('');
  return (
    <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (v.trim()) { dispatch({ type: 'ADD_TASK', text: v.trim() }); sv(''); } }}>
      <input className={styles.taskInput} value={v} onChange={(e) => sv(e.target.value)} placeholder="New task..." />
      <button className={styles.addBtn} type="submit">Add</button>
    </form>
  );
}

function ColumnView({ colKey, title, ids, tasks, dispatch }: { colKey: ColumnKey; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<AppAction> }) {
  const ref = useRef<HTMLDivElement>(null);
  const handleOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const tid = e.dataTransfer.getData('text/plain');
    if (!tid || !tasks[tid]) return;
    let idx = ids.length;
    if (ref.current) {
      const cards = ref.current.querySelectorAll('[data-card-item]');
      for (let i = 0; i < cards.length; i++) {
        const r = cards[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height / 2) { idx = i; break; }
      }
    }
    if (tasks[tid].column === colKey) dispatch({ type: 'REORDER', taskId: tid, pos: idx });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, targetCol: colKey, pos: idx });
  }, [colKey, ids, tasks, dispatch]);
  const onStart = useCallback((e: React.DragEvent, id: string) => { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move'; }, []);

  return (
    <div className={styles.column} onDragOver={handleOver} onDrop={handleDrop} ref={ref}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {colKey === 'todo' && <NewTaskInput dispatch={dispatch} />}
      <div className={styles.cardList}>
        {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card-item><Card task={t} onDragStart={onStart} /></div> : null; })}
      </div>
    </div>
  );
}

function ConflictNotification({ conflicts, tasks, dispatch }: { conflicts: Conflict[]; tasks: Record<string, Task>; dispatch: React.Dispatch<AppAction> }) {
  if (!conflicts.length) return null;
  return (
    <div className={styles.conflictToast}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; also moved by {c.otherUser}</span>
          <button onClick={() => dispatch({ type: 'CLEAR_CONFLICT', taskId: c.taskId })}>OK</button>
        </div>
      ))}
    </div>
  );
}

// ── Root ─────────────────────────────────────────────────────────────────────

const COLUMNS: { key: ColumnKey; title: string }[] = [
  { key: 'todo', title: 'Todo' },
  { key: 'inProgress', title: 'In Progress' },
  { key: 'done', title: 'Done' },
];

function TodoBoard() {
  const [state, dispatch] = useReducer(appReducer, defaultState);

  useEffect(() => {
    const t1 = setInterval(() => backendFlush().forEach((a) => dispatch(a)), 500);
    const t2 = setInterval(() => setTimeout(backendSimulate, Math.random() * 3000), 6000);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);

  return (
    <div className={styles.app}>
      <Header userId={state.userId} peers={state.peers} />
      <div className={styles.board}>
        {COLUMNS.map((c) => <ColumnView key={c.key} colKey={c.key} title={c.title} ids={state.columns[c.key]} tasks={state.tasks} dispatch={dispatch} />)}
      </div>
      <ConflictNotification conflicts={state.activeConflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoard;
