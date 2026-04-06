import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ── Types ────────────────────────────────────────────────────────────────

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
  | { type: 'MOVE_TASK'; taskId: string; to: ColumnId; pos: number }
  | { type: 'REORDER'; taskId: string; pos: number }
  | { type: 'INGEST_REMOTE'; taskMap: Record<string, Task>; columnLists: Record<ColumnId, string[]> }
  | { type: 'RAISE_CONFLICT'; evt: ConflictEvent }
  | { type: 'CLEAR_CONFLICT'; taskId: string }
  | { type: 'CONFIRM'; opId: string }
  | { type: 'REJECT'; opId: string };

function gid(): string { return Math.random().toString(36).slice(2, 10) + '-' + Date.now().toString(36); }

// ── Mock Server ──────────────────────────────────────────────────────────

const MockServer = {
  db: { tasks: {} as Record<string, Task>, cols: { todo: [] as string[], inProgress: [] as string[], done: [] as string[] } },
  log: [] as { opId: string; taskId: string; user: string; ts: number }[],
  bus: [] as BoardAction[],
};

function msPush(op: OpRecord, user: string) {
  const now = Date.now();
  const hit = MockServer.log.find((l) => l.taskId === op.taskId && now - l.ts < 2000 && l.user !== user);
  if (hit) MockServer.bus.push({ type: 'RAISE_CONFLICT', evt: { taskId: op.taskId, rivalUser: hit.user, detail: 'Concurrent edit' } });
  MockServer.log.push({ opId: op.id, taskId: op.taskId, user, ts: now });
  MockServer.bus.push({ type: 'CONFIRM', opId: op.id });
}

function msBot() {
  const ids = Object.keys(MockServer.db.tasks);
  if (!ids.length) return;
  const tid = ids[Math.floor(Math.random() * ids.length)];
  const t = MockServer.db.tasks[tid]; if (!t) return;
  const dst: ColumnId = (['todo', 'inProgress', 'done'] as ColumnId[]).filter((c) => c !== t.column)[Math.floor(Math.random() * 2)];
  MockServer.db.cols[t.column] = MockServer.db.cols[t.column].filter((x) => x !== tid);
  MockServer.db.cols[dst].push(tid);
  MockServer.db.tasks[tid] = { ...t, column: dst, lastActor: 'bot-peer', rev: t.rev + 1 };
  MockServer.log.push({ opId: gid(), taskId: tid, user: 'bot-peer', ts: Date.now() });
  MockServer.bus.push({ type: 'INGEST_REMOTE', taskMap: { ...MockServer.db.tasks }, columnLists: { ...MockServer.db.cols } });
}

function msDrain(): BoardAction[] { const r = [...MockServer.bus]; MockServer.bus = []; return r; }

// ── Reducer ──────────────────────────────────────────────────────────────

function boardReducer(st: BoardState, a: BoardAction): BoardState {
  switch (a.type) {
    case 'ADD_TASK': {
      const nid = gid();
      const task: Task = { id: nid, text: a.text, column: 'todo', sortIndex: 0, lastActor: st.userId, rev: 1 };
      const cols = { ...st.columnLists, todo: [nid, ...st.columnLists.todo] };
      MockServer.db.tasks[nid] = task; MockServer.db.cols = { ...cols };
      const op: OpRecord = { id: gid(), action: 'add', taskId: nid, timestamp: Date.now() };
      setTimeout(() => msPush(op, st.userId), 300 + Math.random() * 500);
      return { ...st, taskMap: { ...st.taskMap, [nid]: task }, columnLists: cols, inflightOps: [...st.inflightOps, op] };
    }
    case 'MOVE_TASK': {
      const { taskId, to, pos } = a;
      const t = st.taskMap[taskId]; if (!t) return st;
      const sl = st.columnLists[t.column].filter((x) => x !== taskId);
      const dl = t.column === to ? sl : [...st.columnLists[to]];
      if (t.column === to) sl.splice(pos, 0, taskId); else dl.splice(pos, 0, taskId);
      const ut = { ...t, column: to, lastActor: st.userId, rev: t.rev + 1 };
      const cols = { ...st.columnLists, [t.column]: sl, [to]: t.column === to ? sl : dl };
      MockServer.db.tasks[taskId] = ut; MockServer.db.cols = { ...cols };
      const op: OpRecord = { id: gid(), action: 'move', taskId, timestamp: Date.now() };
      setTimeout(() => msPush(op, st.userId), 300 + Math.random() * 500);
      return { ...st, taskMap: { ...st.taskMap, [taskId]: ut }, columnLists: cols, inflightOps: [...st.inflightOps, op] };
    }
    case 'REORDER': {
      const { taskId, pos } = a;
      const t = st.taskMap[taskId]; if (!t) return st;
      const l = st.columnLists[t.column].filter((x) => x !== taskId); l.splice(pos, 0, taskId);
      const cols = { ...st.columnLists, [t.column]: l };
      MockServer.db.cols = { ...cols };
      const op: OpRecord = { id: gid(), action: 'reorder', taskId, timestamp: Date.now() };
      setTimeout(() => msPush(op, st.userId), 300 + Math.random() * 500);
      return { ...st, columnLists: cols, inflightOps: [...st.inflightOps, op] };
    }
    case 'INGEST_REMOTE': return { ...st, taskMap: a.taskMap, columnLists: a.columnLists };
    case 'RAISE_CONFLICT': return { ...st, conflictQueue: [...st.conflictQueue, a.evt] };
    case 'CLEAR_CONFLICT': return { ...st, conflictQueue: st.conflictQueue.filter((c) => c.taskId !== a.taskId) };
    case 'CONFIRM': return { ...st, inflightOps: st.inflightOps.filter((o) => o.id !== a.opId) };
    case 'REJECT': return { ...st, inflightOps: st.inflightOps.filter((o) => o.id !== a.opId) };
    default: return st;
  }
}

const initState: BoardState = { taskMap: {}, columnLists: { todo: [], inProgress: [], done: [] }, userId: 'self-' + gid().slice(0, 4), peerIds: [], inflightOps: [], conflictQueue: [] };

// ── UI Components ────────────────────────────────────────────────────────

function Header({ user, peers }: { user: string; peers: string[] }) {
  return <div className={styles.header}><h1>Collaborative Todo Board</h1><div className={styles.users}><span>{user}</span>{peers.map((p) => <span key={p} className={styles.userBadge}>{p}</span>)}</div></div>;
}

function Card({ task, onStart }: { task: Task; onStart: (e: React.DragEvent, id: string) => void }) {
  const [d, sd] = useState(false);
  return <div className={`${styles.card} ${d ? styles.cardDragging : ''}`} draggable="true" onDragStart={(e) => { sd(true); onStart(e, task.id); }} onDragEnd={() => sd(false)}>
    <div className={styles.cardText}>{task.text}</div><div className={styles.cardMeta}>{task.lastActor} · v{task.rev}</div>
  </div>;
}

function CreateInput({ dispatch }: { dispatch: React.Dispatch<BoardAction> }) {
  const [v, sv] = useState('');
  return <form className={styles.taskCreator} onSubmit={(e) => { e.preventDefault(); if (v.trim()) { dispatch({ type: 'ADD_TASK', text: v.trim() }); sv(''); } }}>
    <input className={styles.taskInput} value={v} onChange={(e) => sv(e.target.value)} placeholder="New task..." /><button className={styles.addBtn} type="submit">+</button>
  </form>;
}

function Col({ cid, title, ids, tasks, dispatch }: { cid: ColumnId; title: string; ids: string[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  const ref = useRef<HTMLDivElement>(null);
  const over = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }, []);
  const drop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); const tid = e.dataTransfer.getData('text/plain');
    if (!tid || !tasks[tid]) return; let p = ids.length;
    if (ref.current) { const el = ref.current.querySelectorAll('[data-k]'); for (let i = 0; i < el.length; i++) { const r = el[i].getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) { p = i; break; } } }
    if (tasks[tid].column === cid) dispatch({ type: 'REORDER', taskId: tid, pos: p }); else dispatch({ type: 'MOVE_TASK', taskId: tid, to: cid, pos: p });
  }, [cid, ids, tasks, dispatch]);
  const ds = useCallback((e: React.DragEvent, id: string) => { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move'; }, []);
  return <div className={styles.column} onDragOver={over} onDrop={drop} ref={ref}>
    <h2 className={styles.columnTitle}>{title}</h2>{cid === 'todo' && <CreateInput dispatch={dispatch} />}
    <div className={styles.cardList}>{ids.map((i) => { const t = tasks[i]; return t ? <div key={i} data-k><Card task={t} onStart={ds} /></div> : null; })}</div>
  </div>;
}

function Popup({ items, tasks, dispatch }: { items: ConflictEvent[]; tasks: Record<string, Task>; dispatch: React.Dispatch<BoardAction> }) {
  if (!items.length) return null;
  return <div className={styles.conflictToast}>{items.map((c) => <div key={c.taskId} className={styles.conflictItem}>
    <span>Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; by {c.rivalUser}</span>
    <button onClick={() => dispatch({ type: 'CLEAR_CONFLICT', taskId: c.taskId })}>OK</button>
  </div>)}</div>;
}

// ── Root ─────────────────────────────────────────────────────────────────

const C: { id: ColumnId; t: string }[] = [{ id: 'todo', t: 'Todo' }, { id: 'inProgress', t: 'In Progress' }, { id: 'done', t: 'Done' }];

function App() {
  const [s, d] = useReducer(boardReducer, initState);
  useEffect(() => {
    const p = setInterval(() => msDrain().forEach((a) => d(a)), 500);
    const r = setInterval(() => setTimeout(msBot, Math.random() * 2500), 6000);
    return () => { clearInterval(p); clearInterval(r); };
  }, []);
  return <div className={styles.app}>
    <Header user={s.userId} peers={s.peerIds} />
    <div className={styles.board}>{C.map((c) => <Col key={c.id} cid={c.id} title={c.t} ids={s.columnLists[c.id]} tasks={s.taskMap} dispatch={d} />)}</div>
    <Popup items={s.conflictQueue} tasks={s.taskMap} dispatch={d} />
  </div>;
}

export default App;
