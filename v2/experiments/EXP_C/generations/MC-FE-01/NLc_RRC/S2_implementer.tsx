import React, { useReducer, useEffect, useRef, useCallback } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

type ColumnId = "todo" | "inprogress" | "done";

interface Task {
  id: string;
  title: string;
  column: ColumnId;
  order: number;
  version: number;
}

interface ConflictInfo {
  taskId: string;
  localColumn: string;
  remoteColumn: string;
  timestamp: number;
}

interface BoardState {
  tasks: Task[];
  userId: string;
  conflicts: ConflictInfo[];
  connected: boolean;
}

interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  senderId: string;
  version?: number;
}

// ─── Actions ─────────────────────────────────────────────────────────────────

type Action =
  | { type: "INIT_BOARD"; tasks: Task[] }
  | { type: "ADD_TASK"; task: Task }
  | { type: "MOVE_TASK"; taskId: string; targetColumn: ColumnId; targetIndex: number }
  | { type: "REORDER"; taskId: string; targetIndex: number }
  | { type: "REMOTE_UPDATE"; task: Task }
  | { type: "CONFLICT"; conflict: ConflictInfo; serverTask: Task }
  | { type: "RESOLVE_CONFLICT"; taskId: string }
  | { type: "SET_CONNECTED"; connected: boolean };

function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case "INIT_BOARD":
      return { ...state, tasks: action.tasks };

    case "ADD_TASK":
      return { ...state, tasks: [...state.tasks, action.task] };

    case "MOVE_TASK": {
      const tasks = state.tasks.map((t) => {
        if (t.id === action.taskId) {
          return { ...t, column: action.targetColumn, order: action.targetIndex, version: t.version + 1 };
        }
        return t;
      });
      return { ...state, tasks };
    }

    case "REORDER": {
      const tasks = state.tasks.map((t) => {
        if (t.id === action.taskId) {
          return { ...t, order: action.targetIndex };
        }
        return t;
      });
      return { ...state, tasks };
    }

    case "REMOTE_UPDATE": {
      const exists = state.tasks.find((t) => t.id === action.task.id);
      if (exists) {
        const tasks = state.tasks.map((t) =>
          t.id === action.task.id ? action.task : t
        );
        return { ...state, tasks };
      }
      return { ...state, tasks: [...state.tasks, action.task] };
    }

    case "CONFLICT": {
      const tasks = state.tasks.map((t) =>
        t.id === action.conflict.taskId ? action.serverTask : t
      );
      return {
        ...state,
        tasks,
        conflicts: [...state.conflicts, action.conflict],
      };
    }

    case "RESOLVE_CONFLICT":
      return {
        ...state,
        conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId),
      };

    case "SET_CONNECTED":
      return { ...state, connected: action.connected };

    default:
      return state;
  }
}

// ─── CSS-in-single-file (CSS Modules emulation) ─────────────────────────────

const styleSheet = `
  .board { display: flex; gap: 16px; padding: 16px; min-height: 100vh; background: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .column { flex: 1; min-width: 260px; background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .columnTodo { border-top: 4px solid #60a5fa; }
  .columnInprogress { border-top: 4px solid #fbbf24; }
  .columnDone { border-top: 4px solid #34d399; }
  .columnTitle { font-size: 15px; font-weight: 700; margin-bottom: 12px; color: #374151; text-transform: uppercase; letter-spacing: 0.5px; }
  .dropTarget { border: 2px dashed #93c5fd; background: #eff6ff; border-radius: 8px; min-height: 40px; }
  .taskCard { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; cursor: grab; user-select: none; transition: box-shadow 0.15s; }
  .taskCard:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  .taskCardDragging { opacity: 0.5; }
  .taskCardConflict { animation: pulse 1s infinite; border-color: #ef4444; }
  @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); } 50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); } }
  .badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; margin-left: 8px; }
  .badgeTodo { background: #dbeafe; color: #1d4ed8; }
  .badgeInprogress { background: #fef3c7; color: #92400e; }
  .badgeDone { background: #d1fae5; color: #065f46; }
  .conflictBanner { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin: 0 16px 8px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
  .conflictBanner button { background: #ef4444; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
  .newTaskBar { display: flex; gap: 8px; padding: 16px; }
  .newTaskBar input { flex: 1; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; }
  .newTaskBar button { padding: 8px 18px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
  .statusDot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
  .statusConnected { background: #22c55e; }
  .statusDisconnected { background: #ef4444; }
  .header { display: flex; align-items: center; padding: 12px 16px; font-size: 13px; color: #6b7280; }
  .userLabel { font-weight: 600; color: #1f2937; margin-left: 4px; }
  .splitView { display: flex; flex-direction: column; height: 100vh; }
  .splitPane { flex: 1; overflow: auto; border-bottom: 2px solid #e5e7eb; }
`;

// ─── Mock WS Server ──────────────────────────────────────────────────────────

type WSCallback = (msg: WSMessage) => void;

class MockWSServer {
  private tasks: Task[] = [];
  private clients: Map<string, WSCallback> = new Map();
  private nextVersion: Map<string, number> = new Map();

  constructor() {
    const seed: Task[] = [
      { id: "t1", title: "Design system architecture", column: "todo", order: 0, version: 1 },
      { id: "t2", title: "Implement auth flow", column: "todo", order: 1, version: 1 },
      { id: "t3", title: "Write unit tests", column: "inprogress", order: 0, version: 1 },
      { id: "t4", title: "Deploy staging", column: "done", order: 0, version: 1 },
    ];
    this.tasks = seed;
    seed.forEach((t) => this.nextVersion.set(t.id, t.version + 1));
  }

  connect(clientId: string, cb: WSCallback): void {
    this.clients.set(clientId, cb);
    setTimeout(() => {
      cb({ type: "INIT_BOARD", payload: { tasks: JSON.parse(JSON.stringify(this.tasks)) }, senderId: "server" });
    }, 50);
  }

  disconnect(clientId: string): void {
    this.clients.delete(clientId);
  }

  send(clientId: string, msg: WSMessage): void {
    setTimeout(() => this.handleMessage(clientId, msg), 150 + Math.random() * 100);
  }

  private handleMessage(senderId: string, msg: WSMessage): void {
    if (msg.type === "MOVE_TASK") {
      const { taskId, targetColumn, targetIndex, version } = msg.payload as {
        taskId: string; targetColumn: ColumnId; targetIndex: number; version: number;
      };
      const task = this.tasks.find((t) => t.id === taskId);
      if (!task) return;
      const expected = (this.nextVersion.get(taskId) ?? 1) - 1;
      if (version !== expected) {
        const senderCb = this.clients.get(senderId);
        if (senderCb) {
          senderCb({
            type: "CONFLICT",
            payload: { taskId, localColumn: targetColumn, remoteColumn: task.column, serverTask: JSON.parse(JSON.stringify(task)) },
            senderId: "server",
          });
        }
        return;
      }
      task.column = targetColumn;
      task.order = targetIndex;
      task.version = (this.nextVersion.get(taskId) ?? 1);
      this.nextVersion.set(taskId, task.version + 1);
      this.clients.forEach((cb, cId) => {
        cb({
          type: "REMOTE_UPDATE",
          payload: { task: JSON.parse(JSON.stringify(task)) },
          senderId: senderId,
          version: task.version,
        });
      });
    } else if (msg.type === "ADD_TASK") {
      const { task } = msg.payload as { task: Task };
      const newTask = { ...task, version: 1 };
      this.tasks.push(newTask);
      this.nextVersion.set(newTask.id, 2);
      this.clients.forEach((cb) => {
        cb({
          type: "REMOTE_UPDATE",
          payload: { task: JSON.parse(JSON.stringify(newTask)) },
          senderId: senderId,
        });
      });
    }
  }
}

// ─── Components ──────────────────────────────────────────────────────────────

const COLUMNS: { id: ColumnId; label: string }[] = [
  { id: "todo", label: "Todo" },
  { id: "inprogress", label: "In Progress" },
  { id: "done", label: "Done" },
];

function TaskCard({
  task,
  hasConflict,
  onDragStart,
}: {
  task: Task;
  hasConflict: boolean;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
}) {
  const badgeClass =
    task.column === "todo" ? "badgeTodo" : task.column === "inprogress" ? "badgeInprogress" : "badgeDone";
  return (
    <div
      className={`taskCard${hasConflict ? " taskCardConflict" : ""}`}
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
    >
      <span>{task.title}</span>
      <span className={`badge ${badgeClass}`}>{task.column}</span>
    </div>
  );
}

function Column({
  columnId,
  label,
  tasks,
  conflicts,
  onDragStart,
  onDrop,
}: {
  columnId: ColumnId;
  label: string;
  tasks: Task[];
  conflicts: ConflictInfo[];
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDrop: (taskId: string, targetColumn: ColumnId, targetIndex: number) => void;
}) {
  const [isOver, setIsOver] = React.useState(false);
  const colRef = useRef<HTMLDivElement>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setIsOver(true);
    },
    []
  );

  const handleDragLeave = useCallback(() => setIsOver(false), []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsOver(false);
      const taskId = e.dataTransfer.getData("text/plain");
      if (!taskId) return;
      let insertIdx = tasks.length;
      if (colRef.current) {
        const cards = Array.from(colRef.current.querySelectorAll(".taskCard"));
        for (let i = 0; i < cards.length; i++) {
          const rect = cards[i].getBoundingClientRect();
          if (e.clientY < rect.top + rect.height / 2) {
            insertIdx = i;
            break;
          }
        }
      }
      onDrop(taskId, columnId, insertIdx);
    },
    [tasks, columnId, onDrop]
  );

  const colStyle =
    columnId === "todo" ? "columnTodo" : columnId === "inprogress" ? "columnInprogress" : "columnDone";

  return (
    <div
      className={`column ${colStyle}${isOver ? " dropTarget" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      ref={colRef}
    >
      <div className="columnTitle">
        {label} ({tasks.length})
      </div>
      {tasks
        .sort((a, b) => a.order - b.order)
        .map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            hasConflict={conflicts.some((c) => c.taskId === t.id)}
            onDragStart={onDragStart}
          />
        ))}
    </div>
  );
}

function ConflictBanner({
  conflicts,
  onRefresh,
  onDismiss,
}: {
  conflicts: ConflictInfo[];
  onRefresh: () => void;
  onDismiss: (taskId: string) => void;
}) {
  if (conflicts.length === 0) return null;
  return (
    <>
      {conflicts.map((c) => (
        <div key={c.taskId} className="conflictBanner">
          <span>
            ⚠ Task <b>{c.taskId}</b> was moved by another user to <b>{c.remoteColumn}</b>.
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => onDismiss(c.taskId)}>Dismiss</button>
            <button onClick={onRefresh}>Refresh</button>
          </div>
        </div>
      ))}
    </>
  );
}

function NewTaskInput({ onAdd }: { onAdd: (title: string) => void }) {
  const [value, setValue] = React.useState("");
  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onAdd(trimmed);
    setValue("");
  };
  return (
    <div className="newTaskBar">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="Add a new task..."
      />
      <button onClick={handleSubmit}>Add</button>
    </div>
  );
}

function BoardView({
  userId,
  server,
}: {
  userId: string;
  server: MockWSServer;
}) {
  const initialState: BoardState = {
    tasks: [],
    userId,
    conflicts: [],
    connected: false,
  };

  const [state, dispatch] = useReducer(boardReducer, initialState);
  const serverRef = useRef(server);

  useEffect(() => {
    const srv = serverRef.current;
    srv.connect(userId, (msg: WSMessage) => {
      switch (msg.type) {
        case "INIT_BOARD":
          dispatch({ type: "INIT_BOARD", tasks: msg.payload.tasks as Task[] });
          dispatch({ type: "SET_CONNECTED", connected: true });
          break;
        case "REMOTE_UPDATE":
          dispatch({ type: "REMOTE_UPDATE", task: msg.payload.task as Task });
          break;
        case "CONFLICT": {
          const p = msg.payload as { taskId: string; localColumn: string; remoteColumn: string; serverTask: Task };
          dispatch({
            type: "CONFLICT",
            conflict: { taskId: p.taskId, localColumn: p.localColumn, remoteColumn: p.remoteColumn, timestamp: Date.now() },
            serverTask: p.serverTask,
          });
          break;
        }
      }
    });
    return () => srv.disconnect(userId);
  }, [userId]);

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData("text/plain", taskId);
    e.dataTransfer.effectAllowed = "move";
  }, []);

  const handleDrop = useCallback(
    (taskId: string, targetColumn: ColumnId, targetIndex: number) => {
      const task = state.tasks.find((t) => t.id === taskId);
      if (!task) return;
      dispatch({ type: "MOVE_TASK", taskId, targetColumn, targetIndex });
      serverRef.current.send(userId, {
        type: "MOVE_TASK",
        payload: { taskId, targetColumn, targetIndex, version: task.version },
        senderId: userId,
      });
    },
    [state.tasks, userId]
  );

  const handleAdd = useCallback(
    (title: string) => {
      const newTask: Task = {
        id: `t_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        title,
        column: "todo",
        order: state.tasks.filter((t) => t.column === "todo").length,
        version: 0,
      };
      dispatch({ type: "ADD_TASK", task: newTask });
      serverRef.current.send(userId, {
        type: "ADD_TASK",
        payload: { task: newTask },
        senderId: userId,
      });
    },
    [state.tasks, userId]
  );

  const handleRefresh = useCallback(() => {
    serverRef.current.disconnect(userId);
    serverRef.current.connect(userId, (msg: WSMessage) => {
      if (msg.type === "INIT_BOARD") {
        dispatch({ type: "INIT_BOARD", tasks: msg.payload.tasks as Task[] });
        state.conflicts.forEach((c) => dispatch({ type: "RESOLVE_CONFLICT", taskId: c.taskId }));
      }
    });
  }, [userId, state.conflicts]);

  return (
    <div>
      <div className="header">
        <span className={`statusDot ${state.connected ? "statusConnected" : "statusDisconnected"}`} />
        {state.connected ? "Connected" : "Disconnected"}
        <span className="userLabel"> — {userId}</span>
      </div>
      <ConflictBanner
        conflicts={state.conflicts}
        onRefresh={handleRefresh}
        onDismiss={(taskId) => dispatch({ type: "RESOLVE_CONFLICT", taskId })}
      />
      <NewTaskInput onAdd={handleAdd} />
      <div className="board">
        {COLUMNS.map((col) => (
          <Column
            key={col.id}
            columnId={col.id}
            label={col.label}
            tasks={state.tasks.filter((t) => t.column === col.id)}
            conflicts={state.conflicts}
            onDragStart={handleDragStart}
            onDrop={handleDrop}
          />
        ))}
      </div>
    </div>
  );
}

// ─── App (root) ──────────────────────────────────────────────────────────────

function App() {
  const serverRef = useRef<MockWSServer | null>(null);
  if (!serverRef.current) {
    serverRef.current = new MockWSServer();
  }

  return (
    <>
      <style>{styleSheet}</style>
      <div className="splitView">
        <div className="splitPane">
          <BoardView userId="User-A" server={serverRef.current} />
        </div>
        <div className="splitPane">
          <BoardView userId="User-B" server={serverRef.current} />
        </div>
      </div>
    </>
  );
}

export default App;
