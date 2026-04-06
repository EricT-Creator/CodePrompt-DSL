import React, { useReducer, useEffect, useRef, useCallback } from "react";

// ─── CSS Module mock (inline styles as objects, since single-file) ───
const styles: Record<string, React.CSSProperties> = {
  board: {
    display: "flex",
    gap: 16,
    padding: 24,
    fontFamily: "system-ui, sans-serif",
    minHeight: "100vh",
    background: "#f0f2f5",
  },
  column: {
    flex: 1,
    background: "#fff",
    borderRadius: 8,
    padding: 12,
    minWidth: 260,
    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
  },
  columnTitle: {
    fontWeight: 700,
    fontSize: 16,
    marginBottom: 12,
    padding: "4px 0",
    borderBottom: "2px solid #e0e0e0",
  },
  card: {
    background: "#fafafa",
    border: "1px solid #e0e0e0",
    borderRadius: 6,
    padding: 10,
    marginBottom: 8,
    cursor: "grab",
    transition: "box-shadow 0.15s",
  },
  cardDragging: {
    opacity: 0.4,
  },
  cardConflict: {
    border: "2px solid #ff4d4f",
  },
  cardOptimistic: {
    opacity: 0.6,
    borderStyle: "dashed",
  },
  dragOver: {
    background: "#e6f7ff",
    borderColor: "#1890ff",
  },
  conflictPanel: {
    position: "fixed" as const,
    top: 12,
    right: 12,
    background: "#fff2f0",
    border: "1px solid #ffccc7",
    borderRadius: 8,
    padding: 16,
    maxWidth: 320,
    zIndex: 100,
  },
  conflictItem: {
    marginBottom: 8,
    fontSize: 13,
  },
  resolveBtn: {
    marginRight: 6,
    padding: "2px 8px",
    fontSize: 12,
    cursor: "pointer",
    borderRadius: 4,
    border: "1px solid #d9d9d9",
    background: "#fff",
  },
  statusDot: {
    display: "inline-block",
    width: 8,
    height: 8,
    borderRadius: "50%",
    marginRight: 6,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 24px",
    background: "#fff",
    borderBottom: "1px solid #e0e0e0",
  },
  addBtn: {
    padding: "6px 14px",
    cursor: "pointer",
    borderRadius: 4,
    border: "1px solid #1890ff",
    background: "#1890ff",
    color: "#fff",
    fontSize: 13,
  },
};

// ─── Data Model ───

interface Task {
  id: string;
  title: string;
  description: string;
  status: "todo" | "in-progress" | "done";
  order: number;
  lastModifiedBy: string;
  lastModifiedAt: number;
  version: number;
}

interface Column {
  id: string;
  title: string;
  status: Task["status"];
}

interface OptimisticUpdate {
  taskId: string;
  previousState: Task;
  newState: Task;
  timestamp: number;
  pending: boolean;
}

interface Conflict {
  taskId: string;
  localChange: Task;
  remoteChange: Task;
  detectedAt: number;
  resolution?: "local" | "remote";
}

interface WebSocketMessage {
  type: "TASK_MOVE" | "TASK_CREATE" | "TASK_DELETE" | "TASK_UPDATE" | "ACK" | "REJECT" | "CONFLICT";
  payload: any;
  userId: string;
  timestamp: number;
}

// ─── State & Reducer ───

interface AppState {
  tasks: Record<string, Task>;
  optimisticUpdates: OptimisticUpdate[];
  conflicts: Conflict[];
  connectionStatus: "connected" | "disconnected" | "reconnecting";
  currentUser: string;
  dragTaskId: string | null;
  dragOverColumn: string | null;
}

type AppAction =
  | { type: "MOVE_TASK_OPTIMISTIC"; taskId: string; newStatus: Task["status"]; newOrder: number }
  | { type: "MOVE_TASK_CONFIRMED"; taskId: string }
  | { type: "MOVE_TASK_REJECTED"; taskId: string }
  | { type: "RECEIVE_REMOTE_UPDATE"; task: Task }
  | { type: "DETECT_CONFLICT"; conflict: Conflict }
  | { type: "RESOLVE_CONFLICT"; taskId: string; resolution: "local" | "remote" }
  | { type: "WS_CONNECTED" }
  | { type: "WS_DISCONNECTED" }
  | { type: "SET_DRAG"; taskId: string | null }
  | { type: "SET_DRAG_OVER"; columnId: string | null }
  | { type: "ADD_TASK"; task: Task }
  | { type: "INIT_TASKS"; tasks: Record<string, Task> };

const COLUMNS: Column[] = [
  { id: "col-todo", title: "Todo", status: "todo" },
  { id: "col-in-progress", title: "In Progress", status: "in-progress" },
  { id: "col-done", title: "Done", status: "done" },
];

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "INIT_TASKS":
      return { ...state, tasks: action.tasks };

    case "MOVE_TASK_OPTIMISTIC": {
      const task = state.tasks[action.taskId];
      if (!task) return state;
      const prevTask = { ...task };
      const updatedTask: Task = {
        ...task,
        status: action.newStatus,
        order: action.newOrder,
        lastModifiedBy: state.currentUser,
        lastModifiedAt: Date.now(),
        version: task.version + 1,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: updatedTask },
        optimisticUpdates: [
          ...state.optimisticUpdates,
          {
            taskId: action.taskId,
            previousState: prevTask,
            newState: updatedTask,
            timestamp: Date.now(),
            pending: true,
          },
        ],
      };
    }

    case "MOVE_TASK_CONFIRMED": {
      return {
        ...state,
        optimisticUpdates: state.optimisticUpdates.filter(
          (u) => u.taskId !== action.taskId
        ),
      };
    }

    case "MOVE_TASK_REJECTED": {
      const update = state.optimisticUpdates.find(
        (u) => u.taskId === action.taskId
      );
      if (!update) return state;
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: update.previousState },
        optimisticUpdates: state.optimisticUpdates.filter(
          (u) => u.taskId !== action.taskId
        ),
      };
    }

    case "RECEIVE_REMOTE_UPDATE": {
      const existing = state.tasks[action.task.id];
      if (existing && existing.version >= action.task.version) return state;
      return {
        ...state,
        tasks: { ...state.tasks, [action.task.id]: action.task },
      };
    }

    case "DETECT_CONFLICT":
      return {
        ...state,
        conflicts: [...state.conflicts, action.conflict],
      };

    case "RESOLVE_CONFLICT": {
      const conflict = state.conflicts.find(
        (c) => c.taskId === action.taskId
      );
      if (!conflict) return state;
      const resolvedTask =
        action.resolution === "local"
          ? conflict.localChange
          : conflict.remoteChange;
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: resolvedTask },
        conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId),
      };
    }

    case "WS_CONNECTED":
      return { ...state, connectionStatus: "connected" };
    case "WS_DISCONNECTED":
      return { ...state, connectionStatus: "disconnected" };
    case "SET_DRAG":
      return { ...state, dragTaskId: action.taskId };
    case "SET_DRAG_OVER":
      return { ...state, dragOverColumn: action.columnId };
    case "ADD_TASK":
      return {
        ...state,
        tasks: { ...state.tasks, [action.task.id]: action.task },
      };
    default:
      return state;
  }
}

// ─── Mock WebSocket ───

type WSListener = (msg: WebSocketMessage) => void;

class MockWebSocket {
  private listeners: WSListener[] = [];
  private serverTasks: Record<string, Task> = {};
  private connected = false;
  private latencyMin = 50;
  private latencyMax = 200;
  private conflictChance = 0.15;

  connect(initialTasks: Record<string, Task>): void {
    this.serverTasks = JSON.parse(JSON.stringify(initialTasks));
    this.connected = true;
  }

  onMessage(listener: WSListener): void {
    this.listeners.push(listener);
  }

  private emit(msg: WebSocketMessage): void {
    for (const l of this.listeners) l(msg);
  }

  private delay(): Promise<void> {
    const ms =
      this.latencyMin +
      Math.random() * (this.latencyMax - this.latencyMin);
    return new Promise((r) => setTimeout(r, ms));
  }

  async send(msg: WebSocketMessage): Promise<void> {
    if (!this.connected) return;
    await this.delay();

    if (msg.type === "TASK_MOVE") {
      const { taskId, newStatus, newOrder } = msg.payload;
      const task = this.serverTasks[taskId];
      if (!task) {
        this.emit({ type: "REJECT", payload: { taskId }, userId: "server", timestamp: Date.now() });
        return;
      }
      // simulate conflict
      if (Math.random() < this.conflictChance) {
        const remoteTask: Task = {
          ...task,
          status: ["todo", "in-progress", "done"][Math.floor(Math.random() * 3)] as Task["status"],
          lastModifiedBy: "remote-user",
          lastModifiedAt: Date.now(),
          version: task.version + 1,
        };
        this.serverTasks[taskId] = remoteTask;
        this.emit({
          type: "CONFLICT",
          payload: { taskId, remoteTask },
          userId: "server",
          timestamp: Date.now(),
        });
        return;
      }
      const updated: Task = {
        ...task,
        status: newStatus,
        order: newOrder,
        lastModifiedBy: msg.userId,
        lastModifiedAt: Date.now(),
        version: task.version + 1,
      };
      this.serverTasks[taskId] = updated;
      this.emit({ type: "ACK", payload: { taskId }, userId: "server", timestamp: Date.now() });
    }
  }

  simulateRemoteUpdate(): void {
    if (!this.connected) return;
    const ids = Object.keys(this.serverTasks);
    if (ids.length === 0) return;
    const id = ids[Math.floor(Math.random() * ids.length)];
    const task = this.serverTasks[id];
    const statuses: Task["status"][] = ["todo", "in-progress", "done"];
    const newStatus = statuses[Math.floor(Math.random() * 3)];
    const updated: Task = {
      ...task,
      status: newStatus,
      lastModifiedBy: "remote-user",
      lastModifiedAt: Date.now(),
      version: task.version + 1,
    };
    this.serverTasks[id] = updated;
    this.emit({
      type: "TASK_UPDATE",
      payload: updated,
      userId: "remote-user",
      timestamp: Date.now(),
    });
  }

  disconnect(): void {
    this.connected = false;
  }
}

// ─── Seed data ───

function makeSeedTasks(): Record<string, Task> {
  const tasks: Record<string, Task> = {};
  const items = [
    { title: "Design database schema", status: "todo" as const },
    { title: "Set up CI/CD pipeline", status: "todo" as const },
    { title: "Write unit tests", status: "in-progress" as const },
    { title: "Implement auth module", status: "in-progress" as const },
    { title: "Deploy to staging", status: "done" as const },
  ];
  items.forEach((item, i) => {
    const id = `task-${i + 1}`;
    tasks[id] = {
      id,
      title: item.title,
      description: `Description for ${item.title}`,
      status: item.status,
      order: i,
      lastModifiedBy: "system",
      lastModifiedAt: Date.now(),
      version: 1,
    };
  });
  return tasks;
}

// ─── Components ───

const ConflictPanel: React.FC<{
  conflicts: Conflict[];
  onResolve: (taskId: string, res: "local" | "remote") => void;
}> = ({ conflicts, onResolve }) => {
  if (conflicts.length === 0) return null;
  return (
    <div style={styles.conflictPanel}>
      <strong>⚠ Conflicts ({conflicts.length})</strong>
      {conflicts.map((c) => (
        <div key={c.taskId} style={styles.conflictItem}>
          <div>Task: {c.localChange.title}</div>
          <div style={{ fontSize: 11, color: "#888" }}>
            Remote user moved to {c.remoteChange.status}
          </div>
          <button style={styles.resolveBtn} onClick={() => onResolve(c.taskId, "local")}>
            Keep Mine
          </button>
          <button style={styles.resolveBtn} onClick={() => onResolve(c.taskId, "remote")}>
            Accept Remote
          </button>
        </div>
      ))}
    </div>
  );
};

const TaskCard: React.FC<{
  task: Task;
  isPending: boolean;
  isConflict: boolean;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  draggingId: string | null;
}> = ({ task, isPending, isConflict, onDragStart, onDragEnd, draggingId }) => {
  const isDragging = draggingId === task.id;
  const cardStyle: React.CSSProperties = {
    ...styles.card,
    ...(isDragging ? styles.cardDragging : {}),
    ...(isPending ? styles.cardOptimistic : {}),
    ...(isConflict ? styles.cardConflict : {}),
  };
  return (
    <div
      draggable
      style={cardStyle}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", task.id);
        e.dataTransfer.effectAllowed = "move";
        onDragStart(task.id);
      }}
      onDragEnd={onDragEnd}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{task.title}</div>
      <div style={{ fontSize: 12, color: "#666" }}>{task.description}</div>
      <div style={{ fontSize: 11, color: "#999", marginTop: 4 }}>
        v{task.version} · {task.lastModifiedBy}
        {isPending && " · syncing…"}
      </div>
    </div>
  );
};

const ColumnComponent: React.FC<{
  column: Column;
  tasks: Task[];
  pendingIds: Set<string>;
  conflictIds: Set<string>;
  draggingId: string | null;
  isDragOver: boolean;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onDragOver: (e: React.DragEvent, colId: string) => void;
  onDrop: (e: React.DragEvent, colStatus: Task["status"]) => void;
  onDragLeave: () => void;
}> = ({
  column,
  tasks,
  pendingIds,
  conflictIds,
  draggingId,
  isDragOver,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onDragLeave,
}) => {
  const colStyle: React.CSSProperties = {
    ...styles.column,
    ...(isDragOver ? styles.dragOver : {}),
  };
  return (
    <div
      style={colStyle}
      onDragOver={(e) => onDragOver(e, column.id)}
      onDrop={(e) => onDrop(e, column.status)}
      onDragLeave={onDragLeave}
    >
      <div style={styles.columnTitle}>
        {column.title} ({tasks.length})
      </div>
      {tasks
        .sort((a, b) => a.order - b.order)
        .map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            isPending={pendingIds.has(t.id)}
            isConflict={conflictIds.has(t.id)}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            draggingId={draggingId}
          />
        ))}
    </div>
  );
};

// ─── Main Board ───

const initialState: AppState = {
  tasks: {},
  optimisticUpdates: [],
  conflicts: [],
  connectionStatus: "disconnected",
  currentUser: "user-1",
  dragTaskId: null,
  dragOverColumn: null,
};

const TodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const wsRef = useRef<MockWebSocket | null>(null);
  const taskCounterRef = useRef(6);

  useEffect(() => {
    const seedTasks = makeSeedTasks();
    dispatch({ type: "INIT_TASKS", tasks: seedTasks });

    const ws = new MockWebSocket();
    ws.connect(seedTasks);
    wsRef.current = ws;
    dispatch({ type: "WS_CONNECTED" });

    ws.onMessage((msg) => {
      if (msg.type === "ACK") {
        dispatch({ type: "MOVE_TASK_CONFIRMED", taskId: msg.payload.taskId });
      } else if (msg.type === "REJECT") {
        dispatch({ type: "MOVE_TASK_REJECTED", taskId: msg.payload.taskId });
      } else if (msg.type === "CONFLICT") {
        const local = state.tasks[msg.payload.taskId];
        if (local) {
          dispatch({
            type: "DETECT_CONFLICT",
            conflict: {
              taskId: msg.payload.taskId,
              localChange: local,
              remoteChange: msg.payload.remoteTask,
              detectedAt: Date.now(),
            },
          });
        }
      } else if (msg.type === "TASK_UPDATE") {
        dispatch({ type: "RECEIVE_REMOTE_UPDATE", task: msg.payload });
      }
    });

    const interval = setInterval(() => {
      ws.simulateRemoteUpdate();
    }, 8000);

    return () => {
      clearInterval(interval);
      ws.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pendingIds = new Set(state.optimisticUpdates.map((u) => u.taskId));
  const conflictIds = new Set(state.conflicts.map((c) => c.taskId));

  const handleDragStart = useCallback(
    (taskId: string) => dispatch({ type: "SET_DRAG", taskId }),
    []
  );
  const handleDragEnd = useCallback(
    () => {
      dispatch({ type: "SET_DRAG", taskId: null });
      dispatch({ type: "SET_DRAG_OVER", columnId: null });
    },
    []
  );
  const handleDragOver = useCallback(
    (e: React.DragEvent, colId: string) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      dispatch({ type: "SET_DRAG_OVER", columnId: colId });
    },
    []
  );
  const handleDragLeave = useCallback(
    () => dispatch({ type: "SET_DRAG_OVER", columnId: null }),
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent, newStatus: Task["status"]) => {
      e.preventDefault();
      const taskId = e.dataTransfer.getData("text/plain");
      if (!taskId) return;

      const tasksInCol = Object.values(state.tasks).filter(
        (t) => t.status === newStatus
      );
      const newOrder = tasksInCol.length;

      dispatch({
        type: "MOVE_TASK_OPTIMISTIC",
        taskId,
        newStatus,
        newOrder,
      });

      wsRef.current?.send({
        type: "TASK_MOVE",
        payload: { taskId, newStatus, newOrder },
        userId: state.currentUser,
        timestamp: Date.now(),
      });

      dispatch({ type: "SET_DRAG", taskId: null });
      dispatch({ type: "SET_DRAG_OVER", columnId: null });
    },
    [state.tasks, state.currentUser]
  );

  const handleResolve = useCallback(
    (taskId: string, resolution: "local" | "remote") => {
      dispatch({ type: "RESOLVE_CONFLICT", taskId, resolution });
    },
    []
  );

  const handleAddTask = useCallback(() => {
    const id = `task-${taskCounterRef.current++}`;
    const task: Task = {
      id,
      title: `New Task ${id}`,
      description: "Click to edit",
      status: "todo",
      order: Object.values(state.tasks).filter((t) => t.status === "todo").length,
      lastModifiedBy: state.currentUser,
      lastModifiedAt: Date.now(),
      version: 1,
    };
    dispatch({ type: "ADD_TASK", task });
  }, [state.tasks, state.currentUser]);

  const statusColor =
    state.connectionStatus === "connected"
      ? "#52c41a"
      : state.connectionStatus === "reconnecting"
      ? "#faad14"
      : "#ff4d4f";

  return (
    <div>
      <div style={styles.header}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ ...styles.statusDot, background: statusColor }} />
          <span style={{ fontSize: 13 }}>{state.connectionStatus}</span>
          <span style={{ fontSize: 13, color: "#999", marginLeft: 8 }}>
            User: {state.currentUser}
          </span>
        </div>
        <button style={styles.addBtn} onClick={handleAddTask}>
          + Add Task
        </button>
      </div>
      <div style={styles.board}>
        {COLUMNS.map((col) => {
          const colTasks = Object.values(state.tasks).filter(
            (t) => t.status === col.status
          );
          return (
            <ColumnComponent
              key={col.id}
              column={col}
              tasks={colTasks}
              pendingIds={pendingIds}
              conflictIds={conflictIds}
              draggingId={state.dragTaskId}
              isDragOver={state.dragOverColumn === col.id}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onDragLeave={handleDragLeave}
            />
          );
        })}
      </div>
      <ConflictPanel conflicts={state.conflicts} onResolve={handleResolve} />
    </div>
  );
};

export default TodoBoard;
