import React, { useReducer, useEffect, useRef, useCallback } from "react";

// ─── CSS Modules mock (inline object since single-file) ───
const styles: Record<string, string> = {
  board: "board",
  column: "column",
  columnHeader: "columnHeader",
  columnBody: "columnBody",
  card: "card",
  cardDragging: "cardDragging",
  dropZone: "dropZone",
  dropZoneActive: "dropZoneActive",
  assigneeBadge: "assigneeBadge",
  conflictIndicator: "conflictIndicator",
  conflictToast: "conflictToast",
  conflictToastVisible: "conflictToastVisible",
  addTaskInput: "addTaskInput",
  addTaskRow: "addTaskRow",
  addBtn: "addBtn",
};

// ─── CSS Modules stylesheet ───
const styleSheet = `
.board {
  display: flex;
  gap: 16px;
  padding: 24px;
  min-height: 100vh;
  background: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.column {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  display: flex;
  flex-direction: column;
  min-width: 260px;
}
.columnHeader {
  padding: 16px;
  font-weight: 700;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e8e8e8;
  color: #333;
}
.columnBody {
  flex: 1;
  padding: 8px;
  min-height: 120px;
  transition: background 0.2s;
}
.card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: grab;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  transition: opacity 0.2s, box-shadow 0.2s;
  user-select: none;
}
.card:hover {
  box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}
.cardDragging {
  opacity: 0.4;
}
.dropZoneActive {
  background: #e6f7ff !important;
}
.assigneeBadge {
  display: inline-block;
  background: #1890ff;
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-top: 6px;
}
.conflictIndicator {
  display: inline-block;
  background: #ff4d4f;
  color: #fff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 8px;
}
.conflictToast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #fff1f0;
  border: 1px solid #ffa39e;
  color: #cf1322;
  padding: 16px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
  opacity: 0;
  transform: translateY(-20px);
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
}
.conflictToastVisible {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
.addTaskRow {
  display: flex;
  gap: 8px;
  padding: 8px;
}
.addTaskInput {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
  outline: none;
}
.addTaskInput:focus {
  border-color: #1890ff;
}
.addBtn {
  padding: 8px 16px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.addBtn:hover {
  background: #40a9ff;
}
`;

// ─── Types ───
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

type BoardAction =
  | { type: "ADD_TASK"; payload: { title: string } }
  | { type: "MOVE_TASK"; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: "REORDER_TASK"; payload: { taskId: string; toIndex: number } }
  | { type: "REMOTE_UPDATE"; payload: { task: Task } }
  | { type: "SET_CONFLICT"; payload: ConflictInfo }
  | { type: "DISMISS_CONFLICT" };

// ─── Utilities ───
function generateId(): string {
  return Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
}

// ─── Initial State ───
const INITIAL_TASKS: Task[] = [
  { id: "t1", title: "Design mockups", column: "todo", order: 0, version: 1, lastModifiedBy: "alice" },
  { id: "t2", title: "Setup CI/CD pipeline", column: "todo", order: 1, version: 1, lastModifiedBy: "bob" },
  { id: "t3", title: "Write API endpoints", column: "inprogress", order: 0, version: 2, lastModifiedBy: "alice" },
  { id: "t4", title: "Database schema review", column: "inprogress", order: 1, version: 1, lastModifiedBy: "charlie" },
  { id: "t5", title: "Landing page deployed", column: "done", order: 0, version: 3, lastModifiedBy: "bob" },
];

function buildInitialState(): BoardState {
  const tasks: Record<string, Task> = {};
  const columnOrder: Record<ColumnId, string[]> = { todo: [], inprogress: [], done: [] };
  for (const t of INITIAL_TASKS) {
    tasks[t.id] = t;
    columnOrder[t.column].push(t.id);
  }
  return { tasks, columnOrder, userId: "user_local", conflict: null };
}

// ─── Reducer ───
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
          [fromColumn]: fromList,
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
        columnOrder: { ...state.columnOrder, [col]: list },
      };
    }
    case "REMOTE_UPDATE": {
      const remoteTask = action.payload.task;
      const localTask = state.tasks[remoteTask.id];
      if (!localTask) return state;
      if (remoteTask.version <= localTask.version) return state;
      if (localTask.lastModifiedBy === state.userId && localTask.column !== remoteTask.column) {
        const conflictInfo: ConflictInfo = {
          taskId: remoteTask.id,
          localMove: { from: localTask.column, to: localTask.column },
          remoteMove: { from: localTask.column, to: remoteTask.column, by: remoteTask.lastModifiedBy },
          timestamp: Date.now(),
        };
        const fromList = state.columnOrder[localTask.column].filter((id) => id !== remoteTask.id);
        const toList = [...state.columnOrder[remoteTask.column], remoteTask.id];
        return {
          ...state,
          tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
          columnOrder: {
            ...state.columnOrder,
            [localTask.column]: fromList,
            [remoteTask.column]: toList,
          },
          conflict: conflictInfo,
        };
      }
      const oldCol = localTask.column;
      const newCol = remoteTask.column;
      if (oldCol !== newCol) {
        const fromList = state.columnOrder[oldCol].filter((id) => id !== remoteTask.id);
        const toList = [...state.columnOrder[newCol], remoteTask.id];
        return {
          ...state,
          tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
          columnOrder: { ...state.columnOrder, [oldCol]: fromList, [newCol]: toList },
        };
      }
      return { ...state, tasks: { ...state.tasks, [remoteTask.id]: remoteTask } };
    }
    case "SET_CONFLICT":
      return { ...state, conflict: action.payload };
    case "DISMISS_CONFLICT":
      return { ...state, conflict: null };
    default:
      return state;
  }
}

// ─── Mock WebSocket ───
class MockWebSocket {
  private listeners: Array<(msg: { task: Task }) => void> = [];
  private remoteUserId = "remote_user";

  send(action: { type: string; taskId: string; toColumn: ColumnId }): void {
    const delay = 50 + Math.random() * 150;
    setTimeout(() => {
      if (Math.random() < 0.15) {
        const conflictTask: Task = {
          id: action.taskId,
          title: "",
          column: action.toColumn === "done" ? "inprogress" : "done",
          order: 0,
          version: 999,
          lastModifiedBy: this.remoteUserId,
        };
        this.emit(conflictTask);
      }
    }, delay);
  }

  onMessage(callback: (msg: { task: Task }) => void): void {
    this.listeners.push(callback);
  }

  removeListener(callback: (msg: { task: Task }) => void): void {
    this.listeners = this.listeners.filter((l) => l !== callback);
  }

  private emit(task: Task): void {
    for (const listener of this.listeners) {
      listener({ task });
    }
  }
}

// ─── Sub-components ───
const COLUMN_LABELS: Record<ColumnId, string> = {
  todo: "Todo",
  inprogress: "In Progress",
  done: "Done",
};

interface TaskCardProps {
  task: Task;
  conflictTaskId: string | null;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, taskId: string, fromColumn: ColumnId) => void;
  onDragEnd: (e: React.DragEvent<HTMLDivElement>) => void;
}

function TaskCard({ task, conflictTaskId, onDragStart, onDragEnd }: TaskCardProps) {
  const [dragging, setDragging] = React.useState(false);

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    setDragging(true);
    onDragStart(e, task.id, task.column);
  };

  const handleDragEnd = (e: React.DragEvent<HTMLDivElement>) => {
    setDragging(false);
    onDragEnd(e);
  };

  return (
    <div
      className={`${styles.card} ${dragging ? styles.cardDragging : ""}`}
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div style={{ fontWeight: 500, fontSize: 14 }}>
        {task.title}
        {conflictTaskId === task.id && (
          <span className={styles.conflictIndicator}>⚡ Conflict</span>
        )}
      </div>
      <span className={styles.assigneeBadge}>{task.lastModifiedBy}</span>
    </div>
  );
}

interface AddTaskInputProps {
  onAdd: (title: string) => void;
}

function AddTaskInput({ onAdd }: AddTaskInputProps) {
  const [value, setValue] = React.useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed) {
      onAdd(trimmed);
      setValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit();
  };

  return (
    <div className={styles.addTaskRow}>
      <input
        className={styles.addTaskInput}
        placeholder="Add a new task…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button className={styles.addBtn} onClick={handleSubmit}>
        Add
      </button>
    </div>
  );
}

interface ColumnProps {
  columnId: ColumnId;
  taskIds: string[];
  tasks: Record<string, Task>;
  conflictTaskId: string | null;
  dispatch: React.Dispatch<BoardAction>;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, taskId: string, fromColumn: ColumnId) => void;
  onDragEnd: (e: React.DragEvent<HTMLDivElement>) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>, toColumn: ColumnId, toIndex: number) => void;
}

function Column({
  columnId,
  taskIds,
  tasks,
  conflictTaskId,
  dispatch,
  onDragStart,
  onDragEnd,
  onDrop,
}: ColumnProps) {
  const [dragOver, setDragOver] = React.useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const bodyEl = bodyRef.current;
    if (!bodyEl) return;
    const cards = Array.from(bodyEl.querySelectorAll("[draggable=true]"));
    let insertIndex = cards.length;
    for (let i = 0; i < cards.length; i++) {
      const rect = cards[i].getBoundingClientRect();
      if (e.clientY < rect.top + rect.height / 2) {
        insertIndex = i;
        break;
      }
    }
    onDrop(e, columnId, insertIndex);
  };

  return (
    <div className={styles.column}>
      <div className={styles.columnHeader}>
        {COLUMN_LABELS[columnId]} ({taskIds.length})
      </div>
      <div
        ref={bodyRef}
        className={`${styles.columnBody} ${dragOver ? styles.dropZoneActive : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {taskIds.map((id) => {
          const task = tasks[id];
          if (!task) return null;
          return (
            <TaskCard
              key={id}
              task={task}
              conflictTaskId={conflictTaskId}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
            />
          );
        })}
      </div>
      {columnId === "todo" && (
        <AddTaskInput
          onAdd={(title) => dispatch({ type: "ADD_TASK", payload: { title } })}
        />
      )}
    </div>
  );
}

interface ConflictToastProps {
  conflict: ConflictInfo | null;
  onDismiss: () => void;
}

function ConflictToast({ conflict, onDismiss }: ConflictToastProps) {
  useEffect(() => {
    if (conflict) {
      const timer = setTimeout(onDismiss, 4000);
      return () => clearTimeout(timer);
    }
  }, [conflict, onDismiss]);

  return (
    <div
      className={`${styles.conflictToast} ${conflict ? styles.conflictToastVisible : ""}`}
    >
      {conflict && (
        <>
          <strong>⚡ Conflict detected!</strong>
          <p style={{ margin: "8px 0 0", fontSize: 13 }}>
            User <strong>{conflict.remoteMove.by}</strong> moved this task to{" "}
            <strong>{COLUMN_LABELS[conflict.remoteMove.to]}</strong>.
            Your local change was overridden by the server.
          </p>
        </>
      )}
    </div>
  );
}

// ─── Main Component ───
export default function TodoBoard(): React.ReactElement {
  const [state, dispatch] = useReducer(boardReducer, null, buildInitialState);
  const wsRef = useRef<MockWebSocket | null>(null);
  const dragDataRef = useRef<{ taskId: string; fromColumn: ColumnId } | null>(null);

  useEffect(() => {
    const ws = new MockWebSocket();
    wsRef.current = ws;
    const handler = (msg: { task: Task }) => {
      dispatch({ type: "REMOTE_UPDATE", payload: { task: msg.task } });
    };
    ws.onMessage(handler);
    return () => {
      ws.removeListener(handler);
      wsRef.current = null;
    };
  }, []);

  const handleDragStart = useCallback(
    (e: React.DragEvent<HTMLDivElement>, taskId: string, fromColumn: ColumnId) => {
      e.dataTransfer.setData("text/plain", taskId);
      e.dataTransfer.effectAllowed = "move";
      dragDataRef.current = { taskId, fromColumn };
    },
    []
  );

  const handleDragEnd = useCallback(() => {
    dragDataRef.current = null;
  }, []);

  const handleDrop = useCallback(
    (_e: React.DragEvent<HTMLDivElement>, toColumn: ColumnId, toIndex: number) => {
      const dragData = dragDataRef.current;
      if (!dragData) return;
      const { taskId, fromColumn } = dragData;
      if (fromColumn === toColumn) {
        dispatch({ type: "REORDER_TASK", payload: { taskId, toIndex } });
      } else {
        dispatch({ type: "MOVE_TASK", payload: { taskId, toColumn, toIndex } });
        wsRef.current?.send({ type: "MOVE_TASK", taskId, toColumn });
      }
      dragDataRef.current = null;
    },
    []
  );

  const handleDismissConflict = useCallback(() => {
    dispatch({ type: "DISMISS_CONFLICT" });
  }, []);

  return (
    <>
      <style>{styleSheet}</style>
      <div className={styles.board}>
        {(["todo", "inprogress", "done"] as ColumnId[]).map((colId) => (
          <Column
            key={colId}
            columnId={colId}
            taskIds={state.columnOrder[colId]}
            tasks={state.tasks}
            conflictTaskId={state.conflict?.taskId ?? null}
            dispatch={dispatch}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDrop={handleDrop}
          />
        ))}
      </div>
      <ConflictToast conflict={state.conflict} onDismiss={handleDismissConflict} />
    </>
  );
}
