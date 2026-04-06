import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './CollaborativeBoard.module.css';

// ── Types ──

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  position: number;
  movedBy: string;
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
  columns: Record<ColumnId, string[]>;
  me: string;
  onlineUsers: string[];
  pendingOps: PendingOperation[];
  conflicts: ConflictRecord[];
}

type Action =
  | { type: 'CREATE_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnId; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'RECEIVE_REMOTE'; tasks: Record<string, Task>; columns: Record<ColumnId, string[]> }
  | { type: 'FLAG_CONFLICT'; taskId: string; otherUser: string }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'OP_CONFIRMED'; opId: string }
  | { type: 'OP_REJECTED'; opId: string }
  | { type: 'UPDATE_PEERS'; peers: string[] };

const genId = (): string => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

// ── Reducer ──

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'CREATE_TASK': {
      const id = genId();
      const task: Task = { id, text: action.text, column: 'todo', position: 0, movedBy: state.me, version: 1 };
      return { ...state, tasks: { ...state.tasks, [id]: task }, columns: { ...state.columns, todo: [id, ...state.columns.todo] }, pendingOps: [...state.pendingOps, { opId: genId(), kind: 'add', taskId: id, createdAt: Date.now() }] };
    }
    case 'MOVE_TASK': {
      const t = state.tasks[action.taskId]; if (!t) return state;
      const src = state.columns[t.column].filter((x) => x !== action.taskId);
      const dst = [...state.columns[action.toColumn]]; dst.splice(action.toIndex, 0, action.taskId);
      return { ...state, tasks: { ...state.tasks, [action.taskId]: { ...t, column: action.toColumn, position: action.toIndex, movedBy: state.me, version: t.version + 1 } }, columns: { ...state.columns, [t.column]: src, [action.toColumn]: dst }, pendingOps: [...state.pendingOps, { opId: genId(), kind: 'move', taskId: action.taskId, createdAt: Date.now() }] };
    }
    case 'REORDER_TASK': {
      const t = state.tasks[action.taskId]; if (!t) return state;
      const arr = state.columns[t.column].filter((x) => x !== action.taskId); arr.splice(action.toIndex, 0, action.taskId);
      return { ...state, columns: { ...state.columns, [t.column]: arr }, pendingOps: [...state.pendingOps, { opId: genId(), kind: 'reorder', taskId: action.taskId, createdAt: Date.now() }] };
    }
    case 'RECEIVE_REMOTE': return { ...state, tasks: action.tasks, columns: action.columns };
    case 'FLAG_CONFLICT': return { ...state, conflicts: [...state.conflicts, { taskId: action.taskId, otherUser: action.otherUser, message: 'concurrent move' }] };
    case 'DISMISS_CONFLICT': return { ...state, conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId) };
    case 'OP_CONFIRMED': return { ...state, pendingOps: state.pendingOps.filter((o) => o.opId !== action.opId) };
    case 'OP_REJECTED': return { ...state, pendingOps: state.pendingOps.filter((o) => o.opId !== action.opId) };
    case 'UPDATE_PEERS': return { ...state, onlineUsers: action.peers };
    default: return state;
  }
}

// ── Mock Server ──

const fakeServer = {
  tasks: {} as Record<string, Task>,
  cols: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]>,
  outbox: [] as Array<{ kind: string; data: any }>,
  recentOps: [] as Array<{ taskId: string; user: string; ts: number }>,
};

function processOp(op: PendingOperation, user: string) {
  const now = Date.now();
  const hit = fakeServer.recentOps.find((r) => r.taskId === op.taskId && r.user !== user && now - r.ts < 2000);
  if (hit) fakeServer.outbox.push({ kind: 'conflict', data: { taskId: op.taskId, otherUser: hit.user } });
  fakeServer.recentOps.push({ taskId: op.taskId, user, ts: now });
}

function simulateRemote() {
  const ids = Object.keys(fakeServer.tasks); if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const t = fakeServer.tasks[tid]; if (!t) return;
  const cols: ColumnId[] = ['todo', 'inProgress', 'done'];
  const dest = cols.filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  fakeServer.recentOps.push({ taskId: tid, user: 'remote', ts: Date.now() });
}

function useMockSync(state: State, dispatch: React.Dispatch<Action>) {
  const ref = useRef(state); ref.current = state;
  useEffect(() => { fakeServer.tasks = { ...state.tasks }; fakeServer.cols = { ...state.columns }; }, [state.tasks, state.columns]);
  useEffect(() => {
    const i1 = setInterval(() => {
      const evts = fakeServer.outbox.splice(0);
      for (const e of evts) if (e.kind === 'conflict') dispatch({ type: 'FLAG_CONFLICT', taskId: e.data.taskId, otherUser: e.data.otherUser });
      for (const op of ref.current.pendingOps) { processOp(op, ref.current.me); dispatch({ type: 'OP_CONFIRMED', opId: op.opId }); }
    }, 500);
    const i2 = setInterval(simulateRemote, 4000 + Math.random() * 2000);
    return () => { clearInterval(i1); clearInterval(i2); };
  }, [dispatch]);
}

// ── Sub-Components ──

function TaskCard({ task }: { task: Task }) {
  const [d, setD] = useState(false);
  return (
    <div className={`${styles.card} ${d ? styles.cardDragging : ''}`} draggable="true"
      onDragStart={(e) => { setD(true); e.dataTransfer.setData('text/plain', task.id); e.dataTransfer.effectAllowed = 'move'; }}
      onDragEnd={() => setD(false)}>
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardBadge}>{task.movedBy}</span>
    </div>
  );
}

function Column({ colId, title, ids, tasks, dispatch }: { colId: ColumnId; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Action> }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setOver(false);
    const tid = e.dataTransfer.getData('text/plain'); const t = tasks[tid]; if (!t) return;
    let idx = ids.length;
    if (ref.current) { const cards = ref.current.querySelectorAll('[data-card]'); for (let i = 0; i < cards.length; i++) { const r = cards[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { idx = i; break; } } }
    if (t.column === colId) dispatch({ type: 'REORDER_TASK', taskId: tid, toIndex: idx });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, toColumn: colId, toIndex: idx });
  }, [colId, ids, tasks, dispatch]);

  return (
    <div className={`${styles.column} ${over ? styles.dropIndicator : ''}`} ref={ref}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
      <h2 className={styles.columnTitle}>{title} ({ids.length})</h2>
      {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card><TaskCard task={t} /></div> : null; })}
    </div>
  );
}

function AddTaskForm({ dispatch }: { dispatch: React.Dispatch<Action> }) {
  const [v, setV] = useState('');
  return (
    <form className={styles.creator} onSubmit={(e) => { e.preventDefault(); const s = v.trim(); if (s) { dispatch({ type: 'CREATE_TASK', text: s }); setV(''); } }}>
      <input className={styles.creatorInput} value={v} onChange={(e) => setV(e.target.value)} placeholder="New task..." />
      <button className={styles.creatorButton} type="submit">Add</button>
    </form>
  );
}

function ConflictAlert({ conflicts, tasks, dispatch }: { conflicts: ConflictRecord[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Action> }) {
  if (!conflicts.length) return null;
  return (
    <div className={styles.conflictToast}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; also moved by {c.otherUser}</span>
          <button className={styles.conflictDismiss} onClick={() => dispatch({ type: 'DISMISS_CONFLICT', taskId: c.taskId })}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Root ──

const init: State = { tasks: {}, columns: { todo: [], inProgress: [], done: [] }, me: 'user-' + Math.random().toString(36).slice(2, 6), onlineUsers: [], pendingOps: [], conflicts: [] };

function CollaborativeBoard() {
  const [state, dispatch] = useReducer(reducer, init);
  useMockSync(state, dispatch);
  useEffect(() => { dispatch({ type: 'UPDATE_PEERS', peers: [state.me, 'remote'] }); }, [state.me]);

  return (
    <div className={styles.app}>
      <div className={styles.header}><h1 className={styles.title}>Collaborative Todo Board</h1><div className={styles.users}>{state.onlineUsers.map((u) => <span key={u} className={styles.userBadge}>{u}</span>)}</div></div>
      <AddTaskForm dispatch={dispatch} />
      <div className={styles.board}>
        {([['todo', 'Todo'], ['inProgress', 'In Progress'], ['done', 'Done']] as [ColumnId, string][]).map(([id, title]) => (
          <Column key={id} colId={id} title={title} ids={state.columns[id]} tasks={state.tasks} dispatch={dispatch} />
        ))}
      </div>
      <ConflictAlert conflicts={state.conflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default CollaborativeBoard;
