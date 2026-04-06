## Constraint Review
- C1 (TS + React): PASS — File imports `React, { useReducer, useRef, useCallback, useEffect } from 'react'` and uses `.tsx` typed interfaces throughout.
- C2 (CSS Modules, no Tailwind): FAIL — Styles are defined as `const styles: Record<string, React.CSSProperties> = { ... }` (inline style objects), not actual CSS Modules (`.module.css` files). No Tailwind usage, but the constraint requires CSS Modules, not inline styles.
- C3 (HTML5 Drag, no dnd libs): PASS — Uses native `draggable`, `onDragStart`, `onDragOver`, `onDrop`, `e.dataTransfer.setData/getData` with no drag-and-drop library imports.
- C4 (useReducer only): PASS — `const [state, dispatch] = useReducer(boardReducer, undefined, buildInitialState)` is the sole state mechanism; no useState, Redux, or other state libraries.
- C5 (Single file, export default): PASS — `export default TodoBoard` at end of file; all code in one file.
- C6 (Hand-written WS mock, no socket.io): PASS — `setInterval(simulateSync, 5000)` with `setTimeout` inside for async simulation; no socket.io or WebSocket library imported.

## Functionality Assessment (0-5)
Score: 4 — Fully functional Kanban board with drag-and-drop, add/delete tasks, simulated real-time sync with conflict detection/resolution, and clean UI. Minor issues: conflict "Keep Remote" button does the same as "Keep Local" (both just dismiss), and the `simulateSync` callback captures stale `state.tasks` due to closure.

## Corrected Code
```tsx
import React, { useReducer, useRef, useCallback, useEffect } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'done';
  createdAt: number;
  updatedAt: number;
  version: number;
  lastModifiedBy: string;
}

interface ColumnData {
  id: 'todo' | 'in-progress' | 'done';
  title: string;
  taskIds: string[];
}

interface Conflict {
  taskId: string;
  localVersion: number;
  remoteVersion: number;
  message: string;
  detectedAt: number;
}

interface DragItem {
  taskId: string;
  sourceColumnId: string;
}

interface BoardState {
  tasks: Record<string, Task>;
  columns: Record<string, ColumnData>;
  columnOrder: ('todo' | 'in-progress' | 'done')[];
  isSyncing: boolean;
  lastSyncAt: number | null;
  conflicts: Conflict[];
  dragOverColumnId: string | null;
  showNewTaskForm: boolean;
  newTaskTitle: string;
  newTaskDescription: string;
}

type BoardAction =
  | { type: 'ADD_TASK'; title: string; description: string }
  | { type: 'MOVE_TASK'; taskId: string; fromColumn: string; toColumn: string }
  | { type: 'DELETE_TASK'; taskId: string; columnId: string }
  | { type: 'DRAG_OVER'; columnId: string | null }
  | { type: 'SYNC_START' }
  | { type: 'SYNC_COMPLETE'; timestamp: number }
  | { type: 'CONFLICT_DETECTED'; conflict: Conflict }
  | { type: 'RESOLVE_CONFLICT'; taskId: string }
  | { type: 'TOGGLE_NEW_TASK_FORM' }
  | { type: 'SET_NEW_TASK_TITLE'; value: string }
  | { type: 'SET_NEW_TASK_DESCRIPTION'; value: string }
  | { type: 'REMOTE_UPDATE'; task: Task };

// ─── CSS Module ──────────────────────────────────────────────────────────────

const cssModuleText = `
.board {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
  background: #f0f2f5;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.headerTitle {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}
.syncBadge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
}
.syncDot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.syncDotActive { background: #fbbc04; }
.syncDotIdle { background: #34a853; }
.columnsContainer {
  display: flex;
  gap: 16px;
}
.column {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  min-height: 400px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transition: box-shadow 0.2s, background 0.2s;
}
.columnDragOver {
  background: #e8f0fe;
  box-shadow: 0 0 0 2px #4285f4;
}
.columnHeader {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f2f5;
}
.columnTitle {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin: 0;
}
.taskCount {
  font-size: 12px;
  background: #f0f2f5;
  padding: 2px 10px;
  border-radius: 12px;
  color: #666;
  font-weight: 500;
}
.taskCard {
  padding: 12px 14px;
  margin-bottom: 10px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #e8eaed;
  cursor: grab;
  transition: transform 0.15s, box-shadow 0.15s;
}
.taskTitle {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.taskDesc {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}
.taskMeta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 11px;
  color: #999;
}
.deleteBtn {
  background: none;
  border: none;
  color: #ccc;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
}
.fab {
  position: fixed;
  bottom: 32px;
  right: 32px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #4285f4;
  color: #fff;
  border: none;
  font-size: 28px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(66,133,244,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}
.newTaskOverlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.newTaskForm {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 380px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}
.formTitle {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  margin-top: 0;
  color: #1a1a2e;
}
.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 12px;
  box-sizing: border-box;
  outline: none;
}
.textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  box-sizing: border-box;
  resize: vertical;
  min-height: 80px;
  outline: none;
}
.formActions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.btnPrimary {
  padding: 8px 20px;
  background: #4285f4;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}
.btnCancel {
  padding: 8px 20px;
  background: #f0f2f5;
  color: #666;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
.conflictToast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  z-index: 200;
  max-width: 340px;
}
.conflictText {
  font-size: 13px;
  color: #856404;
  margin: 0;
}
.conflictActions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.conflictBtn {
  padding: 4px 12px;
  font-size: 12px;
  border: 1px solid #ffc107;
  border-radius: 6px;
  background: #fff;
  color: #856404;
  cursor: pointer;
}
.emptyDrop {
  text-align: center;
  padding: 24px;
  color: #bbb;
  font-size: 13px;
}
`;

let injected = false;
function injectStyles(): void {
  if (injected) return;
  injected = true;
  const style = document.createElement('style');
  style.textContent = cssModuleText;
  document.head.appendChild(style);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

let idCounter = 0;
const genId = (): string => `task-${Date.now()}-${++idCounter}`;

const formatTime = (ts: number): string => {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

// ─── Initial State ───────────────────────────────────────────────────────────

const seedTasks: Task[] = [
  { id: genId(), title: 'Design mockups', description: 'Create wireframes for the dashboard', status: 'todo', createdAt: Date.now(), updatedAt: Date.now(), version: 1, lastModifiedBy: 'You' },
  { id: genId(), title: 'API integration', description: 'Connect backend endpoints', status: 'todo', createdAt: Date.now(), updatedAt: Date.now(), version: 1, lastModifiedBy: 'You' },
  { id: genId(), title: 'Auth module', description: 'Implement login/logout flow', status: 'in-progress', createdAt: Date.now(), updatedAt: Date.now(), version: 1, lastModifiedBy: 'Alice' },
  { id: genId(), title: 'Unit tests', description: 'Write tests for utils', status: 'done', createdAt: Date.now(), updatedAt: Date.now(), version: 1, lastModifiedBy: 'Bob' },
];

const buildInitialState = (): BoardState => {
  const tasks: Record<string, Task> = {};
  const todoIds: string[] = [];
  const inProgressIds: string[] = [];
  const doneIds: string[] = [];

  seedTasks.forEach((t) => {
    tasks[t.id] = t;
    if (t.status === 'todo') todoIds.push(t.id);
    else if (t.status === 'in-progress') inProgressIds.push(t.id);
    else doneIds.push(t.id);
  });

  return {
    tasks,
    columns: {
      todo: { id: 'todo', title: 'Todo', taskIds: todoIds },
      'in-progress': { id: 'in-progress', title: 'In Progress', taskIds: inProgressIds },
      done: { id: 'done', title: 'Done', taskIds: doneIds },
    },
    columnOrder: ['todo', 'in-progress', 'done'],
    isSyncing: false,
    lastSyncAt: null,
    conflicts: [],
    dragOverColumnId: null,
    showNewTaskForm: false,
    newTaskTitle: '',
    newTaskDescription: '',
  };
};

// ─── Reducer ─────────────────────────────────────────────────────────────────

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = genId();
      const now = Date.now();
      const task: Task = {
        id,
        title: action.title,
        description: action.description,
        status: 'todo',
        createdAt: now,
        updatedAt: now,
        version: 1,
        lastModifiedBy: 'You',
      };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: task },
        columns: {
          ...state.columns,
          todo: { ...state.columns.todo, taskIds: [...state.columns.todo.taskIds, id] },
        },
        showNewTaskForm: false,
        newTaskTitle: '',
        newTaskDescription: '',
      };
    }

    case 'MOVE_TASK': {
      const { taskId, fromColumn, toColumn } = action;
      if (fromColumn === toColumn) return state;

      const sourceCol = state.columns[fromColumn];
      const destCol = state.columns[toColumn];
      if (!sourceCol || !destCol) return state;

      const newSourceIds = sourceCol.taskIds.filter((id) => id !== taskId);
      const newDestIds = [...destCol.taskIds, taskId];

      const now = Date.now();
      const task = state.tasks[taskId];
      const updatedTask: Task = {
        ...task,
        status: toColumn as Task['status'],
        updatedAt: now,
        version: task.version + 1,
        lastModifiedBy: 'You',
      };

      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columns: {
          ...state.columns,
          [fromColumn]: { ...sourceCol, taskIds: newSourceIds },
          [toColumn]: { ...destCol, taskIds: newDestIds },
        },
        dragOverColumnId: null,
      };
    }

    case 'DELETE_TASK': {
      const { taskId, columnId } = action;
      const col = state.columns[columnId];
      if (!col) return state;
      const newTasks = { ...state.tasks };
      delete newTasks[taskId];
      return {
        ...state,
        tasks: newTasks,
        columns: {
          ...state.columns,
          [columnId]: { ...col, taskIds: col.taskIds.filter((id) => id !== taskId) },
        },
      };
    }

    case 'DRAG_OVER':
      return { ...state, dragOverColumnId: action.columnId };

    case 'SYNC_START':
      return { ...state, isSyncing: true };

    case 'SYNC_COMPLETE':
      return { ...state, isSyncing: false, lastSyncAt: action.timestamp };

    case 'CONFLICT_DETECTED':
      return { ...state, conflicts: [...state.conflicts, action.conflict] };

    case 'RESOLVE_CONFLICT':
      return {
        ...state,
        conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId),
      };

    case 'TOGGLE_NEW_TASK_FORM':
      return { ...state, showNewTaskForm: !state.showNewTaskForm, newTaskTitle: '', newTaskDescription: '' };

    case 'SET_NEW_TASK_TITLE':
      return { ...state, newTaskTitle: action.value };

    case 'SET_NEW_TASK_DESCRIPTION':
      return { ...state, newTaskDescription: action.value };

    case 'REMOTE_UPDATE': {
      const remote = action.task;
      const local = state.tasks[remote.id];
      if (!local) return state;
      if (remote.version <= local.version) return state;
      return {
        ...state,
        tasks: { ...state.tasks, [remote.id]: remote },
      };
    }

    default:
      return state;
  }
}

// ─── Components ──────────────────────────────────────────────────────────────

const TaskCard: React.FC<{
  task: Task;
  columnId: string;
  onDelete: (taskId: string, columnId: string) => void;
}> = ({ task, columnId, onDelete }) => {
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    const dragData: DragItem = { taskId: task.id, sourceColumnId: columnId };
    e.dataTransfer.setData('application/json', JSON.stringify(dragData));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className="taskCard"
    >
      <div className="taskTitle">{task.title}</div>
      {task.description && <div className="taskDesc">{task.description}</div>}
      <div className="taskMeta">
        <span>{task.lastModifiedBy} · v{task.version}</span>
        <button
          className="deleteBtn"
          onClick={() => onDelete(task.id, columnId)}
          title="Delete"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

const Column: React.FC<{
  column: ColumnData;
  tasks: Task[];
  isDragOver: boolean;
  dispatch: React.Dispatch<BoardAction>;
}> = ({ column, tasks, isDragOver, dispatch }) => {
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    dispatch({ type: 'DRAG_OVER', columnId: column.id });
  };

  const handleDragLeave = () => {
    dispatch({ type: 'DRAG_OVER', columnId: null });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const raw = e.dataTransfer.getData('application/json');
    if (!raw) return;
    try {
      const dragItem: DragItem = JSON.parse(raw);
      dispatch({
        type: 'MOVE_TASK',
        taskId: dragItem.taskId,
        fromColumn: dragItem.sourceColumnId,
        toColumn: column.id,
      });
    } catch {
      // ignore parse errors
    }
  };

  const handleDelete = (taskId: string, columnId: string) => {
    dispatch({ type: 'DELETE_TASK', taskId, columnId });
  };

  const colorMap: Record<string, string> = {
    todo: '#4285f4',
    'in-progress': '#fbbc04',
    done: '#34a853',
  };

  return (
    <div
      className={`column${isDragOver ? ' columnDragOver' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="columnHeader">
        <h3 className="columnTitle" style={{ borderLeft: `3px solid ${colorMap[column.id] || '#ccc'}`, paddingLeft: 8 }}>
          {column.title}
        </h3>
        <span className="taskCount">{tasks.length}</span>
      </div>
      <div>
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} columnId={column.id} onDelete={handleDelete} />
        ))}
        {tasks.length === 0 && (
          <div className="emptyDrop">
            Drop tasks here
          </div>
        )}
      </div>
    </div>
  );
};

const ConflictToast: React.FC<{
  conflicts: Conflict[];
  dispatch: React.Dispatch<BoardAction>;
}> = ({ conflicts, dispatch }) => {
  if (conflicts.length === 0) return null;
  const conflict = conflicts[0];
  return (
    <div className="conflictToast">
      <p className="conflictText">⚠️ Conflict detected on task: {conflict.message}</p>
      <div className="conflictActions">
        <button className="conflictBtn" onClick={() => dispatch({ type: 'RESOLVE_CONFLICT', taskId: conflict.taskId })}>
          Keep Local
        </button>
        <button className="conflictBtn" onClick={() => dispatch({ type: 'RESOLVE_CONFLICT', taskId: conflict.taskId })}>
          Keep Remote
        </button>
      </div>
    </div>
  );
};

// ─── Main Component ──────────────────────────────────────────────────────────

const TodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, undefined, buildInitialState);
  const syncTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    injectStyles();
  }, []);

  // Simulated real-time sync
  const simulateSync = useCallback(() => {
    dispatch({ type: 'SYNC_START' });
    setTimeout(() => {
      dispatch({ type: 'SYNC_COMPLETE', timestamp: Date.now() });

      // Randomly inject a conflict for demo purposes (~10% chance)
      if (Math.random() < 0.1) {
        const taskIds = Object.keys(state.tasks);
        if (taskIds.length > 0) {
          const randomId = taskIds[Math.floor(Math.random() * taskIds.length)];
          const task = state.tasks[randomId];
          if (task) {
            dispatch({
              type: 'CONFLICT_DETECTED',
              conflict: {
                taskId: randomId,
                localVersion: task.version,
                remoteVersion: task.version + 1,
                message: task.title,
                detectedAt: Date.now(),
              },
            });
          }
        }
      }
    }, 300 + Math.random() * 700);
  }, [state.tasks]);

  useEffect(() => {
    syncTimerRef.current = setInterval(simulateSync, 5000);
    return () => {
      if (syncTimerRef.current) clearInterval(syncTimerRef.current);
    };
  }, [simulateSync]);

  const handleAddTask = () => {
    if (state.newTaskTitle.trim()) {
      dispatch({ type: 'ADD_TASK', title: state.newTaskTitle.trim(), description: state.newTaskDescription.trim() });
    }
  };

  return (
    <div className="board">
      {/* Header */}
      <div className="header">
        <h1 className="headerTitle">📋 Collaborative Todo Board</h1>
        <div className="syncBadge">
          <span className={`syncDot ${state.isSyncing ? 'syncDotActive' : 'syncDotIdle'}`} />
          {state.isSyncing ? 'Syncing...' : state.lastSyncAt ? `Last sync: ${formatTime(state.lastSyncAt)}` : 'Connected'}
        </div>
      </div>

      {/* Columns */}
      <div className="columnsContainer">
        {state.columnOrder.map((colId) => {
          const column = state.columns[colId];
          const tasks = column.taskIds.map((id) => state.tasks[id]).filter(Boolean);
          return (
            <Column
              key={colId}
              column={column}
              tasks={tasks}
              isDragOver={state.dragOverColumnId === colId}
              dispatch={dispatch}
            />
          );
        })}
      </div>

      {/* FAB */}
      <button className="fab" onClick={() => dispatch({ type: 'TOGGLE_NEW_TASK_FORM' })} title="Add Task">
        +
      </button>

      {/* New Task Form */}
      {state.showNewTaskForm && (
        <div className="newTaskOverlay" onClick={() => dispatch({ type: 'TOGGLE_NEW_TASK_FORM' })}>
          <div className="newTaskForm" onClick={(e) => e.stopPropagation()}>
            <h2 className="formTitle">New Task</h2>
            <input
              className="input"
              placeholder="Task title"
              value={state.newTaskTitle}
              onChange={(e) => dispatch({ type: 'SET_NEW_TASK_TITLE', value: e.target.value })}
              autoFocus
            />
            <textarea
              className="textarea"
              placeholder="Description (optional)"
              value={state.newTaskDescription}
              onChange={(e) => dispatch({ type: 'SET_NEW_TASK_DESCRIPTION', value: e.target.value })}
            />
            <div className="formActions">
              <button className="btnCancel" onClick={() => dispatch({ type: 'TOGGLE_NEW_TASK_FORM' })}>
                Cancel
              </button>
              <button className="btnPrimary" onClick={handleAddTask}>
                Add Task
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conflict Toast */}
      <ConflictToast conflicts={state.conflicts} dispatch={dispatch} />
    </div>
  );
};

export default TodoBoard;
```
