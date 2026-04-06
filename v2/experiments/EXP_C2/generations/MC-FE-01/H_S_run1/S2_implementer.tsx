import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ── Type Definitions ──

interface Task {
  id: string;
  text: string;
  column: 'todo' | 'inProgress' | 'done';
  order: number;
  lastMovedBy: string;
  version: number;
}

type ColumnId = 'todo' | 'inProgress' | 'done';

interface PendingOp {
  opId: string;
  type: 'MOVE' | 'REORDER' | 'ADD';
  taskId: string;
  timestamp: number;
}

interface ConflictInfo {
  taskId: string;
  yourAction: string;
  theirUser: string;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: { todo: string[]; inProgress: string[]; done: string[] };
  currentUser: string;
  connectedUsers: string[];
  optimisticQueue: PendingOp[];
  conflictHints: ConflictInfo[];
}

type Action =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnId; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'APPLY_REMOTE'; tasks: Record<string, Task>; columnOrder: BoardState['columnOrder'] }
  | { type: 'MARK_CONFLICT'; taskId: string; theirUser: string }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'CONFIRM_OP'; opId: string }
  | { type: 'ROLLBACK_OP'; opId: string }
  | { type: 'SET_USERS'; users: string[] };

const genId = (): string => Math.random().toString(36).slice(2, 9) + Date.now().toString(36);

// ── Reducer ──

function reducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = genId();
      const task: Task = { id, text: action.text, column: 'todo', order: 0, lastMovedBy: state.currentUser, version: 1 };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: task },
        columnOrder: { ...state.columnOrder, todo: [id, ...state.columnOrder.todo] },
        optimisticQueue: [...state.optimisticQueue, { opId: genId(), type: 'ADD', taskId: id, timestamp: Date.now() }],
      };
    }
    case 'MOVE_TASK': {
      const t = state.tasks[action.taskId];
      if (!t) return state;
      const from = state.columnOrder[t.column].filter((x) => x !== action.taskId);
      const to = [...state.columnOrder[action.toColumn]];
      to.splice(action.toIndex, 0, action.taskId);
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: { ...t, column: action.toColumn, order: action.toIndex, lastMovedBy: state.currentUser, version: t.version + 1 } },
        columnOrder: { ...state.columnOrder, [t.column]: from, [action.toColumn]: to },
        optimisticQueue: [...state.optimisticQueue, { opId: genId(), type: 'MOVE', taskId: action.taskId, timestamp: Date.now() }],
      };
    }
    case 'REORDER_TASK': {
      const t = state.tasks[action.taskId];
      if (!t) return state;
      const arr = state.columnOrder[t.column].filter((x) => x !== action.taskId);
      arr.splice(action.toIndex, 0, action.taskId);
      return {
        ...state,
        columnOrder: { ...state.columnOrder, [t.column]: arr },
        optimisticQueue: [...state.optimisticQueue, { opId: genId(), type: 'REORDER', taskId: action.taskId, timestamp: Date.now() }],
      };
    }
    case 'APPLY_REMOTE':
      return { ...state, tasks: action.tasks, columnOrder: action.columnOrder };
    case 'MARK_CONFLICT':
      return { ...state, conflictHints: [...state.conflictHints, { taskId: action.taskId, yourAction: 'move', theirUser: action.theirUser }] };
    case 'DISMISS_CONFLICT':
      return { ...state, conflictHints: state.conflictHints.filter((c) => c.taskId !== action.taskId) };
    case 'CONFIRM_OP':
      return { ...state, optimisticQueue: state.optimisticQueue.filter((o) => o.opId !== action.opId) };
    case 'ROLLBACK_OP':
      return { ...state, optimisticQueue: state.optimisticQueue.filter((o) => o.opId !== action.opId) };
    case 'SET_USERS':
      return { ...state, connectedUsers: action.users };
    default:
      return state;
  }
}

// ── Mock Server ──

const mockServer = {
  tasks: {} as Record<string, Task>,
  cols: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]>,
  events: [] as Array<{ kind: string; data: any }>,
  recent: [] as Array<{ taskId: string; user: string; ts: number }>,
};

function msSubmit(op: PendingOp, user: string) {
  const now = Date.now();
  const clash = mockServer.recent.find((r) => r.taskId === op.taskId && r.user !== user && now - r.ts < 2000);
  if (clash) mockServer.events.push({ kind: 'conflict', data: { taskId: op.taskId, remoteUser: clash.user } });
  mockServer.recent.push({ taskId: op.taskId, user, ts: now });
}

function msSimRemote() {
  const ids = Object.keys(mockServer.tasks);
  if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const t = mockServer.tasks[tid];
  if (!t) return;
  const cols: ColumnId[] = ['todo', 'inProgress', 'done'];
  const dest = cols.filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  mockServer.recent.push({ taskId: tid, user: 'peer-user', ts: Date.now() });
  mockServer.events.push({ kind: 'remote', data: { taskId: tid, to: dest } });
}

// ── useMockSync ──

function useMockSync(state: BoardState, dispatch: React.Dispatch<Action>) {
  const sRef = useRef(state);
  sRef.current = state;

  useEffect(() => {
    mockServer.tasks = { ...state.tasks };
    mockServer.cols = { ...state.columnOrder };
  }, [state.tasks, state.columnOrder]);

  useEffect(() => {
    const t1 = setInterval(() => {
      const evts = mockServer.events.splice(0);
      for (const e of evts) {
        if (e.kind === 'conflict') dispatch({ type: 'MARK_CONFLICT', taskId: e.data.taskId, theirUser: e.data.remoteUser });
      }
      for (const op of sRef.current.optimisticQueue) { msSubmit(op, sRef.current.currentUser); dispatch({ type: 'CONFIRM_OP', opId: op.opId }); }
    }, 500);
    const t2 = setInterval(msSimRemote, 4000 + Math.random() * 2000);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, [dispatch]);
}

// ── UI Components ──

function BoardHeader({ users }: { users: string[] }) {
  return (
    <div className={styles.header}>
      <h1 className={styles.title}>Collaborative Todo Board</h1>
      <div className={styles.users}>{users.map((u) => <span key={u} className={styles.userBadge}>{u}</span>)}</div>
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  const [dragging, setDragging] = useState(false);
  return (
    <div
      className={`${styles.card} ${dragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={(e) => { setDragging(true); e.dataTransfer.setData('text/plain', task.id); e.dataTransfer.effectAllowed = 'move'; }}
      onDragEnd={() => setDragging(false)}
    >
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardBadge}>{task.lastMovedBy}</span>
    </div>
  );
}

function Column({ colId, title, ids, tasks, dispatch }: { colId: ColumnId; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Action> }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setOver(false);
    const taskId = e.dataTransfer.getData('text/plain');
    const task = tasks[taskId]; if (!task) return;
    let idx = ids.length;
    if (ref.current) { const cards = ref.current.querySelectorAll('[data-card]'); for (let i = 0; i < cards.length; i++) { const r = cards[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { idx = i; break; } } }
    if (task.column === colId) dispatch({ type: 'REORDER_TASK', taskId, toIndex: idx });
    else dispatch({ type: 'MOVE_TASK', taskId, toColumn: colId, toIndex: idx });
  }, [colId, ids, tasks, dispatch]);

  return (
    <div className={`${styles.column} ${over ? styles.columnDragOver : ''}`} ref={ref}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card><TaskCard task={t} /></div> : null; })}
    </div>
  );
}

function TaskCreator({ dispatch }: { dispatch: React.Dispatch<Action> }) {
  const [text, setText] = useState('');
  return (
    <form className={styles.creator} onSubmit={(e) => { e.preventDefault(); const v = text.trim(); if (v) { dispatch({ type: 'ADD_TASK', text: v }); setText(''); } }}>
      <input className={styles.creatorInput} value={text} onChange={(e) => setText(e.target.value)} placeholder="New task..." />
      <button className={styles.creatorButton} type="submit">Add</button>
    </form>
  );
}

function ConflictBanner({ hints, tasks, dispatch }: { hints: ConflictInfo[]; tasks: Record<string, Task>; dispatch: React.Dispatch<Action> }) {
  if (!hints.length) return null;
  return (
    <div className={styles.conflictToast}>
      {hints.map((h) => (
        <div key={h.taskId} className={styles.conflictItem}>
          <span>Conflict: &quot;{tasks[h.taskId]?.text ?? h.taskId}&quot; also moved by {h.theirUser}</span>
          <button className={styles.conflictDismiss} onClick={() => dispatch({ type: 'DISMISS_CONFLICT', taskId: h.taskId })}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Root ──

const initialState: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user-' + Math.random().toString(36).slice(2, 6),
  connectedUsers: [],
  optimisticQueue: [],
  conflictHints: [],
};

function TodoBoardApp() {
  const [state, dispatch] = useReducer(reducer, initialState);
  useMockSync(state, dispatch);
  useEffect(() => { dispatch({ type: 'SET_USERS', users: [state.currentUser, 'peer-user'] }); }, [state.currentUser]);

  return (
    <div className={styles.app}>
      <BoardHeader users={state.connectedUsers} />
      <TaskCreator dispatch={dispatch} />
      <div className={styles.board}>
        {(['todo', 'inProgress', 'done'] as ColumnId[]).map((c) => (
          <Column key={c} colId={c} title={c === 'todo' ? 'Todo' : c === 'inProgress' ? 'In Progress' : 'Done'} ids={state.columnOrder[c]} tasks={state.tasks} dispatch={dispatch} />
        ))}
      </div>
      <ConflictBanner hints={state.conflictHints} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoardApp;
