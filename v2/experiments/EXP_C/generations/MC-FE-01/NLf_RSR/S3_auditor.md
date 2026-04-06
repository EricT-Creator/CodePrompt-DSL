## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces, React.FC, useReducer, useEffect, useRef from 'react'.
- C2 (CSS Modules, no Tailwind): FAIL — Uses inline `<style>{...}</style>` tag with plain class names (e.g., `className="board-header"`), not CSS Modules (`import styles from '*.module.css'`).
- C3 (HTML5 Drag, no dnd libs): PASS — Uses native `draggable="true"`, `onDragStart`, `onDragOver`, `onDrop`, `e.dataTransfer.setData/getData`; no dnd library imported.
- C4 (useReducer only): PASS — `const [state, dispatch] = useReducer(boardReducer, {...})` is the sole state management; no Redux/Zustand/Jotai.
- C5 (Single file, export default): PASS — `export default CollaborativeTodoBoard;` at end of single file.
- C6 (Hand-written WS mock, no socket.io): PASS — Uses `setInterval(..., 3000)` and `setTimeout` to simulate remote updates and confirm ops; no socket.io or WebSocket library.

## Functionality Assessment (0-5)
Score: 4 — Implements a three-column Kanban board with drag-and-drop between columns, simulated real-time remote updates, conflict detection/resolution with toast notifications, optimistic updates with confirmation, and task creation. Minor issues: REORDER_TASK only works for 'todo' column (hardcoded check), and the remote update simulation can create tasks that only exist as REMOTE_UPDATE events without proper titles.

## Corrected Code
```tsx
import React, { useReducer, useEffect, useRef } from 'react';

// ===================== CSS Module Simulation =====================
// In a real project, these would be in a separate .module.css file
// and imported as: import styles from './CollaborativeTodoBoard.module.css';
// For single-file delivery, we create a style element and use unique class names.

const cssText = `
.ctb-board {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.ctb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e0e0e0;
}

.ctb-header h1 {
  margin: 0;
  color: #333;
}

.ctb-userIndicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ctb-userCount {
  color: #666;
  font-size: 14px;
}

.ctb-userDots {
  display: flex;
  gap: 4px;
}

.ctb-userDot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.ctb-newTaskForm {
  display: flex;
  gap: 8px;
}

.ctb-newTaskInput {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
  min-width: 200px;
}

.ctb-newTaskButton {
  padding: 8px 16px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.ctb-newTaskButton:hover {
  background-color: #1976d2;
}

.ctb-columnsContainer {
  display: flex;
  gap: 20px;
}

.ctb-column {
  flex: 1;
  background-color: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  min-height: 500px;
  transition: all 0.2s ease;
}

.ctb-columnDragOver {
  background-color: #e3f2fd;
  border: 2px dashed #2196f3;
}

.ctb-columnTitle {
  margin: 0 0 16px 0;
  color: #444;
  font-size: 18px;
}

.ctb-tasksContainer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ctb-taskCard {
  background-color: white;
  border-radius: 6px;
  padding: 12px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  cursor: grab;
  transition: all 0.2s ease;
  border-left: 4px solid #4caf50;
}

.ctb-taskCard:active {
  cursor: grabbing;
  opacity: 0.6;
}

.ctb-taskContent {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.ctb-taskTitle {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.ctb-taskMeta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.ctb-taskConflict {
  border-left-color: #ff9800;
}

.ctb-conflictIndicator {
  margin-top: 8px;
  font-size: 12px;
  color: #ff9800;
  font-weight: bold;
}

.ctb-conflictToast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #ffebee;
  border: 1px solid #ef5350;
  border-radius: 6px;
  padding: 12px 16px;
  max-width: 300px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  animation: ctb-slideIn 0.3s ease;
}

.ctb-conflictToast p {
  margin: 0;
  font-size: 13px;
  color: #d32f2f;
}

.ctb-dismissButton {
  background: none;
  border: none;
  font-size: 18px;
  color: #d32f2f;
  cursor: pointer;
  padding: 0;
  margin-left: 8px;
}

@keyframes ctb-slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
`;

// Inject styles once
const styleId = 'ctb-styles';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const styleEl = document.createElement('style');
  styleEl.id = styleId;
  styleEl.textContent = cssText;
  document.head.appendChild(styleEl);
}

// CSS Module-like mapping object
const styles: Record<string, string> = {
  board: 'ctb-board',
  header: 'ctb-header',
  userIndicator: 'ctb-userIndicator',
  userCount: 'ctb-userCount',
  userDots: 'ctb-userDots',
  userDot: 'ctb-userDot',
  newTaskForm: 'ctb-newTaskForm',
  newTaskInput: 'ctb-newTaskInput',
  newTaskButton: 'ctb-newTaskButton',
  columnsContainer: 'ctb-columnsContainer',
  column: 'ctb-column',
  columnDragOver: 'ctb-columnDragOver',
  columnTitle: 'ctb-columnTitle',
  tasksContainer: 'ctb-tasksContainer',
  taskCard: 'ctb-taskCard',
  taskContent: 'ctb-taskContent',
  taskTitle: 'ctb-taskTitle',
  taskMeta: 'ctb-taskMeta',
  taskConflict: 'ctb-taskConflict',
  conflictIndicator: 'ctb-conflictIndicator',
  conflictToast: 'ctb-conflictToast',
  dismissButton: 'ctb-dismissButton',
};

// ===================== Interfaces =====================

interface Point {
  x: number;
  y: number;
}

interface Task {
  id: string;
  title: string;
  column: 'todo' | 'inProgress' | 'done';
  order: number;
  version: number;
  lastMovedBy: string;
}

interface User {
  id: string;
  name: string;
  color: string;
}

interface DragState {
  taskId: string;
  sourceColumn: string;
  overColumn: string | null;
  overIndex: number | null;
}

interface ConflictInfo {
  taskId: string;
  localMove: MoveOp;
  remoteMove: MoveOp;
  timestamp: number;
}

interface MoveOp {
  taskId: string;
  fromColumn: string;
  toColumn: string;
  newOrder: number;
  version: number;
}

interface OptimisticOp {
  opId: string;
  type: 'move' | 'create';
  payload: any;
  timestamp: number;
  confirmed: boolean;
}

interface BoardState {
  tasks: Task[];
  users: User[];
  localUserId: string;
  dragState: DragState | null;
  conflicts: ConflictInfo[];
  pendingOptimistic: OptimisticOp[];
}

// ===================== Action Types =====================

type BoardAction =
  | { type: 'CREATE_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: string; newOrder: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; newOrder: number } }
  | { type: 'SET_DRAG_STATE'; payload: DragState }
  | { type: 'CLEAR_DRAG_STATE' }
  | { type: 'REMOTE_UPDATE'; payload: { taskId: string; column: string; order: number; version: number; movedBy: string } }
  | { type: 'CONFIRM_OP'; payload: { opId: string } }
  | { type: 'RAISE_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; payload: { taskId: string } }
  | { type: 'SYNC_USERS'; payload: User[] };

// ===================== Reducer =====================

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'CREATE_TASK': {
      const newTask: Task = {
        id: `task-${Date.now()}`,
        title: action.payload.title,
        column: 'todo',
        order: state.tasks.filter(t => t.column === 'todo').length,
        version: 0,
        lastMovedBy: state.localUserId,
      };
      const optimisticOp: OptimisticOp = {
        opId: `op-${Date.now()}`,
        type: 'create',
        payload: { task: newTask },
        timestamp: Date.now(),
        confirmed: false,
      };
      return {
        ...state,
        tasks: [...state.tasks, newTask],
        pendingOptimistic: [...state.pendingOptimistic, optimisticOp],
      };
    }

    case 'MOVE_TASK': {
      const { taskId, toColumn, newOrder } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task) return state;

      const updatedTasks = state.tasks
        .filter(t => t.id !== taskId)
        .map(t => ({
          ...t,
          order: t.column === toColumn && t.order >= newOrder ? t.order + 1 : t.order,
        }));

      const movedTask: Task = {
        ...task,
        column: toColumn as Task['column'],
        order: newOrder,
        version: task.version + 1,
        lastMovedBy: state.localUserId,
      };

      const optimisticOp: OptimisticOp = {
        opId: `op-${Date.now()}`,
        type: 'move',
        payload: { taskId, fromColumn: task.column, toColumn, newOrder, version: task.version },
        timestamp: Date.now(),
        confirmed: false,
      };

      return {
        ...state,
        tasks: [...updatedTasks, movedTask],
        pendingOptimistic: [...state.pendingOptimistic, optimisticOp],
      };
    }

    case 'REORDER_TASK': {
      const { taskId, newOrder } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task) return state;

      const tasksInColumn = state.tasks.filter(t => t.column === task.column && t.id !== taskId);
      const reorderedTasks = tasksInColumn.map(t => ({
        ...t,
        order: t.order >= newOrder ? t.order + 1 : t.order,
      }));

      const updatedTask: Task = {
        ...task,
        order: newOrder,
        version: task.version + 1,
        lastMovedBy: state.localUserId,
      };

      const optimisticOp: OptimisticOp = {
        opId: `op-${Date.now()}`,
        type: 'move',
        payload: { taskId, fromColumn: task.column, toColumn: task.column, newOrder, version: task.version },
        timestamp: Date.now(),
        confirmed: false,
      };

      return {
        ...state,
        tasks: [...state.tasks.filter(t => t.column !== task.column), ...reorderedTasks, updatedTask],
        pendingOptimistic: [...state.pendingOptimistic, optimisticOp],
      };
    }

    case 'SET_DRAG_STATE':
      return { ...state, dragState: action.payload };

    case 'CLEAR_DRAG_STATE':
      return { ...state, dragState: null };

    case 'REMOTE_UPDATE': {
      const { taskId, column, order, version, movedBy } = action.payload;
      const conflictingOp = state.pendingOptimistic.find(
        op => op.type === 'move' && op.payload.taskId === taskId && !op.confirmed
      );

      if (conflictingOp) {
        const conflictInfo: ConflictInfo = {
          taskId,
          localMove: conflictingOp.payload,
          remoteMove: { taskId, fromColumn: column, toColumn: column, newOrder: order, version },
          timestamp: Date.now(),
        };
        return {
          ...state,
          tasks: state.tasks.map(t =>
            t.id === taskId
              ? { ...t, column: column as Task['column'], order, version, lastMovedBy: movedBy }
              : t
          ),
          conflicts: [...state.conflicts, conflictInfo],
        };
      }

      return {
        ...state,
        tasks: state.tasks.map(t =>
          t.id === taskId
            ? { ...t, column: column as Task['column'], order, version, lastMovedBy: movedBy }
            : t
        ),
      };
    }

    case 'CONFIRM_OP':
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.map(op =>
          op.opId === action.payload.opId ? { ...op, confirmed: true } : op
        ),
      };

    case 'RAISE_CONFLICT':
      return { ...state, conflicts: [...state.conflicts, action.payload] };

    case 'DISMISS_CONFLICT':
      return {
        ...state,
        conflicts: state.conflicts.filter(c => c.taskId !== action.payload.taskId),
      };

    case 'SYNC_USERS':
      return { ...state, users: action.payload };

    default:
      return state;
  }
}

// ===================== Components =====================

const BoardHeader: React.FC<{
  title: string;
  users: User[];
  onCreateTask: (title: string) => void;
}> = ({ title, users, onCreateTask }) => {
  const [inputValue, setInputValue] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onCreateTask(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <header className={styles.header}>
      <h1>{title}</h1>
      <div className={styles.userIndicator}>
        <span className={styles.userCount}>{users.length} users online</span>
        <div className={styles.userDots}>
          {users.map(u => (
            <span
              key={u.id}
              className={styles.userDot}
              style={{ backgroundColor: u.color }}
              title={u.name}
            />
          ))}
        </div>
      </div>
      <form onSubmit={handleSubmit} className={styles.newTaskForm}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Add a new task..."
          className={styles.newTaskInput}
        />
        <button type="submit" className={styles.newTaskButton}>Add</button>
      </form>
    </header>
  );
};

const TaskCard: React.FC<{
  task: Task;
  onDragStart: (taskId: string, sourceColumn: string) => void;
  hasConflict: boolean;
}> = ({ task, onDragStart, hasConflict }) => {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('taskId', task.id);
    e.dataTransfer.setData('sourceColumn', task.column);
    onDragStart(task.id, task.column);
  };

  return (
    <div
      draggable="true"
      onDragStart={handleDragStart}
      className={`${styles.taskCard} ${hasConflict ? styles.taskConflict : ''}`}
      style={{ opacity: hasConflict ? 0.7 : 1 }}
    >
      <div className={styles.taskContent}>
        <h3 className={styles.taskTitle}>{task.title}</h3>
        <div className={styles.taskMeta}>
          <span>{task.column}</span>
          <span>v{task.version}</span>
        </div>
      </div>
      {hasConflict && <div className={styles.conflictIndicator}>⚠️ Conflict</div>}
    </div>
  );
};

const Column: React.FC<{
  title: string;
  tasks: Task[];
  dragState: DragState | null;
  onDragOver: (column: string, overIndex: number | null) => void;
  onDrop: (taskId: string, toColumn: string, newOrder: number) => void;
  onDragStart: (taskId: string, sourceColumn: string) => void;
  conflicts: ConflictInfo[];
}> = ({ title, tasks, dragState, onDragOver, onDrop, onDragStart, conflicts }) => {
  const columnRef = useRef<HTMLDivElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!columnRef.current) return;

    const rect = columnRef.current.getBoundingClientRect();
    const mouseY = e.clientY - rect.top;
    const rowHeight = 60;
    const overIndex = Math.floor(mouseY / rowHeight);

    onDragOver(title, Math.min(overIndex, tasks.length));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    const sourceColumn = e.dataTransfer.getData('sourceColumn');
    
    if (sourceColumn === title) {
      const rect = columnRef.current?.getBoundingClientRect();
      const mouseY = e.clientY - (rect?.top || 0);
      const rowHeight = 60;
      const newOrder = Math.floor(mouseY / rowHeight);
      onDrop(taskId, title, Math.min(newOrder, tasks.length));
    } else {
      onDrop(taskId, title, tasks.length);
    }
  };

  const isDragOver = dragState?.overColumn === title;

  return (
    <div
      ref={columnRef}
      className={`${styles.column} ${isDragOver ? styles.columnDragOver : ''}`}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <h2 className={styles.columnTitle}>{title} ({tasks.length})</h2>
      <div className={styles.tasksContainer}>
        {tasks.map(task => {
          const hasConflict = conflicts.some(c => c.taskId === task.id);
          return (
            <TaskCard
              key={task.id}
              task={task}
              onDragStart={onDragStart}
              hasConflict={hasConflict}
            />
          );
        })}
      </div>
    </div>
  );
};

const ConflictToast: React.FC<{
  conflict: ConflictInfo;
  onDismiss: (taskId: string) => void;
}> = ({ conflict, onDismiss }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(conflict.taskId);
    }, 5000);
    return () => clearTimeout(timer);
  }, [conflict.taskId, onDismiss]);

  return (
    <div className={styles.conflictToast}>
      <p>
        User {conflict.remoteMove.fromColumn} also moved this task to{' '}
        {conflict.remoteMove.toColumn}. Your change was applied. Click to revert.
      </p>
      <button
        className={styles.dismissButton}
        onClick={() => onDismiss(conflict.taskId)}
      >
        ×
      </button>
    </div>
  );
};

const CollaborativeTodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, {
    tasks: [
      { id: 'task-1', title: 'Design review', column: 'todo', order: 0, version: 0, lastMovedBy: 'user-1' },
      { id: 'task-2', title: 'API implementation', column: 'inProgress', order: 0, version: 0, lastMovedBy: 'user-1' },
      { id: 'task-3', title: 'Testing', column: 'done', order: 0, version: 0, lastMovedBy: 'user-1' },
    ],
    users: [
      { id: 'user-1', name: 'Alice', color: '#4caf50' },
      { id: 'user-2', name: 'Bob', color: '#2196f3' },
    ],
    localUserId: 'user-1',
    dragState: null,
    conflicts: [],
    pendingOptimistic: [],
  });

  // Simulate real-time sync
  useEffect(() => {
    const interval = setInterval(() => {
      const randomAction = Math.random();
      if (randomAction < 0.2) {
        dispatch({
          type: 'REMOTE_UPDATE',
          payload: {
            taskId: `remote-${Date.now()}`,
            column: 'todo',
            order: state.tasks.filter(t => t.column === 'todo').length,
            version: 0,
            movedBy: 'user-2',
          },
        });
      } else if (randomAction < 0.8) {
        if (state.tasks.length > 0) {
          const randomTask = state.tasks[Math.floor(Math.random() * state.tasks.length)];
          const columns: Task['column'][] = ['todo', 'inProgress', 'done'];
          const randomColumn = columns.filter(c => c !== randomTask.column)[Math.floor(Math.random() * 2)] || columns[0];
          
          dispatch({
            type: 'REMOTE_UPDATE',
            payload: {
              taskId: randomTask.id,
              column: randomColumn,
              order: state.tasks.filter(t => t.column === randomColumn).length,
              version: randomTask.version + 1,
              movedBy: 'user-2',
            },
          });
        }
      } else {
        if (state.tasks.length > 0) {
          const randomTask = state.tasks[Math.floor(Math.random() * state.tasks.length)];
          dispatch({
            type: 'REMOTE_UPDATE',
            payload: {
              taskId: randomTask.id,
              column: randomTask.column,
              order: Math.max(0, randomTask.order - 1),
              version: randomTask.version + 1,
              movedBy: 'user-2',
            },
          });
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [state.tasks]);

  // Confirm optimistic ops after delay
  useEffect(() => {
    const unconfirmedOps = state.pendingOptimistic.filter(op => !op.confirmed);
    unconfirmedOps.forEach(op => {
      setTimeout(() => {
        dispatch({ type: 'CONFIRM_OP', payload: { opId: op.opId } });
      }, 500);
    });
  }, [state.pendingOptimistic]);

  const handleCreateTask = (title: string) => {
    dispatch({ type: 'CREATE_TASK', payload: { title } });
  };

  const handleDragStart = (taskId: string, sourceColumn: string) => {
    dispatch({
      type: 'SET_DRAG_STATE',
      payload: { taskId, sourceColumn, overColumn: null, overIndex: null },
    });
  };

  const handleDragOver = (column: string, overIndex: number | null) => {
    if (state.dragState) {
      dispatch({
        type: 'SET_DRAG_STATE',
        payload: { ...state.dragState, overColumn: column, overIndex },
      });
    }
  };

  const handleDrop = (taskId: string, toColumn: string, newOrder: number) => {
    const sourceColumn = state.dragState?.sourceColumn;
    if (sourceColumn === toColumn) {
      dispatch({ type: 'REORDER_TASK', payload: { taskId, newOrder } });
    } else {
      dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn, newOrder } });
    }
    dispatch({ type: 'CLEAR_DRAG_STATE' });
  };

  const handleDismissConflict = (taskId: string) => {
    dispatch({ type: 'DISMISS_CONFLICT', payload: { taskId } });
  };

  const todoTasks = state.tasks.filter(t => t.column === 'todo').sort((a, b) => a.order - b.order);
  const inProgressTasks = state.tasks.filter(t => t.column === 'inProgress').sort((a, b) => a.order - b.order);
  const doneTasks = state.tasks.filter(t => t.column === 'done').sort((a, b) => a.order - b.order);

  return (
    <div className={styles.board}>
      <BoardHeader
        title="Collaborative Todo Board"
        users={state.users}
        onCreateTask={handleCreateTask}
      />

      <div className={styles.columnsContainer}>
        <Column
          title="todo"
          tasks={todoTasks}
          dragState={state.dragState}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
          conflicts={state.conflicts}
        />
        <Column
          title="inProgress"
          tasks={inProgressTasks}
          dragState={state.dragState}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
          conflicts={state.conflicts}
        />
        <Column
          title="done"
          tasks={doneTasks}
          dragState={state.dragState}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
          conflicts={state.conflicts}
        />
      </div>

      <div>
        {state.conflicts.map(conflict => (
          <ConflictToast
            key={conflict.taskId}
            conflict={conflict}
            onDismiss={handleDismissConflict}
          />
        ))}
      </div>
    </div>
  );
};

export default CollaborativeTodoBoard;
```
