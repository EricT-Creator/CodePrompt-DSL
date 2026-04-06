import React, { useReducer, useEffect, useRef, useCallback } from "react";

// ── Types ──────────────────────────────────────────────────────────
type ColumnId = "todo" | "inProgress" | "done";
type Priority = "low" | "medium" | "high";

interface Task {
  id: string;
  title: string;
  description: string;
  column: ColumnId;
  position: number;
  assignee: string;
  priority: Priority;
  createdAt: string;
  updatedAt: string;
  version: number;
}

interface User {
  id: string;
  name: string;
  color: string;
  online: boolean;
}

interface Conflict {
  taskId: string;
  localVersion: number;
  remoteVersion: number;
  localChange: Partial<Task>;
  remoteChange: Partial<Task>;
  resolved: boolean;
}

interface WSEvent {
  type: "task_moved" | "task_created" | "task_updated" | "user_joined" | "user_left";
  payload: any;
  timestamp: string;
  userId: string;
}

interface BoardState {
  tasks: Task[];
  users: User[];
  draggingTask: { taskId: string; sourceColumn: ColumnId } | null;
  conflicts: Conflict[];
  showConflictModal: boolean;
  connected: boolean;
  newTaskColumn: ColumnId | null;
  newTaskTitle: string;
}

type BoardAction =
  | { type: "TASK_DRAG_START"; payload: { taskId: string; column: ColumnId } }
  | { type: "TASK_DRAG_END" }
  | { type: "TASK_DROP"; payload: { taskId: string; targetColumn: ColumnId; position: number } }
  | { type: "TASK_CREATE"; payload: { title: string; column: ColumnId } }
  | { type: "WS_EVENT"; payload: WSEvent }
  | { type: "CONFLICT_DETECTED"; payload: Conflict }
  | { type: "CONFLICT_RESOLVED"; payload: { taskId: string; resolution: "keep_local" | "use_remote" } }
  | { type: "SET_CONNECTED"; payload: boolean }
  | { type: "SHOW_ADD_TASK"; payload: ColumnId | null }
  | { type: "SET_NEW_TASK_TITLE"; payload: string };

// ── CSS Modules (inlined as objects for SFC) ─────────────────────
const styles: Record<string, React.CSSProperties> = {
  board: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: 1100,
    margin: "0 auto",
    padding: 16,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
    padding: "12px 16px",
    background: "#1a1a2e",
    color: "#fff",
    borderRadius: 8,
  },
  headerTitle: { margin: 0, fontSize: 20 },
  userBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    marginLeft: 8,
    padding: "2px 8px",
    borderRadius: 12,
    fontSize: 12,
    color: "#fff",
  },
  columns: {
    display: "flex",
    gap: 16,
  },
  column: {
    flex: 1,
    background: "#f0f2f5",
    borderRadius: 8,
    padding: 12,
    minHeight: 400,
  },
  columnHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
    fontWeight: 600,
    fontSize: 14,
    textTransform: "uppercase" as const,
    letterSpacing: 1,
    color: "#555",
  },
  card: {
    background: "#fff",
    borderRadius: 6,
    padding: 12,
    marginBottom: 8,
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
    cursor: "grab",
    transition: "box-shadow 0.15s",
  },
  cardDragging: {
    opacity: 0.5,
  },
  cardTitle: { fontWeight: 600, marginBottom: 4, fontSize: 14 },
  cardDesc: { color: "#666", fontSize: 12, marginBottom: 6 },
  badge: {
    display: "inline-block",
    padding: "1px 6px",
    borderRadius: 4,
    fontSize: 10,
    fontWeight: 600,
    textTransform: "uppercase" as const,
  },
  addBtn: {
    width: "100%",
    padding: "6px 0",
    background: "transparent",
    border: "2px dashed #ccc",
    borderRadius: 6,
    cursor: "pointer",
    color: "#888",
    fontSize: 13,
  },
  input: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #ccc",
    borderRadius: 4,
    marginBottom: 6,
    fontSize: 13,
    boxSizing: "border-box" as const,
  },
  dropZone: {
    minHeight: 40,
    borderRadius: 4,
    transition: "background 0.15s",
  },
  dropZoneActive: {
    background: "rgba(66,133,244,0.1)",
    border: "2px dashed #4285f4",
  },
  modal: {
    position: "fixed" as const,
    inset: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(0,0,0,0.4)",
    zIndex: 1000,
  },
  modalContent: {
    background: "#fff",
    borderRadius: 12,
    padding: 24,
    width: 400,
    maxWidth: "90vw",
  },
  modalBtn: {
    padding: "6px 16px",
    borderRadius: 4,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
    marginRight: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    display: "inline-block",
    marginRight: 4,
  },
};

const PRIORITY_COLORS: Record<Priority, string> = {
  low: "#4caf50",
  medium: "#ff9800",
  high: "#f44336",
};

const COLUMN_LABELS: Record<ColumnId, string> = {
  todo: "To Do",
  inProgress: "In Progress",
  done: "Done",
};

// ── Helpers ────────────────────────────────────────────────────────
let idCounter = 100;
const uid = (): string => `t_${++idCounter}_${Date.now()}`;
const now = (): string => new Date().toISOString();

// ── Mock WebSocket ─────────────────────────────────────────────────
class MockWebSocket {
  private listeners: Record<string, ((e: any) => void)[]> = {};
  private interval: ReturnType<typeof setInterval> | null = null;

  connect(onEvent: (evt: WSEvent) => void): void {
    this.interval = setInterval(() => {
      const rand = Math.random();
      if (rand < 0.15) {
        onEvent({
          type: "user_joined",
          payload: { id: "u_remote", name: "Alice", color: "#e91e63", online: true },
          timestamp: now(),
          userId: "u_remote",
        });
      } else if (rand < 0.25) {
        onEvent({
          type: "task_updated",
          payload: { taskId: "t_1", changes: { title: "Updated remotely" }, version: 99 },
          timestamp: now(),
          userId: "u_remote",
        });
      }
    }, 5000 + Math.random() * 5000);
  }

  send(_data: any): void {
    // simulate latency
  }

  disconnect(): void {
    if (this.interval) clearInterval(this.interval);
  }
}

// ── Initial state ──────────────────────────────────────────────────
const INITIAL_TASKS: Task[] = [
  { id: "t_1", title: "Design mockups", description: "Create UI wireframes", column: "todo", position: 0, assignee: "You", priority: "high", createdAt: now(), updatedAt: now(), version: 1 },
  { id: "t_2", title: "Setup CI/CD", description: "Configure pipelines", column: "todo", position: 1, assignee: "You", priority: "medium", createdAt: now(), updatedAt: now(), version: 1 },
  { id: "t_3", title: "Write tests", description: "Unit & integration", column: "inProgress", position: 0, assignee: "You", priority: "low", createdAt: now(), updatedAt: now(), version: 1 },
  { id: "t_4", title: "Deploy v1", description: "Push to staging", column: "done", position: 0, assignee: "You", priority: "medium", createdAt: now(), updatedAt: now(), version: 1 },
];

const INITIAL_USERS: User[] = [
  { id: "u_me", name: "You", color: "#4285f4", online: true },
];

const initialState: BoardState = {
  tasks: INITIAL_TASKS,
  users: INITIAL_USERS,
  draggingTask: null,
  conflicts: [],
  showConflictModal: false,
  connected: false,
  newTaskColumn: null,
  newTaskTitle: "",
};

// ── Reducer ────────────────────────────────────────────────────────
function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case "TASK_DRAG_START":
      return { ...state, draggingTask: { taskId: action.payload.taskId, sourceColumn: action.payload.column } };

    case "TASK_DRAG_END":
      return { ...state, draggingTask: null };

    case "TASK_DROP": {
      const { taskId, targetColumn, position } = action.payload;
      const tasks = state.tasks.map((t) =>
        t.id === taskId ? { ...t, column: targetColumn, position, updatedAt: now(), version: t.version + 1 } : t
      );
      return { ...state, tasks, draggingTask: null };
    }

    case "TASK_CREATE": {
      const maxPos = state.tasks.filter((t) => t.column === action.payload.column).length;
      const task: Task = {
        id: uid(),
        title: action.payload.title,
        description: "",
        column: action.payload.column,
        position: maxPos,
        assignee: "You",
        priority: "medium",
        createdAt: now(),
        updatedAt: now(),
        version: 1,
      };
      return { ...state, tasks: [...state.tasks, task], newTaskColumn: null, newTaskTitle: "" };
    }

    case "WS_EVENT": {
      const evt = action.payload;
      if (evt.type === "user_joined") {
        const u = evt.payload as User;
        const exists = state.users.some((x) => x.id === u.id);
        return exists ? state : { ...state, users: [...state.users, { ...u, online: true }] };
      }
      if (evt.type === "user_left") {
        return { ...state, users: state.users.map((u) => (u.id === evt.userId ? { ...u, online: false } : u)) };
      }
      if (evt.type === "task_updated") {
        const { taskId, changes, version } = evt.payload;
        const local = state.tasks.find((t) => t.id === taskId);
        if (local && local.version >= version) {
          const conflict: Conflict = {
            taskId,
            localVersion: local.version,
            remoteVersion: version,
            localChange: {},
            remoteChange: changes,
            resolved: false,
          };
          return { ...state, conflicts: [...state.conflicts, conflict], showConflictModal: true };
        }
        const tasks = state.tasks.map((t) => (t.id === taskId ? { ...t, ...changes, version } : t));
        return { ...state, tasks };
      }
      return state;
    }

    case "CONFLICT_DETECTED":
      return { ...state, conflicts: [...state.conflicts, action.payload], showConflictModal: true };

    case "CONFLICT_RESOLVED": {
      const { taskId, resolution } = action.payload;
      if (resolution === "use_remote") {
        const conflict = state.conflicts.find((c) => c.taskId === taskId);
        if (conflict) {
          const tasks = state.tasks.map((t) =>
            t.id === taskId ? { ...t, ...conflict.remoteChange, version: conflict.remoteVersion } : t
          );
          return { ...state, tasks, conflicts: state.conflicts.filter((c) => c.taskId !== taskId), showConflictModal: false };
        }
      }
      return { ...state, conflicts: state.conflicts.filter((c) => c.taskId !== taskId), showConflictModal: state.conflicts.length > 1 };
    }

    case "SET_CONNECTED":
      return { ...state, connected: action.payload };

    case "SHOW_ADD_TASK":
      return { ...state, newTaskColumn: action.payload, newTaskTitle: "" };

    case "SET_NEW_TASK_TITLE":
      return { ...state, newTaskTitle: action.payload };

    default:
      return state;
  }
}

// ── Component ──────────────────────────────────────────────────────
const TodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const wsRef = useRef<MockWebSocket | null>(null);
  const dragOverCol = useRef<ColumnId | null>(null);

  useEffect(() => {
    const ws = new MockWebSocket();
    wsRef.current = ws;
    ws.connect((evt) => dispatch({ type: "WS_EVENT", payload: evt }));
    dispatch({ type: "SET_CONNECTED", payload: true });
    return () => {
      ws.disconnect();
      dispatch({ type: "SET_CONNECTED", payload: false });
    };
  }, []);

  const handleDragStart = useCallback(
    (e: React.DragEvent<HTMLDivElement>, taskId: string, column: ColumnId) => {
      e.dataTransfer.setData("application/json", JSON.stringify({ taskId, column }));
      e.dataTransfer.effectAllowed = "move";
      dispatch({ type: "TASK_DRAG_START", payload: { taskId, column } });
    },
    []
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>, col: ColumnId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    dragOverCol.current = col;
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>, targetColumn: ColumnId) => {
      e.preventDefault();
      try {
        const data = JSON.parse(e.dataTransfer.getData("application/json"));
        const position = state.tasks.filter((t) => t.column === targetColumn).length;
        dispatch({ type: "TASK_DROP", payload: { taskId: data.taskId, targetColumn, position } });
        wsRef.current?.send({ type: "task_moved", taskId: data.taskId, targetColumn });
      } catch {
        // ignore
      }
      dragOverCol.current = null;
    },
    [state.tasks]
  );

  const handleDragEnd = useCallback(() => {
    dispatch({ type: "TASK_DRAG_END" });
    dragOverCol.current = null;
  }, []);

  const handleAddTask = useCallback(
    (column: ColumnId) => {
      if (state.newTaskTitle.trim()) {
        dispatch({ type: "TASK_CREATE", payload: { title: state.newTaskTitle.trim(), column } });
      }
    },
    [state.newTaskTitle]
  );

  const columnTasks = (col: ColumnId) =>
    state.tasks.filter((t) => t.column === col).sort((a, b) => a.position - b.position);

  return (
    <div style={styles.board}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.headerTitle}>Collaborative Kanban</h2>
        <div>
          <span style={{ ...styles.statusDot, background: state.connected ? "#4caf50" : "#f44336" }} />
          <span style={{ fontSize: 12 }}>{state.connected ? "Connected" : "Offline"}</span>
          {state.users.map((u) => (
            <span key={u.id} style={{ ...styles.userBadge, background: u.color, opacity: u.online ? 1 : 0.4 }}>
              {u.name}
            </span>
          ))}
        </div>
      </div>

      {/* Columns */}
      <div style={styles.columns}>
        {(["todo", "inProgress", "done"] as ColumnId[]).map((col) => (
          <div
            key={col}
            style={styles.column}
            onDragOver={(e) => handleDragOver(e, col)}
            onDrop={(e) => handleDrop(e, col)}
          >
            <div style={styles.columnHeader}>
              <span>{COLUMN_LABELS[col]}</span>
              <span style={{ fontSize: 12, fontWeight: 400 }}>{columnTasks(col).length}</span>
            </div>

            {columnTasks(col).map((task) => (
              <div
                key={task.id}
                draggable
                onDragStart={(e) => handleDragStart(e, task.id, col)}
                onDragEnd={handleDragEnd}
                style={{
                  ...styles.card,
                  ...(state.draggingTask?.taskId === task.id ? styles.cardDragging : {}),
                }}
              >
                <div style={styles.cardTitle}>{task.title}</div>
                {task.description && <div style={styles.cardDesc}>{task.description}</div>}
                <span style={{ ...styles.badge, background: PRIORITY_COLORS[task.priority], color: "#fff" }}>
                  {task.priority}
                </span>
                <span style={{ float: "right", fontSize: 11, color: "#999" }}>{task.assignee}</span>
              </div>
            ))}

            {/* Drop zone visual */}
            <div style={styles.dropZone} />

            {/* Add task */}
            {state.newTaskColumn === col ? (
              <div>
                <input
                  autoFocus
                  style={styles.input}
                  placeholder="Task title…"
                  value={state.newTaskTitle}
                  onChange={(e) => dispatch({ type: "SET_NEW_TASK_TITLE", payload: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddTask(col);
                    if (e.key === "Escape") dispatch({ type: "SHOW_ADD_TASK", payload: null });
                  }}
                />
                <button style={{ ...styles.modalBtn, background: "#4285f4", color: "#fff" }} onClick={() => handleAddTask(col)}>
                  Add
                </button>
                <button style={{ ...styles.modalBtn, background: "#eee" }} onClick={() => dispatch({ type: "SHOW_ADD_TASK", payload: null })}>
                  Cancel
                </button>
              </div>
            ) : (
              <button style={styles.addBtn} onClick={() => dispatch({ type: "SHOW_ADD_TASK", payload: col })}>
                + Add Task
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Conflict Modal */}
      {state.showConflictModal && state.conflicts.length > 0 && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h3 style={{ marginTop: 0 }}>Conflict Detected</h3>
            {state.conflicts
              .filter((c) => !c.resolved)
              .map((c) => {
                const task = state.tasks.find((t) => t.id === c.taskId);
                return (
                  <div key={c.taskId} style={{ marginBottom: 16 }}>
                    <p>
                      <strong>{task?.title ?? c.taskId}</strong> was modified by another user.
                    </p>
                    <p style={{ fontSize: 13, color: "#666" }}>
                      Local v{c.localVersion} vs Remote v{c.remoteVersion}
                    </p>
                    <button
                      style={{ ...styles.modalBtn, background: "#4285f4", color: "#fff" }}
                      onClick={() => dispatch({ type: "CONFLICT_RESOLVED", payload: { taskId: c.taskId, resolution: "keep_local" } })}
                    >
                      Keep Mine
                    </button>
                    <button
                      style={{ ...styles.modalBtn, background: "#ff9800", color: "#fff" }}
                      onClick={() => dispatch({ type: "CONFLICT_RESOLVED", payload: { taskId: c.taskId, resolution: "use_remote" } })}
                    >
                      Use Remote
                    </button>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
};

export default TodoBoard;
