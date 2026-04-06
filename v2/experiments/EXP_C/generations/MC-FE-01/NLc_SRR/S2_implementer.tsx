import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ── Types ──────────────────────────────────────────────────────────────

interface Task {
  id: string;
  title: string;
  description?: string;
  column: 'todo' | 'inProgress' | 'done';
  position: number;
  createdAt: string;
  updatedAt: string;
  version: number;
  createdBy: string;
  optimisticId?: string;
  isOptimistic?: boolean;
}

interface PendingOperation {
  id: string;
  type: 'create' | 'move' | 'reorder';
  taskId: string;
  data: Record<string, unknown>;
  timestamp: number;
  resolved: boolean;
}

interface Conflict {
  id: string;
  taskId: string;
  localVersion: number;
  remoteVersion: number;
  message: string;
  timestamp: number;
}

interface BoardState {
  columns: {
    todo: Task[];
    inProgress: Task[];
    done: Task[];
  };
  connectedUsers: number;
  lastSyncTime: string | null;
  pendingOperations: PendingOperation[];
  conflicts: Conflict[];
  draggedTaskId: string | null;
  dragOverColumn: string | null;
  newTaskTitle: string;
  wsConnected: boolean;
}

type BoardAction =
  | { type: 'ADD_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: 'todo' | 'inProgress' | 'done' } }
  | { type: 'SET_OPTIMISTIC'; payload: { taskId: string } }
  | { type: 'CLEAR_OPTIMISTIC'; payload: { taskId: string } }
  | { type: 'ADD_PENDING_OP'; payload: PendingOperation }
  | { type: 'RESOLVE_PENDING_OP'; payload: { id: string } }
  | { type: 'SET_CONNECTED_USERS'; payload: number }
  | { type: 'SYNC_STATE'; payload: { columns: BoardState['columns'] } }
  | { type: 'SET_DRAG'; payload: { taskId: string | null } }
  | { type: 'SET_DRAG_OVER'; payload: { column: string | null } }
  | { type: 'SET_NEW_TASK_TITLE'; payload: string }
  | { type: 'SET_WS_CONNECTED'; payload: boolean }
  | { type: 'ADD_CONFLICT'; payload: Conflict }
  | { type: 'RESOLVE_CONFLICT'; payload: { id: string; resolution: 'local' | 'remote' } }
  | { type: 'REMOTE_ADD_TASK'; payload: Task }
  | { type: 'REMOTE_MOVE_TASK'; payload: { taskId: string; toColumn: 'todo' | 'inProgress' | 'done' } };

// ── CSS Modules (inline object) ────────────────────────────────────────

const css = `
.board { display:flex; flex-direction:column; height:100vh; font-family:system-ui,-apple-system,sans-serif; background:#f0f2f5; }
.header { display:flex; align-items:center; justify-content:space-between; padding:12px 24px; background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.1); }
.header h1 { margin:0; font-size:20px; color:#1a1a1a; }
.statusBar { display:flex; align-items:center; gap:12px; font-size:13px; color:#666; }
.dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:4px; }
.dotOn { background:#22c55e; }
.dotOff { background:#ef4444; }
.addRow { display:flex; gap:8px; padding:12px 24px; }
.addInput { flex:1; padding:8px 12px; border:1px solid #d1d5db; border-radius:6px; font-size:14px; outline:none; }
.addInput:focus { border-color:#3b82f6; box-shadow:0 0 0 2px rgba(59,130,246,.2); }
.addBtn { padding:8px 20px; background:#3b82f6; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:14px; font-weight:500; }
.addBtn:hover { background:#2563eb; }
.addBtn:disabled { background:#93c5fd; cursor:not-allowed; }
.columns { display:flex; flex:1; gap:16px; padding:16px 24px; overflow:auto; }
.column { flex:1; background:#fff; border-radius:10px; padding:12px; display:flex; flex-direction:column; min-width:240px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.columnDragOver { background:#eff6ff; outline:2px dashed #3b82f6; }
.colHeader { font-weight:600; font-size:14px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; color:#374151; }
.badge { background:#e5e7eb; color:#374151; font-size:11px; padding:2px 8px; border-radius:10px; font-weight:500; }
.taskList { flex:1; display:flex; flex-direction:column; gap:6px; min-height:60px; }
.taskItem { padding:10px 12px; background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; cursor:grab; transition:box-shadow .15s,transform .15s; user-select:none; }
.taskItem:hover { box-shadow:0 2px 6px rgba(0,0,0,.08); }
.taskDragging { opacity:.5; transform:scale(.97); }
.taskOptimistic { border-left:3px solid #f59e0b; background:#fffbeb; }
.taskTitle { font-size:14px; color:#1f2937; margin-bottom:4px; }
.taskMeta { font-size:11px; color:#9ca3af; display:flex; justify-content:space-between; }
.conflicts { padding:8px 24px; }
.conflictBanner { display:flex; align-items:center; justify-content:space-between; padding:10px 14px; background:#fef2f2; border:1px solid #fecaca; border-radius:8px; margin-bottom:6px; font-size:13px; color:#991b1b; }
.conflictBtns { display:flex; gap:6px; }
.conflictBtn { padding:4px 10px; font-size:12px; border:none; border-radius:4px; cursor:pointer; }
.conflictLocal { background:#3b82f6; color:#fff; }
.conflictRemote { background:#6b7280; color:#fff; }
`;

// ── Helpers ─────────────────────────────────────────────────────────────

let idCounter = 0;
function uid(): string {
  return `t_${Date.now()}_${++idCounter}`;
}

function now(): string {
  return new Date().toISOString();
}

// ── Reducer ─────────────────────────────────────────────────────────────

function findAndRemoveTask(columns: BoardState['columns'], taskId: string): { task: Task | null; columns: BoardState['columns'] } {
  for (const col of ['todo', 'inProgress', 'done'] as const) {
    const idx = columns[col].findIndex((t) => t.id === taskId);
    if (idx !== -1) {
      const task = columns[col][idx];
      const newCol = [...columns[col]];
      newCol.splice(idx, 1);
      return { task, columns: { ...columns, [col]: newCol } };
    }
  }
  return { task: null, columns };
}

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const task: Task = {
        id: uid(),
        title: action.payload.title,
        column: 'todo',
        position: state.columns.todo.length,
        createdAt: now(),
        updatedAt: now(),
        version: 1,
        createdBy: 'local',
        isOptimistic: true,
      };
      return {
        ...state,
        columns: { ...state.columns, todo: [...state.columns.todo, task] },
        newTaskTitle: '',
      };
    }
    case 'MOVE_TASK': {
      const { taskId, toColumn } = action.payload;
      const { task, columns } = findAndRemoveTask(state.columns, taskId);
      if (!task) return state;
      const moved: Task = { ...task, column: toColumn, updatedAt: now(), version: task.version + 1, isOptimistic: true };
      return {
        ...state,
        columns: { ...columns, [toColumn]: [...columns[toColumn], moved] },
        draggedTaskId: null,
        dragOverColumn: null,
      };
    }
    case 'SET_OPTIMISTIC': {
      const cols = { ...state.columns };
      for (const col of ['todo', 'inProgress', 'done'] as const) {
        cols[col] = cols[col].map((t) => (t.id === action.payload.taskId ? { ...t, isOptimistic: true } : t));
      }
      return { ...state, columns: cols };
    }
    case 'CLEAR_OPTIMISTIC': {
      const cols2 = { ...state.columns };
      for (const col of ['todo', 'inProgress', 'done'] as const) {
        cols2[col] = cols2[col].map((t) => (t.id === action.payload.taskId ? { ...t, isOptimistic: false } : t));
      }
      return { ...state, columns: cols2 };
    }
    case 'ADD_PENDING_OP':
      return { ...state, pendingOperations: [...state.pendingOperations, action.payload] };
    case 'RESOLVE_PENDING_OP':
      return { ...state, pendingOperations: state.pendingOperations.filter((op) => op.id !== action.payload.id) };
    case 'SET_CONNECTED_USERS':
      return { ...state, connectedUsers: action.payload };
    case 'SYNC_STATE':
      return { ...state, columns: action.payload.columns, lastSyncTime: now() };
    case 'SET_DRAG':
      return { ...state, draggedTaskId: action.payload.taskId };
    case 'SET_DRAG_OVER':
      return { ...state, dragOverColumn: action.payload.column };
    case 'SET_NEW_TASK_TITLE':
      return { ...state, newTaskTitle: action.payload };
    case 'SET_WS_CONNECTED':
      return { ...state, wsConnected: action.payload };
    case 'ADD_CONFLICT':
      return { ...state, conflicts: [...state.conflicts, action.payload] };
    case 'RESOLVE_CONFLICT':
      return { ...state, conflicts: state.conflicts.filter((c) => c.id !== action.payload.id) };
    case 'REMOTE_ADD_TASK': {
      const t = action.payload;
      return { ...state, columns: { ...state.columns, [t.column]: [...state.columns[t.column], t] } };
    }
    case 'REMOTE_MOVE_TASK': {
      const { taskId: tid, toColumn: tc } = action.payload;
      const res = findAndRemoveTask(state.columns, tid);
      if (!res.task) return state;
      const movedRemote = { ...res.task, column: tc, updatedAt: now() };
      return { ...state, columns: { ...res.columns, [tc]: [...res.columns[tc], movedRemote] } };
    }
    default:
      return state;
  }
}

// ── Initial state ───────────────────────────────────────────────────────

const initialState: BoardState = {
  columns: {
    todo: [
      { id: 't1', title: 'Research project requirements', column: 'todo', position: 0, createdAt: now(), updatedAt: now(), version: 1, createdBy: 'alice' },
      { id: 't2', title: 'Create wireframes', column: 'todo', position: 1, createdAt: now(), updatedAt: now(), version: 1, createdBy: 'bob' },
    ],
    inProgress: [
      { id: 't3', title: 'Set up development environment', column: 'inProgress', position: 0, createdAt: now(), updatedAt: now(), version: 2, createdBy: 'alice' },
    ],
    done: [
      { id: 't4', title: 'Define team roles', column: 'done', position: 0, createdAt: now(), updatedAt: now(), version: 3, createdBy: 'bob' },
    ],
  },
  connectedUsers: 1,
  lastSyncTime: null,
  pendingOperations: [],
  conflicts: [],
  draggedTaskId: null,
  dragOverColumn: null,
  newTaskTitle: '',
  wsConnected: false,
};

// ── Mock WebSocket ──────────────────────────────────────────────────────

function useMockWebSocket(dispatch: React.Dispatch<BoardAction>) {
  const wsRef = useRef<{ connected: boolean; interval: ReturnType<typeof setInterval> | null }>({ connected: false, interval: null });

  useEffect(() => {
    // Simulate connection
    const connectDelay = setTimeout(() => {
      wsRef.current.connected = true;
      dispatch({ type: 'SET_WS_CONNECTED', payload: true });
      dispatch({ type: 'SET_CONNECTED_USERS', payload: 2 });
    }, 800);

    // Simulate periodic remote events
    const interval = setInterval(() => {
      if (!wsRef.current.connected) return;
      const rand = Math.random();
      if (rand < 0.15) {
        // Simulate remote user adding a task
        dispatch({
          type: 'REMOTE_ADD_TASK',
          payload: {
            id: uid(),
            title: `Remote task #${Math.floor(Math.random() * 100)}`,
            column: 'todo',
            position: 0,
            createdAt: now(),
            updatedAt: now(),
            version: 1,
            createdBy: 'remote-user',
          },
        });
      } else if (rand < 0.2) {
        dispatch({ type: 'SET_CONNECTED_USERS', payload: Math.floor(Math.random() * 4) + 1 });
      } else if (rand < 0.25) {
        // Simulate conflict
        dispatch({
          type: 'ADD_CONFLICT',
          payload: {
            id: uid(),
            taskId: 't3',
            localVersion: 2,
            remoteVersion: 3,
            message: 'Another user moved this task simultaneously',
            timestamp: Date.now(),
          },
        });
      }
    }, 6000);

    wsRef.current.interval = interval;

    return () => {
      clearTimeout(connectDelay);
      clearInterval(interval);
      wsRef.current.connected = false;
    };
  }, [dispatch]);
}

// ── Column labels ───────────────────────────────────────────────────────

const COLUMN_CONFIG: Record<string, { label: string; color: string }> = {
  todo: { label: 'To Do', color: '#6366f1' },
  inProgress: { label: 'In Progress', color: '#f59e0b' },
  done: { label: 'Done', color: '#22c55e' },
};

// ── Component ───────────────────────────────────────────────────────────

const TodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  useMockWebSocket(dispatch);

  const handleDragStart = useCallback(
    (e: React.DragEvent, taskId: string) => {
      e.dataTransfer.setData('text/plain', taskId);
      e.dataTransfer.effectAllowed = 'move';
      dispatch({ type: 'SET_DRAG', payload: { taskId } });
    },
    [],
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent, column: string) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      dispatch({ type: 'SET_DRAG_OVER', payload: { column } });
    },
    [],
  );

  const handleDragLeave = useCallback(() => {
    dispatch({ type: 'SET_DRAG_OVER', payload: { column: null } });
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, toColumn: 'todo' | 'inProgress' | 'done') => {
      e.preventDefault();
      const taskId = e.dataTransfer.getData('text/plain');
      if (taskId) {
        dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn } });
        // Add pending operation (optimistic)
        dispatch({
          type: 'ADD_PENDING_OP',
          payload: { id: uid(), type: 'move', taskId, data: { toColumn }, timestamp: Date.now(), resolved: false },
        });
        // Simulate server confirmation
        setTimeout(() => {
          dispatch({ type: 'CLEAR_OPTIMISTIC', payload: { taskId } });
        }, 1200);
      }
    },
    [],
  );

  const handleAddTask = useCallback(() => {
    const title = state.newTaskTitle.trim();
    if (!title) return;
    dispatch({ type: 'ADD_TASK', payload: { title } });
  }, [state.newTaskTitle]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleAddTask();
    },
    [handleAddTask],
  );

  return (
    <>
      <style>{css}</style>
      <div className="board">
        {/* Header */}
        <div className="header">
          <h1>📋 Collaborative Todo Board</h1>
          <div className="statusBar">
            <span>
              <span className={`dot ${state.wsConnected ? 'dotOn' : 'dotOff'}`} />
              {state.wsConnected ? 'Connected' : 'Connecting…'}
            </span>
            <span>👥 {state.connectedUsers} online</span>
            {state.pendingOperations.length > 0 && <span>⏳ {state.pendingOperations.length} pending</span>}
          </div>
        </div>

        {/* Add task */}
        <div className="addRow">
          <input
            className="addInput"
            placeholder="Add a new task…"
            value={state.newTaskTitle}
            onChange={(e) => dispatch({ type: 'SET_NEW_TASK_TITLE', payload: e.target.value })}
            onKeyDown={handleKeyDown}
          />
          <button className="addBtn" onClick={handleAddTask} disabled={!state.newTaskTitle.trim()}>
            + Add
          </button>
        </div>

        {/* Conflicts */}
        {state.conflicts.length > 0 && (
          <div className="conflicts">
            {state.conflicts.map((c) => (
              <div key={c.id} className="conflictBanner">
                <span>⚠️ Conflict: {c.message}</span>
                <div className="conflictBtns">
                  <button className="conflictBtn conflictLocal" onClick={() => dispatch({ type: 'RESOLVE_CONFLICT', payload: { id: c.id, resolution: 'local' } })}>
                    Keep Local
                  </button>
                  <button className="conflictBtn conflictRemote" onClick={() => dispatch({ type: 'RESOLVE_CONFLICT', payload: { id: c.id, resolution: 'remote' } })}>
                    Use Remote
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Columns */}
        <div className="columns">
          {(['todo', 'inProgress', 'done'] as const).map((colKey) => {
            const config = COLUMN_CONFIG[colKey];
            const tasks = state.columns[colKey];
            const isDragOver = state.dragOverColumn === colKey;
            return (
              <div
                key={colKey}
                className={`column${isDragOver ? ' columnDragOver' : ''}`}
                onDragOver={(e) => handleDragOver(e, colKey)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, colKey)}
              >
                <div className="colHeader">
                  <span style={{ borderBottom: `2px solid ${config.color}`, paddingBottom: 2 }}>{config.label}</span>
                  <span className="badge">{tasks.length}</span>
                </div>
                <div className="taskList">
                  {tasks.map((task) => (
                    <div
                      key={task.id}
                      className={`taskItem${state.draggedTaskId === task.id ? ' taskDragging' : ''}${task.isOptimistic ? ' taskOptimistic' : ''}`}
                      draggable
                      onDragStart={(e) => handleDragStart(e, task.id)}
                      onDragEnd={() => dispatch({ type: 'SET_DRAG', payload: { taskId: null } })}
                    >
                      <div className="taskTitle">{task.title}</div>
                      <div className="taskMeta">
                        <span>by {task.createdBy}</span>
                        <span>v{task.version}</span>
                      </div>
                    </div>
                  ))}
                  {tasks.length === 0 && (
                    <div style={{ textAlign: 'center', padding: 20, color: '#9ca3af', fontSize: 13 }}>
                      Drop tasks here
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
};

export default TodoBoard;
