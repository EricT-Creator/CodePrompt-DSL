import React, { useReducer, useEffect, useCallback, useRef } from "react";

// ── CSS Modules (inline object approach for single-file) ──────────────
const css = `
  .board { display:flex; gap:16px; padding:24px; font-family:system-ui,sans-serif; min-height:100vh; background:#f0f2f5; }
  .column { flex:1; background:#fff; border-radius:12px; padding:16px; min-width:260px; box-shadow:0 1px 3px rgba(0,0,0,.1); display:flex; flex-direction:column; }
  .columnHeader { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
  .columnTitle { font-size:16px; font-weight:700; color:#333; }
  .badge { background:#e8eaed; border-radius:12px; padding:2px 8px; font-size:12px; color:#666; }
  .card { background:#fff; border:1px solid #e0e0e0; border-radius:8px; padding:12px; margin-bottom:8px; cursor:grab; transition:box-shadow .15s,transform .15s; }
  .card:active { cursor:grabbing; }
  .cardDragging { opacity:.5; transform:scale(.97); }
  .cardTitle { font-size:14px; font-weight:600; color:#333; margin-bottom:4px; }
  .cardDesc { font-size:12px; color:#888; margin-bottom:8px; }
  .cardMeta { display:flex; justify-content:space-between; align-items:center; font-size:11px; color:#aaa; }
  .cardActions { display:flex; gap:4px; }
  .actionBtn { background:none; border:none; cursor:pointer; font-size:12px; color:#999; padding:2px 6px; border-radius:4px; }
  .actionBtn:hover { background:#f0f0f0; color:#333; }
  .dropZone { min-height:40px; border:2px dashed transparent; border-radius:8px; transition:border-color .15s,background .15s; flex:1; }
  .dropZoneActive { border-color:#4a90d9; background:#e8f0fe; }
  .formContainer { margin-bottom:12px; }
  .formInput { width:100%; padding:8px 10px; border:1px solid #ddd; border-radius:6px; font-size:13px; margin-bottom:6px; box-sizing:border-box; }
  .formBtn { width:100%; padding:8px; background:#4a90d9; color:#fff; border:none; border-radius:6px; font-size:13px; cursor:pointer; font-weight:600; }
  .formBtn:hover { background:#3a7bc8; }
  .conflict { background:#fff3cd; border:1px solid #ffc107; border-radius:8px; padding:10px; margin-bottom:8px; font-size:12px; }
  .conflictTitle { font-weight:700; color:#856404; margin-bottom:4px; }
  .conflictBtn { padding:4px 10px; border:none; border-radius:4px; cursor:pointer; font-size:11px; margin-right:4px; }
  .conflictKeep { background:#28a745; color:#fff; }
  .conflictUseRemote { background:#dc3545; color:#fff; }
  .syncIndicator { text-align:center; padding:4px; font-size:11px; color:#888; }
`;

// ── Types ──────────────────────────────────────────────────────────────
type ColumnId = "todo" | "inProgress" | "done";

interface Task {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
  position: number;
  createdAt: number;
  updatedAt: number;
  createdBy: string;
  version: number;
}

interface Conflict {
  taskId: string;
  localVersion: number;
  remoteVersion: number;
  resolved: boolean;
}

interface PendingOp {
  type: "create" | "move" | "update" | "delete";
  taskId: string;
  timestamp: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columns: { id: ColumnId; title: string }[];
  lastSyncTime: number;
  pendingOps: PendingOp[];
  conflicts: Conflict[];
  syncStatus: "idle" | "syncing";
}

type Action =
  | { type: "ADD_TASK"; payload: { title: string; description: string } }
  | { type: "MOVE_TASK"; payload: { taskId: string; targetColumn: ColumnId } }
  | { type: "DELETE_TASK"; payload: string }
  | { type: "SYNC_START" }
  | { type: "SYNC_SUCCESS"; payload: { time: number } }
  | { type: "SYNC_CONFLICT"; payload: Conflict }
  | { type: "RESOLVE_CONFLICT"; payload: { taskId: string; keepLocal: boolean } };

// ── Helpers ────────────────────────────────────────────────────────────
let idCounter = 0;
const uid = (): string => `task_${Date.now()}_${++idCounter}`;

const COLUMNS: { id: ColumnId; title: string }[] = [
  { id: "todo", title: "Todo" },
  { id: "inProgress", title: "In Progress" },
  { id: "done", title: "Done" },
];

const SEED_TASKS: Task[] = [
  { id: uid(), title: "Setup project", description: "Initialize repo", columnId: "todo", position: 0, createdAt: Date.now(), updatedAt: Date.now(), createdBy: "userA", version: 1 },
  { id: uid(), title: "Design UI", description: "Create wireframes", columnId: "todo", position: 1, createdAt: Date.now(), updatedAt: Date.now(), createdBy: "userB", version: 1 },
  { id: uid(), title: "Write tests", description: "Unit tests", columnId: "inProgress", position: 0, createdAt: Date.now(), updatedAt: Date.now(), createdBy: "userA", version: 1 },
  { id: uid(), title: "Deploy", description: "CI/CD pipeline", columnId: "done", position: 0, createdAt: Date.now(), updatedAt: Date.now(), createdBy: "userB", version: 1 },
];

const seedMap: Record<string, Task> = {};
SEED_TASKS.forEach((t) => { seedMap[t.id] = t; });

const initialState: BoardState = {
  tasks: seedMap,
  columns: COLUMNS,
  lastSyncTime: Date.now(),
  pendingOps: [],
  conflicts: [],
  syncStatus: "idle",
};

// ── Reducer ────────────────────────────────────────────────────────────
function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case "ADD_TASK": {
      const id = uid();
      const columnTasks = Object.values(state.tasks).filter((t) => t.columnId === "todo");
      const task: Task = {
        id,
        title: action.payload.title,
        description: action.payload.description,
        columnId: "todo",
        position: columnTasks.length,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        createdBy: "localUser",
        version: 1,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: task },
        pendingOps: [...state.pendingOps, { type: "create", taskId: id, timestamp: Date.now() }],
      };
    }
    case "MOVE_TASK": {
      const { taskId, targetColumn } = action.payload;
      const t = state.tasks[taskId];
      if (!t || t.columnId === targetColumn) return state;
      const updated: Task = { ...t, columnId: targetColumn, updatedAt: Date.now(), version: t.version + 1 };
      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updated },
        pendingOps: [...state.pendingOps, { type: "move", taskId, timestamp: Date.now() }],
      };
    }
    case "DELETE_TASK": {
      const copy = { ...state.tasks };
      delete copy[action.payload];
      return {
        ...state,
        tasks: copy,
        pendingOps: [...state.pendingOps, { type: "delete", taskId: action.payload, timestamp: Date.now() }],
      };
    }
    case "SYNC_START":
      return { ...state, syncStatus: "syncing" };
    case "SYNC_SUCCESS":
      return { ...state, syncStatus: "idle", lastSyncTime: action.payload.time, pendingOps: [] };
    case "SYNC_CONFLICT":
      return { ...state, conflicts: [...state.conflicts, action.payload] };
    case "RESOLVE_CONFLICT": {
      const { taskId, keepLocal } = action.payload;
      const conflicts = state.conflicts.map((c) =>
        c.taskId === taskId ? { ...c, resolved: true } : c
      );
      if (!keepLocal) {
        const t = state.tasks[taskId];
        if (t) {
          const reverted: Task = { ...t, version: t.version + 1, updatedAt: Date.now() };
          return { ...state, conflicts, tasks: { ...state.tasks, [taskId]: reverted } };
        }
      }
      return { ...state, conflicts };
    }
    default:
      return state;
  }
}

// ── Sub-components ─────────────────────────────────────────────────────
const TaskCard = React.memo(function TaskCard({
  task,
  onDelete,
}: {
  task: Task;
  onDelete: (id: string) => void;
}) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("text/plain", task.id);
    e.dataTransfer.effectAllowed = "move";
    (e.currentTarget as HTMLElement).classList.add("cardDragging");
  };
  const handleDragEnd = (e: React.DragEvent) => {
    (e.currentTarget as HTMLElement).classList.remove("cardDragging");
  };
  return (
    <div className="card" draggable onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="cardTitle">{task.title}</div>
      <div className="cardDesc">{task.description}</div>
      <div className="cardMeta">
        <span>v{task.version} · {task.createdBy}</span>
        <div className="cardActions">
          <button className="actionBtn" onClick={() => onDelete(task.id)}>✕</button>
        </div>
      </div>
    </div>
  );
});

function ConflictIndicator({
  conflict,
  onResolve,
}: {
  conflict: Conflict;
  onResolve: (taskId: string, keepLocal: boolean) => void;
}) {
  if (conflict.resolved) return null;
  return (
    <div className="conflict">
      <div className="conflictTitle">⚠ Sync Conflict</div>
      <div>Local v{conflict.localVersion} vs Remote v{conflict.remoteVersion}</div>
      <div style={{ marginTop: 6 }}>
        <button className="conflictBtn conflictKeep" onClick={() => onResolve(conflict.taskId, true)}>Keep Local</button>
        <button className="conflictBtn conflictUseRemote" onClick={() => onResolve(conflict.taskId, false)}>Use Remote</button>
      </div>
    </div>
  );
}

function TaskForm({ onAdd }: { onAdd: (title: string, desc: string) => void }) {
  const [open, setOpen] = React.useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const descRef = useRef<HTMLInputElement>(null);
  const submit = () => {
    const title = titleRef.current?.value.trim();
    if (!title) return;
    onAdd(title, descRef.current?.value.trim() || "");
    if (titleRef.current) titleRef.current.value = "";
    if (descRef.current) descRef.current.value = "";
    setOpen(false);
  };
  if (!open) return <button className="formBtn" onClick={() => setOpen(true)}>+ Add Task</button>;
  return (
    <div className="formContainer">
      <input ref={titleRef} className="formInput" placeholder="Title" autoFocus />
      <input ref={descRef} className="formInput" placeholder="Description" />
      <button className="formBtn" onClick={submit}>Add</button>
    </div>
  );
}

function Column({
  col,
  tasks,
  conflicts,
  onDrop,
  onDelete,
  onResolve,
  onAdd,
}: {
  col: { id: ColumnId; title: string };
  tasks: Task[];
  conflicts: Conflict[];
  onDrop: (taskId: string, target: ColumnId) => void;
  onDelete: (id: string) => void;
  onResolve: (taskId: string, keepLocal: boolean) => void;
  onAdd: (title: string, desc: string) => void;
}) {
  const [over, setOver] = React.useState(false);
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; };
  const handleDragEnter = (e: React.DragEvent) => { e.preventDefault(); setOver(true); };
  const handleDragLeave = () => setOver(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setOver(false);
    const taskId = e.dataTransfer.getData("text/plain");
    if (taskId) onDrop(taskId, col.id);
  };
  return (
    <div className="column">
      <div className="columnHeader">
        <span className="columnTitle">{col.title}</span>
        <span className="badge">{tasks.length}</span>
      </div>
      {col.id === "todo" && <TaskForm onAdd={onAdd} />}
      {conflicts.filter((c) => !c.resolved).map((c) => (
        <ConflictIndicator key={c.taskId} conflict={c} onResolve={onResolve} />
      ))}
      <div
        className={`dropZone${over ? " dropZoneActive" : ""}`}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {tasks.map((t) => (
          <TaskCard key={t.id} task={t} onDelete={onDelete} />
        ))}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────
export default function TodoBoard() {
  const [state, dispatch] = useReducer(boardReducer, initialState);

  const onAdd = useCallback((title: string, desc: string) => {
    dispatch({ type: "ADD_TASK", payload: { title, description: desc } });
  }, []);
  const onDrop = useCallback((taskId: string, target: ColumnId) => {
    dispatch({ type: "MOVE_TASK", payload: { taskId, targetColumn: target } });
  }, []);
  const onDelete = useCallback((id: string) => {
    dispatch({ type: "DELETE_TASK", payload: id });
  }, []);
  const onResolve = useCallback((taskId: string, keepLocal: boolean) => {
    dispatch({ type: "RESOLVE_CONFLICT", payload: { taskId, keepLocal } });
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      dispatch({ type: "SYNC_START" });
      setTimeout(() => {
        if (Math.random() < 0.15) {
          const ids = Object.keys(state.tasks);
          if (ids.length > 0) {
            const randomId = ids[Math.floor(Math.random() * ids.length)];
            const t = state.tasks[randomId];
            if (t) {
              dispatch({
                type: "SYNC_CONFLICT",
                payload: { taskId: randomId, localVersion: t.version, remoteVersion: t.version + 1, resolved: false },
              });
            }
          }
        }
        dispatch({ type: "SYNC_SUCCESS", payload: { time: Date.now() } });
      }, 800);
    }, 5000);
    return () => clearInterval(interval);
  }, [state.tasks]);

  const tasksByColumn = (colId: ColumnId) =>
    Object.values(state.tasks)
      .filter((t) => t.columnId === colId)
      .sort((a, b) => a.position - b.position);

  const conflictsFor = (colId: ColumnId) =>
    state.conflicts.filter((c) => {
      const t = state.tasks[c.taskId];
      return t && t.columnId === colId;
    });

  return (
    <>
      <style>{css}</style>
      <div className="board">
        {state.columns.map((col) => (
          <Column
            key={col.id}
            col={col}
            tasks={tasksByColumn(col.id)}
            conflicts={conflictsFor(col.id)}
            onDrop={onDrop}
            onDelete={onDelete}
            onResolve={onResolve}
            onAdd={onAdd}
          />
        ))}
      </div>
      <div className="syncIndicator">
        {state.syncStatus === "syncing" ? "Syncing…" : `Last sync: ${new Date(state.lastSyncTime).toLocaleTimeString()}`}
      </div>
    </>
  );
}
