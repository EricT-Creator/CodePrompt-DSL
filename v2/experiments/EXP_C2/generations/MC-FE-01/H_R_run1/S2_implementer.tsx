import React, { useReducer, useEffect, useCallback, useRef } from 'react';
import styles from './TodoBoard.module.css';

// ── Interfaces ──

interface Task {
  id: string;
  text: string;
  column: 'todo' | 'inProgress' | 'done';
  order: number;
  lastMovedBy: string;
  version: number;
}

type ColumnId = 'todo' | 'inProgress' | 'done';

interface OptimisticOp {
  opId: string;
  type: 'MOVE' | 'REORDER' | 'ADD';
  payload: any;
  timestamp: number;
}

interface ConflictHint {
  taskId: string;
  localUser: string;
  remoteUser: string;
  resolvedAt?: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  currentUser: string;
  connectedUsers: string[];
  pendingOptimistic: OptimisticOp[];
  conflicts: ConflictHint[];
}

type Action =
  | { type: 'ADD_TASK'; text: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: ColumnId; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'REMOTE_UPDATE'; tasks: Record<string, Task>; columnOrder: Record<ColumnId, string[]> }
  | { type: 'CONFLICT_DETECTED'; taskId: string; remoteUser: string }
  | { type: 'CONFLICT_DISMISSED'; taskId: string }
  | { type: 'SYNC_ACK'; opId: string }
  | { type: 'SET_USERS'; users: string[] };

// ── Helpers ──

function uuid(): string {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

// ── Reducer ──

function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = uuid();
      const task: Task = {
        id,
        text: action.text,
        column: 'todo',
        order: 0,
        lastMovedBy: state.currentUser,
        version: 1,
      };
      const newTodoOrder = [id, ...state.columnOrder.todo];
      return {
        ...state,
        tasks: { ...state.tasks, [id]: task },
        columnOrder: { ...state.columnOrder, todo: newTodoOrder },
        pendingOptimistic: [
          ...state.pendingOptimistic,
          { opId: uuid(), type: 'ADD', payload: { taskId: id }, timestamp: Date.now() },
        ],
      };
    }
    case 'MOVE_TASK': {
      const task = state.tasks[action.taskId];
      if (!task) return state;
      const fromCol = task.column;
      const fromOrder = state.columnOrder[fromCol].filter((id) => id !== action.taskId);
      const toOrder = [...state.columnOrder[action.toColumn]];
      toOrder.splice(action.toIndex, 0, action.taskId);
      const updatedTask: Task = {
        ...task,
        column: action.toColumn,
        order: action.toIndex,
        lastMovedBy: state.currentUser,
        version: task.version + 1,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [action.taskId]: updatedTask },
        columnOrder: { ...state.columnOrder, [fromCol]: fromOrder, [action.toColumn]: toOrder },
        pendingOptimistic: [
          ...state.pendingOptimistic,
          { opId: uuid(), type: 'MOVE', payload: { taskId: action.taskId, toColumn: action.toColumn }, timestamp: Date.now() },
        ],
      };
    }
    case 'REORDER_TASK': {
      const task = state.tasks[action.taskId];
      if (!task) return state;
      const col = task.column;
      const order = state.columnOrder[col].filter((id) => id !== action.taskId);
      order.splice(action.toIndex, 0, action.taskId);
      return {
        ...state,
        columnOrder: { ...state.columnOrder, [col]: order },
        pendingOptimistic: [
          ...state.pendingOptimistic,
          { opId: uuid(), type: 'REORDER', payload: { taskId: action.taskId, toIndex: action.toIndex }, timestamp: Date.now() },
        ],
      };
    }
    case 'REMOTE_UPDATE': {
      return { ...state, tasks: action.tasks, columnOrder: action.columnOrder };
    }
    case 'CONFLICT_DETECTED': {
      const hint: ConflictHint = {
        taskId: action.taskId,
        localUser: state.currentUser,
        remoteUser: action.remoteUser,
      };
      return { ...state, conflicts: [...state.conflicts, hint] };
    }
    case 'CONFLICT_DISMISSED': {
      return {
        ...state,
        conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId),
      };
    }
    case 'SYNC_ACK': {
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.filter((op) => op.opId !== action.opId),
      };
    }
    case 'SET_USERS': {
      return { ...state, connectedUsers: action.users };
    }
    default:
      return state;
  }
}

// ── Mock Server ──

interface ServerState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  outbox: Array<{ type: string; payload: any }>;
  recentOps: Array<{ taskId: string; user: string; ts: number }>;
}

const mockServer: ServerState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  outbox: [],
  recentOps: [],
};

function serverSubmitOp(op: OptimisticOp, user: string) {
  const taskId = op.payload?.taskId;
  if (taskId) {
    const now = Date.now();
    const conflict = mockServer.recentOps.find(
      (r) => r.taskId === taskId && r.user !== user && now - r.ts < 2000
    );
    if (conflict) {
      mockServer.outbox.push({
        type: 'CONFLICT',
        payload: { taskId, remoteUser: conflict.user },
      });
    }
    mockServer.recentOps.push({ taskId, user, ts: now });
  }
}

function serverSimulateRemote() {
  const taskIds = Object.keys(mockServer.tasks);
  if (taskIds.length === 0) return;
  const taskId = taskIds[Math.floor(Math.random() * taskIds.length)];
  const task = mockServer.tasks[taskId];
  if (!task) return;
  const columns: ColumnId[] = ['todo', 'inProgress', 'done'];
  const otherCols = columns.filter((c) => c !== task.column);
  const newCol = otherCols[Math.floor(Math.random() * otherCols.length)];
  mockServer.recentOps.push({ taskId, user: 'remote-user', ts: Date.now() });
  mockServer.outbox.push({
    type: 'REMOTE_MOVE',
    payload: { taskId, from: task.column, to: newCol },
  });
}

// ── Custom Hook: Mock Sync ──

function useMockSync(
  state: BoardState,
  dispatch: React.Dispatch<Action>
) {
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    mockServer.tasks = { ...state.tasks };
    mockServer.columnOrder = { ...state.columnOrder };
  }, [state.tasks, state.columnOrder]);

  useEffect(() => {
    const interval = setInterval(() => {
      const events = mockServer.outbox.splice(0);
      for (const evt of events) {
        if (evt.type === 'CONFLICT') {
          dispatch({
            type: 'CONFLICT_DETECTED',
            taskId: evt.payload.taskId,
            remoteUser: evt.payload.remoteUser,
          });
        }
      }

      for (const op of stateRef.current.pendingOptimistic) {
        serverSubmitOp(op, stateRef.current.currentUser);
        dispatch({ type: 'SYNC_ACK', opId: op.opId });
      }
    }, 500);

    const remoteInterval = setInterval(() => {
      serverSimulateRemote();
    }, 3000 + Math.random() * 2000);

    return () => {
      clearInterval(interval);
      clearInterval(remoteInterval);
    };
  }, [dispatch]);
}

// ── Components ──

function BoardHeader({ connectedUsers }: { connectedUsers: string[] }) {
  return (
    <div className={styles.header}>
      <h1 className={styles.title}>Collaborative Todo Board</h1>
      <div className={styles.users}>
        {connectedUsers.map((u) => (
          <span key={u} className={styles.userBadge}>
            {u}
          </span>
        ))}
      </div>
    </div>
  );
}

function TaskCard({
  task,
  onDragStart,
}: {
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
}) {
  const [dragging, setDragging] = React.useState(false);

  const handleDragStart = (e: React.DragEvent) => {
    setDragging(true);
    e.dataTransfer.setData('text/plain', task.id);
    e.dataTransfer.effectAllowed = 'move';
    onDragStart(e, task.id);
  };

  const handleDragEnd = () => {
    setDragging(false);
  };

  return (
    <div
      className={`${styles.card} ${dragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <span className={styles.cardText}>{task.text}</span>
      <span className={styles.cardBadge}>{task.lastMovedBy}</span>
    </div>
  );
}

function Column({
  columnId,
  title,
  taskIds,
  tasks,
  dispatch,
}: {
  columnId: ColumnId;
  title: string;
  taskIds: string[];
  tasks: Record<string, Task>;
  dispatch: React.Dispatch<Action>;
}) {
  const [dragOver, setDragOver] = React.useState(false);
  const columnRef = useRef<HTMLDivElement>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      setDragOver(true);
    },
    []
  );

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const taskId = e.dataTransfer.getData('text/plain');
      if (!taskId) return;

      const task = tasks[taskId];
      if (!task) return;

      let insertIndex = taskIds.length;
      if (columnRef.current) {
        const cards = columnRef.current.querySelectorAll('[data-card]');
        const mouseY = e.clientY;
        for (let i = 0; i < cards.length; i++) {
          const rect = cards[i].getBoundingClientRect();
          const midpoint = rect.top + rect.height / 2;
          if (mouseY < midpoint) {
            insertIndex = i;
            break;
          }
        }
      }

      if (task.column === columnId) {
        dispatch({ type: 'REORDER_TASK', taskId, toIndex: insertIndex });
      } else {
        dispatch({ type: 'MOVE_TASK', taskId, toColumn: columnId, toIndex: insertIndex });
      }
    },
    [columnId, taskIds, tasks, dispatch]
  );

  const handleCardDragStart = useCallback(() => {}, []);

  return (
    <div
      className={`${styles.column} ${dragOver ? styles.columnDragOver : ''}`}
      ref={columnRef}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <h2 className={styles.columnTitle}>{title}</h2>
      {taskIds.map((id) => {
        const task = tasks[id];
        if (!task) return null;
        return (
          <div key={id} data-card>
            <TaskCard task={task} onDragStart={handleCardDragStart} />
          </div>
        );
      })}
    </div>
  );
}

function TaskCreator({ dispatch }: { dispatch: React.Dispatch<Action> }) {
  const [text, setText] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    dispatch({ type: 'ADD_TASK', text: trimmed });
    setText('');
  };

  return (
    <form className={styles.creator} onSubmit={handleSubmit}>
      <input
        className={styles.creatorInput}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="New task..."
      />
      <button className={styles.creatorButton} type="submit">
        Add
      </button>
    </form>
  );
}

function ConflictToast({
  conflicts,
  tasks,
  dispatch,
}: {
  conflicts: ConflictHint[];
  tasks: Record<string, Task>;
  dispatch: React.Dispatch<Action>;
}) {
  if (conflicts.length === 0) return null;

  return (
    <div className={styles.conflictToast}>
      {conflicts.map((c) => (
        <div key={c.taskId} className={styles.conflictItem}>
          <span>
            Conflict: &quot;{tasks[c.taskId]?.text ?? c.taskId}&quot; was also moved by{' '}
            {c.remoteUser}
          </span>
          <button
            className={styles.conflictDismiss}
            onClick={() => dispatch({ type: 'CONFLICT_DISMISSED', taskId: c.taskId })}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Root ──

const initialState: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user-' + Math.random().toString(36).substring(2, 6),
  connectedUsers: [],
  pendingOptimistic: [],
  conflicts: [],
};

function TodoBoardApp() {
  const [state, dispatch] = useReducer(boardReducer, initialState);

  useMockSync(state, dispatch);

  useEffect(() => {
    dispatch({ type: 'SET_USERS', users: [state.currentUser, 'remote-user'] });
  }, [state.currentUser]);

  const columnConfig: { id: ColumnId; title: string }[] = [
    { id: 'todo', title: 'Todo' },
    { id: 'inProgress', title: 'In Progress' },
    { id: 'done', title: 'Done' },
  ];

  return (
    <div className={styles.app}>
      <BoardHeader connectedUsers={state.connectedUsers} />
      <TaskCreator dispatch={dispatch} />
      <div className={styles.board}>
        {columnConfig.map((col) => (
          <Column
            key={col.id}
            columnId={col.id}
            title={col.title}
            taskIds={state.columnOrder[col.id]}
            tasks={state.tasks}
            dispatch={dispatch}
          />
        ))}
      </div>
      <ConflictToast conflicts={state.conflicts} tasks={state.tasks} dispatch={dispatch} />
    </div>
  );
}

export default TodoBoardApp;
