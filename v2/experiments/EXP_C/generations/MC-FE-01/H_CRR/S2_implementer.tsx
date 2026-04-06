import React, { useReducer, useEffect, useCallback, useRef } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

type TaskStatus = 'todo' | 'in-progress' | 'done';

interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  createdAt: number;
  updatedAt: number;
  version: number;
}

interface OptimisticUpdate {
  taskId: string;
  previousStatus: TaskStatus;
  pendingStatus: TaskStatus;
  timestamp: number;
}

interface ConflictHint {
  taskId: string;
  message: string;
  resolvedAt: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: TaskStatus[];
  optimisticUpdates: Record<string, OptimisticUpdate>;
  conflictHints: ConflictHint[];
  connected: boolean;
}

type BoardAction =
  | { type: 'ADD_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; newStatus: TaskStatus } }
  | { type: 'CONFIRM_MOVE'; payload: { taskId: string } }
  | { type: 'REJECT_MOVE'; payload: { taskId: string } }
  | { type: 'DETECT_CONFLICT'; payload: { taskId: string; message: string } }
  | { type: 'RESOLVE_CONFLICT'; payload: { taskId: string; resolution: 'mine' | 'theirs'; serverStatus: TaskStatus } }
  | { type: 'REMOTE_UPDATE'; payload: { taskId: string; newStatus: TaskStatus } }
  | { type: 'SET_CONNECTED'; payload: boolean };

// ─── CSS Module mock (inline styles as CSS module alternative) ───────────────

const styles: Record<string, React.CSSProperties> = {
  board: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: 960,
    margin: '0 auto',
    padding: 20,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    padding: '12px 16px',
    borderRadius: 8,
    background: '#f8f9fa',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: 700,
    margin: 0,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    display: 'inline-block',
    marginRight: 6,
  },
  columns: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 16,
  },
  column: {
    background: '#f1f3f5',
    borderRadius: 8,
    padding: 12,
    minHeight: 300,
  },
  columnHeader: {
    fontSize: 15,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    marginBottom: 12,
    paddingBottom: 8,
    borderBottom: '2px solid #dee2e6',
  },
  card: {
    background: '#ffffff',
    borderRadius: 6,
    padding: '10px 14px',
    marginBottom: 8,
    cursor: 'grab',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    border: '2px solid transparent',
    transition: 'border-color 0.15s, opacity 0.15s',
  },
  cardDragging: {
    opacity: 0.5,
  },
  cardConflict: {
    border: '2px solid #e03131',
    background: '#fff5f5',
  },
  cardPending: {
    border: '2px dashed #fab005',
  },
  cardTitle: {
    fontSize: 14,
    margin: 0,
  },
  cardMeta: {
    fontSize: 11,
    color: '#868e96',
    marginTop: 4,
  },
  dropZone: {
    border: '2px dashed #4dabf7',
    borderRadius: 6,
    background: '#e7f5ff',
    minHeight: 40,
  },
  conflictBar: {
    display: 'flex',
    gap: 6,
    marginTop: 8,
  },
  conflictBtn: {
    fontSize: 11,
    padding: '3px 8px',
    borderRadius: 4,
    border: '1px solid #dee2e6',
    cursor: 'pointer',
    background: '#fff',
  },
  addForm: {
    display: 'flex',
    gap: 8,
    marginBottom: 16,
  },
  addInput: {
    flex: 1,
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ced4da',
    fontSize: 14,
  },
  addBtn: {
    padding: '8px 16px',
    borderRadius: 6,
    border: 'none',
    background: '#228be6',
    color: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

let idCounter = 0;
const uid = (): string => `task_${Date.now()}_${++idCounter}`;

const COLUMN_LABELS: Record<TaskStatus, string> = {
  'todo': 'To Do',
  'in-progress': 'In Progress',
  'done': 'Done',
};

// ─── Initial state ───────────────────────────────────────────────────────────

const MOCK_TASKS: Task[] = [
  { id: uid(), title: 'Design landing page', status: 'todo', createdAt: Date.now(), updatedAt: Date.now(), version: 1 },
  { id: uid(), title: 'Set up CI/CD pipeline', status: 'todo', createdAt: Date.now(), updatedAt: Date.now(), version: 1 },
  { id: uid(), title: 'Write unit tests', status: 'in-progress', createdAt: Date.now(), updatedAt: Date.now(), version: 1 },
  { id: uid(), title: 'Code review PR #42', status: 'in-progress', createdAt: Date.now(), updatedAt: Date.now(), version: 1 },
  { id: uid(), title: 'Deploy v1.0', status: 'done', createdAt: Date.now(), updatedAt: Date.now(), version: 1 },
];

function buildInitialState(): BoardState {
  const tasks: Record<string, Task> = {};
  for (const t of MOCK_TASKS) {
    tasks[t.id] = t;
  }
  return {
    tasks,
    columnOrder: ['todo', 'in-progress', 'done'],
    optimisticUpdates: {},
    conflictHints: [],
    connected: true,
  };
}

// ─── Reducer ─────────────────────────────────────────────────────────────────

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = uid();
      const now = Date.now();
      const newTask: Task = {
        id,
        title: action.payload.title,
        status: 'todo',
        createdAt: now,
        updatedAt: now,
        version: 1,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: newTask },
      };
    }

    case 'MOVE_TASK': {
      const { taskId, newStatus } = action.payload;
      const task = state.tasks[taskId];
      if (!task || task.status === newStatus) return state;

      const optimistic: OptimisticUpdate = {
        taskId,
        previousStatus: task.status,
        pendingStatus: newStatus,
        timestamp: Date.now(),
      };

      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, status: newStatus, updatedAt: Date.now() },
        },
        optimisticUpdates: {
          ...state.optimisticUpdates,
          [taskId]: optimistic,
        },
      };
    }

    case 'CONFIRM_MOVE': {
      const { taskId } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const newOpts = { ...state.optimisticUpdates };
      delete newOpts[taskId];
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, version: task.version + 1 },
        },
        optimisticUpdates: newOpts,
      };
    }

    case 'REJECT_MOVE': {
      const { taskId } = action.payload;
      const opt = state.optimisticUpdates[taskId];
      const task = state.tasks[taskId];
      if (!task || !opt) return state;
      const newOpts = { ...state.optimisticUpdates };
      delete newOpts[taskId];
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, status: opt.previousStatus, updatedAt: Date.now() },
        },
        optimisticUpdates: newOpts,
      };
    }

    case 'DETECT_CONFLICT': {
      const hint: ConflictHint = {
        taskId: action.payload.taskId,
        message: action.payload.message,
        resolvedAt: 0,
      };
      return {
        ...state,
        conflictHints: [...state.conflictHints, hint],
      };
    }

    case 'RESOLVE_CONFLICT': {
      const { taskId, resolution, serverStatus } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;

      const finalStatus = resolution === 'theirs' ? serverStatus : task.status;
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, status: finalStatus, version: task.version + 1, updatedAt: Date.now() },
        },
        conflictHints: state.conflictHints.filter((h) => h.taskId !== taskId),
        optimisticUpdates: (() => {
          const o = { ...state.optimisticUpdates };
          delete o[taskId];
          return o;
        })(),
      };
    }

    case 'REMOTE_UPDATE': {
      const { taskId, newStatus } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;

      if (state.optimisticUpdates[taskId]) {
        return state;
      }

      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: { ...task, status: newStatus, version: task.version + 1, updatedAt: Date.now() },
        },
      };
    }

    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };

    default:
      return state;
  }
}

// ─── Components ──────────────────────────────────────────────────────────────

interface TaskCardProps {
  task: Task;
  isPending: boolean;
  conflict: ConflictHint | undefined;
  onResolve: (resolution: 'mine' | 'theirs') => void;
}

function TaskCard({ task, isPending, conflict, onResolve }: TaskCardProps) {
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    e.dataTransfer.setData('text/plain', task.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const cardStyle: React.CSSProperties = {
    ...styles.card,
    ...(isPending ? styles.cardPending : {}),
    ...(conflict ? styles.cardConflict : {}),
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      style={cardStyle}
    >
      <p style={styles.cardTitle}>{task.title}</p>
      <p style={styles.cardMeta}>v{task.version} · {new Date(task.updatedAt).toLocaleTimeString()}</p>
      {isPending && <p style={{ ...styles.cardMeta, color: '#fab005' }}>⏳ Syncing...</p>}
      {conflict && (
        <div>
          <p style={{ ...styles.cardMeta, color: '#e03131' }}>⚠ {conflict.message}</p>
          <div style={styles.conflictBar}>
            <button style={styles.conflictBtn} onClick={() => onResolve('mine')}>Keep Mine</button>
            <button style={styles.conflictBtn} onClick={() => onResolve('theirs')}>Accept Theirs</button>
          </div>
        </div>
      )}
    </div>
  );
}

interface ColumnProps {
  status: TaskStatus;
  tasks: Task[];
  optimisticUpdates: Record<string, OptimisticUpdate>;
  conflictHints: ConflictHint[];
  dispatch: React.Dispatch<BoardAction>;
}

function Column({ status, tasks, optimisticUpdates, conflictHints, dispatch }: ColumnProps) {
  const dragOverRef = useRef(false);
  const [isDragOver, setIsDragOver] = React.useState(false);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (!dragOverRef.current) {
      dragOverRef.current = true;
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback(() => {
    dragOverRef.current = false;
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      dragOverRef.current = false;
      setIsDragOver(false);
      const taskId = e.dataTransfer.getData('text/plain');
      if (taskId) {
        dispatch({ type: 'MOVE_TASK', payload: { taskId, newStatus: status } });
      }
    },
    [dispatch, status],
  );

  const columnStyle: React.CSSProperties = {
    ...styles.column,
    ...(isDragOver ? { background: '#e7f5ff', border: '2px dashed #4dabf7' } : {}),
  };

  return (
    <div
      style={columnStyle}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div style={styles.columnHeader}>
        {COLUMN_LABELS[status]} ({tasks.length})
      </div>
      {tasks.map((task) => {
        const conflict = conflictHints.find((c) => c.taskId === task.id);
        return (
          <TaskCard
            key={task.id}
            task={task}
            isPending={!!optimisticUpdates[task.id]}
            conflict={conflict}
            onResolve={(resolution) => {
              const serverStatus: TaskStatus = optimisticUpdates[task.id]?.previousStatus ?? task.status;
              dispatch({
                type: 'RESOLVE_CONFLICT',
                payload: { taskId: task.id, resolution, serverStatus },
              });
            }}
          />
        );
      })}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

const TodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, undefined, buildInitialState);
  const [newTitle, setNewTitle] = React.useState('');

  // Mock server confirmation with delay
  useEffect(() => {
    const entries = Object.entries(state.optimisticUpdates);
    if (entries.length === 0) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    for (const [taskId, opt] of entries) {
      const timer = setTimeout(() => {
        const shouldConflict = Math.random() < 0.15;
        if (shouldConflict) {
          dispatch({ type: 'DETECT_CONFLICT', payload: { taskId, message: 'Another user moved this task' } });
        } else {
          dispatch({ type: 'CONFIRM_MOVE', payload: { taskId } });
        }
      }, 800 + Math.random() * 600);
      timers.push(timer);
    }

    return () => timers.forEach(clearTimeout);
  }, [state.optimisticUpdates]);

  // Mock real-time remote updates (simulating other users)
  useEffect(() => {
    const interval = setInterval(() => {
      const taskIds = Object.keys(state.tasks);
      if (taskIds.length === 0) return;

      const randomId = taskIds[Math.floor(Math.random() * taskIds.length)];
      const task = state.tasks[randomId];
      if (!task) return;

      const statuses: TaskStatus[] = ['todo', 'in-progress', 'done'];
      const others = statuses.filter((s) => s !== task.status);
      const newStatus = others[Math.floor(Math.random() * others.length)];

      dispatch({ type: 'REMOTE_UPDATE', payload: { taskId: randomId, newStatus } });
    }, 5000 + Math.random() * 3000);

    return () => clearInterval(interval);
  }, [state.tasks]);

  const handleAdd = useCallback(() => {
    const trimmed = newTitle.trim();
    if (!trimmed) return;
    dispatch({ type: 'ADD_TASK', payload: { title: trimmed } });
    setNewTitle('');
  }, [newTitle]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleAdd();
    },
    [handleAdd],
  );

  const tasksForColumn = useCallback(
    (status: TaskStatus): Task[] =>
      Object.values(state.tasks)
        .filter((t) => t.status === status)
        .sort((a, b) => b.updatedAt - a.updatedAt),
    [state.tasks],
  );

  return (
    <div style={styles.board}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.headerTitle}>Collaborative Todo Board</h1>
        <span>
          <span
            style={{
              ...styles.statusDot,
              background: state.connected ? '#40c057' : '#e03131',
            }}
          />
          {state.connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Add Task */}
      <div style={styles.addForm}>
        <input
          style={styles.addInput}
          placeholder="Add a new task..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button style={styles.addBtn} onClick={handleAdd}>
          Add
        </button>
      </div>

      {/* Columns */}
      <div style={styles.columns}>
        {state.columnOrder.map((status) => (
          <Column
            key={status}
            status={status}
            tasks={tasksForColumn(status)}
            optimisticUpdates={state.optimisticUpdates}
            conflictHints={state.conflictHints}
            dispatch={dispatch}
          />
        ))}
      </div>
    </div>
  );
};

export default TodoBoard;
