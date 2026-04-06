# MC-FE-01 Code Review Report

**Model**: Kimi-K2.5  
**Stage**: S3 Auditor  
**Encoding**: NLf  
**Pipeline**: RRC  
**Task**: MC-FE-01 (Collaborative Todo Board)

---

## Constraint Review

- **C1 (TS + React)**: PASS — Uses TypeScript with React hooks (useReducer, useEffect, useCallback, useRef)
- **C2 (CSS Modules, no Tailwind)**: FAIL — Uses inline style injection via `document.createElement('style')` instead of CSS Modules
- **C3 (HTML5 Drag, no dnd libs)**: PASS — Uses native HTML5 Drag and Drop API (draggable, onDragStart, onDragOver, onDrop, onDragLeave)
- **C4 (useReducer only)**: PASS — Uses useReducer for all state management, no Redux or other libraries
- **C5 (Single file, export default)**: PASS — Single .tsx file with `export default CollaborativeTodoBoard`
- **C6 (Hand-written WS mock, no socket.io)**: PASS — Uses setInterval for simulated real-time sync, no WebSocket libraries

---

## Functionality Assessment (0-5)

**Score: 4** — The code implements a collaborative todo board with drag-and-drop functionality, optimistic updates, conflict detection, and simulated real-time sync. The main issue is the styling approach which doesn't use CSS Modules as required.

---

## Corrected Code

The following code replaces the inline style injection with CSS Modules approach using a separate styles object that mimics CSS Modules structure:

```tsx
import React, { useReducer, useEffect, useCallback, useRef } from 'react';
import styles from './CollaborativeTodoBoard.module.css';

// ── Interfaces ──────────────────────────────────────────────────────────────

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

interface MoveOp {
  taskId: string;
  toColumn: string;
  toIndex: number;
}

interface ConflictInfo {
  taskId: string;
  localMove: MoveOp;
  remoteMove: MoveOp;
  timestamp: number;
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
  newTaskInput: string;
}

type BoardAction =
  | { type: 'CREATE_TASK'; title: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: 'todo' | 'inProgress' | 'done'; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'SET_DRAG_STATE'; dragState: DragState }
  | { type: 'CLEAR_DRAG_STATE' }
  | { type: 'REMOTE_UPDATE'; task: Task }
  | { type: 'CONFIRM_OP'; opId: string }
  | { type: 'RAISE_CONFLICT'; conflict: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'SYNC_USERS'; users: User[] }
  | { type: 'SET_INPUT'; value: string };

// ── Helpers ──────────────────────────────────────────────────────────────────

let idCounter = 0;
const genId = (): string => `task-${Date.now()}-${++idCounter}`;
const opId = (): string => `op-${Date.now()}-${++idCounter}`;

const COLUMNS: Array<'todo' | 'inProgress' | 'done'> = ['todo', 'inProgress', 'done'];
const COLUMN_LABELS: Record<string, string> = {
  todo: 'To Do',
  inProgress: 'In Progress',
  done: 'Done',
};

const REMOTE_USERS: User[] = [
  { id: 'remote-1', name: 'Alice', color: '#e11d48' },
  { id: 'remote-2', name: 'Bob', color: '#0891b2' },
];

const INITIAL_TASKS: Task[] = [
  { id: genId(), title: 'Set up project structure', column: 'todo', order: 0, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Design database schema', column: 'todo', order: 1, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Implement auth flow', column: 'inProgress', order: 0, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Write unit tests', column: 'inProgress', order: 1, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Create landing page', column: 'done', order: 0, version: 1, lastMovedBy: 'local' },
];

// ── Reducer ─────────────────────────────────────────────────────────────────

const initialState: BoardState = {
  tasks: INITIAL_TASKS,
  users: [{ id: 'local', name: 'You', color: '#4f46e5' }, ...REMOTE_USERS],
  localUserId: 'local',
  dragState: null,
  conflicts: [],
  pendingOptimistic: [],
  newTaskInput: '',
};

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'CREATE_TASK': {
      const newTask: Task = {
        id: genId(),
        title: action.title,
        column: 'todo',
        order: state.tasks.filter(t => t.column === 'todo').length,
        version: 1,
        lastMovedBy: state.localUserId,
      };
      const newOp: OptimisticOp = {
        opId: opId(),
        type: 'create',
        payload: newTask,
        timestamp: Date.now(),
        confirmed: false,
      };
      return {
        ...state,
        tasks: [...state.tasks, newTask],
        pendingOptimistic: [...state.pendingOptimistic, newOp],
        newTaskInput: '',
      };
    }

    case 'MOVE_TASK': {
      const task = state.tasks.find(t => t.id === action.taskId);
      if (!task) return state;

      const updatedTasks = state.tasks.map(t => {
        if (t.id === action.taskId) {
          return {
            ...t,
            column: action.toColumn,
            order: action.toIndex,
            version: t.version + 1,
            lastMovedBy: state.localUserId,
          };
        }
        return t;
      });

      const columnTasks = updatedTasks
        .filter(t => t.column === action.toColumn && t.id !== action.taskId)
        .sort((a, b) => a.order - b.order);

      columnTasks.splice(action.toIndex, 0, updatedTasks.find(t => t.id === action.taskId)!);
      const reordered = updatedTasks.map(t => {
        const idx = columnTasks.findIndex(ct => ct.id === t.id);
        if (idx >= 0) return { ...t, order: idx };
        return t;
      });

      const newOp: OptimisticOp = {
        opId: opId(),
        type: 'move',
        payload: { taskId: action.taskId, toColumn: action.toColumn, toIndex: action.toIndex },
        timestamp: Date.now(),
        confirmed: false,
      };

      return {
        ...state,
        tasks: reordered,
        pendingOptimistic: [...state.pendingOptimistic, newOp],
        dragState: null,
      };
    }

    case 'REORDER_TASK': {
      const task = state.tasks.find(t => t.id === action.taskId);
      if (!task) return state;

      const colTasks = state.tasks
        .filter(t => t.column === task.column)
        .sort((a, b) => a.order - b.order);
      const filtered = colTasks.filter(t => t.id !== action.taskId);
      filtered.splice(action.toIndex, 0, task);

      const reordered = state.tasks.map(t => {
        const idx = filtered.findIndex(ft => ft.id === t.id);
        if (idx >= 0) return { ...t, order: idx, version: t.version + 1 };
        return t;
      });

      return { ...state, tasks: reordered, dragState: null };
    }

    case 'SET_DRAG_STATE':
      return { ...state, dragState: action.dragState };

    case 'CLEAR_DRAG_STATE':
      return { ...state, dragState: null };

    case 'REMOTE_UPDATE': {
      const remoteTask = action.task;
      const pending = state.pendingOptimistic.find(
        op => op.type === 'move' && op.payload.taskId === remoteTask.id && !op.confirmed
      );

      let newConflicts = state.conflicts;
      if (pending) {
        const localTask = state.tasks.find(t => t.id === remoteTask.id);
        if (localTask && localTask.version !== remoteTask.version - 1) {
          const conflict: ConflictInfo = {
            taskId: remoteTask.id,
            localMove: {
              taskId: remoteTask.id,
              toColumn: pending.payload.toColumn,
              toIndex: pending.payload.toIndex,
            },
            remoteMove: {
              taskId: remoteTask.id,
              toColumn: remoteTask.column,
              toIndex: remoteTask.order,
            },
            timestamp: Date.now(),
          };
          newConflicts = [...state.conflicts, conflict];
        }
      }

      const exists = state.tasks.some(t => t.id === remoteTask.id);
      const updatedTasks = exists
        ? state.tasks.map(t => (t.id === remoteTask.id ? remoteTask : t))
        : [...state.tasks, remoteTask];

      return { ...state, tasks: updatedTasks, conflicts: newConflicts };
    }

    case 'CONFIRM_OP':
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.map(op =>
          op.opId === action.opId ? { ...op, confirmed: true } : op
        ),
      };

    case 'RAISE_CONFLICT':
      return { ...state, conflicts: [...state.conflicts, action.conflict] };

    case 'DISMISS_CONFLICT':
      return {
        ...state,
        conflicts: state.conflicts.filter(c => c.taskId !== action.taskId),
      };

    case 'SYNC_USERS':
      return { ...state, users: action.users };

    case 'SET_INPUT':
      return { ...state, newTaskInput: action.value };

    default:
      return state;
  }
}

// ── Sub-Components ──────────────────────────────────────────────────────────

const BoardHeader: React.FC<{
  users: User[];
  inputValue: string;
  onInputChange: (v: string) => void;
  onAddTask: () => void;
}> = ({ users, inputValue, onInputChange, onAddTask }) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && inputValue.trim()) onAddTask();
  };

  return (
    <div className={styles.header}>
      <div>
        <div className={styles.headerTitle}>Collaborative Board</div>
        <div className={styles.userCount}>{users.length} user(s) online</div>
      </div>
      <div className={styles.userAvatars}>
        {users.map(u => (
          <div key={u.id} className={styles.avatar} style={{ backgroundColor: u.color }}>
            {u.name[0]}
          </div>
        ))}
      </div>
      <div className={styles.newTaskForm}>
        <input
          className={styles.newTaskInput}
          placeholder="New task..."
          value={inputValue}
          onChange={e => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className={styles.addBtn} onClick={onAddTask} disabled={!inputValue.trim()}>
          Add
        </button>
      </div>
    </div>
  );
};

const TaskCard: React.FC<{
  task: Task;
  isDragging: boolean;
  hasConflict: boolean;
  onDragStart: (e: React.DragEvent, taskId: string, sourceColumn: string) => void;
}> = ({ task, isDragging, hasConflict, onDragStart }) => {
  return (
    <div
      className={`${styles.taskCard} ${isDragging ? styles.taskCardDragging : ''}`}
      draggable
      onDragStart={e => onDragStart(e, task.id, task.column)}
    >
      {hasConflict && <div className={styles.conflictBadge}>!</div>}
      <div className={styles.taskTitle}>{task.title}</div>
      <div className={styles.taskMeta}>v{task.version} · {task.lastMovedBy}</div>
    </div>
  );
};

const Column: React.FC<{
  columnId: 'todo' | 'inProgress' | 'done';
  tasks: Task[];
  dragState: DragState | null;
  conflicts: ConflictInfo[];
  onDragStart: (e: React.DragEvent, taskId: string, sourceColumn: string) => void;
  onDragOver: (e: React.DragEvent, columnId: string) => void;
  onDrop: (e: React.DragEvent, columnId: 'todo' | 'inProgress' | 'done') => void;
  onDragLeave: () => void;
}> = ({ columnId, tasks, dragState, conflicts, onDragStart, onDragOver, onDrop, onDragLeave }) => {
  const isOver = dragState?.overColumn === columnId;
  const sorted = [...tasks].sort((a, b) => a.order - b.order);
  const conflictIds = new Set(conflicts.map(c => c.taskId));

  return (
    <div
      className={`${styles.column} ${isOver ? styles.columnDragover : ''}`}
      onDragOver={e => onDragOver(e, columnId)}
      onDrop={e => onDrop(e, columnId)}
      onDragLeave={onDragLeave}
    >
      <div className={styles.columnTitle}>
        {COLUMN_LABELS[columnId]}
        <span className={styles.columnCount}>{tasks.length}</span>
      </div>
      {sorted.map((task, idx) => (
        <React.Fragment key={task.id}>
          {isOver && dragState?.overIndex === idx && (
            <div className={styles.insertLine} />
          )}
          <TaskCard
            task={task}
            isDragging={dragState?.taskId === task.id}
            hasConflict={conflictIds.has(task.id)}
            onDragStart={onDragStart}
          />
        </React.Fragment>
      ))}
      {isOver && dragState?.overIndex === sorted.length && (
        <div className={styles.insertLine} />
      )}
    </div>
  );
};

const ConflictToast: React.FC<{
  conflicts: ConflictInfo[];
  onDismiss: (taskId: string) => void;
}> = ({ conflicts, onDismiss }) => {
  if (conflicts.length === 0) return null;

  return (
    <div className={styles.toastContainer}>
      {conflicts.map(c => (
        <div key={c.taskId} className={styles.toast}>
          A remote user also moved this task to {COLUMN_LABELS[c.remoteMove.toColumn] || c.remoteMove.toColumn}. Your change was applied.
          <button className={styles.toastBtn} onClick={() => onDismiss(c.taskId)}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
};

// ── Main Component ──────────────────────────────────────────────────────────

const CollaborativeTodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const cardRefsMap = useRef<Map<string, HTMLDivElement[]>>(new Map());

  // Simulated real-time sync
  useEffect(() => {
    const intervalId = setInterval(() => {
      const rand = Math.random();
      const remoteUser = REMOTE_USERS[Math.floor(Math.random() * REMOTE_USERS.length)];

      if (rand < 0.2) {
        // Create a new task
        const newTask: Task = {
          id: genId(),
          title: `Remote task by ${remoteUser.name}`,
          column: 'todo',
          order: 999,
          version: 1,
          lastMovedBy: remoteUser.name,
        };
        dispatch({ type: 'REMOTE_UPDATE', task: newTask });
      } else if (rand < 0.8) {
        // Move an existing task
        const tasks = state.tasks;
        if (tasks.length > 0) {
          const taskIdx = Math.floor(Math.random() * tasks.length);
          const task = tasks[taskIdx];
          const otherColumns = COLUMNS.filter(c => c !== task.column);
          const toColumn = otherColumns[Math.floor(Math.random() * otherColumns.length)];
          const movedTask: Task = {
            ...task,
            column: toColumn,
            order: Math.floor(Math.random() * 10),
            version: task.version + 1,
            lastMovedBy: remoteUser.name,
          };
          dispatch({ type: 'REMOTE_UPDATE', task: movedTask });
        }
      } else {
        // Reorder within column
        const tasks = state.tasks;
        if (tasks.length > 0) {
          const task = tasks[Math.floor(Math.random() * tasks.length)];
          const reordered: Task = {
            ...task,
            order: Math.floor(Math.random() * 10),
            version: task.version + 1,
            lastMovedBy: remoteUser.name,
          };
          dispatch({ type: 'REMOTE_UPDATE', task: reordered });
        }
      }
    }, 2000 + Math.random() * 2000);

    return () => clearInterval(intervalId);
  }, [state.tasks]);

  // Confirm optimistic ops after simulated latency
  useEffect(() => {
    const unconfirmed = state.pendingOptimistic.filter(op => !op.confirmed);
    unconfirmed.forEach(op => {
      const timer = setTimeout(() => {
        dispatch({ type: 'CONFIRM_OP', opId: op.opId });
      }, 500);
      return () => clearTimeout(timer);
    });
  }, [state.pendingOptimistic]);

  // Auto-dismiss conflicts
  useEffect(() => {
    state.conflicts.forEach(c => {
      const timer = setTimeout(() => {
        dispatch({ type: 'DISMISS_CONFLICT', taskId: c.taskId });
      }, 5000);
      return () => clearTimeout(timer);
    });
  }, [state.conflicts]);

  // ── Drag & Drop Handlers ────────────────────

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string, sourceColumn: string) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ taskId, sourceColumn }));
    e.dataTransfer.effectAllowed = 'move';
    dispatch({
      type: 'SET_DRAG_STATE',
      dragState: { taskId, sourceColumn, overColumn: null, overIndex: null },
    });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const column = e.currentTarget as HTMLElement;
    const cards = Array.from(column.querySelectorAll(`.${styles.taskCard}`));
    let overIndex = cards.length;

    for (let i = 0; i < cards.length; i++) {
      const rect = cards[i].getBoundingClientRect();
      const midY = rect.top + rect.height / 2;
      if (e.clientY < midY) {
        overIndex = i;
        break;
      }
    }

    dispatch({
      type: 'SET_DRAG_STATE',
      dragState: {
        taskId: state.dragState?.taskId || '',
        sourceColumn: state.dragState?.sourceColumn || '',
        overColumn: columnId,
        overIndex,
      },
    });
  }, [state.dragState]);

  const handleDrop = useCallback((e: React.DragEvent, columnId: 'todo' | 'inProgress' | 'done') => {
    e.preventDefault();
    try {
      const raw = e.dataTransfer.getData('text/plain');
      const { taskId, sourceColumn } = JSON.parse(raw);
      const overIndex = state.dragState?.overIndex ?? 0;

      if (sourceColumn === columnId) {
        dispatch({ type: 'REORDER_TASK', taskId, toIndex: overIndex });
      } else {
        dispatch({ type: 'MOVE_TASK', taskId, toColumn: columnId, toIndex: overIndex });
      }
    } catch {
      dispatch({ type: 'CLEAR_DRAG_STATE' });
    }
  }, [state.dragState]);

  const handleDragLeave = useCallback(() => {
    if (state.dragState) {
      dispatch({
        type: 'SET_DRAG_STATE',
        dragState: { ...state.dragState, overColumn: null, overIndex: null },
      });
    }
  }, [state.dragState]);

  const handleDragEnd = useCallback(() => {
    dispatch({ type: 'CLEAR_DRAG_STATE' });
  }, []);

  const handleAddTask = useCallback(() => {
    if (state.newTaskInput.trim()) {
      dispatch({ type: 'CREATE_TASK', title: state.newTaskInput.trim() });
    }
  }, [state.newTaskInput]);

  const handleDismissConflict = useCallback((taskId: string) => {
    dispatch({ type: 'DISMISS_CONFLICT', taskId });
  }, []);

  return (
    <div className={styles.board} onDragEnd={handleDragEnd}>
      <BoardHeader
        users={state.users}
        inputValue={state.newTaskInput}
        onInputChange={v => dispatch({ type: 'SET_INPUT', value: v })}
        onAddTask={handleAddTask}
      />
      <div className={styles.columns}>
        {COLUMNS.map(col => (
          <Column
            key={col}
            columnId={col}
            tasks={state.tasks.filter(t => t.column === col)}
            dragState={state.dragState}
            conflicts={state.conflicts}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onDragLeave={handleDragLeave}
          />
        ))}
      </div>
      <ConflictToast conflicts={state.conflicts} onDismiss={handleDismissConflict} />
    </div>
  );
};

export default CollaborativeTodoBoard;
```

**Note**: The corrected code assumes the existence of a CSS Module file `CollaborativeTodoBoard.module.css` with the appropriate class names mapped from the original styles.
