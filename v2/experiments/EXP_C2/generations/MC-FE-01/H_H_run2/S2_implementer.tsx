import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ─── Types ───────────────────────────────────────────────────────────────────

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  order: number;
  lastMovedBy: string;
  version: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  currentUser: string;
  connectedUsers: string[];
  pendingOptimistic: { opId: string; type: string; payload: any; timestamp: number }[];
  conflicts: { taskId: string; localUser: string; remoteUser: string; resolvedAt?: number }[];
}

type Action =
  | { type: 'ADD_TASK'; payload: { text: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; toIndex: number } }
  | { type: 'REMOTE_UPDATE'; payload: { tasks: Record<string, Task>; columnOrder: Record<ColumnId, string[]> } }
  | { type: 'CONFLICT_DETECTED'; payload: { taskId: string; localUser: string; remoteUser: string } }
  | { type: 'CONFLICT_DISMISSED'; payload: { taskId: string } }
  | { type: 'SYNC_ACK'; payload: { opId: string } }
  | { type: 'SET_USERS'; payload: { users: string[] } };

function genId(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

// ─── Mock Server ─────────────────────────────────────────────────────────────

const serverState = {
  tasks: {} as Record<string, Task>,
  columns: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]>,
  log: [] as { opId: string; taskId: string; userId: string; ts: number }[],
  pending: [] as Action[],
};

function serverPush(op: { opId: string; taskId: string; type: string }, userId: string) {
  const now = Date.now();
  const conflict = serverState.log.find(
    (l) => l.taskId === op.taskId && now - l.ts < 2000 && l.userId !== userId
  );
  if (conflict) {
    serverState.pending.push({
      type: 'CONFLICT_DETECTED',
      payload: { taskId: op.taskId, localUser: userId, remoteUser: conflict.userId },
    });
  }
  serverState.log.push({ opId: op.opId, taskId: op.taskId, userId, ts: now });
  serverState.pending.push({ type: 'SYNC_ACK', payload: { opId: op.opId } });
}

function simulateRemote() {
  const ids = Object.keys(serverState.tasks);
  if (ids.length === 0) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const task = serverState.tasks[tid];
  if (!task) return;
  const cols: ColumnId[] = ['todo', 'inProgress', 'done'];
  const dest = cols.filter((c) => c !== task.column)[Math.floor(Math.random() * 2)];
  serverState.columns[task.column] = serverState.columns[task.column].filter((i) => i !== tid);
  serverState.columns[dest] = [...serverState.columns[dest], tid];
  serverState.tasks[tid] = { ...task, column: dest, lastMovedBy: 'peer-alice', version: task.version + 1 };
  serverState.log.push({ opId: genId(), taskId: tid, userId: 'peer-alice', ts: Date.now() });
  serverState.pending.push({
    type: 'REMOTE_UPDATE',
    payload: { tasks: { ...serverState.tasks }, columnOrder: { ...serverState.columns } },
  });
}

function serverDrain(): Action[] {
  const out = [...serverState.pending];
  serverState.pending = [];
  return out;
}

// ─── Reducer ─────────────────────────────────────────────────────────────────

function reducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = genId();
      const task: Task = { id, text: action.payload.text, column: 'todo', order: 0, lastMovedBy: state.currentUser, version: 1 };
      const cols = { ...state.columnOrder, todo: [id, ...state.columnOrder.todo] };
      serverState.tasks[id] = task;
      serverState.columns = { ...cols };
      const opId = genId();
      setTimeout(() => serverPush({ opId, taskId: id, type: 'ADD' }, state.currentUser), 400);
      return { ...state, tasks: { ...state.tasks, [id]: task }, columnOrder: cols, pendingOptimistic: [...state.pendingOptimistic, { opId, type: 'ADD', payload: { taskId: id }, timestamp: Date.now() }] };
    }
    case 'MOVE_TASK': {
      const { taskId, toColumn, toIndex } = action.payload;
      const t = state.tasks[taskId];
      if (!t) return state;
      const from = t.column;
      const fromList = state.columnOrder[from].filter((i) => i !== taskId);
      const toList = from === toColumn ? fromList : [...state.columnOrder[toColumn]];
      if (from === toColumn) { fromList.splice(toIndex, 0, taskId); }
      else { toList.splice(toIndex, 0, taskId); }
      const updated = { ...t, column: toColumn, lastMovedBy: state.currentUser, version: t.version + 1 };
      const cols = { ...state.columnOrder, [from]: fromList, [toColumn]: from === toColumn ? fromList : toList };
      serverState.tasks[taskId] = updated;
      serverState.columns = { ...cols };
      const opId = genId();
      setTimeout(() => serverPush({ opId, taskId, type: 'MOVE' }, state.currentUser), 400);
      return { ...state, tasks: { ...state.tasks, [taskId]: updated }, columnOrder: cols, pendingOptimistic: [...state.pendingOptimistic, { opId, type: 'MOVE', payload: action.payload, timestamp: Date.now() }] };
    }
    case 'REORDER_TASK': {
      const { taskId, toIndex } = action.payload;
      const t = state.tasks[taskId];
      if (!t) return state;
      const list = state.columnOrder[t.column].filter((i) => i !== taskId);
      list.splice(toIndex, 0, taskId);
      const cols = { ...state.columnOrder, [t.column]: list };
      serverState.columns = { ...cols };
      const opId = genId();
      setTimeout(() => serverPush({ opId, taskId, type: 'REORDER' }, state.currentUser), 400);
      return { ...state, columnOrder: cols, pendingOptimistic: [...state.pendingOptimistic, { opId, type: 'REORDER', payload: action.payload, timestamp: Date.now() }] };
    }
    case 'REMOTE_UPDATE':
      return { ...state, tasks: action.payload.tasks, columnOrder: action.payload.columnOrder };
    case 'CONFLICT_DETECTED':
      return { ...state, conflicts: [...state.conflicts, { ...action.payload, resolvedAt: undefined }] };
    case 'CONFLICT_DISMISSED':
      return { ...state, conflicts: state.conflicts.filter((c) => c.taskId !== action.payload.taskId) };
    case 'SYNC_ACK':
      return { ...state, pendingOptimistic: state.pendingOptimistic.filter((o) => o.opId !== action.payload.opId) };
    case 'SET_USERS':
      return { ...state, connectedUsers: action.payload.users };
    default:
      return state;
  }
}

const init: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'me-' + genId().slice(0, 4),
  connectedUsers: [],
  pendingOptimistic: [],
  conflicts: [],
};

// ─── Sub-components ──────────────────────────────────────────────────────────

function BoardHeader({ user, peers }: { user: string; peers: string[] }) {
  return (
    <div className={styles.header}>
      <h1>Collaborative Todo Board</h1>
      <div className={styles.users}>
        <span>{user}</span>
        {peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}
      </div>
    </div>
  );
}

function TaskCard({ task, onStart }: { task: Task; onStart: (e: React.DragEvent, id: string) => void }) {
  const [isDragging, setDragging] = useState(false);
  return (
    <div
      className={`${styles.card} ${isDragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={(e) => { setDragging(true); onStart(e, task.id); }}
      onDragEnd={() => setDragging(false)}
    >
      <p className={styles.cardText}>{task.text}</p>
      <small className={styles.cardMeta}>{task.lastMovedBy} · v{task.version}</small>
    </div>
  );
}

function TaskCreator({ dispatch }: { dispatch: React.Dispatch<Action> }) {
  const [val, setVal] = useState('');
  return (
    <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (val.trim()) { dispatch({ type: 'ADD_TASK', payload: { text: val.trim() } }); setVal(''); } }}>
      <input className={styles.taskInput} value={val} onChange={(e) => setVal(e.target.value)} placeholder="Add task..." />
      <button type="submit" className={styles.addBtn}>+</button>
    </form>
  );
}

function Column({ colId, label, ids, tasks, dispatch }: { colId: ColumnId; label: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Action> }) {
  const ref = useRef<HTMLDivElement>(null);

  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId || !tasks[taskId]) return;
    let idx = ids.length;
    if (ref.current) {
      const cards = ref.current.querySelectorAll('[data-crd]');
      for (let i = 0; i < cards.length; i++) {
        const r = cards[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height / 2) { idx = i; break; }
      }
    }
    if (tasks[taskId].column === colId) dispatch({ type: 'REORDER_TASK', payload: { taskId, toIndex: idx } });
    else dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn: colId, toIndex: idx } });
  }, [colId, ids, tasks, dispatch]);

  const onCardStart = useCallback((e: React.DragEvent, id: string) => {
    e.dataTransfer.setData('text/plain', id);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <div className={styles.column} onDragOver={onDragOver} onDrop={onDrop} ref={ref}>
      <h2 className={styles.columnTitle}>{label}</h2>
      {colId === 'todo' && <TaskCreator dispatch={dispatch} />}
      <div className={styles.cardList}>
        {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-crd><TaskCard task={t} onStart={onCardStart} /></div> : null; })}
      </div>
    </div>
  );
}

function ConflictToast({ conflicts, tasks, dispatch }: { conflicts: BoardState['conflicts']; tasks: Record<string, Task>; dispatch: React.Dispatch<Action> }) {
  if (!conflicts.length) return null;
  return (
    <div className={styles.conflictToast}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; moved by {c.remoteUser}</span>
          <button onClick={() => dispatch({ type: 'CONFLICT_DISMISSED', payload: { taskId: c.taskId } })}>OK</button>
        </div>
      ))}
    </div>
  );
}

// ─── Root ────────────────────────────────────────────────────────────────────

const COLS: { id: ColumnId; label: string }[] = [
  { id: 'todo', label: 'Todo' },
  { id: 'inProgress', label: 'In Progress' },
  { id: 'done', label: 'Done' },
];

function TodoBoardApp() {
  const [state, dispatch] = useReducer(reducer, init);

  useEffect(() => {
    const poll = setInterval(() => { serverDrain().forEach((a) => dispatch(a)); }, 500);
    const remote = setInterval(() => { setTimeout(simulateRemote, Math.random() * 2000); }, 6000);
    dispatch({ type: 'SET_USERS', payload: { users: ['peer-alice'] } });
    return () => { clearInterval(poll); clearInterval(remote); };
  }, []);

  return (
    <div className={styles.app}>
      <BoardHeader user={state.currentUser} peers={state.connectedUsers} />
      <div className={styles.board}>
        {COLS.map((c) => (
          <Column key={c.id} colId={c.id} label={c.label} ids={state.columnOrder[c.id]} tasks={state.tasks} dispatch={dispatch} />
        ))}
      </div>
      <ConflictToast conflicts={state.conflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoardApp;
