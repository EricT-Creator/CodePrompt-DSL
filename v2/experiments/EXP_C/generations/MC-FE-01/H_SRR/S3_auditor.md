## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript types (interfaces, type aliases) and imports from "react"
- C2 [Y]CSS_MODULES [!Y]NO_TW: FAIL — No CSS Modules (`.module.css`) used; styles are inline `React.CSSProperties` objects (`const styles: Record<string, React.CSSProperties>`), not CSS Modules. No Tailwind present (PASS on `!Y`).
- C3 [!D]NO_DND_LIB [DRAG]HTML5: PASS — No drag-and-drop library imported; uses native HTML5 drag API (`draggable`, `onDragStart`, `onDragOver`, `onDrop`, `e.dataTransfer`)
- C4 [STATE]useReducer: PASS — State managed via `useReducer(boardReducer, initialState)` at line 427
- C5 [O]SFC [EXP]DEFAULT: PASS — Single `const TodoBoard: React.FC` component with `export default TodoBoard`
- C6 [WS]MOCK [!D]NO_SOCKETIO: PASS — Uses custom `MockWebSocket` class with `setInterval`-based simulation; no socket.io imported

## Functionality Assessment (0-5)
Score: 4 — Fully functional Kanban board with drag-and-drop, real-time mock WebSocket events, conflict detection/resolution modal, task creation, and online user display. Minor gap: drop zone visual feedback (`dropZoneActive` style defined but never conditionally applied).

## Corrected Code
```tsx
import React, { useReducer, useEffect, useRef, useCallback } from "react";
import boardStyles from "./TodoBoard.module.css";

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
    <div className={boardStyles.board}>
      {/* Header */}
      <div className={boardStyles.header}>
        <h2 className={boardStyles.headerTitle}>Collaborative Kanban</h2>
        <div>
          <span className={boardStyles.statusDot} style={{ background: state.connected ? "#4caf50" : "#f44336" }} />
          <span style={{ fontSize: 12 }}>{state.connected ? "Connected" : "Offline"}</span>
          {state.users.map((u) => (
            <span key={u.id} className={boardStyles.userBadge} style={{ background: u.color, opacity: u.online ? 1 : 0.4 }}>
              {u.name}
            </span>
          ))}
        </div>
      </div>

      {/* Columns */}
      <div className={boardStyles.columns}>
        {(["todo", "inProgress", "done"] as ColumnId[]).map((col) => (
          <div
            key={col}
            className={boardStyles.column}
            onDragOver={(e) => handleDragOver(e, col)}
            onDrop={(e) => handleDrop(e, col)}
          >
            <div className={boardStyles.columnHeader}>
              <span>{COLUMN_LABELS[col]}</span>
              <span style={{ fontSize: 12, fontWeight: 400 }}>{columnTasks(col).length}</span>
            </div>

            {columnTasks(col).map((task) => (
              <div
                key={task.id}
                draggable
                onDragStart={(e) => handleDragStart(e, task.id, col)}
                onDragEnd={handleDragEnd}
                className={`${boardStyles.card} ${state.draggingTask?.taskId === task.id ? boardStyles.cardDragging : ""}`}
              >
                <div className={boardStyles.cardTitle}>{task.title}</div>
                {task.description && <div className={boardStyles.cardDesc}>{task.description}</div>}
                <span className={boardStyles.badge} style={{ background: PRIORITY_COLORS[task.priority], color: "#fff" }}>
                  {task.priority}
                </span>
                <span style={{ float: "right", fontSize: 11, color: "#999" }}>{task.assignee}</span>
              </div>
            ))}

            {/* Drop zone visual */}
            <div className={boardStyles.dropZone} />

            {/* Add task */}
            {state.newTaskColumn === col ? (
              <div>
                <input
                  autoFocus
                  className={boardStyles.input}
                  placeholder="Task title…"
                  value={state.newTaskTitle}
                  onChange={(e) => dispatch({ type: "SET_NEW_TASK_TITLE", payload: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddTask(col);
                    if (e.key === "Escape") dispatch({ type: "SHOW_ADD_TASK", payload: null });
                  }}
                />
                <button className={`${boardStyles.modalBtn} ${boardStyles.modalBtnPrimary}`} onClick={() => handleAddTask(col)}>
                  Add
                </button>
                <button className={`${boardStyles.modalBtn} ${boardStyles.modalBtnSecondary}`} onClick={() => dispatch({ type: "SHOW_ADD_TASK", payload: null })}>
                  Cancel
                </button>
              </div>
            ) : (
              <button className={boardStyles.addBtn} onClick={() => dispatch({ type: "SHOW_ADD_TASK", payload: col })}>
                + Add Task
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Conflict Modal */}
      {state.showConflictModal && state.conflicts.length > 0 && (
        <div className={boardStyles.modal}>
          <div className={boardStyles.modalContent}>
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
                      className={`${boardStyles.modalBtn} ${boardStyles.modalBtnPrimary}`}
                      onClick={() => dispatch({ type: "CONFLICT_RESOLVED", payload: { taskId: c.taskId, resolution: "keep_local" } })}
                    >
                      Keep Mine
                    </button>
                    <button
                      className={`${boardStyles.modalBtn} ${boardStyles.modalBtnWarning}`}
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
```
