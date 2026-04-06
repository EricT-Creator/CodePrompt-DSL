import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './App.module.css';

// ── Types ──

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  sortIndex: number;
  lastActor: string;
  rev: number;
}

interface OpRecord { id: string; action: string; taskId: string; timestamp: number; }
interface ConflictEvent { taskId: string; rivalUser: string; detail: string; }

interface BoardState {
  taskMap: Record<string, Task>;
  columnLists: Record<ColumnId, string[]>;
  userId: string;
  peerIds: string[];
  inflightOps: OpRecord[];
  conflictQueue: ConflictEvent[];
}

type BoardAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnId; toIndex: number }
  | { type: 'REORDER'; taskId: string; toIndex: number }
  | { type: 'INGEST_REMOTE'; taskMap: Record<string, Task>; columnLists: Record<ColumnId, string[]> }
  | { type: 'RAISE_CONFLICT'; taskId: string; rivalUser: string }
  | { type: 'CLEAR_CONFLICT'; taskId: string }
  | { type: 'CONFIRM'; opId: string }
  | { type: 'REJECT'; opId: string }
  | { type: 'SET_PEERS'; peers: string[] };

const mkId = (): string => Math.random().toString(36).slice(2, 9) + Date.now().toString(36);

// ── Reducer ──

function reducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = mkId();
      const task: Task = { id, text: action.text, column: 'todo', sortIndex: 0, lastActor: state.userId, rev: 1 };
      return { ...state, taskMap: { ...state.taskMap, [id]: task }, columnLists: { ...state.columnLists, todo: [id, ...state.columnLists.todo] }, inflightOps: [...state.inflightOps, { id: mkId(), action: 'add', taskId: id, timestamp: Date.now() }] };
    }
    case 'MOVE_TASK': {
      const t = state.taskMap[action.taskId]; if (!t) return state;
      const src = state.columnLists[t.column].filter((x) => x !== action.taskId);
      const dst = [...state.columnLists[action.toColumn]]; dst.splice(action.toIndex, 0, action.taskId);
      return { ...state, taskMap: { ...state.taskMap, [action.taskId]: { ...t, column: action.toColumn, sortIndex: action.toIndex, lastActor: state.userId, rev: t.rev + 1 } }, columnLists: { ...state.columnLists, [t.column]: src, [action.toColumn]: dst }, inflightOps: [...state.inflightOps, { id: mkId(), action: 'move', taskId: action.taskId, timestamp: Date.now() }] };
    }
    case 'REORDER': {
      const t = state.taskMap[action.taskId]; if (!t) return state;
      const arr = state.columnLists[t.column].filter((x) => x !== action.taskId); arr.splice(action.toIndex, 0, action.taskId);
      return { ...state, columnLists: { ...state.columnLists, [t.column]: arr }, inflightOps: [...state.inflightOps, { id: mkId(), action: 'reorder', taskId: action.taskId, timestamp: Date.now() }] };
    }
    case 'INGEST_REMOTE': return { ...state, taskMap: action.taskMap, columnLists: action.columnLists };
    case 'RAISE_CONFLICT': return { ...state, conflictQueue: [...state.conflictQueue, { taskId: action.taskId, rivalUser: action.rivalUser, detail: 'concurrent move' }] };
    case 'CLEAR_CONFLICT': return { ...state, conflictQueue: state.conflictQueue.filter((c) => c.taskId !== action.taskId) };
    case 'CONFIRM': return { ...state, inflightOps: state.inflightOps.filter((o) => o.id !== action.opId) };
    case 'REJECT': return { ...state, inflightOps: state.inflightOps.filter((o) => o.id !== action.opId) };
    case 'SET_PEERS': return { ...state, peerIds: action.peers };
    default: return state;
  }
}

// ── Mock Server ──

const MockServer = {
  tasks: {} as Record<string, Task>,
  cols: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]>,
  queue: [] as Array<{ kind: string; data: any }>,
  log: [] as Array<{ taskId: string; user: string; ts: number }>,
};

function msProcess(op: OpRecord, user: string) {
  const now = Date.now();
  const hit = MockServer.log.find((r) => r.taskId === op.taskId && r.user !== user && now - r.ts < 2000);
  if (hit) MockServer.queue.push({ kind: 'conflict', data: { taskId: op.taskId, rivalUser: hit.user } });
  MockServer.log.push({ taskId: op.taskId, user, ts: now });
}

function msSim() {
  const ids = Object.keys(MockServer.tasks); if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const t = MockServer.tasks[tid]; if (!t) return;
  const cols: ColumnId[] = ['todo', 'inProgress', 'done'];
  const dest = cols.filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  MockServer.log.push({ taskId: tid, user: 'rival', ts: Date.now() });
}

function useMockSync(state: BoardState, dispatch: React.Dispatch<BoardAction>) {
  const ref = useRef(state); ref.current = state;
  useEffect(() => { MockServer.tasks = { ...state.taskMap }; MockServer.cols = { ...state.columnLists }; }, [state.taskMap, state.columnLists]);
  useEffect(() => {
    const i1 = setInterval(() => {
      const evts = MockServer.queue.splice(0);
      for (const e of evts) if (e.kind === 'conflict') dispatch({ type: 'RAISE_CONFLICT', taskId: e.data.taskId, rivalUser: e.data.rivalUser });
      for (const op of ref.current.inflightOps) { msProcess(op, ref.current.userId); dispatch({ type: 'CONFIRM', opId: op.id }); }
    }, 500);
    const i2 = setInterval(msSim, 3500 + Math.random() * 2500);
    return () => { clearInterval(i1); clearInterval(i2); };
  }, [dispatch]);
}

// ── UI Components ──

function TaskCard({ task }: { task: Task }) {
  const [d, setD] = useState(false);
  return (
    <div className={`${styles.card} ${d ? styles.cardActive : ''}`} draggable="true"
      onDragStart={(e) => { setD(true); e.dataTransfer.setData('text/plain', task.id); e.dataTransfer.effectAllowed = 'move'; }}
      onDragEnd={() => setD(false)}>
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardBadge}>{task.lastActor}</span>
    </div>
  );
}

function ColumnView({ colId, title, ids, tasks, dispatch }: { colId: ColumnId; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setOver(false);
    const tid = e.dataTransfer.getData('text/plain'); const t = tasks[tid]; if (!t) return;
    let idx = ids.length;
    if (ref.current) { const cards = ref.current.querySelectorAll('[data-card]'); for (let i = 0; i < cards.length; i++) { const r = cards[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { idx = i; break; } } }
    if (t.column === colId) dispatch({ type: 'REORDER', taskId: tid, toIndex: idx });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, toColumn: colId, toIndex: idx });
  }, [colId, ids, tasks, dispatch]);

  return (
    <div className={`${styles.column} ${over ? styles.dropHighlight : ''}`} ref={ref}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card><TaskCard task={t} /></div> : null; })}
    </div>
  );
}

function ConflictPopup({ conflicts, tasks, dispatch }: { conflicts: ConflictEvent[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  if (!conflicts.length) return null;
  return (
    <div className={styles.popup}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.popupItem}>
          <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; — {c.rivalUser}</span>
          <button className={styles.popupClose} onClick={() => dispatch({ type: 'CLEAR_CONFLICT', taskId: c.taskId })}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Root ──

const init: BoardState = { taskMap: {}, columnLists: { todo: [], inProgress: [], done: [] }, userId: 'user-' + Math.random().toString(36).slice(2, 6), peerIds: [], inflightOps: [], conflictQueue: [] };

function App() {
  const [state, dispatch] = useReducer(reducer, init);
  useMockSync(state, dispatch);
  useEffect(() => { dispatch({ type: 'SET_PEERS', peers: [state.userId, 'rival'] }); }, [state.userId]);

  const [newText, setNewText] = useState('');
  const onAdd = (e: React.FormEvent) => { e.preventDefault(); const s = newText.trim(); if (s) { dispatch({ type: 'ADD_TASK', text: s }); setNewText(''); } };

  return (
    <div className={styles.app}>
      <div className={styles.header}><h1 className={styles.title}>Collaborative Todo Board</h1><div className={styles.users}>{state.peerIds.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}</div></div>
      <form className={styles.creator} onSubmit={onAdd}><input className={styles.creatorInput} value={newText} onChange={(e) => setNewText(e.target.value)} placeholder="New task..." /><button className={styles.creatorButton} type="submit">Add</button></form>
      <div className={styles.board}>
        {([['todo', 'Todo'], ['inProgress', 'In Progress'], ['done', 'Done']] as [ColumnId, string][]).map(([id, title]) => (
          <ColumnView key={id} colId={id} title={title} ids={state.columnLists[id]} tasks={state.taskMap} dispatch={dispatch} />
        ))}
      </div>
      <ConflictPopup conflicts={state.conflictQueue} tasks={state.taskMap} dispatch={dispatch} />
    </div>
  );
}

export default App;
