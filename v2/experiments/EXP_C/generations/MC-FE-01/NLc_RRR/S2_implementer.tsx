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
  | { type: "SET_CONNECTED"; connected: boolean };

// ---- CSS Styles (inline CSS Module simulation) ----

const styles: Record<string, React.CSSProperties> = {
  app: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    padding: "20px",
    maxWidth: "1200px",
    margin: "0 auto",
    backgroundColor: "#f0f2f5",
    minHeight: "100vh",
  },
  header: {
    textAlign: "center" as const,
    marginBottom: "20px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#333",
  },
  connectionStatus: {
    fontSize: "12px",
    padding: "4px 8px",
    borderRadius: "12px",
    display: "inline-block",
    marginTop: "8px",
  },
  board: {
    display: "flex",
    gap: "16px",
    justifyContent: "center",
  },
  column: {
    flex: 1,
    maxWidth: "350px",
    backgroundColor: "#fff",
    borderRadius: "8px",
    padding: "16px",
    minHeight: "400px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
  },
  columnHeader: {
    fontSize: "16px",
    fontWeight: "600",
    marginBottom: "12px",
    paddingBottom: "8px",
    borderBottom: "2px solid #eee",
  },
  taskCard: {
    backgroundColor: "#fff",
    border: "1px solid #e0e0e0",
    borderRadius: "6px",
    padding: "12px",
    marginBottom: "8px",
    cursor: "grab",
    transition: "box-shadow 0.2s, border-color 0.2s",
    position: "relative" as const,
  },
  taskTitle: {
    fontSize: "14px",
    color: "#333",
  },
  badge: {
    fontSize: "10px",
    padding: "2px 6px",
    borderRadius: "10px",
    display: "inline-block",
    marginTop: "6px",
    color: "#fff",
  },
  dropTarget: {
    border: "2px dashed #4a90d9",
    backgroundColor: "#f0f7ff",
  },
  conflictBanner: {
    backgroundColor: "#fff3cd",
    border: "1px solid #ffc107",
    borderRadius: "6px",
    padding: "12px 16px",
    marginBottom: "16px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  newTaskContainer: {
    display: "flex",
    gap: "8px",
    justifyContent: "center",
    marginBottom: "16px",
  },
  input: {
    padding: "8px 12px",
    border: "1px solid #ccc",
    borderRadius: "4px",
    fontSize: "14px",
    width: "300px",
  },
  button: {
    padding: "8px 16px",
    backgroundColor: "#4a90d9",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "14px",
  },
  refreshButton: {
    padding: "4px 12px",
    backgroundColor: "#ffc107",
    color: "#333",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "12px",
  },
  userSection: {
    display: "flex",
    gap: "24px",
    justifyContent: "center",
  },
  userPanel: {
    flex: 1,
    maxWidth: "600px",
    border: "1px solid #ddd",
    borderRadius: "8px",
    padding: "16px",
    backgroundColor: "#fafafa",
  },
  userLabel: {
    fontSize: "14px",
    fontWeight: "600",
    marginBottom: "8px",
    color: "#555",
  },
};

const columnColors: Record<ColumnId, string> = {
  todo: "#e3f2fd",
  inprogress: "#fff8e1",
  done: "#e8f5e9",
};

const badgeColors: Record<ColumnId, string> = {
  todo: "#2196f3",
  inprogress: "#ff9800",
  done: "#4caf50",
};

const columnLabels: Record<ColumnId, string> = {
  todo: "Todo",
  inprogress: "In Progress",
  done: "Done",
};

// ---- Reducer ----

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
    <div style={styles.conflictBanner}>
      <div>
        <strong>⚠ Conflict detected:</strong>{" "}
        {conflicts.map((c) => (
          <span key={c.taskId} style={{ marginRight: "8px" }}>
            Task {c.taskId} was moved by another user.{" "}
            <button
              onClick={() => onResolve(c.taskId)}
              style={{ ...styles.refreshButton, marginLeft: "4px", fontSize: "11px" }}
            >
              Dismiss
            </button>
          </span>
        ))}
      </div>
      <button onClick={onRefresh} style={styles.refreshButton}>
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
  const conflictStyle: React.CSSProperties = hasConflict
    ? {
        borderColor: "#f44336",
        animation: "pulse 1s infinite",
      }
    : {};

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      style={{ ...styles.taskCard, ...conflictStyle }}
    >
      <div style={styles.taskTitle}>{task.title}</div>
      <span style={{ ...styles.badge, backgroundColor: badgeColors[task.column] }}>
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
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDrop: (columnId: ColumnId, targetIndex: number, taskId: string) => void;
}> = ({ columnId, tasks, conflicts, onDragStart, onDrop }) => {
  const [isDragOver, setIsDragOver] = React.useState(false);
  const columnRef = useRef<HTMLDivElement>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setIsDragOver(true);
    },
    []
  );

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
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
    [columnId, tasks.length, onDrop]
  );

  const sortedTasks = [...tasks].sort((a, b) => a.order - b.order);

  return (
    <div
      ref={columnRef}
      style={{
        ...styles.column,
        backgroundColor: columnColors[columnId],
        ...(isDragOver ? styles.dropTarget : {}),
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div style={styles.columnHeader}>
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
  const [value, setValue] = React.useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed) {
      onAdd(trimmed);
      setValue("");
    }
  };

  return (
    <div style={styles.newTaskContainer}>
      <input
        style={styles.input}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="Add a new task..."
      />
      <button style={styles.button} onClick={handleSubmit}>
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

  const columns: ColumnId[] = ["todo", "inprogress", "done"];

  return (
    <div style={styles.userPanel}>
      <div style={styles.userLabel}>👤 {userId}</div>
      <ConflictBanner
        conflicts={state.conflicts}
        onRefresh={handleRefresh}
        onResolve={handleResolve}
      />
      <NewTaskInput onAdd={handleAddTask} />
      <div style={styles.board}>
        {columns.map((col) => (
          <Column
            key={col}
            columnId={col}
            tasks={state.tasks.filter((t) => t.column === col)}
            conflicts={state.conflicts}
            onDragStart={handleDragStart}
            onDrop={handleDrop}
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
    <div style={styles.app}>
      <style>{`
        @keyframes pulse {
          0%, 100% { border-color: #f44336; }
          50% { border-color: transparent; }
        }
      `}</style>
      <div style={styles.header}>
        <div style={styles.title}>Real-Time Collaborative Todo Board</div>
        <div
          style={{
            ...styles.connectionStatus,
            backgroundColor: state1.connected ? "#e8f5e9" : "#ffebee",
            color: state1.connected ? "#2e7d32" : "#c62828",
          }}
        >
          {state1.connected ? "● Connected" : "● Disconnected"}
        </div>
      </div>
      <div style={styles.userSection}>
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
