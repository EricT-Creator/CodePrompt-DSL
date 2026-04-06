import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './KanbanBoard.module.css';

// ── Types ──

type ColumnKey = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnKey;
  rank: number;
  editor: string;
  version: number;
}

interface WriteOp { wid: string; type: 'add' | 'move' | 'reorder'; taskId: string; ts: number; }
interface ConflictMsg { taskId: string; otherUser: string; info: string; }

interface Store {
  tasks: Record<string, Task>;
  lists: Record<ColumnKey, string[]>;
  myId: string;
  activePeers: string[];
  pendingWrites: WriteOp[];
  conflictMessages: ConflictMsg[];
}

type StoreAction =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnKey; toIndex: number }
  | { type: 'REORDER'; taskId: string; toIndex: number }
  | { type: 'REMOTE_EVENT'; tasks: Record<string, Task>; lists: Record<ColumnKey, string[]> }
  | { type: 'SHOW_CONFLICT'; taskId: string; otherUser: string }
  | { type: 'HIDE_CONFLICT'; taskId: string }
  | { type: 'WRITE_OK'; wid: string }
  | { type: 'WRITE_FAIL'; wid: string }
  | { type: 'SET_PEERS'; peers: string[] };

const uid = (): string => Math.random().toString(36).slice(2, 9) + Date.now().toString(36);

function reducer(state: Store, action: StoreAction): Store {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = uid();
      const task: Task = { id, text: action.text, column: 'todo', rank: 0, editor: state.myId, version: 1 };
      return { ...state, tasks: { ...state.tasks, [id]: task }, lists: { ...state.lists, todo: [id, ...state.lists.todo] }, pendingWrites: [...state.pendingWrites, { wid: uid(), type: 'add', taskId: id, ts: Date.now() }] };
    }
    case 'MOVE_TASK': {
      const t = state.tasks[action.taskId]; if (!t) return state;
      const src = state.lists[t.column].filter((x) => x !== action.taskId);
      const dst = [...state.lists[action.toColumn]]; dst.splice(action.toIndex, 0, action.taskId);
      return { ...state, tasks: { ...state.tasks, [action.taskId]: { ...t, column: action.toColumn, rank: action.toIndex, editor: state.myId, version: t.version + 1 } }, lists: { ...state.lists, [t.column]: src, [action.toColumn]: dst }, pendingWrites: [...state.pendingWrites, { wid: uid(), type: 'move', taskId: action.taskId, ts: Date.now() }] };
    }
    case 'REORDER': {
      const t = state.tasks[action.taskId]; if (!t) return state;
      const arr = state.lists[t.column].filter((x) => x !== action.taskId); arr.splice(action.toIndex, 0, action.taskId);
      return { ...state, lists: { ...state.lists, [t.column]: arr }, pendingWrites: [...state.pendingWrites, { wid: uid(), type: 'reorder', taskId: action.taskId, ts: Date.now() }] };
    }
    case 'REMOTE_EVENT': return { ...state, tasks: action.tasks, lists: action.lists };
    case 'SHOW_CONFLICT': return { ...state, conflictMessages: [...state.conflictMessages, { taskId: action.taskId, otherUser: action.otherUser, info: 'concurrent edit' }] };
    case 'HIDE_CONFLICT': return { ...state, conflictMessages: state.conflictMessages.filter((c) => c.taskId !== action.taskId) };
    case 'WRITE_OK': return { ...state, pendingWrites: state.pendingWrites.filter((w) => w.wid !== action.wid) };
    case 'WRITE_FAIL': return { ...state, pendingWrites: state.pendingWrites.filter((w) => w.wid !== action.wid) };
    case 'SET_PEERS': return { ...state, activePeers: action.peers };
    default: return state;
  }
}

// ── SimServer ──

const SimServer = {
  tasks: {} as Record<string, Task>,
  cols: { todo: [], inProgress: [], done: [] } as Record<ColumnKey, string[]>,
  outbox: [] as Array<{ kind: string; data: any }>,
  log: [] as Array<{ taskId: string; user: string; ts: number }>,
};

function simProcess(op: WriteOp, user: string) {
  const now = Date.now();
  const hit = SimServer.log.find((r) => r.taskId === op.taskId && r.user !== user && now - r.ts < 2000);
  if (hit) SimServer.outbox.push({ kind: 'conflict', data: { taskId: op.taskId, otherUser: hit.user } });
  SimServer.log.push({ taskId: op.taskId, user, ts: now });
}

function simRemote() {
  const ids = Object.keys(SimServer.tasks); if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  SimServer.log.push({ taskId: tid, user: 'bot', ts: Date.now() });
}

function useMockSync(state: Store, dispatch: React.Dispatch<StoreAction>) {
  const ref = useRef(state); ref.current = state;
  useEffect(() => { SimServer.tasks = { ...state.tasks }; SimServer.cols = { ...state.lists }; }, [state.tasks, state.lists]);
  useEffect(() => {
    const i1 = setInterval(() => {
      const evts = SimServer.outbox.splice(0);
      for (const e of evts) if (e.kind === 'conflict') dispatch({ type: 'SHOW_CONFLICT', taskId: e.data.taskId, otherUser: e.data.otherUser });
      for (const w of ref.current.pendingWrites) { simProcess(w, ref.current.myId); dispatch({ type: 'WRITE_OK', wid: w.wid }); }
    }, 500);
    const i2 = setInterval(simRemote, 4000 + Math.random() * 2000);
    return () => { clearInterval(i1); clearInterval(i2); };
  }, [dispatch]);
}

// ── Components ──

function TaskItem({ task }: { task: Task }) {
  const [d, setD] = useState(false);
  return (
    <div className={`${styles.card} ${d ? styles.dragging : ''}`} draggable="true"
      onDragStart={(e) => { setD(true); e.dataTransfer.setData('text/plain', task.id); e.dataTransfer.effectAllowed = 'move'; }}
      onDragEnd={() => setD(false)}>
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardOwner}>{task.editor}</span>
    </div>
  );
}

function ColumnPanel({ colKey, title, ids, tasks, dispatch }: { colKey: ColumnKey; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<StoreAction> }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setOver(false);
    const tid = e.dataTransfer.getData('text/plain'); const t = tasks[tid]; if (!t) return;
    let idx = ids.length;
    if (ref.current) { const cards = ref.current.querySelectorAll('[data-card]'); for (let i = 0; i < cards.length; i++) { const r = cards[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { idx = i; break; } } }
    if (t.column === colKey) dispatch({ type: 'REORDER', taskId: tid, toIndex: idx });
    else dispatch({ type: 'MOVE_TASK', taskId: tid, toColumn: colKey, toIndex: idx });
  }, [colKey, ids, tasks, dispatch]);

  return (
    <div className={`${styles.panel} ${over ? styles.dropTarget : ''}`} ref={ref}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
      <h2 className={styles.panelTitle}>{title}</h2>
      {ids.map((id) => { const t = tasks[id]; return t ? <div key={id} data-card><TaskItem task={t} /></div> : null; })}
    </div>
  );
}

function ConflictToast({ msgs, tasks, dispatch }: { msgs: ConflictMsg[]; tasks: Record<string, Task>; dispatch: React.Dispatch<StoreAction> }) {
  if (!msgs.length) return null;
  return (
    <div className={styles.toast}>
      {msgs.map((m) => (
        <div key={m.taskId} className={styles.toastItem}>
          <span>Conflict: &quot;{tasks[m.taskId]?.text ?? m.taskId}&quot; — {m.otherUser}</span>
          <button className={styles.toastClose} onClick={() => dispatch({ type: 'HIDE_CONFLICT', taskId: m.taskId })}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ── Root ──

const init: Store = { tasks: {}, lists: { todo: [], inProgress: [], done: [] }, myId: 'user-' + Math.random().toString(36).slice(2, 6), activePeers: [], pendingWrites: [], conflictMessages: [] };

function KanbanBoard() {
  const [state, dispatch] = useReducer(reducer, init);
  useMockSync(state, dispatch);
  useEffect(() => { dispatch({ type: 'SET_PEERS', peers: [state.myId, 'bot'] }); }, [state.myId]);
  const [txt, setTxt] = useState('');

  return (
    <div className={styles.app}>
      <div className={styles.header}><h1 className={styles.title}>Collaborative Todo Board</h1><div className={styles.peers}>{state.activePeers.map((p) => <span key={p} className={styles.peerBadge}>{p}</span>)}</div></div>
      <form className={styles.form} onSubmit={(e) => { e.preventDefault(); const s = txt.trim(); if (s) { dispatch({ type: 'ADD_TASK', text: s }); setTxt(''); } }}>
        <input className={styles.input} value={txt} onChange={(e) => setTxt(e.target.value)} placeholder="New task..." />
        <button className={styles.button} type="submit">Add</button>
      </form>
      <div className={styles.kanban}>
        {([['todo', 'Todo'], ['inProgress', 'In Progress'], ['done', 'Done']] as [ColumnKey, string][]).map(([k, t]) => (
          <ColumnPanel key={k} colKey={k} title={t} ids={state.lists[k]} tasks={state.tasks} dispatch={dispatch} />
        ))}
      </div>
      <ConflictToast msgs={state.conflictMessages} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default KanbanBoard;
