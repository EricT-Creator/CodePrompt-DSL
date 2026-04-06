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

// ─── CSS Module Simulation (inline object styles as CSS Modules) ────────────

const styles: Record<string, React.CSSProperties> = {
  board: {
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
    maxWidth: 1100,
    margin: '0 auto',
    padding: 20,
    minHeight: '100vh',
    background: '#f0f2f5',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
    padding: '16px 20px',
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: 700,
    color: '#1a1a2e',
    margin: 0,
  },
  syncBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#666',
  },
  syncDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    display: 'inline-block',
  },
  columnsContainer: {
    display: 'flex',
    gap: 16,
  },
  column: {
    flex: 1,
    background: '#fff',
    borderRadius: 12,
    padding: 16,
    minHeight: 400,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    transition: 'box-shadow 0.2s, background 0.2s',
  },
  columnDragOver: {
    background: '#e8f0fe',
    boxShadow: '0 0 0 2px #4285f4',
  },
  columnHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottom: '2px solid #f0f2f5',
  },
  columnTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: '#333',
    margin: 0,
  },
  taskCount: {
    fontSize: 12,
    background: '#f0f2f5',
    padding: '2px 10px',
    borderRadius: 12,
    color: '#666',
    fontWeight: 500,
  },
  taskCard: {
    padding: '12px 14px',
    marginBottom: 10,
    background: '#fafbfc',
    borderRadius: 8,
    border: '1px solid #e8eaed',
    cursor: 'grab',
    transition: 'transform 0.15s, box-shadow 0.15s',
  },
  taskCardDragging: {
    opacity: 0.5,
  },
  taskTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#1a1a2e',
    marginBottom: 4,
  },
  taskDesc: {
    fontSize: 12,
    color: '#666',
    lineHeight: 1.4,
  },
  taskMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    fontSize: 11,
    color: '#999',
  },
  deleteBtn: {
    background: 'none',
    border: 'none',
    color: '#ccc',
    cursor: 'pointer',
    fontSize: 14,
    padding: '2px 6px',
    borderRadius: 4,
  },
  fab: {
    position: 'fixed' as const,
    bottom: 32,
    right: 32,
    width: 56,
    height: 56,
    borderRadius: '50%',
    background: '#4285f4',
    color: '#fff',
    border: 'none',
    fontSize: 28,
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(66,133,244,0.4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  newTaskOverlay: {
    position: 'fixed' as const,
    inset: 0,
    background: 'rgba(0,0,0,0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  newTaskForm: {
    background: '#fff',
    borderRadius: 12,
    padding: 24,
    width: 380,
    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
  },
  formTitle: {
    fontSize: 18,
    fontWeight: 600,
    marginBottom: 16,
    margin: 0,
    color: '#1a1a2e',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ddd',
    borderRadius: 8,
    fontSize: 14,
    marginBottom: 12,
    boxSizing: 'border-box' as const,
    outline: 'none',
  },
  textarea: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ddd',
    borderRadius: 8,
    fontSize: 14,
    marginBottom: 16,
    boxSizing: 'border-box' as const,
    resize: 'vertical' as const,
    minHeight: 80,
    outline: 'none',
  },
  formActions: {
    display: 'flex',
    gap: 10,
    justifyContent: 'flex-end',
  },
  btnPrimary: {
    padding: '8px 20px',
    background: '#4285f4',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    cursor: 'pointer',
    fontWeight: 500,
  },
  btnCancel: {
    padding: '8px 20px',
    background: '#f0f2f5',
    color: '#666',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    cursor: 'pointer',
  },
  conflictToast: {
    position: 'fixed' as const,
    top: 20,
    right: 20,
    background: '#fff3cd',
    border: '1px solid #ffc107',
    borderRadius: 8,
    padding: '12px 16px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    zIndex: 200,
    maxWidth: 340,
  },
  conflictText: {
    fontSize: 13,
    color: '#856404',
    margin: 0,
  },
  conflictActions: {
    display: 'flex',
    gap: 8,
    marginTop: 8,
  },
  conflictBtn: {
    padding: '4px 12px',
    fontSize: 12,
    border: '1px solid #ffc107',
    borderRadius: 6,
    background: '#fff',
    color: '#856404',
    cursor: 'pointer',
  },
};

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
      style={styles.taskCard}
    >
      <div style={styles.taskTitle}>{task.title}</div>
      {task.description && <div style={styles.taskDesc}>{task.description}</div>}
      <div style={styles.taskMeta}>
        <span>{task.lastModifiedBy} · v{task.version}</span>
        <button
          style={styles.deleteBtn}
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

  const colStyle: React.CSSProperties = {
    ...styles.column,
    ...(isDragOver ? styles.columnDragOver : {}),
  };

  const colorMap: Record<string, string> = {
    todo: '#4285f4',
    'in-progress': '#fbbc04',
    done: '#34a853',
  };

  return (
    <div
      style={colStyle}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div style={styles.columnHeader}>
        <h3 style={{ ...styles.columnTitle, borderLeft: `3px solid ${colorMap[column.id] || '#ccc'}`, paddingLeft: 8 }}>
          {column.title}
        </h3>
        <span style={styles.taskCount}>{tasks.length}</span>
      </div>
      <div>
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} columnId={column.id} onDelete={handleDelete} />
        ))}
        {tasks.length === 0 && (
          <div style={{ textAlign: 'center', padding: 24, color: '#bbb', fontSize: 13 }}>
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
    <div style={styles.conflictToast}>
      <p style={styles.conflictText}>⚠️ Conflict detected on task: {conflict.message}</p>
      <div style={styles.conflictActions}>
        <button style={styles.conflictBtn} onClick={() => dispatch({ type: 'RESOLVE_CONFLICT', taskId: conflict.taskId })}>
          Keep Local
        </button>
        <button style={styles.conflictBtn} onClick={() => dispatch({ type: 'RESOLVE_CONFLICT', taskId: conflict.taskId })}>
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
    <div style={styles.board}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.headerTitle}>📋 Collaborative Todo Board</h1>
        <div style={styles.syncBadge}>
          <span
            style={{
              ...styles.syncDot,
              background: state.isSyncing ? '#fbbc04' : '#34a853',
            }}
          />
          {state.isSyncing ? 'Syncing...' : state.lastSyncAt ? `Last sync: ${formatTime(state.lastSyncAt)}` : 'Connected'}
        </div>
      </div>

      {/* Columns */}
      <div style={styles.columnsContainer}>
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
      <button style={styles.fab} onClick={() => dispatch({ type: 'TOGGLE_NEW_TASK_FORM' })} title="Add Task">
        +
      </button>

      {/* New Task Form */}
      {state.showNewTaskForm && (
        <div style={styles.newTaskOverlay} onClick={() => dispatch({ type: 'TOGGLE_NEW_TASK_FORM' })}>
          <div style={styles.newTaskForm} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.formTitle}>New Task</h2>
            <input
              style={styles.input}
              placeholder="Task title"
              value={state.newTaskTitle}
              onChange={(e) => dispatch({ type: 'SET_NEW_TASK_TITLE', value: e.target.value })}
              autoFocus
            />
            <textarea
              style={styles.textarea}
              placeholder="Description (optional)"
              value={state.newTaskDescription}
              onChange={(e) => dispatch({ type: 'SET_NEW_TASK_DESCRIPTION', value: e.target.value })}
            />
            <div style={styles.formActions}>
              <button style={styles.btnCancel} onClick={() => dispatch({ type: 'TOGGLE_NEW_TASK_FORM' })}>
                Cancel
              </button>
              <button style={styles.btnPrimary} onClick={handleAddTask}>
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
