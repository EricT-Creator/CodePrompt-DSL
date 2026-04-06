import React, { useReducer, useEffect, useCallback, useRef } from 'react';

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

// ── Styles ──────────────────────────────────────────────────────────────────

const STYLE_ID = 'ctb-styles';
const PREFIX = 'ctb';

const cssText = `
.${PREFIX}-board {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background: #f0f2f5;
  min-height: 100vh;
}
.${PREFIX}-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.${PREFIX}-header-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}
.${PREFIX}-user-count {
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}
.${PREFIX}-new-task-form {
  display: flex;
  gap: 8px;
}
.${PREFIX}-new-task-input {
  padding: 8px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 14px;
  width: 220px;
  outline: none;
  transition: border-color 0.15s;
}
.${PREFIX}-new-task-input:focus {
  border-color: #4f46e5;
}
.${PREFIX}-add-btn {
  padding: 8px 18px;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.${PREFIX}-add-btn:hover {
  background: #4338ca;
}
.${PREFIX}-user-avatars {
  display: flex;
  gap: 6px;
  align-items: center;
}
.${PREFIX}-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}
.${PREFIX}-columns {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.${PREFIX}-column {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  min-height: 400px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: border-color 0.15s, box-shadow 0.15s;
  border: 2px solid transparent;
}
.${PREFIX}-column-dragover {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.15);
}
.${PREFIX}-column-title {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #555;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.${PREFIX}-column-count {
  background: #eef;
  color: #4f46e5;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}
.${PREFIX}-task-card {
  padding: 12px 14px;
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: grab;
  transition: opacity 0.15s, transform 0.1s, box-shadow 0.15s;
  position: relative;
}
.${PREFIX}-task-card:hover {
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.${PREFIX}-task-card-dragging {
  opacity: 0.4;
  transform: rotate(2deg);
}
.${PREFIX}-task-title {
  font-size: 14px;
  color: #1a1a2e;
}
.${PREFIX}-task-meta {
  font-size: 11px;
  color: #aaa;
  margin-top: 6px;
}
.${PREFIX}-conflict-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  background: #ef4444;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #fff;
  font-weight: 700;
}
.${PREFIX}-insert-line {
  height: 3px;
  background: #4f46e5;
  border-radius: 2px;
  margin: 4px 0;
  transition: opacity 0.1s;
}
.${PREFIX}-toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1000;
}
.${PREFIX}-toast {
  background: #1e293b;
  color: #fff;
  padding: 12px 18px;
  border-radius: 10px;
  font-size: 13px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  animation: ${PREFIX}-slidein 0.25s ease-out;
  max-width: 340px;
}
.${PREFIX}-toast-btn {
  background: transparent;
  color: #a5b4fc;
  border: none;
  cursor: pointer;
  text-decoration: underline;
  font-size: 12px;
  margin-left: 8px;
}
@keyframes ${PREFIX}-slidein {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
`;

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
    <div className={`${PREFIX}-header`}>
      <div>
        <div className={`${PREFIX}-header-title`}>Collaborative Board</div>
        <div className={`${PREFIX}-user-count`}>{users.length} user(s) online</div>
      </div>
      <div className={`${PREFIX}-user-avatars`}>
        {users.map(u => (
          <div key={u.id} className={`${PREFIX}-avatar`} style={{ backgroundColor: u.color }}>
            {u.name[0]}
          </div>
        ))}
      </div>
      <div className={`${PREFIX}-new-task-form`}>
        <input
          className={`${PREFIX}-new-task-input`}
          placeholder="New task..."
          value={inputValue}
          onChange={e => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className={`${PREFIX}-add-btn`} onClick={onAddTask} disabled={!inputValue.trim()}>
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
      className={`${PREFIX}-task-card ${isDragging ? `${PREFIX}-task-card-dragging` : ''}`}
      draggable
      onDragStart={e => onDragStart(e, task.id, task.column)}
    >
      {hasConflict && <div className={`${PREFIX}-conflict-badge`}>!</div>}
      <div className={`${PREFIX}-task-title`}>{task.title}</div>
      <div className={`${PREFIX}-task-meta`}>v{task.version} · {task.lastMovedBy}</div>
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
      className={`${PREFIX}-column ${isOver ? `${PREFIX}-column-dragover` : ''}`}
      onDragOver={e => onDragOver(e, columnId)}
      onDrop={e => onDrop(e, columnId)}
      onDragLeave={onDragLeave}
    >
      <div className={`${PREFIX}-column-title`}>
        {COLUMN_LABELS[columnId]}
        <span className={`${PREFIX}-column-count`}>{tasks.length}</span>
      </div>
      {sorted.map((task, idx) => (
        <React.Fragment key={task.id}>
          {isOver && dragState?.overIndex === idx && (
            <div className={`${PREFIX}-insert-line`} />
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
        <div className={`${PREFIX}-insert-line`} />
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
    <div className={`${PREFIX}-toast-container`}>
      {conflicts.map(c => (
        <div key={c.taskId} className={`${PREFIX}-toast`}>
          A remote user also moved this task to {COLUMN_LABELS[c.remoteMove.toColumn] || c.remoteMove.toColumn}. Your change was applied.
          <button className={`${PREFIX}-toast-btn`} onClick={() => onDismiss(c.taskId)}>
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

  // Inject styles
  useEffect(() => {
    if (!document.getElementById(STYLE_ID)) {
      const style = document.createElement('style');
      style.id = STYLE_ID;
      style.textContent = cssText;
      document.head.appendChild(style);
    }
    return () => {
      const el = document.getElementById(STYLE_ID);
      if (el) el.remove();
    };
  }, []);

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
    const cards = Array.from(column.querySelectorAll(`.${PREFIX}-task-card`));
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
    <div className={`${PREFIX}-board`} onDragEnd={handleDragEnd}>
      <BoardHeader
        users={state.users}
        inputValue={state.newTaskInput}
        onInputChange={v => dispatch({ type: 'SET_INPUT', value: v })}
        onAddTask={handleAddTask}
      />
      <div className={`${PREFIX}-columns`}>
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
