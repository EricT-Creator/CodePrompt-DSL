import React, { useReducer, useEffect, useRef, useCallback } from 'react';

// ─── CSS Modules mock (inline object simulating .module.css import) ───
const styles: Record<string, string> = {
  board: 'board',
  column: 'column',
  columnHeader: 'columnHeader',
  taskList: 'taskList',
  card: 'card',
  dragging: 'dragging',
  dropZone: 'dropZone',
  dropZoneActive: 'dropZoneActive',
  conflictToast: 'conflictToast',
  conflictToastVisible: 'conflictToastVisible',
  addInput: 'addInput',
  addInputWrapper: 'addInputWrapper',
  assigneeBadge: 'assigneeBadge',
  conflictIndicator: 'conflictIndicator',
  addButton: 'addButton',
};

// ─── Style tag (CSS Modules scoped classes) ───
const STYLE_CONTENT = `
.board {
  display: flex;
  gap: 16px;
  padding: 24px;
  min-height: 100vh;
  background: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.column {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  min-width: 280px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  display: flex;
  flex-direction: column;
}
.columnHeader {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e8e8e8;
  color: #333;
}
.taskList {
  flex: 1;
  min-height: 60px;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: opacity 0.2s, box-shadow 0.2s;
}
.card:hover {
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.dragging {
  opacity: 0.4;
}
.dropZone {
  border: 2px dashed transparent;
  border-radius: 6px;
  transition: border-color 0.2s, background 0.2s;
}
.dropZoneActive {
  border-color: #1890ff;
  background: #e6f7ff;
}
.assigneeBadge {
  font-size: 11px;
  background: #e6f7ff;
  color: #1890ff;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
  white-space: nowrap;
}
.conflictIndicator {
  color: #ff4d4f;
  font-size: 12px;
  margin-left: 4px;
}
.conflictToast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 8px;
  padding: 16px 24px;
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
.addInputWrapper {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.addInput {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
}
.addInput:focus {
  border-color: #1890ff;
}
.addButton {
  padding: 8px 16px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.addButton:hover {
  background: #40a9ff;
}
`;

// ─── Types ───
type ColumnId = 'todo' | 'inprogress' | 'done';

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
  | { type: 'ADD_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; toIndex: number } }
  | { type: 'REMOTE_UPDATE'; payload: { task: Task } }
  | { type: 'SET_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT' };

// ─── Helpers ───
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const COLUMN_LABELS: Record<ColumnId, string> = {
  todo: 'Todo',
  inprogress: 'In Progress',
  done: 'Done',
};

// ─── Initial state ───
function createInitialState(): BoardState {
  const tasks: Record<string, Task> = {};
  const columnOrder: Record<ColumnId, string[]> = {
    todo: [],
    inprogress: [],
    done: [],
  };

  const sampleTasks = [
    { title: 'Set up project structure', column: 'todo' as ColumnId },
    { title: 'Design database schema', column: 'todo' as ColumnId },
    { title: 'Implement auth module', column: 'inprogress' as ColumnId },
    { title: 'Write unit tests', column: 'inprogress' as ColumnId },
    { title: 'Deploy to staging', column: 'done' as ColumnId },
  ];

  sampleTasks.forEach((t, i) => {
    const id = `task-${i + 1}`;
    tasks[id] = {
      id,
      title: t.title,
      column: t.column,
      order: i,
      version: 1,
      lastModifiedBy: 'user-local',
    };
    columnOrder[t.column].push(id);
  });

  return {
    tasks,
    columnOrder,
    userId: 'user-local',
    conflict: null,
  };
}

// ─── Reducer ───
function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = generateId();
      const newTask: Task = {
        id,
        title: action.payload.title,
        column: 'todo',
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

    case 'MOVE_TASK': {
      const { taskId, toColumn, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const fromColumn = task.column;

      const newFromList = state.columnOrder[fromColumn].filter((id) => id !== taskId);
      const newToList =
        fromColumn === toColumn
          ? newFromList
          : [...state.columnOrder[toColumn]];
      const insertIdx = Math.min(toIndex, newToList.length);
      newToList.splice(insertIdx, 0, taskId);

      const updatedTask: Task = {
        ...task,
        column: toColumn,
        order: insertIdx,
        version: task.version + 1,
        lastModifiedBy: state.userId,
      };

      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columnOrder: {
          ...state.columnOrder,
          [fromColumn]: fromColumn === toColumn ? newToList : newFromList,
          [toColumn]: newToList,
        },
      };
    }

    case 'REORDER_TASK': {
      const { taskId, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const col = task.column;
      const list = state.columnOrder[col].filter((id) => id !== taskId);
      const idx = Math.min(toIndex, list.length);
      list.splice(idx, 0, taskId);

      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, order: idx, version: task.version + 1, lastModifiedBy: state.userId },
        },
        columnOrder: { ...state.columnOrder, [col]: list },
      };
    }

    case 'REMOTE_UPDATE': {
      const remoteTask = action.payload.task;
      const localTask = state.tasks[remoteTask.id];
      if (!localTask) {
        return {
          ...state,
          tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
          columnOrder: {
            ...state.columnOrder,
            [remoteTask.column]: [...state.columnOrder[remoteTask.column], remoteTask.id],
          },
        };
      }
      if (remoteTask.version > localTask.version) {
        const oldColumn = localTask.column;
        const newColumn = remoteTask.column;
        const newOrder = { ...state.columnOrder };
        if (oldColumn !== newColumn) {
          newOrder[oldColumn] = newOrder[oldColumn].filter((id) => id !== remoteTask.id);
          newOrder[newColumn] = [...newOrder[newColumn], remoteTask.id];
        }
        return {
          ...state,
          tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
          columnOrder: newOrder,
        };
      }
      if (remoteTask.version === localTask.version && remoteTask.lastModifiedBy !== localTask.lastModifiedBy) {
        const conflictInfo: ConflictInfo = {
          taskId: remoteTask.id,
          localMove: { from: localTask.column, to: localTask.column },
          remoteMove: { from: localTask.column, to: remoteTask.column, by: remoteTask.lastModifiedBy },
          timestamp: Date.now(),
        };
        return { ...state, conflict: conflictInfo };
      }
      return state;
    }

    case 'SET_CONFLICT':
      return { ...state, conflict: action.payload };

    case 'DISMISS_CONFLICT':
      return { ...state, conflict: null };

    default:
      return state;
  }
}

// ─── Mock WebSocket ───
class MockWebSocket {
  private _onMessage: ((data: { task: Task }) => void) | null = null;
  private _timers: ReturnType<typeof setTimeout>[] = [];

  send(action: { type: string; task: Task }): void {
    const delay = 50 + Math.random() * 150;
    const timer = setTimeout(() => {
      if (Math.random() < 0.15 && this._onMessage) {
        const conflictTask: Task = {
          ...action.task,
          lastModifiedBy: 'user-remote',
          version: action.task.version,
        };
        this._onMessage({ task: conflictTask });
      }
    }, delay);
    this._timers.push(timer);
  }

  onMessage(callback: (data: { task: Task }) => void): void {
    this._onMessage = callback;
  }

  close(): void {
    this._timers.forEach(clearTimeout);
    this._timers = [];
    this._onMessage = null;
  }
}

// ─── Sub-components (internal) ───

function AddTaskInput({ onAdd }: { onAdd: (title: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleAdd = () => {
    const val = inputRef.current?.value.trim();
    if (val) {
      onAdd(val);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAdd();
  };

  return (
    <div className={styles.addInputWrapper}>
      <input
        ref={inputRef}
        className={styles.addInput}
        placeholder="Add a task..."
        onKeyDown={handleKeyDown}
      />
      <button className={styles.addButton} onClick={handleAdd}>
        Add
      </button>
    </div>
  );
}

function TaskCard({
  task,
  onDragStart,
  onDragEnd,
  isDragging,
}: {
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string, column: ColumnId) => void;
  onDragEnd: () => void;
  isDragging: boolean;
}) {
  return (
    <div
      className={`${styles.card} ${isDragging ? styles.dragging : ''}`}
      draggable
      onDragStart={(e) => onDragStart(e, task.id, task.column)}
      onDragEnd={onDragEnd}
    >
      <span>{task.title}</span>
      <span className={styles.assigneeBadge}>{task.lastModifiedBy}</span>
    </div>
  );
}

function Column({
  columnId,
  label,
  taskIds,
  tasks,
  draggingTaskId,
  dragOverColumn,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onAddTask,
}: {
  columnId: ColumnId;
  label: string;
  taskIds: string[];
  tasks: Record<string, Task>;
  draggingTaskId: string | null;
  dragOverColumn: ColumnId | null;
  onDragStart: (e: React.DragEvent, taskId: string, column: ColumnId) => void;
  onDragEnd: () => void;
  onDragOver: (e: React.DragEvent, columnId: ColumnId) => void;
  onDrop: (e: React.DragEvent, columnId: ColumnId) => void;
  onAddTask?: (title: string) => void;
}) {
  return (
    <div className={styles.column}>
      <div className={styles.columnHeader}>
        {label} ({taskIds.length})
      </div>
      <div
        className={`${styles.taskList} ${styles.dropZone} ${
          dragOverColumn === columnId ? styles.dropZoneActive : ''
        }`}
        onDragOver={(e) => onDragOver(e, columnId)}
        onDrop={(e) => onDrop(e, columnId)}
      >
        {taskIds.map((id) => {
          const task = tasks[id];
          if (!task) return null;
          return (
            <TaskCard
              key={id}
              task={task}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              isDragging={draggingTaskId === id}
            />
          );
        })}
      </div>
      {onAddTask && <AddTaskInput onAdd={onAddTask} />}
    </div>
  );
}

function ConflictToast({
  conflict,
  onDismiss,
}: {
  conflict: ConflictInfo | null;
  onDismiss: () => void;
}) {
  useEffect(() => {
    if (conflict) {
      const timer = setTimeout(onDismiss, 4000);
      return () => clearTimeout(timer);
    }
  }, [conflict, onDismiss]);

  return (
    <div
      className={`${styles.conflictToast} ${conflict ? styles.conflictToastVisible : ''}`}
    >
      {conflict && (
        <>
          <strong>⚠ Conflict Detected</strong>
          <p>
            User <em>{conflict.remoteMove.by}</em> moved the same task from{' '}
            <strong>{COLUMN_LABELS[conflict.remoteMove.from]}</strong> to{' '}
            <strong>{COLUMN_LABELS[conflict.remoteMove.to]}</strong>.
          </p>
        </>
      )}
    </div>
  );
}

// ─── Main Component ───
export default function TodoBoard(): React.ReactElement {
  const [state, dispatch] = useReducer(boardReducer, undefined, createInitialState);
  const wsRef = useRef<MockWebSocket | null>(null);
  const draggingRef = useRef<{ taskId: string; sourceColumn: ColumnId } | null>(null);
  const [draggingTaskId, setDraggingTaskId] = React.useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = React.useState<ColumnId | null>(null);

  // Init mock WebSocket
  useEffect(() => {
    const ws = new MockWebSocket();
    ws.onMessage((data) => {
      dispatch({ type: 'REMOTE_UPDATE', payload: { task: data.task } });
    });
    wsRef.current = ws;
    return () => {
      ws.close();
    };
  }, []);

  const handleDragStart = useCallback(
    (e: React.DragEvent, taskId: string, column: ColumnId) => {
      e.dataTransfer.setData('text/plain', taskId);
      e.dataTransfer.effectAllowed = 'move';
      draggingRef.current = { taskId, sourceColumn: column };
      setDraggingTaskId(taskId);
    },
    []
  );

  const handleDragEnd = useCallback(() => {
    draggingRef.current = null;
    setDraggingTaskId(null);
    setDragOverColumn(null);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverColumn(columnId);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, toColumn: ColumnId) => {
      e.preventDefault();
      const taskId = e.dataTransfer.getData('text/plain');
      if (!taskId || !draggingRef.current) return;

      const sourceColumn = draggingRef.current.sourceColumn;

      // Calculate insertion index from mouse position
      const container = e.currentTarget as HTMLElement;
      const cards = Array.from(container.querySelectorAll(`.${styles.card}`));
      let toIndex = cards.length;
      for (let i = 0; i < cards.length; i++) {
        const rect = cards[i].getBoundingClientRect();
        if (e.clientY < rect.top + rect.height / 2) {
          toIndex = i;
          break;
        }
      }

      if (sourceColumn === toColumn) {
        dispatch({ type: 'REORDER_TASK', payload: { taskId, toIndex } });
      } else {
        dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn, toIndex } });
      }

      // Send to mock WebSocket
      const updatedTask = state.tasks[taskId];
      if (updatedTask && wsRef.current) {
        wsRef.current.send({
          type: 'MOVE',
          task: { ...updatedTask, column: toColumn, version: updatedTask.version + 1 },
        });
      }

      setDragOverColumn(null);
      draggingRef.current = null;
      setDraggingTaskId(null);
    },
    [state.tasks]
  );

  const handleAddTask = useCallback((title: string) => {
    dispatch({ type: 'ADD_TASK', payload: { title } });
  }, []);

  const handleDismissConflict = useCallback(() => {
    dispatch({ type: 'DISMISS_CONFLICT' });
  }, []);

  return (
    <>
      <style>{STYLE_CONTENT}</style>
      <div className={styles.board}>
        {(['todo', 'inprogress', 'done'] as ColumnId[]).map((colId) => (
          <Column
            key={colId}
            columnId={colId}
            label={COLUMN_LABELS[colId]}
            taskIds={state.columnOrder[colId]}
            tasks={state.tasks}
            draggingTaskId={draggingTaskId}
            dragOverColumn={dragOverColumn}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onAddTask={colId === 'todo' ? handleAddTask : undefined}
          />
        ))}
      </div>
      <ConflictToast conflict={state.conflict} onDismiss={handleDismissConflict} />
    </>
  );
}
