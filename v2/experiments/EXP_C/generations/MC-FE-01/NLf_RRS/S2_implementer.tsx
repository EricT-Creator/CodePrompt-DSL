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

interface ConflictInfo {
  taskId: string;
  localMove: { column: string; taskId: string };
  remoteMove: { column: string; taskId: string; userName: string };
  timestamp: number;
}

interface OptimisticOp {
  opId: string;
  type: 'move' | 'create';
  payload: { taskId: string; toColumn?: string };
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
  newTaskTitle: string;
}

type BoardAction =
  | { type: 'CREATE_TASK'; title: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: 'todo' | 'inProgress' | 'done'; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'SET_DRAG_STATE'; dragState: DragState }
  | { type: 'CLEAR_DRAG_STATE' }
  | { type: 'REMOTE_UPDATE'; task: Task; userName: string }
  | { type: 'CONFIRM_OP'; opId: string }
  | { type: 'RAISE_CONFLICT'; conflict: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'SYNC_USERS'; users: User[] }
  | { type: 'SET_NEW_TASK_TITLE'; title: string };

// ── Style injection ─────────────────────────────────────────────────────────

const PREFIX = 'ctb_';

const cssText = `
.${PREFIX}board {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
  background: #f0f2f5;
}
.${PREFIX}header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.${PREFIX}headerTitle {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}
.${PREFIX}userBadge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #555;
}
.${PREFIX}dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.${PREFIX}inputRow {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.${PREFIX}input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}
.${PREFIX}input:focus {
  border-color: #5b6abf;
}
.${PREFIX}addBtn {
  padding: 8px 18px;
  background: #5b6abf;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}
.${PREFIX}addBtn:hover {
  background: #4a59a8;
}
.${PREFIX}columns {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.${PREFIX}column {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  min-height: 300px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: border 0.15s;
  border: 2px solid transparent;
}
.${PREFIX}columnOver {
  border-color: #5b6abf;
  background: #f5f6ff;
}
.${PREFIX}colTitle {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #888;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
}
.${PREFIX}count {
  background: #eee;
  border-radius: 10px;
  padding: 0 8px;
  font-size: 12px;
  color: #666;
}
.${PREFIX}card {
  padding: 12px 14px;
  background: #fafbfc;
  border: 1px solid #e8e8ee;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: grab;
  font-size: 14px;
  color: #333;
  position: relative;
  transition: opacity 0.15s, box-shadow 0.15s;
}
.${PREFIX}card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.${PREFIX}cardDragging {
  opacity: 0.4;
}
.${PREFIX}cardConflict {
  border-left: 3px solid #e74c3c;
}
.${PREFIX}movedBy {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
.${PREFIX}insertLine {
  height: 3px;
  background: #5b6abf;
  border-radius: 2px;
  margin-bottom: 8px;
  transition: opacity 0.1s;
}
.${PREFIX}toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: #fff3cd;
  color: #856404;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  font-size: 13px;
  max-width: 340px;
  z-index: 1000;
  animation: ${PREFIX}fadeIn 0.2s;
}
@keyframes ${PREFIX}fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
`;

// ── Helpers ──────────────────────────────────────────────────────────────────

let idCounter = 0;
const genId = (): string => `task-${Date.now()}-${++idCounter}`;
const genOpId = (): string => `op-${Date.now()}-${++idCounter}`;

const COLUMNS: Array<'todo' | 'inProgress' | 'done'> = ['todo', 'inProgress', 'done'];
const COLUMN_LABELS: Record<string, string> = {
  todo: 'Todo',
  inProgress: 'In Progress',
  done: 'Done',
};

const REMOTE_USERS: User[] = [
  { id: 'remote-1', name: 'Alice', color: '#e74c3c' },
  { id: 'remote-2', name: 'Bob', color: '#2ecc71' },
];

const INITIAL_TASKS: Task[] = [
  { id: genId(), title: 'Set up project structure', column: 'todo', order: 0, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Design database schema', column: 'todo', order: 1, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Implement auth flow', column: 'inProgress', order: 0, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Write unit tests', column: 'done', order: 0, version: 1, lastMovedBy: 'local' },
];

// ── Reducer ─────────────────────────────────────────────────────────────────

const initialState: BoardState = {
  tasks: INITIAL_TASKS,
  users: [{ id: 'local', name: 'You', color: '#5b6abf' }, ...REMOTE_USERS],
  localUserId: 'local',
  dragState: null,
  conflicts: [],
  pendingOptimistic: [],
  newTaskTitle: '',
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
      const op: OptimisticOp = {
        opId: genOpId(),
        type: 'create',
        payload: { taskId: newTask.id },
        timestamp: Date.now(),
        confirmed: false,
      };
      return {
        ...state,
        tasks: [...state.tasks, newTask],
        pendingOptimistic: [...state.pendingOptimistic, op],
        newTaskTitle: '',
      };
    }

    case 'MOVE_TASK': {
      const op: OptimisticOp = {
        opId: genOpId(),
        type: 'move',
        payload: { taskId: action.taskId, toColumn: action.toColumn },
        timestamp: Date.now(),
        confirmed: false,
      };
      const tasks = state.tasks.map(t => {
        if (t.id === action.taskId) {
          return { ...t, column: action.toColumn, order: action.toIndex, version: t.version + 1, lastMovedBy: state.localUserId };
        }
        return t;
      });
      return {
        ...state,
        tasks,
        pendingOptimistic: [...state.pendingOptimistic, op],
        dragState: null,
      };
    }

    case 'REORDER_TASK': {
      const tasks = state.tasks.map(t => {
        if (t.id === action.taskId) {
          return { ...t, order: action.toIndex };
        }
        return t;
      });
      return { ...state, tasks };
    }

    case 'SET_DRAG_STATE':
      return { ...state, dragState: action.dragState };

    case 'CLEAR_DRAG_STATE':
      return { ...state, dragState: null };

    case 'REMOTE_UPDATE': {
      const incoming = action.task;
      const pendingConflict = state.pendingOptimistic.find(
        op => !op.confirmed && op.payload.taskId === incoming.id
      );
      let conflicts = state.conflicts;
      if (pendingConflict) {
        const conflict: ConflictInfo = {
          taskId: incoming.id,
          localMove: { column: pendingConflict.payload.toColumn || '', taskId: incoming.id },
          remoteMove: { column: incoming.column, taskId: incoming.id, userName: action.userName },
          timestamp: Date.now(),
        };
        conflicts = [...conflicts, conflict];
      }
      const tasks = state.tasks.map(t => {
        if (t.id === incoming.id) {
          if (pendingConflict) return t;
          return incoming;
        }
        return t;
      });
      const hasTask = tasks.some(t => t.id === incoming.id);
      return {
        ...state,
        tasks: hasTask ? tasks : [...tasks, incoming],
        conflicts,
      };
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
      return { ...state, conflicts: state.conflicts.filter(c => c.taskId !== action.taskId) };

    case 'SYNC_USERS':
      return { ...state, users: [state.users[0], ...action.users] };

    case 'SET_NEW_TASK_TITLE':
      return { ...state, newTaskTitle: action.title };

    default:
      return state;
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────

const BoardHeader: React.FC<{
  userCount: number;
  users: User[];
  newTaskTitle: string;
  onTitleChange: (v: string) => void;
  onAdd: () => void;
}> = ({ userCount, users, newTaskTitle, onTitleChange, onAdd }) => (
  <div className={`${PREFIX}header`}>
    <div>
      <div className={`${PREFIX}headerTitle`}>Collaborative Todo Board</div>
      <div className={`${PREFIX}inputRow`}>
        <input
          className={`${PREFIX}input`}
          placeholder="Add a new task..."
          value={newTaskTitle}
          onChange={e => onTitleChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && newTaskTitle.trim()) onAdd(); }}
        />
        <button className={`${PREFIX}addBtn`} onClick={onAdd}>Add</button>
      </div>
    </div>
    <div className={`${PREFIX}userBadge`}>
      {users.map(u => (
        <span key={u.id} className={`${PREFIX}dot`} style={{ background: u.color }} title={u.name} />
      ))}
      <span>{userCount} online</span>
    </div>
  </div>
);

const TaskCard: React.FC<{
  task: Task;
  isDragging: boolean;
  hasConflict: boolean;
  onDragStart: (e: React.DragEvent, taskId: string, column: string) => void;
}> = ({ task, isDragging, hasConflict, onDragStart }) => {
  const cls = [
    `${PREFIX}card`,
    isDragging ? `${PREFIX}cardDragging` : '',
    hasConflict ? `${PREFIX}cardConflict` : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={cls}
      draggable
      onDragStart={e => onDragStart(e, task.id, task.column)}
    >
      {task.title}
      <div className={`${PREFIX}movedBy`}>v{task.version}</div>
    </div>
  );
};

const Column: React.FC<{
  column: 'todo' | 'inProgress' | 'done';
  tasks: Task[];
  dragState: DragState | null;
  conflicts: ConflictInfo[];
  onDragStart: (e: React.DragEvent, taskId: string, column: string) => void;
  onDragOver: (e: React.DragEvent, column: string) => void;
  onDrop: (e: React.DragEvent, column: 'todo' | 'inProgress' | 'done') => void;
  onDragLeave: () => void;
}> = ({ column, tasks, dragState, conflicts, onDragStart, onDragOver, onDrop, onDragLeave }) => {
  const isOver = dragState?.overColumn === column;
  const sorted = [...tasks].sort((a, b) => a.order - b.order);
  const conflictIds = new Set(conflicts.map(c => c.taskId));

  return (
    <div
      className={`${PREFIX}column ${isOver ? `${PREFIX}columnOver` : ''}`}
      onDragOver={e => onDragOver(e, column)}
      onDrop={e => onDrop(e, column)}
      onDragLeave={onDragLeave}
    >
      <div className={`${PREFIX}colTitle`}>
        {COLUMN_LABELS[column]}
        <span className={`${PREFIX}count`}>{tasks.length}</span>
      </div>
      {sorted.map((task, idx) => (
        <React.Fragment key={task.id}>
          {isOver && dragState?.overIndex === idx && (
            <div className={`${PREFIX}insertLine`} />
          )}
          <TaskCard
            task={task}
            isDragging={dragState?.taskId === task.id}
            hasConflict={conflictIds.has(task.id)}
            onDragStart={onDragStart}
          />
        </React.Fragment>
      ))}
      {isOver && dragState?.overIndex != null && dragState.overIndex >= sorted.length && (
        <div className={`${PREFIX}insertLine`} />
      )}
    </div>
  );
};

const ConflictToast: React.FC<{ conflicts: ConflictInfo[]; onDismiss: (taskId: string) => void }> = ({ conflicts, onDismiss }) => {
  if (conflicts.length === 0) return null;
  const c = conflicts[0];
  return (
    <div className={`${PREFIX}toast`} onClick={() => onDismiss(c.taskId)}>
      <strong>{c.remoteMove.userName}</strong> also moved this task to <strong>{COLUMN_LABELS[c.remoteMove.column] || c.remoteMove.column}</strong>. Your change was applied. Click to dismiss.
    </div>
  );
};

// ── Main component ──────────────────────────────────────────────────────────

const CollaborativeTodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const styleRef = useRef<HTMLStyleElement | null>(null);
  const cardRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());

  // Inject styles
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = cssText;
    document.head.appendChild(style);
    styleRef.current = style;
    return () => { style.remove(); };
  }, []);

  // Simulate remote sync
  useEffect(() => {
    const interval = setInterval(() => {
      const rand = Math.random();
      const remoteUser = REMOTE_USERS[Math.floor(Math.random() * REMOTE_USERS.length)];

      if (rand < 0.2) {
        // Create
        const newTask: Task = {
          id: genId(),
          title: `Remote task by ${remoteUser.name}`,
          column: 'todo',
          order: 0,
          version: 1,
          lastMovedBy: remoteUser.id,
        };
        dispatch({ type: 'REMOTE_UPDATE', task: newTask, userName: remoteUser.name });
      } else if (rand < 0.8) {
        // Move
        const available = state.tasks.filter(t => t.column !== 'done');
        if (available.length > 0) {
          const target = available[Math.floor(Math.random() * available.length)];
          const possibleCols = COLUMNS.filter(c => c !== target.column);
          const newCol = possibleCols[Math.floor(Math.random() * possibleCols.length)];
          const updated: Task = { ...target, column: newCol, version: target.version + 1, lastMovedBy: remoteUser.id };
          dispatch({ type: 'REMOTE_UPDATE', task: updated, userName: remoteUser.name });
        }
      } else {
        // Reorder
        const col = COLUMNS[Math.floor(Math.random() * COLUMNS.length)];
        const colTasks = state.tasks.filter(t => t.column === col);
        if (colTasks.length > 1) {
          const target = colTasks[Math.floor(Math.random() * colTasks.length)];
          const updated: Task = { ...target, order: Math.floor(Math.random() * colTasks.length), version: target.version + 1, lastMovedBy: remoteUser.id };
          dispatch({ type: 'REMOTE_UPDATE', task: updated, userName: remoteUser.name });
        }
      }
    }, 2000 + Math.random() * 2000);

    return () => clearInterval(interval);
  }, [state.tasks]);

  // Confirm optimistic ops after delay
  useEffect(() => {
    const pending = state.pendingOptimistic.filter(op => !op.confirmed);
    pending.forEach(op => {
      const timer = setTimeout(() => {
        dispatch({ type: 'CONFIRM_OP', opId: op.opId });
      }, 500);
      return () => clearTimeout(timer);
    });
  }, [state.pendingOptimistic]);

  // Auto-dismiss conflicts
  useEffect(() => {
    if (state.conflicts.length > 0) {
      const timer = setTimeout(() => {
        dispatch({ type: 'DISMISS_CONFLICT', taskId: state.conflicts[0].taskId });
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [state.conflicts]);

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string, column: string) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ taskId, sourceColumn: column }));
    e.dataTransfer.effectAllowed = 'move';
    dispatch({
      type: 'SET_DRAG_STATE',
      dragState: { taskId, sourceColumn: column, overColumn: null, overIndex: null },
    });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, column: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const container = e.currentTarget as HTMLElement;
    const cards = container.querySelectorAll(`.${PREFIX}card`);
    const mouseY = e.clientY;
    let insertIndex = cards.length;

    for (let i = 0; i < cards.length; i++) {
      const rect = cards[i].getBoundingClientRect();
      if (mouseY < rect.top + rect.height / 2) {
        insertIndex = i;
        break;
      }
    }

    dispatch({
      type: 'SET_DRAG_STATE',
      dragState: {
        taskId: state.dragState?.taskId || '',
        sourceColumn: state.dragState?.sourceColumn || '',
        overColumn: column,
        overIndex: insertIndex,
      },
    });
  }, [state.dragState]);

  const handleDrop = useCallback((e: React.DragEvent, column: 'todo' | 'inProgress' | 'done') => {
    e.preventDefault();
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
      const toIndex = state.dragState?.overIndex ?? 0;
      if (data.sourceColumn === column) {
        dispatch({ type: 'REORDER_TASK', taskId: data.taskId, toIndex });
      } else {
        dispatch({ type: 'MOVE_TASK', taskId: data.taskId, toColumn: column, toIndex });
      }
    } catch {
      dispatch({ type: 'CLEAR_DRAG_STATE' });
    }
  }, [state.dragState]);

  const handleDragEnd = useCallback(() => {
    dispatch({ type: 'CLEAR_DRAG_STATE' });
  }, []);

  const handleAddTask = useCallback(() => {
    if (state.newTaskTitle.trim()) {
      dispatch({ type: 'CREATE_TASK', title: state.newTaskTitle.trim() });
    }
  }, [state.newTaskTitle]);

  return (
    <div className={`${PREFIX}board`} onDragEnd={handleDragEnd}>
      <BoardHeader
        userCount={state.users.length}
        users={state.users}
        newTaskTitle={state.newTaskTitle}
        onTitleChange={v => dispatch({ type: 'SET_NEW_TASK_TITLE', title: v })}
        onAdd={handleAddTask}
      />
      <div className={`${PREFIX}columns`}>
        {COLUMNS.map(col => (
          <Column
            key={col}
            column={col}
            tasks={state.tasks.filter(t => t.column === col)}
            dragState={state.dragState}
            conflicts={state.conflicts}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onDragLeave={() => {
              if (state.dragState) {
                dispatch({
                  type: 'SET_DRAG_STATE',
                  dragState: { ...state.dragState, overColumn: null, overIndex: null },
                });
              }
            }}
          />
        ))}
      </div>
      <ConflictToast conflicts={state.conflicts} onDismiss={taskId => dispatch({ type: 'DISMISS_CONFLICT', taskId })} />
    </div>
  );
};

export default CollaborativeTodoBoard;
