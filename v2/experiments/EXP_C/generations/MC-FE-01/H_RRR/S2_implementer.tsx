import React, { useReducer, useEffect, useRef, useCallback } from "react";

// ── CSS Module mock (inline styles object simulating .module.css) ──
const styles: Record<string, React.CSSProperties> = {
  board: {
    display: "flex",
    gap: "16px",
    padding: "24px",
    minHeight: "100vh",
    backgroundColor: "#f0f2f5",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  },
  column: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderRadius: "8px",
    padding: "16px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
    display: "flex",
    flexDirection: "column",
    minWidth: "280px",
  },
  columnHeader: {
    fontSize: "16px",
    fontWeight: 600,
    marginBottom: "12px",
    padding: "8px 0",
    borderBottom: "2px solid #e8e8e8",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    color: "#333",
  },
  taskList: {
    flex: 1,
    minHeight: "100px",
    padding: "4px 0",
  },
  card: {
    padding: "12px",
    marginBottom: "8px",
    backgroundColor: "#fafafa",
    borderRadius: "6px",
    boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
    cursor: "grab",
    border: "1px solid #e8e8e8",
    transition: "opacity 0.2s, box-shadow 0.2s",
  },
  cardDragging: {
    opacity: 0.4,
  },
  cardTitle: {
    fontSize: "14px",
    fontWeight: 500,
    color: "#333",
    marginBottom: "6px",
  },
  cardMeta: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "11px",
    color: "#999",
  },
  assigneeBadge: {
    backgroundColor: "#e6f7ff",
    color: "#1890ff",
    padding: "2px 8px",
    borderRadius: "10px",
    fontSize: "11px",
  },
  conflictIndicator: {
    color: "#ff4d4f",
    fontSize: "11px",
    fontWeight: 600,
  },
  dropZoneActive: {
    backgroundColor: "#e6f7ff",
    border: "2px dashed #1890ff",
    borderRadius: "6px",
    minHeight: "60px",
  },
  addTaskInput: {
    display: "flex",
    gap: "8px",
    marginTop: "12px",
  },
  input: {
    flex: 1,
    padding: "8px 12px",
    borderRadius: "4px",
    border: "1px solid #d9d9d9",
    fontSize: "13px",
    outline: "none",
  },
  addButton: {
    padding: "8px 16px",
    backgroundColor: "#1890ff",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: 500,
  },
  conflictToast: {
    position: "fixed" as const,
    top: "20px",
    right: "20px",
    backgroundColor: "#fff2f0",
    border: "1px solid #ffccc7",
    borderRadius: "8px",
    padding: "16px 24px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    zIndex: 1000,
    maxWidth: "360px",
    animation: "fadeIn 0.3s ease-in",
  },
  conflictTitle: {
    fontWeight: 600,
    color: "#ff4d4f",
    marginBottom: "8px",
    fontSize: "14px",
  },
  conflictBody: {
    fontSize: "13px",
    color: "#666",
    lineHeight: 1.5,
  },
  versionBadge: {
    fontSize: "10px",
    color: "#bbb",
  },
};

// ── Data Model ──
type ColumnId = "todo" | "inprogress" | "done";

interface Task {
  id: string;
  title: string;
  column: ColumnId;
  order: number;
  version: number;
  lastModifiedBy: string;
}

interface ConflictInfo {
  taskId: string;
  localMove: { from: ColumnId; to: ColumnId };
  remoteMove: { from: ColumnId; to: ColumnId; by: string };
  timestamp: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  userId: string;
  conflict: ConflictInfo | null;
}

// ── Actions ──
type BoardAction =
  | { type: "ADD_TASK"; payload: { title: string } }
  | { type: "MOVE_TASK"; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: "REORDER_TASK"; payload: { taskId: string; toIndex: number } }
  | { type: "REMOTE_UPDATE"; payload: { task: Task } }
  | { type: "SET_CONFLICT"; payload: ConflictInfo }
  | { type: "DISMISS_CONFLICT" };

// ── UUID helper ──
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

// ── Initial state ──
const INITIAL_TASKS: Task[] = [
  { id: "t1", title: "Design landing page", column: "todo", order: 0, version: 1, lastModifiedBy: "user-1" },
  { id: "t2", title: "Set up CI/CD pipeline", column: "todo", order: 1, version: 1, lastModifiedBy: "user-1" },
  { id: "t3", title: "Write API docs", column: "inprogress", order: 0, version: 1, lastModifiedBy: "user-2" },
  { id: "t4", title: "Fix login bug", column: "inprogress", order: 1, version: 2, lastModifiedBy: "user-1" },
  { id: "t5", title: "Deploy v1.0", column: "done", order: 0, version: 3, lastModifiedBy: "user-2" },
];

function buildInitialState(): BoardState {
  const tasks: Record<string, Task> = {};
  const columnOrder: Record<ColumnId, string[]> = { todo: [], inprogress: [], done: [] };

  for (const t of INITIAL_TASKS) {
    tasks[t.id] = t;
    columnOrder[t.column].push(t.id);
  }

  return { tasks, columnOrder, userId: "user-1", conflict: null };
}

// ── Reducer ──
function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case "ADD_TASK": {
      const id = generateId();
      const newTask: Task = {
        id,
        title: action.payload.title,
        column: "todo",
        order: state.columnOrder.todo.length,
        version: 1,
        lastModifiedBy: state.userId,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: newTask },
        columnOrder: {
          ...state.columnOrder,
          todo: [...state.columnOrder.todo, id],
        },
      };
    }

    case "MOVE_TASK": {
      const { taskId, toColumn, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const fromColumn = task.column;

      const fromList = state.columnOrder[fromColumn].filter((id) => id !== taskId);
      const toList = fromColumn === toColumn ? fromList : [...state.columnOrder[toColumn]];
      toList.splice(toIndex, 0, taskId);

      const updatedTask: Task = {
        ...task,
        column: toColumn,
        order: toIndex,
        version: task.version + 1,
        lastModifiedBy: state.userId,
      };

      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columnOrder: {
          ...state.columnOrder,
          [fromColumn]: fromColumn === toColumn ? toList : fromList,
          [toColumn]: toList,
        },
      };
    }

    case "REORDER_TASK": {
      const { taskId, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const col = task.column;
      const list = state.columnOrder[col].filter((id) => id !== taskId);
      list.splice(toIndex, 0, taskId);
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, order: toIndex, version: task.version + 1, lastModifiedBy: state.userId },
        },
        columnOrder: { ...state.columnOrder, [col]: list },
      };
    }

    case "REMOTE_UPDATE": {
      const remoteTask = action.payload.task;
      const localTask = state.tasks[remoteTask.id];
      if (!localTask) return state;

      if (remoteTask.version <= localTask.version && localTask.column !== remoteTask.column) {
        const conflictInfo: ConflictInfo = {
          taskId: remoteTask.id,
          localMove: { from: remoteTask.column, to: localTask.column },
          remoteMove: { from: localTask.column, to: remoteTask.column, by: remoteTask.lastModifiedBy },
          timestamp: Date.now(),
        };
        return { ...state, conflict: conflictInfo };
      }

      const fromCol = localTask.column;
      const toCol = remoteTask.column;
      const fromList = state.columnOrder[fromCol].filter((id) => id !== remoteTask.id);
      const toList = fromCol === toCol ? fromList : [...state.columnOrder[toCol]];
      if (!toList.includes(remoteTask.id)) {
        toList.splice(remoteTask.order, 0, remoteTask.id);
      }

      return {
        ...state,
        tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
        columnOrder: {
          ...state.columnOrder,
          [fromCol]: fromCol === toCol ? toList : fromList,
          [toCol]: toList,
        },
      };
    }

    case "SET_CONFLICT":
      return { ...state, conflict: action.payload };

    case "DISMISS_CONFLICT":
      return { ...state, conflict: null };

    default:
      return state;
  }
}

// ── Mock WebSocket ──
class MockWebSocket {
  private onMessageCallback: ((data: { task: Task }) => void) | null = null;
  private timeoutIds: ReturnType<typeof setTimeout>[] = [];

  send(action: { type: string; task: Task }): void {
    const delay = 50 + Math.random() * 150;
    const tid = setTimeout(() => {
      if (Math.random() < 0.15 && this.onMessageCallback) {
        const conflictTask: Task = {
          ...action.task,
          column: (["todo", "inprogress", "done"] as ColumnId[]).filter((c) => c !== action.task.column)[
            Math.floor(Math.random() * 2)
          ],
          version: action.task.version + 1,
          lastModifiedBy: "user-2",
        };
        this.onMessageCallback({ task: conflictTask });
      }
    }, delay);
    this.timeoutIds.push(tid);
  }

  onMessage(callback: (data: { task: Task }) => void): void {
    this.onMessageCallback = callback;
  }

  simulateRemoteActivity(tasks: Record<string, Task>): void {
    const taskIds = Object.keys(tasks);
    if (taskIds.length === 0) return;
    const tid = setTimeout(() => {
      const randomId = taskIds[Math.floor(Math.random() * taskIds.length)];
      const task = tasks[randomId];
      if (task && this.onMessageCallback) {
        const columns: ColumnId[] = ["todo", "inprogress", "done"];
        const otherCols = columns.filter((c) => c !== task.column);
        const newCol = otherCols[Math.floor(Math.random() * otherCols.length)];
        this.onMessageCallback({
          task: { ...task, column: newCol, version: task.version + 1, lastModifiedBy: "user-2" },
        });
      }
    }, 3000 + Math.random() * 5000);
    this.timeoutIds.push(tid);
  }

  close(): void {
    this.timeoutIds.forEach(clearTimeout);
    this.timeoutIds = [];
    this.onMessageCallback = null;
  }
}

// ── Column labels ──
const COLUMN_LABELS: Record<ColumnId, string> = {
  todo: "Todo",
  inprogress: "In Progress",
  done: "Done",
};

const COLUMNS: ColumnId[] = ["todo", "inprogress", "done"];

// ── Sub-components ──

function ConflictToast({
  conflict,
  onDismiss,
}: {
  conflict: ConflictInfo;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [conflict, onDismiss]);

  return (
    <div style={styles.conflictToast}>
      <div style={styles.conflictTitle}>⚠ Conflict Detected</div>
      <div style={styles.conflictBody}>
        <p>
          Task was moved to <strong>{COLUMN_LABELS[conflict.localMove.to]}</strong> locally, but{" "}
          <strong>{conflict.remoteMove.by}</strong> moved it to{" "}
          <strong>{COLUMN_LABELS[conflict.remoteMove.to]}</strong>.
        </p>
        <p>The remote change has been applied. You may re-drag if needed.</p>
      </div>
      <button
        onClick={onDismiss}
        style={{
          marginTop: "8px",
          padding: "4px 12px",
          border: "1px solid #ffccc7",
          borderRadius: "4px",
          background: "transparent",
          cursor: "pointer",
          fontSize: "12px",
        }}
      >
        Dismiss
      </button>
    </div>
  );
}

function AddTaskInput({ onAdd }: { onAdd: (title: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleAdd = () => {
    const value = inputRef.current?.value.trim();
    if (value) {
      onAdd(value);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleAdd();
  };

  return (
    <div style={styles.addTaskInput}>
      <input
        ref={inputRef}
        style={styles.input}
        placeholder="Add a new task…"
        onKeyDown={handleKeyDown}
      />
      <button style={styles.addButton} onClick={handleAdd}>
        Add
      </button>
    </div>
  );
}

function TaskCard({
  task,
  onDragStart,
  draggingId,
}: {
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string, column: ColumnId) => void;
  draggingId: string | null;
}) {
  const isDragging = draggingId === task.id;
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id, task.column)}
      style={{
        ...styles.card,
        ...(isDragging ? styles.cardDragging : {}),
      }}
    >
      <div style={styles.cardTitle}>{task.title}</div>
      <div style={styles.cardMeta}>
        <span style={styles.assigneeBadge}>{task.lastModifiedBy}</span>
        <span style={styles.versionBadge}>v{task.version}</span>
      </div>
    </div>
  );
}

function Column({
  columnId,
  taskIds,
  tasks,
  dispatch,
  draggingId,
  setDraggingId,
  dragOverColumn,
  setDragOverColumn,
  wsRef,
}: {
  columnId: ColumnId;
  taskIds: string[];
  tasks: Record<string, Task>;
  dispatch: React.Dispatch<BoardAction>;
  draggingId: string | null;
  setDraggingId: (id: string | null) => void;
  dragOverColumn: ColumnId | null;
  setDragOverColumn: (col: ColumnId | null) => void;
  wsRef: React.MutableRefObject<MockWebSocket | null>;
}) {
  const listRef = useRef<HTMLDivElement>(null);

  const handleDragStart = useCallback(
    (e: React.DragEvent, taskId: string, fromColumn: ColumnId) => {
      e.dataTransfer.setData("taskId", taskId);
      e.dataTransfer.setData("fromColumn", fromColumn);
      e.dataTransfer.effectAllowed = "move";
      setDraggingId(taskId);
    },
    [setDraggingId]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDragOverColumn(columnId);
    },
    [columnId, setDragOverColumn]
  );

  const handleDragLeave = useCallback(() => {
    setDragOverColumn(null);
  }, [setDragOverColumn]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const taskId = e.dataTransfer.getData("taskId");
      const fromColumn = e.dataTransfer.getData("fromColumn") as ColumnId;
      if (!taskId) return;

      let toIndex = taskIds.length;
      if (listRef.current) {
        const cards = Array.from(listRef.current.children) as HTMLElement[];
        for (let i = 0; i < cards.length; i++) {
          const rect = cards[i].getBoundingClientRect();
          if (e.clientY < rect.top + rect.height / 2) {
            toIndex = i;
            break;
          }
        }
      }

      if (fromColumn === columnId) {
        dispatch({ type: "REORDER_TASK", payload: { taskId, toIndex } });
      } else {
        dispatch({ type: "MOVE_TASK", payload: { taskId, toColumn: columnId, toIndex } });
      }

      const task = tasks[taskId];
      if (task && wsRef.current) {
        wsRef.current.send({
          type: "MOVE_TASK",
          task: { ...task, column: columnId, version: task.version + 1 },
        });
      }

      setDraggingId(null);
      setDragOverColumn(null);
    },
    [columnId, taskIds, tasks, dispatch, setDraggingId, setDragOverColumn, wsRef]
  );

  const handleDragEnd = useCallback(() => {
    setDraggingId(null);
    setDragOverColumn(null);
  }, [setDraggingId, setDragOverColumn]);

  const isOver = dragOverColumn === columnId;

  return (
    <div style={styles.column}>
      <div style={styles.columnHeader}>
        {COLUMN_LABELS[columnId]} ({taskIds.length})
      </div>
      <div
        ref={listRef}
        style={{
          ...styles.taskList,
          ...(isOver ? styles.dropZoneActive : {}),
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onDragEnd={handleDragEnd}
      >
        {taskIds.map((id) => {
          const task = tasks[id];
          if (!task) return null;
          return (
            <TaskCard
              key={id}
              task={task}
              onDragStart={handleDragStart}
              draggingId={draggingId}
            />
          );
        })}
      </div>
      {columnId === "todo" && (
        <AddTaskInput onAdd={(title) => dispatch({ type: "ADD_TASK", payload: { title } })} />
      )}
    </div>
  );
}

// ── Main Component ──
export default function TodoBoard() {
  const [state, dispatch] = useReducer(boardReducer, undefined, buildInitialState);
  const wsRef = useRef<MockWebSocket | null>(null);
  const draggingIdRef = useRef<string | null>(null);
  const [draggingId, setDraggingId] = React.useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = React.useState<ColumnId | null>(null);

  const setDraggingIdWrapped = useCallback((id: string | null) => {
    draggingIdRef.current = id;
    setDraggingId(id);
  }, []);

  useEffect(() => {
    const ws = new MockWebSocket();
    wsRef.current = ws;

    ws.onMessage((data) => {
      dispatch({ type: "REMOTE_UPDATE", payload: { task: data.task } });
    });

    ws.simulateRemoteActivity(state.tasks);

    return () => {
      ws.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDismissConflict = useCallback(() => {
    dispatch({ type: "DISMISS_CONFLICT" });
  }, []);

  return (
    <div style={styles.board}>
      {COLUMNS.map((col) => (
        <Column
          key={col}
          columnId={col}
          taskIds={state.columnOrder[col]}
          tasks={state.tasks}
          dispatch={dispatch}
          draggingId={draggingId}
          setDraggingId={setDraggingIdWrapped}
          dragOverColumn={dragOverColumn}
          setDragOverColumn={setDragOverColumn}
          wsRef={wsRef}
        />
      ))}
      {state.conflict && (
        <ConflictToast conflict={state.conflict} onDismiss={handleDismissConflict} />
      )}
    </div>
  );
}
