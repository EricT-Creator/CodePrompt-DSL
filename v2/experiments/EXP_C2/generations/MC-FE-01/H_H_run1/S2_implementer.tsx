import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ── Types ──

interface Task {
  id: string;
  text: string;
  column: 'todo' | 'inProgress' | 'done';
  order: number;
  lastMovedBy: string;
  version: number;
}

type ColumnId = 'todo' | 'inProgress' | 'done';

interface OptimisticOp {
  opId: string;
  type: 'MOVE' | 'REORDER' | 'ADD';
  payload: Record<string, unknown>;
  timestamp: number;
}

interface ConflictHint {
  taskId: string;
  localUser: string;
  remoteUser: string;
  resolvedAt?: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  currentUser: string;
  connectedUsers: string[];
  pendingOptimistic: OptimisticOp[];
  conflicts: ConflictHint[];
}

type BoardAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnId; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'REMOTE_UPDATE'; tasks: Record<string, Task>; columnOrder: Record<ColumnId, string[]> }
  | { type: 'CONFLICT_DETECTED'; taskId: string; remoteUser: string }
  | { type: 'CONFLICT_DISMISSED'; taskId: string }
  | { type: 'SYNC_ACK'; opId: string }
  | { type: 'SET_USERS'; users: string[] };

// ── Utils ──

const uid = (): string => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

// ── Reducer ──

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = uid();
      const task: Task = { id, text: action.text, column: 'todo', order: 0, lastMovedBy: state.currentUser, version: 1 };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: task },
        columnOrder: { ...state.columnOrder, todo: [id, ...state.columnOrder.todo] },
        pendingOptimistic: [...state.pendingOptimistic, { opId: uid(), type: 'ADD', payload: { taskId: id }, timestamp: Date.now() }],
      };
    }
    case 'MOVE_TASK': {
      const task = state.tasks[action.taskId];
      if (!task) return state;
      const srcCol = task.column;
      const srcOrder = state.columnOrder[srcCol].filter((i) => i !== action.taskId);
      const dstOrder = [...state.columnOrder[action.toColumn]];
      dstOrder.splice(action.toIndex, 0, action.taskId);
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: { ...task, column: action.toColumn, order: action.toIndex, lastMovedBy: state.currentUser, version: task.version + 1 } },
        columnOrder: { ...state.columnOrder, [srcCol]: srcOrder, [action.toColumn]: dstOrder },
        pendingOptimistic: [...state.pendingOptimistic, { opId: uid(), type: 'MOVE', payload: { taskId: action.taskId }, timestamp: Date.now() }],
      };
    }
    case 'REORDER_TASK': {
      const task = state.tasks[action.taskId];
      if (!task) return state;
      const col = task.column;
      const reordered = state.columnOrder[col].filter((i) => i !== action.taskId);
      reordered.splice(action.toIndex, 0, action.taskId);
      return {
        ...state,
        columnOrder: { ...state.columnOrder, [col]: reordered },
        pendingOptimistic: [...state.pendingOptimistic, { opId: uid(), type: 'REORDER', payload: { taskId: action.taskId }, timestamp: Date.now() }],
      };
    }
    case 'REMOTE_UPDATE':
      return { ...state, tasks: action.tasks, columnOrder: action.columnOrder };
    case 'CONFLICT_DETECTED':
      return { ...state, conflicts: [...state.conflicts, { taskId: action.taskId, localUser: state.currentUser, remoteUser: action.remoteUser }] };
    case 'CONFLICT_DISMISSED':
      return { ...state, conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId) };
    case 'SYNC_ACK':
      return { ...state, pendingOptimistic: state.pendingOptimistic.filter((o) => o.opId !== action.opId) };
    case 'SET_USERS':
      return { ...state, connectedUsers: action.users };
    default:
      return state;
  }
}

// ── Mock Server ──

const mockServerState = {
  tasks: {} as Record<string, Task>,
  columnOrder: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]>,
  outbox: [] as Array<{ kind: string; data: Record<string, unknown> }>,
  recentOps: [] as Array<{ taskId: string; user: string; ts: number }>,
};

function serverPush(op: OptimisticOp, user: string) {
  const tid = (op.payload as any)?.taskId;
  if (!tid) return;
  const now = Date.now();
  const clash = mockServerState.recentOps.find((r) => r.taskId === tid && r.user !== user && now - r.ts < 2000);
  if (clash) {
    mockServerState.outbox.push({ kind: 'CONFLICT', data: { taskId: tid, remoteUser: clash.user } });
  }
  mockServerState.recentOps.push({ taskId: tid, user, ts: now });
}

function simulateRemoteUser() {
  const ids = Object.keys(mockServerState.tasks);
  if (ids.length === 0) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const task = mockServerState.tasks[tid];
  if (!task) return;
  const cols: ColumnId[] = ['todo', 'inProgress', 'done'];
  const others = cols.filter((c) => c !== task.column);
  const dest = others[Math.floor(Math.random() * others.length)];
  mockServerState.recentOps.push({ taskId: tid, user: 'remote-user', ts: Date.now() });
  mockServerState.outbox.push({ kind: 'REMOTE_MOVE', data: { taskId: tid, to: dest } });
}

// ── Hook: useMockSync ──

function useMockSync(state: BoardState, dispatch: React.Dispatch<BoardAction>) {
  const ref = useRef(state);
  ref.current = state;

  useEffect(() => {
    mockServerState.tasks = { ...state.tasks };
    mockServerState.columnOrder = { ...state.columnOrder };
  }, [state.tasks, state.columnOrder]);

  useEffect(() => {
    const poll = setInterval(() => {
      const evts = mockServerState.outbox.splice(0);
      for (const e of evts) {
        if (e.kind === 'CONFLICT') {
          dispatch({ type: 'CONFLICT_DETECTED', taskId: e.data.taskId as string, remoteUser: e.data.remoteUser as string });
        }
      }
      for (const op of ref.current.pendingOptimistic) {
        serverPush(op, ref.current.currentUser);
        dispatch({ type: 'SYNC_ACK', opId: op.opId });
      }
    }, 500);
    const remote = setInterval(() => simulateRemoteUser(), 3500 + Math.random() * 2000);
    return () => { clearInterval(poll); clearInterval(remote); };
  }, [dispatch]);
}

// ── Sub-components ──

function BoardHeader({ users }: { users: string[] }) {
  return (
    <div className={styles.header}>
      <h1 className={styles.title}>Collaborative Todo Board</h1>
      <div className={styles.users}>
        {users.map((u) => (<span key={u} className={styles.userBadge}>{u}</span>))}
      </div>
    </div>
  );
}

function TaskCard({ task, onDragStart }: { task: Task; onDragStart: (e: React.DragEvent, id: string) => void }) {
  const [isDragging, setIsDragging] = useState(false);
  return (
    <div
      className={`${styles.card} ${isDragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={(e) => { setIsDragging(true); e.dataTransfer.setData('text/plain', task.id); e.dataTransfer.effectAllowed = 'move'; onDragStart(e, task.id); }}
      onDragEnd={() => setIsDragging(false)}
    >
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardBadge}>{task.lastMovedBy}</span>
    </div>
  );
}

function Column({ columnId, title, taskIds, tasks, dispatch }: { columnId: ColumnId; title: string; taskIds: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  const [over, setOver] = useState(false);
  const colRef = useRef<HTMLDivElement>(null);

  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setOver(true); }, []);
  const onDragLeave = useCallback(() => setOver(false), []);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setOver(false);
    const taskId = e.dataTransfer.getData('text/plain');
    const task = tasks[taskId];
    if (!task) return;
    let idx = taskIds.length;
    if (colRef.current) {
      const cards = colRef.current.querySelectorAll('[data-card]');
      for (let i = 0; i < cards.length; i++) {
        const r = cards[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height / 2) { idx = i; break; }
      }
    }
    if (task.column === columnId) dispatch({ type: 'REORDER_TASK', taskId, toIndex: idx });
    else dispatch({ type: 'MOVE_TASK', taskId, toColumn: columnId, toIndex: idx });
  }, [columnId, taskIds, tasks, dispatch]);

  return (
    <div className={`${styles.column} ${over ? styles.columnDragOver : ''}`} ref={colRef} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {taskIds.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card><TaskCard task={t} onDragStart={() => {}} /></div> : null; })}
    </div>
  );
}

function TaskCreator({ dispatch }: { dispatch: React.Dispatch<BoardAction> }) {
  const [text, setText] = useState('');
  const submit = (e: React.FormEvent) => { e.preventDefault(); const t = text.trim(); if (!t) return; dispatch({ type: 'ADD_TASK', text: t }); setText(''); };
  return (
    <form className={styles.creator} onSubmit={submit}>
      <input className={styles.creatorInput} value={text} onChange={(e) => setText(e.target.value)} placeholder="New task..." />
      <button className={styles.creatorButton} type="submit">Add</button>
    </form>
  );
}

function ConflictToast({ conflicts, tasks, dispatch }: { conflicts: ConflictHint[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  if (conflicts.length === 0) return null;
  return (
    <div className={styles.conflictToast}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>Conflict on &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; — also moved by {c.remoteUser}</span>
          <button className={styles.conflictDismiss} onClick={() => dispatch({ type: 'CONFLICT_DISMISSED', taskId: c.taskId })}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Root Component ──

const init: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user-' + Math.random().toString(36).slice(2, 6),
  connectedUsers: [],
  pendingOptimistic: [],
  conflicts: [],
};

function TodoBoardApp() {
  const [state, dispatch] = useReducer(boardReducer, init);
  useMockSync(state, dispatch);

  useEffect(() => { dispatch({ type: 'SET_USERS', users: [state.currentUser, 'remote-user'] }); }, [state.currentUser]);

  const cols: { id: ColumnId; title: string }[] = [
    { id: 'todo', title: 'Todo' },
    { id: 'inProgress', title: 'In Progress' },
    { id: 'done', title: 'Done' },
  ];

  return (
    <div className={styles.app}>
      <BoardHeader users={state.connectedUsers} />
      <TaskCreator dispatch={dispatch} />
      <div className={styles.board}>
        {cols.map((c) => (<Column key={c.id} columnId={c.id} title={c.title} taskIds={state.columnOrder[c.id]} tasks={state.tasks} dispatch={dispatch} />))}
      </div>
      <ConflictToast conflicts={state.conflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoardApp;
