import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ── Interfaces ──

type ColumnKey = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnKey;
  order: number;
  lastEditor: string;
  version: number;
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

interface AppState {
  tasks: Record<string, Task>;
  columns: Record<ColumnKey, string[]>;
  userId: string;
  peers: string[];
  pendingOps: LocalOp[];
  activeConflicts: Conflict[];
}

type AppAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnKey; toIndex: number }
  | { type: 'REORDER'; taskId: string; toIndex: number }
  | { type: 'REMOTE_CHANGE'; tasks: Record<string, Task>; columns: Record<ColumnKey, string[]> }
  | { type: 'CONFLICT'; taskId: string; otherUser: string }
  | { type: 'CLEAR_CONFLICT'; taskId: string }
  | { type: 'ACK'; opId: string }
  | { type: 'NACK'; opId: string }
  | { type: 'SET_PEERS'; peers: string[] };

const mkId = (): string => Math.random().toString(36).slice(2, 9) + Date.now().toString(36);

// ── Reducer ──

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = mkId();
      const task: Task = { id, text: action.text, column: 'todo', order: 0, lastEditor: state.userId, version: 1 };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: task },
        columns: { ...state.columns, todo: [id, ...state.columns.todo] },
        pendingOps: [...state.pendingOps, { id: mkId(), kind: 'add', taskId: id, ts: Date.now() }],
      };
    }
    case 'MOVE_TASK': {
      const t = state.tasks[action.taskId];
      if (!t) return state;
      const src = state.columns[t.column].filter((x) => x !== action.taskId);
      const dst = [...state.columns[action.toColumn]];
      dst.splice(action.toIndex, 0, action.taskId);
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: { ...t, column: action.toColumn, order: action.toIndex, lastEditor: state.userId, version: t.version + 1 } },
        columns: { ...state.columns, [t.column]: src, [action.toColumn]: dst },
        pendingOps: [...state.pendingOps, { id: mkId(), kind: 'move', taskId: action.taskId, ts: Date.now() }],
      };
    }
    case 'REORDER': {
      const t = state.tasks[action.taskId];
      if (!t) return state;
      const arr = state.columns[t.column].filter((x) => x !== action.taskId);
      arr.splice(action.toIndex, 0, action.taskId);
      return { ...state, columns: { ...state.columns, [t.column]: arr }, pendingOps: [...state.pendingOps, { id: mkId(), kind: 'reorder', taskId: action.taskId, ts: Date.now() }] };
    }
    case 'REMOTE_CHANGE':
      return { ...state, tasks: action.tasks, columns: action.columns };
    case 'CONFLICT':
      return { ...state, activeConflicts: [...state.activeConflicts, { taskId: action.taskId, otherUser: action.otherUser, description: 'concurrent move' }] };
    case 'CLEAR_CONFLICT':
      return { ...state, activeConflicts: state.activeConflicts.filter((c) => c.taskId !== action.taskId) };
    case 'ACK':
      return { ...state, pendingOps: state.pendingOps.filter((o) => o.id !== action.opId) };
    case 'NACK':
      return { ...state, pendingOps: state.pendingOps.filter((o) => o.id !== action.opId) };
    case 'SET_PEERS':
      return { ...state, peers: action.peers };
    default:
      return state;
  }
}

// ── Mock Backend ──

const mockBackend = {
  tasks: {} as Record<string, Task>,
  cols: { todo: [], inProgress: [], done: [] } as Record<ColumnKey, string[]>,
  outbox: [] as Array<{ kind: string; data: any }>,
  opLog: [] as Array<{ taskId: string; user: string; ts: number }>,
};

function mbProcess(op: LocalOp, user: string) {
  const now = Date.now();
  const hit = mockBackend.opLog.find((r) => r.taskId === op.taskId && r.user !== user && now - r.ts < 2000);
  if (hit) mockBackend.outbox.push({ kind: 'conflict', data: { taskId: op.taskId, otherUser: hit.user } });
  mockBackend.opLog.push({ taskId: op.taskId, user, ts: now });
}

function mbSimulate() {
  const ids = Object.keys(mockBackend.tasks);
  if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const task = mockBackend.tasks[tid];
  if (!task) return;
  const allCols: ColumnKey[] = ['todo', 'inProgress', 'done'];
  const dest = allCols.filter((c) => c !== task.column)[Math.floor(Math.random() * 2)];
  mockBackend.opLog.push({ taskId: tid, user: 'remote-peer', ts: Date.now() });
  mockBackend.outbox.push({ kind: 'sim', data: { taskId: tid, to: dest } });
}

function useMockSync(state: AppState, dispatch: React.Dispatch<AppAction>) {
  const ref = useRef(state);
  ref.current = state;
  useEffect(() => { mockBackend.tasks = { ...state.tasks }; mockBackend.cols = { ...state.columns }; }, [state.tasks, state.columns]);
  useEffect(() => {
    const i1 = setInterval(() => {
      const evts = mockBackend.outbox.splice(0);
      for (const e of evts) { if (e.kind === 'conflict') dispatch({ type: 'CONFLICT', taskId: e.data.taskId, otherUser: e.data.otherUser }); }
      for (const op of ref.current.pendingOps) { mbProcess(op, ref.current.userId); dispatch({ type: 'ACK', opId: op.id }); }
    }, 500);
    const i2 = setInterval(mbSimulate, 3000 + Math.random() * 3000);
    return () => { clearInterval(i1); clearInterval(i2); };
  }, [dispatch]);
}

// ── Components ──

function Header({ peers }: { peers: string[] }) {
  return (<div className={styles.header}><h1 className={styles.title}>Collaborative Todo Board</h1><div className={styles.users}>{peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}</div></div>);
}

function Card({ task }: { task: Task }) {
  const [d, setD] = useState(false);
  return (
    <div className={`${styles.card} ${d ? styles.cardDragging : ''}`} draggable="true"
      onDragStart={(e) => { setD(true); e.dataTransfer.setData('text/plain', task.id); e.dataTransfer.effectAllowed = 'move'; }}
      onDragEnd={() => setD(false)}>
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardBadge}>{task.lastEditor}</span>
    </div>
  );
}

function Col({ colKey, label, ids, tasks, dispatch }: { colKey: ColumnKey; label: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<AppAction> }) {
  const [over, setOver] = useState(false);
  const cRef = useRef<HTMLDivElement>(null);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setOver(false);
    const tid = e.dataTransfer.getData('text/plain');
    const t = tasks[tid]; if (!t) return;
    let idx = ids.length;
    if (cRef.current) { const cards = cRef.current.querySelectorAll('[data-card]'); for (let i = 0; i < cards.length; i++) { const r = cards[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { idx = i; break; } } }
    if (t.column === colKey) dispatch({ type: 'REORDER', taskId: tid, toIndex: idx });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, toColumn: colKey, toIndex: idx });
  }, [colKey, ids, tasks, dispatch]);

  return (
    <div className={`${styles.column} ${over ? styles.columnDragOver : ''}`} ref={cRef}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
      <h2 className={styles.columnTitle}>{label}</h2>
      {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card><Card task={t} /></div> : null; })}
    </div>
  );
}

function NewTaskInput({ dispatch }: { dispatch: React.Dispatch<AppAction> }) {
  const [v, setV] = useState('');
  return (
    <form className={styles.creator} onSubmit={(e) => { e.preventDefault(); const s = v.trim(); if (s) { dispatch({ type: 'ADD_TASK', text: s }); setV(''); } }}>
      <input className={styles.creatorInput} value={v} onChange={(e) => setV(e.target.value)} placeholder="New task..." />
      <button className={styles.creatorButton} type="submit">Add</button>
    </form>
  );
}

function ConflictNotification({ conflicts, tasks, dispatch }: { conflicts: Conflict[]; tasks: Record<string, Task>; dispatch: React.Dispatch<AppAction> }) {
  if (!conflicts.length) return null;
  return (
    <div className={styles.conflictToast}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; moved by {c.otherUser}</span>
          <button className={styles.conflictDismiss} onClick={() => dispatch({ type: 'CLEAR_CONFLICT', taskId: c.taskId })}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Root ──

const initState: AppState = {
  tasks: {},
  columns: { todo: [], inProgress: [], done: [] },
  userId: 'user-' + Math.random().toString(36).slice(2, 6),
  peers: [],
  pendingOps: [],
  activeConflicts: [],
};

function TodoBoard() {
  const [state, dispatch] = useReducer(appReducer, initState);
  useMockSync(state, dispatch);
  useEffect(() => { dispatch({ type: 'SET_PEERS', peers: [state.userId, 'remote-peer'] }); }, [state.userId]);

  const layout: { key: ColumnKey; label: string }[] = [{ key: 'todo', label: 'Todo' }, { key: 'inProgress', label: 'In Progress' }, { key: 'done', label: 'Done' }];

  return (
    <div className={styles.app}>
      <Header peers={state.peers} />
      <NewTaskInput dispatch={dispatch} />
      <div className={styles.board}>{layout.map((l) => <Col key={l.key} colKey={l.key} label={l.label} ids={state.columns[l.key]} tasks={state.tasks} dispatch={dispatch} />)}</div>
      <ConflictNotification conflicts={state.activeConflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoard;
