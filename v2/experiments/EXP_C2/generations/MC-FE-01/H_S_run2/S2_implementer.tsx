import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ═══ Type Definitions ═══════════════════════════════════════════════════════

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
  columnOrder: { todo: string[]; inProgress: string[]; done: string[] };
  currentUser: string;
  connectedUsers: string[];
  optimisticQueue: PendingOp[];
  conflictHints: ConflictInfo[];
}

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

type BoardAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toCol: ColumnId; idx: number }
  | { type: 'REORDER_TASK'; taskId: string; idx: number }
  | { type: 'APPLY_REMOTE'; tasks: Record<string, Task>; columnOrder: BoardState['columnOrder'] }
  | { type: 'MARK_CONFLICT'; info: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'CONFIRM_OP'; opId: string }
  | { type: 'ROLLBACK_OP'; opId: string };

function uid(): string {
  return Math.random().toString(36).slice(2, 9) + '-' + Date.now().toString(36);
}

// ═══ Mock Server ════════════════════════════════════════════════════════════

const mockServer = {
  canonical: { tasks: {} as Record<string, Task>, cols: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]> },
  ops: [] as { id: string; taskId: string; user: string; t: number }[],
  outbox: [] as BoardAction[],
};

function srvSubmit(op: PendingOp, user: string) {
  const now = Date.now();
  const clash = mockServer.ops.find((o) => o.taskId === op.taskId && now - o.t < 2000 && o.user !== user);
  if (clash) {
    mockServer.outbox.push({ type: 'MARK_CONFLICT', info: { taskId: op.taskId, yourAction: op.type, theirUser: clash.user } });
  }
  mockServer.ops.push({ id: op.opId, taskId: op.taskId, user, t: now });
  mockServer.outbox.push({ type: 'CONFIRM_OP', opId: op.opId });
}

function srvRemoteAction() {
  const ids = Object.keys(mockServer.canonical.tasks);
  if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const task = mockServer.canonical.tasks[tid];
  if (!task) return;
  const targets: ColumnId[] = (['todo', 'inProgress', 'done'] as ColumnId[]).filter((c) => c !== task.column);
  const dest = targets[Math.floor(Math.random() * targets.length)];
  mockServer.canonical.cols[task.column] = mockServer.canonical.cols[task.column].filter((x) => x !== tid);
  mockServer.canonical.cols[dest].push(tid);
  mockServer.canonical.tasks[tid] = { ...task, column: dest, lastMovedBy: 'bot-peer', version: task.version + 1 };
  mockServer.ops.push({ id: uid(), taskId: tid, user: 'bot-peer', t: Date.now() });
  mockServer.outbox.push({ type: 'APPLY_REMOTE', tasks: { ...mockServer.canonical.tasks }, columnOrder: { ...mockServer.canonical.cols } });
}

function srvFlush(): BoardAction[] {
  const a = [...mockServer.outbox];
  mockServer.outbox = [];
  return a;
}

// ═══ Reducer ════════════════════════════════════════════════════════════════

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = uid();
      const t: Task = { id, text: action.text, column: 'todo', order: 0, lastMovedBy: state.currentUser, version: 1 };
      const co = { ...state.columnOrder, todo: [id, ...state.columnOrder.todo] };
      mockServer.canonical.tasks[id] = t;
      mockServer.canonical.cols = { ...co };
      const op: PendingOp = { opId: uid(), type: 'ADD', taskId: id, timestamp: Date.now() };
      setTimeout(() => srvSubmit(op, state.currentUser), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [id]: t }, columnOrder: co, optimisticQueue: [...state.optimisticQueue, op] };
    }
    case 'MOVE_TASK': {
      const { taskId, toCol, idx } = action;
      const task = state.tasks[taskId];
      if (!task) return state;
      const srcList = state.columnOrder[task.column].filter((x) => x !== taskId);
      const dstList = task.column === toCol ? srcList : [...state.columnOrder[toCol]];
      if (task.column === toCol) srcList.splice(idx, 0, taskId);
      else dstList.splice(idx, 0, taskId);
      const upd: Task = { ...task, column: toCol, lastMovedBy: state.currentUser, version: task.version + 1 };
      const co = { ...state.columnOrder, [task.column]: srcList, [toCol]: task.column === toCol ? srcList : dstList };
      mockServer.canonical.tasks[taskId] = upd;
      mockServer.canonical.cols = { ...co };
      const op: PendingOp = { opId: uid(), type: 'MOVE', taskId, timestamp: Date.now() };
      setTimeout(() => srvSubmit(op, state.currentUser), 300 + Math.random() * 500);
      return { ...state, tasks: { ...state.tasks, [taskId]: upd }, columnOrder: co, optimisticQueue: [...state.optimisticQueue, op] };
    }
    case 'REORDER_TASK': {
      const { taskId, idx } = action;
      const task = state.tasks[taskId];
      if (!task) return state;
      const list = state.columnOrder[task.column].filter((x) => x !== taskId);
      list.splice(idx, 0, taskId);
      const co = { ...state.columnOrder, [task.column]: list };
      mockServer.canonical.cols = { ...co };
      const op: PendingOp = { opId: uid(), type: 'REORDER', taskId, timestamp: Date.now() };
      setTimeout(() => srvSubmit(op, state.currentUser), 300 + Math.random() * 500);
      return { ...state, columnOrder: co, optimisticQueue: [...state.optimisticQueue, op] };
    }
    case 'APPLY_REMOTE':
      return { ...state, tasks: action.tasks, columnOrder: action.columnOrder };
    case 'MARK_CONFLICT':
      return { ...state, conflictHints: [...state.conflictHints, action.info] };
    case 'DISMISS_CONFLICT':
      return { ...state, conflictHints: state.conflictHints.filter((c) => c.taskId !== action.taskId) };
    case 'CONFIRM_OP':
      return { ...state, optimisticQueue: state.optimisticQueue.filter((o) => o.opId !== action.opId) };
    case 'ROLLBACK_OP':
      return { ...state, optimisticQueue: state.optimisticQueue.filter((o) => o.opId !== action.opId) };
    default:
      return state;
  }
}

const initState: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user-' + uid().slice(0, 4),
  connectedUsers: [],
  optimisticQueue: [],
  conflictHints: [],
};

// ═══ Components ═════════════════════════════════════════════════════════════

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

function TaskCard({ task, onDragStart }: { task: Task; onDragStart: (e: React.DragEvent, id: string) => void }) {
  const [dragging, setDragging] = useState(false);
  return (
    <div
      className={`${styles.card} ${dragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={(e) => { setDragging(true); onDragStart(e, task.id); }}
      onDragEnd={() => setDragging(false)}
    >
      <div className={styles.cardText}>{task.text}</div>
      <div className={styles.cardMeta}>{task.lastMovedBy} · v{task.version}</div>
    </div>
  );
}

function TaskCreator({ dispatch }: { dispatch: React.Dispatch<BoardAction> }) {
  const [v, setV] = useState('');
  return (
    <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (v.trim()) { dispatch({ type: 'ADD_TASK', text: v.trim() }); setV(''); } }}>
      <input className={styles.taskInput} placeholder="New task..." value={v} onChange={(e) => setV(e.target.value)} />
      <button className={styles.addBtn} type="submit">Add</button>
    </form>
  );
}

function Column({ cid, title, ids, tasks, dispatch }: { cid: ColumnId; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  const ref = useRef<HTMLDivElement>(null);
  const onOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const tid = e.dataTransfer.getData('text/plain');
    if (!tid || !tasks[tid]) return;
    let pos = ids.length;
    if (ref.current) {
      const els = ref.current.querySelectorAll('[data-ci]');
      for (let i = 0; i < els.length; i++) {
        const r = els[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height / 2) { pos = i; break; }
      }
    }
    if (tasks[tid].column === cid) dispatch({ type: 'REORDER_TASK', taskId: tid, idx: pos });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, toCol: cid, idx: pos });
  }, [cid, ids, tasks, dispatch]);
  const startDrag = useCallback((e: React.DragEvent, id: string) => { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move'; }, []);

  return (
    <div className={styles.column} onDragOver={onOver} onDrop={onDrop} ref={ref}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {cid === 'todo' && <TaskCreator dispatch={dispatch} />}
      <div className={styles.cardList}>
        {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-ci><TaskCard task={t} onDragStart={startDrag} /></div> : null; })}
      </div>
    </div>
  );
}

function ConflictBanner({ hints, tasks, dispatch }: { hints: ConflictInfo[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  if (!hints.length) return null;
  return (
    <div className={styles.conflictToast}>
      {hints.map((h) => (
        <div key={h.taskId} className={styles.conflictItem}>
          <span>Conflict on &quot;{tasks[h.taskId]?.text ?? h.taskId}&quot; by {h.theirUser}</span>
          <button onClick={() => dispatch({ type: 'DISMISS_CONFLICT', taskId: h.taskId })}>Dismiss</button>
        </div>
      ))}
    </div>
  );
}

// ═══ Root ═══════════════════════════════════════════════════════════════════

const COL_DEF: { id: ColumnId; title: string }[] = [
  { id: 'todo', title: 'Todo' },
  { id: 'inProgress', title: 'In Progress' },
  { id: 'done', title: 'Done' },
];

function TodoBoardApp() {
  const [state, dispatch] = useReducer(boardReducer, initState);

  useEffect(() => {
    const t1 = setInterval(() => srvFlush().forEach((a) => dispatch(a)), 500);
    const t2 = setInterval(() => setTimeout(srvRemoteAction, Math.random() * 2000), 5000);
    dispatch({ type: 'APPLY_REMOTE', tasks: state.tasks, columnOrder: state.columnOrder });
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);

  return (
    <div className={styles.app}>
      <BoardHeader user={state.currentUser} peers={state.connectedUsers} />
      <div className={styles.board}>
        {COL_DEF.map((c) => <Column key={c.id} cid={c.id} title={c.title} ids={state.columnOrder[c.id]} tasks={state.tasks} dispatch={dispatch} />)}
      </div>
      <ConflictBanner hints={state.conflictHints} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoardApp;
