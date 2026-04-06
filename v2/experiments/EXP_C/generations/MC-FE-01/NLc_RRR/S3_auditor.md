## Constraint Review
- C1 (TS + React): PASS — File uses React with TypeScript interfaces (Task, BoardState, Action) and typed hooks (useReducer, useRef, useCallback).
- C2 (CSS Modules, no Tailwind): FAIL — Styles are defined as inline `React.CSSProperties` objects (`const styles: Record<string, React.CSSProperties>`), not actual CSS Modules (`.module.css` imports).
- C3 (HTML5 Drag, no dnd libs): PASS — Uses native `draggable`, `onDragStart`, `onDragOver`, `onDrop` with `e.dataTransfer`; no dnd library imported.
- C4 (useReducer only): FAIL — `Column` component uses `React.useState(false)` for `isDragOver` (line ~508); `NewTaskInput` uses `React.useState("")` for input value (line ~583).
- C5 (Single file, export default): PASS — All code in one file, ends with `export default App`.
- C6 (Hand-written WS mock, no socket.io): PASS — `MockWSServer` class is fully hand-written with `connect`, `disconnect`, `send`, `broadcast` methods; no socket.io import.

## Functionality Assessment (0-5)
Score: 4 — Implements a real-time collaborative Kanban board with two user panels, drag-and-drop across columns, optimistic updates, conflict detection via version checking, conflict resolution UI, and task creation. The mock WS server simulates latency and broadcasts. Missing: no persistence, limited reorder logic within same column.

## Corrected Code
```tsx
import React, { useReducer, useEffect, useRef, useCallback } from "react";

// ---- Types ----

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

type Action =
  | { type: "INIT_BOARD"; tasks: Task[] }
  | { type: "ADD_TASK"; task: Task }
  | { type: "MOVE_TASK"; taskId: string; targetColumn: ColumnId; targetIndex: number }
  | { type: "REORDER"; taskId: string; targetIndex: number }
  | { type: "REMOTE_UPDATE"; task: Task }
  | { type: "CONFLICT"; conflict: ConflictInfo }
  | { type: "RESOLVE_CONFLICT"; taskId: string }
  | { type: "SET_CONNECTED"; connected: boolean }
  | { type: "SET_DRAG_OVER"; columnId: ColumnId; isDragOver: boolean }
  | { type: "SET_NEW_TASK_INPUT"; value: string };

// ---- CSS Module Simulation ----
// NOTE: In a real project this would be a .module.css file imported as `import styles from './App.module.css'`.
// Since the constraint requires single-file delivery, we use a <style> tag with class names to simulate CSS Modules.

const CLASS_PREFIX = "kb_";

const classNames = {
  app: `${CLASS_PREFIX}app`,
  header: `${CLASS_PREFIX}header`,
  title: `${CLASS_PREFIX}title`,
  connectionStatus: `${CLASS_PREFIX}connectionStatus`,
  board: `${CLASS_PREFIX}board`,
  column: `${CLASS_PREFIX}column`,
  columnHeader: `${CLASS_PREFIX}columnHeader`,
  taskCard: `${CLASS_PREFIX}taskCard`,
  taskTitle: `${CLASS_PREFIX}taskTitle`,
  badge: `${CLASS_PREFIX}badge`,
  dropTarget: `${CLASS_PREFIX}dropTarget`,
  conflictBanner: `${CLASS_PREFIX}conflictBanner`,
  newTaskContainer: `${CLASS_PREFIX}newTaskContainer`,
  input: `${CLASS_PREFIX}input`,
  button: `${CLASS_PREFIX}button`,
  refreshButton: `${CLASS_PREFIX}refreshButton`,
  userSection: `${CLASS_PREFIX}userSection`,
  userPanel: `${CLASS_PREFIX}userPanel`,
  userLabel: `${CLASS_PREFIX}userLabel`,
  conflictCard: `${CLASS_PREFIX}conflictCard`,
  connectedBadge: `${CLASS_PREFIX}connectedBadge`,
  disconnectedBadge: `${CLASS_PREFIX}disconnectedBadge`,
  todoCol: `${CLASS_PREFIX}todoCol`,
  inprogressCol: `${CLASS_PREFIX}inprogressCol`,
  doneCol: `${CLASS_PREFIX}doneCol`,
  todoBadge: `${CLASS_PREFIX}todoBadge`,
  inprogressBadge: `${CLASS_PREFIX}inprogressBadge`,
  doneBadge: `${CLASS_PREFIX}doneBadge`,
};

const CSS_TEXT = `
@keyframes pulse {
  0%, 100% { border-color: #f44336; }
  50% { border-color: transparent; }
}
.${classNames.app} {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  background-color: #f0f2f5;
  min-height: 100vh;
}
.${classNames.header} {
  text-align: center;
  margin-bottom: 20px;
}
.${classNames.title} {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}
.${classNames.connectionStatus} {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 12px;
  display: inline-block;
  margin-top: 8px;
}
.${classNames.connectedBadge} {
  background-color: #e8f5e9;
  color: #2e7d32;
}
.${classNames.disconnectedBadge} {
  background-color: #ffebee;
  color: #c62828;
}
.${classNames.board} {
  display: flex;
  gap: 16px;
  justify-content: center;
}
.${classNames.column} {
  flex: 1;
  max-width: 350px;
  border-radius: 8px;
  padding: 16px;
  min-height: 400px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
.${classNames.todoCol} { background-color: #e3f2fd; }
.${classNames.inprogressCol} { background-color: #fff8e1; }
.${classNames.doneCol} { background-color: #e8f5e9; }
.${classNames.columnHeader} {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #eee;
}
.${classNames.taskCard} {
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: grab;
  transition: box-shadow 0.2s, border-color 0.2s;
  position: relative;
}
.${classNames.conflictCard} {
  border-color: #f44336;
  animation: pulse 1s infinite;
}
.${classNames.taskTitle} {
  font-size: 14px;
  color: #333;
}
.${classNames.badge} {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  display: inline-block;
  margin-top: 6px;
  color: #fff;
}
.${classNames.todoBadge} { background-color: #2196f3; }
.${classNames.inprogressBadge} { background-color: #ff9800; }
.${classNames.doneBadge} { background-color: #4caf50; }
.${classNames.dropTarget} {
  border: 2px dashed #4a90d9;
  background-color: #f0f7ff !important;
}
.${classNames.conflictBanner} {
  background-color: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.${classNames.newTaskContainer} {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 16px;
}
.${classNames.input} {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
  width: 300px;
}
.${classNames.button} {
  padding: 8px 16px;
  background-color: #4a90d9;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.${classNames.refreshButton} {
  padding: 4px 12px;
  background-color: #ffc107;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.${classNames.userSection} {
  display: flex;
  gap: 24px;
  justify-content: center;
}
.${classNames.userPanel} {
  flex: 1;
  max-width: 600px;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  background-color: #fafafa;
}
.${classNames.userLabel} {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #555;
}
`;

const columnColorClass: Record<ColumnId, string> = {
  todo: classNames.todoCol,
  inprogress: classNames.inprogressCol,
  done: classNames.doneCol,
};

const badgeClass: Record<ColumnId, string> = {
  todo: classNames.todoBadge,
  inprogress: classNames.inprogressBadge,
  done: classNames.doneBadge,
};

const columnLabels: Record<ColumnId, string> = {
  todo: "Todo",
  inprogress: "In Progress",
  done: "Done",
};

// ---- Reducer ----

interface AppLevelState {
  board1: BoardState;
  board2: BoardState;
  dragOver: Record<string, boolean>;
  newTaskInput1: string;
  newTaskInput2: string;
}

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
      const tasks = state.tasks.map((t) => {
        if (t.id === action.task.id) {
          return action.task;
        }
        return t;
      });
      const exists = tasks.find((t) => t.id === action.task.id);
      if (!exists) {
        tasks.push(action.task);
      }
      return { ...state, tasks };
    }

    case "CONFLICT":
      return { ...state, conflicts: [...state.conflicts, action.conflict] };

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

// Column-level drag-over state managed via reducer
interface ColumnDragState {
  dragOverColumns: Record<string, boolean>;
}

type ColumnDragAction =
  | { type: "SET_DRAG_OVER"; key: string; value: boolean };

function columnDragReducer(state: ColumnDragState, action: ColumnDragAction): ColumnDragState {
  switch (action.type) {
    case "SET_DRAG_OVER":
      return { ...state, dragOverColumns: { ...state.dragOverColumns, [action.key]: action.value } };
    default:
      return state;
  }
}

// Input value managed via reducer
interface InputState {
  value: string;
}

type InputAction = { type: "SET_VALUE"; value: string } | { type: "CLEAR" };

function inputReducer(state: InputState, action: InputAction): InputState {
  switch (action.type) {
    case "SET_VALUE":
      return { value: action.value };
    case "CLEAR":
      return { value: "" };
    default:
      return state;
  }
}

// ---- Mock WebSocket Server ----

type ClientCallback = (msg: WSMessage) => void;

class MockWSServer {
  private tasks: Task[] = [];
  private clients: Map<string, ClientCallback> = new Map();
  private nextId = 1;

  constructor() {
    this.tasks = [
      { id: "task-1", title: "Design landing page", column: "todo", order: 0, version: 1 },
      { id: "task-2", title: "Set up CI/CD pipeline", column: "todo", order: 1, version: 1 },
      { id: "task-3", title: "Write unit tests", column: "inprogress", order: 0, version: 1 },
      { id: "task-4", title: "Code review PR #42", column: "inprogress", order: 1, version: 1 },
      { id: "task-5", title: "Deploy v1.0", column: "done", order: 0, version: 1 },
    ];
    this.nextId = 6;
  }

  connect(clientId: string, callback: ClientCallback): void {
    this.clients.set(clientId, callback);
    setTimeout(() => {
      callback({
        type: "INIT_BOARD",
        payload: { tasks: JSON.parse(JSON.stringify(this.tasks)) },
        senderId: "server",
      });
    }, 100);
  }

  disconnect(clientId: string): void {
    this.clients.delete(clientId);
  }

  send(clientId: string, msg: WSMessage): void {
    setTimeout(() => {
      this.processMessage(clientId, msg);
    }, 200);
  }

  private processMessage(senderId: string, msg: WSMessage): void {
    switch (msg.type) {
      case "ADD_TASK": {
        const title = msg.payload.title as string;
        const newTask: Task = {
          id: `task-${this.nextId++}`,
          title,
          column: "todo",
          order: this.tasks.filter((t) => t.column === "todo").length,
          version: 1,
        };
        this.tasks.push(newTask);
        this.broadcast(
          { type: "REMOTE_UPDATE", payload: { task: newTask }, senderId: "server" },
          null
        );
        break;
      }

      case "MOVE_TASK": {
        const { taskId, targetColumn, targetIndex, version } = msg.payload as {
          taskId: string;
          targetColumn: ColumnId;
          targetIndex: number;
          version: number;
        };
        const task = this.tasks.find((t) => t.id === taskId);
        if (!task) return;

        if (task.version !== version) {
          const senderCb = this.clients.get(senderId);
          if (senderCb) {
            senderCb({
              type: "CONFLICT",
              payload: {
                taskId,
                localColumn: targetColumn,
                remoteColumn: task.column,
                serverTask: JSON.parse(JSON.stringify(task)),
              },
              senderId: "server",
            });
          }
          return;
        }

        task.column = targetColumn;
        task.order = targetIndex;
        task.version += 1;

        this.broadcast(
          {
            type: "REMOTE_UPDATE",
            payload: { task: JSON.parse(JSON.stringify(task)) },
            senderId: "server",
          },
          senderId
        );

        const senderCb = this.clients.get(senderId);
        if (senderCb) {
          senderCb({
            type: "REMOTE_UPDATE",
            payload: { task: JSON.parse(JSON.stringify(task)) },
            senderId: "server",
          });
        }
        break;
      }
    }
  }

  private broadcast(msg: WSMessage, excludeId: string | null): void {
    this.clients.forEach((cb, id) => {
      if (id !== excludeId) {
        cb(msg);
      }
    });
  }

  getSnapshot(): Task[] {
    return JSON.parse(JSON.stringify(this.tasks));
  }
}

// ---- Components ----

const ConflictBanner: React.FC<{
  conflicts: ConflictInfo[];
  onRefresh: () => void;
  onResolve: (taskId: string) => void;
}> = ({ conflicts, onRefresh, onResolve }) => {
  if (conflicts.length === 0) return null;
  return (
    <div className={classNames.conflictBanner}>
      <div>
        <strong>⚠ Conflict detected:</strong>{" "}
        {conflicts.map((c) => (
          <span key={c.taskId} style={{ marginRight: "8px" }}>
            Task {c.taskId} was moved by another user.{" "}
            <button
              onClick={() => onResolve(c.taskId)}
              className={classNames.refreshButton}
            >
              Dismiss
            </button>
          </span>
        ))}
      </div>
      <button onClick={onRefresh} className={classNames.refreshButton}>
        Refresh
      </button>
    </div>
  );
};

const TaskCard: React.FC<{
  task: Task;
  hasConflict: boolean;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
}> = ({ task, hasConflict, onDragStart }) => {
  const cardClass = hasConflict
    ? `${classNames.taskCard} ${classNames.conflictCard}`
    : classNames.taskCard;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      className={cardClass}
    >
      <div className={classNames.taskTitle}>{task.title}</div>
      <span className={`${classNames.badge} ${badgeClass[task.column]}`}>
        {columnLabels[task.column]}
      </span>
      <span style={{ fontSize: "10px", color: "#999", marginLeft: "8px" }}>v{task.version}</span>
    </div>
  );
};

const Column: React.FC<{
  columnId: ColumnId;
  tasks: Task[];
  conflicts: ConflictInfo[];
  isDragOver: boolean;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDrop: (columnId: ColumnId, targetIndex: number, taskId: string) => void;
  onDragOverChange: (columnId: ColumnId, value: boolean) => void;
}> = ({ columnId, tasks, conflicts, isDragOver, onDragStart, onDrop, onDragOverChange }) => {
  const columnRef = useRef<HTMLDivElement>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      onDragOverChange(columnId, true);
    },
    [columnId, onDragOverChange]
  );

  const handleDragLeave = useCallback(() => {
    onDragOverChange(columnId, false);
  }, [columnId, onDragOverChange]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      onDragOverChange(columnId, false);
      const taskId = e.dataTransfer.getData("text/plain");
      if (!taskId) return;

      const columnEl = columnRef.current;
      if (!columnEl) {
        onDrop(columnId, tasks.length, taskId);
        return;
      }

      const cardElements = Array.from(columnEl.querySelectorAll("[data-task-card]"));
      let targetIndex = tasks.length;
      for (let i = 0; i < cardElements.length; i++) {
        const rect = cardElements[i].getBoundingClientRect();
        if (e.clientY < rect.top + rect.height / 2) {
          targetIndex = i;
          break;
        }
      }

      onDrop(columnId, targetIndex, taskId);
    },
    [columnId, tasks.length, onDrop, onDragOverChange]
  );

  const sortedTasks = [...tasks].sort((a, b) => a.order - b.order);

  const colClass = isDragOver
    ? `${classNames.column} ${columnColorClass[columnId]} ${classNames.dropTarget}`
    : `${classNames.column} ${columnColorClass[columnId]}`;

  return (
    <div
      ref={columnRef}
      className={colClass}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={classNames.columnHeader}>
        {columnLabels[columnId]} ({sortedTasks.length})
      </div>
      {sortedTasks.map((task) => (
        <div key={task.id} data-task-card>
          <TaskCard
            task={task}
            hasConflict={conflicts.some((c) => c.taskId === task.id)}
            onDragStart={onDragStart}
          />
        </div>
      ))}
    </div>
  );
};

const NewTaskInput: React.FC<{ onAdd: (title: string) => void }> = ({ onAdd }) => {
  const [inputState, inputDispatch] = useReducer(inputReducer, { value: "" });

  const handleSubmit = useCallback(() => {
    const trimmed = inputState.value.trim();
    if (trimmed) {
      onAdd(trimmed);
      inputDispatch({ type: "CLEAR" });
    }
  }, [inputState.value, onAdd]);

  return (
    <div className={classNames.newTaskContainer}>
      <input
        className={classNames.input}
        value={inputState.value}
        onChange={(e) => inputDispatch({ type: "SET_VALUE", value: e.target.value })}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="Add a new task..."
      />
      <button className={classNames.button} onClick={handleSubmit}>
        Add Task
      </button>
    </div>
  );
};

// ---- App (User Panel) ----

const UserPanel: React.FC<{
  userId: string;
  state: BoardState;
  dispatch: React.Dispatch<Action>;
  server: MockWSServer;
}> = ({ userId, state, dispatch, server }) => {
  const [dragState, dragDispatch] = useReducer(columnDragReducer, { dragOverColumns: {} });

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData("text/plain", taskId);
    e.dataTransfer.effectAllowed = "move";
  }, []);

  const handleDrop = useCallback(
    (targetColumn: ColumnId, targetIndex: number, taskId: string) => {
      const task = state.tasks.find((t) => t.id === taskId);
      if (!task) return;
      if (task.column === targetColumn && task.order === targetIndex) return;

      dispatch({ type: "MOVE_TASK", taskId, targetColumn, targetIndex });

      server.send(userId, {
        type: "MOVE_TASK",
        payload: { taskId, targetColumn, targetIndex, version: task.version },
        senderId: userId,
      });
    },
    [state.tasks, dispatch, server, userId]
  );

  const handleAddTask = useCallback(
    (title: string) => {
      server.send(userId, {
        type: "ADD_TASK",
        payload: { title },
        senderId: userId,
      });
    },
    [server, userId]
  );

  const handleRefresh = useCallback(() => {
    const snapshot = server.getSnapshot();
    dispatch({ type: "INIT_BOARD", tasks: snapshot });
    state.conflicts.forEach((c) => {
      dispatch({ type: "RESOLVE_CONFLICT", taskId: c.taskId });
    });
  }, [server, dispatch, state.conflicts]);

  const handleResolve = useCallback(
    (taskId: string) => {
      dispatch({ type: "RESOLVE_CONFLICT", taskId });
    },
    [dispatch]
  );

  const handleDragOverChange = useCallback(
    (columnId: ColumnId, value: boolean) => {
      dragDispatch({ type: "SET_DRAG_OVER", key: columnId, value });
    },
    []
  );

  const columns: ColumnId[] = ["todo", "inprogress", "done"];

  return (
    <div className={classNames.userPanel}>
      <div className={classNames.userLabel}>👤 {userId}</div>
      <ConflictBanner
        conflicts={state.conflicts}
        onRefresh={handleRefresh}
        onResolve={handleResolve}
      />
      <NewTaskInput onAdd={handleAddTask} />
      <div className={classNames.board}>
        {columns.map((col) => (
          <Column
            key={col}
            columnId={col}
            tasks={state.tasks.filter((t) => t.column === col)}
            conflicts={state.conflicts}
            isDragOver={!!dragState.dragOverColumns[col]}
            onDragStart={handleDragStart}
            onDrop={handleDrop}
            onDragOverChange={handleDragOverChange}
          />
        ))}
      </div>
    </div>
  );
};

// ---- Main App ----

const initialState: BoardState = {
  tasks: [],
  userId: "",
  conflicts: [],
  connected: false,
};

const App: React.FC = () => {
  const [state1, dispatch1] = useReducer(boardReducer, { ...initialState, userId: "User-A" });
  const [state2, dispatch2] = useReducer(boardReducer, { ...initialState, userId: "User-B" });
  const serverRef = useRef<MockWSServer | null>(null);

  useEffect(() => {
    const server = new MockWSServer();
    serverRef.current = server;

    server.connect("User-A", (msg: WSMessage) => {
      switch (msg.type) {
        case "INIT_BOARD":
          dispatch1({ type: "INIT_BOARD", tasks: msg.payload.tasks as Task[] });
          break;
        case "REMOTE_UPDATE":
          dispatch1({ type: "REMOTE_UPDATE", task: msg.payload.task as Task });
          break;
        case "CONFLICT": {
          const p = msg.payload as {
            taskId: string;
            localColumn: string;
            remoteColumn: string;
            serverTask: Task;
          };
          dispatch1({
            type: "CONFLICT",
            conflict: {
              taskId: p.taskId,
              localColumn: p.localColumn,
              remoteColumn: p.remoteColumn,
              timestamp: Date.now(),
            },
          });
          dispatch1({ type: "REMOTE_UPDATE", task: p.serverTask });
          break;
        }
      }
    });

    server.connect("User-B", (msg: WSMessage) => {
      switch (msg.type) {
        case "INIT_BOARD":
          dispatch2({ type: "INIT_BOARD", tasks: msg.payload.tasks as Task[] });
          break;
        case "REMOTE_UPDATE":
          dispatch2({ type: "REMOTE_UPDATE", task: msg.payload.task as Task });
          break;
        case "CONFLICT": {
          const p = msg.payload as {
            taskId: string;
            localColumn: string;
            remoteColumn: string;
            serverTask: Task;
          };
          dispatch2({
            type: "CONFLICT",
            conflict: {
              taskId: p.taskId,
              localColumn: p.localColumn,
              remoteColumn: p.remoteColumn,
              timestamp: Date.now(),
            },
          });
          dispatch2({ type: "REMOTE_UPDATE", task: p.serverTask });
          break;
        }
      }
    });

    dispatch1({ type: "SET_CONNECTED", connected: true });
    dispatch2({ type: "SET_CONNECTED", connected: true });

    return () => {
      server.disconnect("User-A");
      server.disconnect("User-B");
    };
  }, []);

  return (
    <div className={classNames.app}>
      <style>{CSS_TEXT}</style>
      <div className={classNames.header}>
        <div className={classNames.title}>Real-Time Collaborative Todo Board</div>
        <div
          className={`${classNames.connectionStatus} ${
            state1.connected ? classNames.connectedBadge : classNames.disconnectedBadge
          }`}
        >
          {state1.connected ? "● Connected" : "● Disconnected"}
        </div>
      </div>
      <div className={classNames.userSection}>
        {serverRef.current && (
          <>
            <UserPanel userId="User-A" state={state1} dispatch={dispatch1} server={serverRef.current} />
            <UserPanel userId="User-B" state={state2} dispatch={dispatch2} server={serverRef.current} />
          </>
        )}
      </div>
    </div>
  );
};

export default App;
```
