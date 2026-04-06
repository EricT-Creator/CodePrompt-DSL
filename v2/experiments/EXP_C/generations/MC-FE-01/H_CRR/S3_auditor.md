## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript interfaces/types throughout (`TaskStatus`, `Task`, `BoardState`, `BoardAction`) and React functional components with proper typing.
- C2 [Y]CSS_MODULES [!Y]NO_TW: FAIL — Code uses inline style objects (`const styles: Record<string, React.CSSProperties>`) instead of importing a `.module.css` file. No Tailwind is used (that part passes), but the CSS Modules requirement is violated.
- C3 [!D]NO_DND_LIB [DRAG]HTML5: PASS — Drag-and-drop is implemented via native HTML5 Drag API (`draggable`, `onDragStart`, `onDragOver`, `onDrop`, `e.dataTransfer`); no external DnD library imported.
- C4 [STATE]useReducer: PASS — Primary state management uses `useReducer(boardReducer, ...)` in the main `TodoBoard` component. Minor local `useState` calls exist for UI-only state (`newTitle`, `isDragOver`) which is acceptable.
- C5 [O]SFC [EXP]DEFAULT: PASS — All components (`TaskCard`, `Column`, `TodoBoard`) are stateless/functional components; `TodoBoard` is exported as `export default TodoBoard`.
- C6 [WS]MOCK [!D]NO_SOCKETIO: PASS — WebSocket behavior is mocked via `setTimeout` and `setInterval` to simulate server confirmations and remote updates; no `socket.io` or real WebSocket is imported.

## Functionality Assessment (0-5)
Score: 5 — Fully functional collaborative Kanban board with drag-and-drop between columns, optimistic UI updates with mock server confirmation, conflict detection and resolution (keep mine / accept theirs), real-time simulated remote updates, task creation, and connection status indicator. All core features are correctly implemented.

## Corrected Code
```tsx
import React, { useReducer, useEffect, useCallback, useRef } from 'react';
import cssStyles from './TodoBoard.module.css';

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

  const cardClassName = [
    cssStyles.card,
    isPending ? cssStyles.cardPending : '',
    conflict ? cssStyles.cardConflict : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={cardClassName}
    >
      <p className={cssStyles.cardTitle}>{task.title}</p>
      <p className={cssStyles.cardMeta}>v{task.version} · {new Date(task.updatedAt).toLocaleTimeString()}</p>
      {isPending && <p className={`${cssStyles.cardMeta} ${cssStyles.syncingText}`}>⏳ Syncing...</p>}
      {conflict && (
        <div>
          <p className={`${cssStyles.cardMeta} ${cssStyles.conflictText}`}>⚠ {conflict.message}</p>
          <div className={cssStyles.conflictBar}>
            <button className={cssStyles.conflictBtn} onClick={() => onResolve('mine')}>Keep Mine</button>
            <button className={cssStyles.conflictBtn} onClick={() => onResolve('theirs')}>Accept Theirs</button>
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

  const columnClassName = [
    cssStyles.column,
    isDragOver ? cssStyles.columnDragOver : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={columnClassName}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={cssStyles.columnHeader}>
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
    <div className={cssStyles.board}>
      {/* Header */}
      <div className={cssStyles.header}>
        <h1 className={cssStyles.headerTitle}>Collaborative Todo Board</h1>
        <span>
          <span
            className={`${cssStyles.statusDot} ${state.connected ? cssStyles.statusDotConnected : cssStyles.statusDotDisconnected}`}
          />
          {state.connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Add Task */}
      <div className={cssStyles.addForm}>
        <input
          className={cssStyles.addInput}
          placeholder="Add a new task..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className={cssStyles.addBtn} onClick={handleAdd}>
          Add
        </button>
      </div>

      {/* Columns */}
      <div className={cssStyles.columns}>
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
```
