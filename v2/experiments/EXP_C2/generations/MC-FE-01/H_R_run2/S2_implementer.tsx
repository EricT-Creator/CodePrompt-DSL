import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import styles from './TodoBoard.module.css';

// ─── Types ───────────────────────────────────────────────────────────────────

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  order: number;
  lastMovedBy: string;
  version: number;
}

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
  | { type: 'ADD_TASK'; payload: { text: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; toIndex: number } }
  | { type: 'REMOTE_UPDATE'; payload: { tasks: Record<string, Task>; columnOrder: Record<ColumnId, string[]> } }
  | { type: 'CONFLICT_DETECTED'; payload: ConflictHint }
  | { type: 'CONFLICT_DISMISSED'; payload: { taskId: string } }
  | { type: 'SYNC_ACK'; payload: { opId: string } }
  | { type: 'SET_USERS'; payload: { users: string[] } };

// ─── Utilities ───────────────────────────────────────────────────────────────

function uuid(): string {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

// ─── Mock Server ─────────────────────────────────────────────────────────────

interface ServerState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  opLog: { opId: string; taskId: string; userId: string; timestamp: number }[];
  outbox: Action[];
}

const mockServer: ServerState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  opLog: [],
  outbox: [],
};

function serverApplyOp(op: OptimisticOp, userId: string): void {
  const now = Date.now();
  const recentOps = mockServer.opLog.filter(
    (o) => o.taskId === op.payload.taskId && now - o.timestamp < 2000 && o.userId !== userId
  );
  if (recentOps.length > 0) {
    mockServer.outbox.push({
      type: 'CONFLICT_DETECTED',
      payload: {
        taskId: op.payload.taskId,
        localUser: userId,
        remoteUser: recentOps[0].userId,
      },
    });
  }
  mockServer.opLog.push({ opId: op.opId, taskId: op.payload.taskId || '', userId, timestamp: now });
  mockServer.outbox.push({ type: 'SYNC_ACK', payload: { opId: op.opId } });
}

function serverSimulateRemoteUser(): void {
  const allIds = Object.keys(mockServer.tasks);
  if (allIds.length === 0) return;
  const randomId = allIds[Math.floor(Math.random() * allIds.length)];
  const task = mockServer.tasks[randomId];
  if (!task) return;
  const columns: ColumnId[] = ['todo', 'inProgress', 'done'];
  const otherCols = columns.filter((c) => c !== task.column);
  const newCol = otherCols[Math.floor(Math.random() * otherCols.length)];

  const oldCol = task.column;
  mockServer.columnOrder[oldCol] = mockServer.columnOrder[oldCol].filter((id) => id !== randomId);
  mockServer.columnOrder[newCol].push(randomId);
  mockServer.tasks[randomId] = { ...task, column: newCol, lastMovedBy: 'remote-user', version: task.version + 1 };

  mockServer.opLog.push({ opId: uuid(), taskId: randomId, userId: 'remote-user', timestamp: Date.now() });
  mockServer.outbox.push({
    type: 'REMOTE_UPDATE',
    payload: {
      tasks: { ...mockServer.tasks },
      columnOrder: { ...mockServer.columnOrder },
    },
  });
}

function serverFlush(): Action[] {
  const actions = [...mockServer.outbox];
  mockServer.outbox = [];
  return actions;
}

// ─── Reducer ─────────────────────────────────────────────────────────────────

function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = uuid();
      const newTask: Task = {
        id,
        text: action.payload.text,
        column: 'todo',
        order: 0,
        lastMovedBy: state.currentUser,
        version: 1,
      };
      const newColumnOrder = { ...state.columnOrder, todo: [id, ...state.columnOrder.todo] };
      const op: OptimisticOp = { opId: uuid(), type: 'ADD', payload: { taskId: id }, timestamp: Date.now() };
      mockServer.tasks[id] = newTask;
      mockServer.columnOrder = { ...newColumnOrder };
      setTimeout(() => serverApplyOp(op, state.currentUser), 300 + Math.random() * 500);
      return {
        ...state,
        tasks: { ...state.tasks, [id]: newTask },
        columnOrder: newColumnOrder,
        pendingOptimistic: [...state.pendingOptimistic, op],
      };
    }
    case 'MOVE_TASK': {
      const { taskId, toColumn, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const fromColumn = task.column;
      const newFromList = state.columnOrder[fromColumn].filter((id) => id !== taskId);
      const newToList = fromColumn === toColumn ? newFromList : [...state.columnOrder[toColumn]];
      if (fromColumn !== toColumn) {
        newToList.splice(toIndex, 0, taskId);
      } else {
        newFromList.splice(toIndex, 0, taskId);
      }
      const updatedTask = { ...task, column: toColumn, lastMovedBy: state.currentUser, version: task.version + 1 };
      const newColumnOrder = {
        ...state.columnOrder,
        [fromColumn]: fromColumn === toColumn ? newFromList : newFromList,
        [toColumn]: fromColumn === toColumn ? newFromList : newToList,
      };
      const op: OptimisticOp = { opId: uuid(), type: 'MOVE', payload: { taskId, toColumn, toIndex }, timestamp: Date.now() };
      mockServer.tasks[taskId] = updatedTask;
      mockServer.columnOrder = { ...newColumnOrder };
      setTimeout(() => serverApplyOp(op, state.currentUser), 300 + Math.random() * 500);
      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columnOrder: newColumnOrder,
        pendingOptimistic: [...state.pendingOptimistic, op],
      };
    }
    case 'REORDER_TASK': {
      const { taskId, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const col = task.column;
      const list = state.columnOrder[col].filter((id) => id !== taskId);
      list.splice(toIndex, 0, taskId);
      const newColumnOrder = { ...state.columnOrder, [col]: list };
      const op: OptimisticOp = { opId: uuid(), type: 'REORDER', payload: { taskId, toIndex }, timestamp: Date.now() };
      mockServer.columnOrder = { ...newColumnOrder };
      setTimeout(() => serverApplyOp(op, state.currentUser), 300 + Math.random() * 500);
      return {
        ...state,
        columnOrder: newColumnOrder,
        pendingOptimistic: [...state.pendingOptimistic, op],
      };
    }
    case 'REMOTE_UPDATE': {
      return {
        ...state,
        tasks: action.payload.tasks,
        columnOrder: action.payload.columnOrder,
      };
    }
    case 'CONFLICT_DETECTED': {
      return {
        ...state,
        conflicts: [...state.conflicts, action.payload],
      };
    }
    case 'CONFLICT_DISMISSED': {
      return {
        ...state,
        conflicts: state.conflicts.filter((c) => c.taskId !== action.payload.taskId),
      };
    }
    case 'SYNC_ACK': {
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.filter((op) => op.opId !== action.payload.opId),
      };
    }
    case 'SET_USERS': {
      return { ...state, connectedUsers: action.payload.users };
    }
    default:
      return state;
  }
}

// ─── Initial State ───────────────────────────────────────────────────────────

const initialState: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user-' + Math.random().toString(36).substring(2, 6),
  connectedUsers: [],
  pendingOptimistic: [],
  conflicts: [],
};

// ─── Components ──────────────────────────────────────────────────────────────

function BoardHeader({ currentUser, connectedUsers }: { currentUser: string; connectedUsers: string[] }) {
  return (
    <div className={styles.header}>
      <h1>Collaborative Todo Board</h1>
      <div className={styles.users}>
        <span>You: {currentUser}</span>
        {connectedUsers.map((u) => (
          <span key={u} className={styles.userBadge}>{u}</span>
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
  const [dragging, setDragging] = useState(false);

  const handleDragStart = (e: React.DragEvent) => {
    setDragging(true);
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
      <div className={styles.cardText}>{task.text}</div>
      <div className={styles.cardMeta}>
        <span className={styles.assignee}>{task.lastMovedBy}</span>
        <span className={styles.version}>v{task.version}</span>
      </div>
    </div>
  );
}

function TaskCreator({ dispatch }: { dispatch: React.Dispatch<Action> }) {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    dispatch({ type: 'ADD_TASK', payload: { text: trimmed } });
    setText('');
  };

  return (
    <form className={styles.taskCreator} onSubmit={handleSubmit}>
      <input
        className={styles.taskInput}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="New task..."
      />
      <button className={styles.addBtn} type="submit">Add</button>
    </form>
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
  const columnRef = useRef<HTMLDivElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const taskId = e.dataTransfer.getData('text/plain');
      if (!taskId) return;
      const task = tasks[taskId];
      if (!task) return;

      let toIndex = taskIds.length;
      if (columnRef.current) {
        const cards = columnRef.current.querySelectorAll('[data-card]');
        for (let i = 0; i < cards.length; i++) {
          const rect = cards[i].getBoundingClientRect();
          const midY = rect.top + rect.height / 2;
          if (e.clientY < midY) {
            toIndex = i;
            break;
          }
        }
      }

      if (task.column === columnId) {
        dispatch({ type: 'REORDER_TASK', payload: { taskId, toIndex } });
      } else {
        dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn: columnId, toIndex } });
      }
    },
    [columnId, taskIds, tasks, dispatch]
  );

  const handleCardDragStart = useCallback((e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData('text/plain', taskId);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <div className={styles.column} onDragOver={handleDragOver} onDrop={handleDrop} ref={columnRef}>
      <h2 className={styles.columnTitle}>{title}</h2>
      {columnId === 'todo' && <TaskCreator dispatch={dispatch} />}
      <div className={styles.cardList}>
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
    </div>
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
            Conflict on &quot;{tasks[c.taskId]?.text || c.taskId}&quot; — also moved by {c.remoteUser}
          </span>
          <button onClick={() => dispatch({ type: 'CONFLICT_DISMISSED', payload: { taskId: c.taskId } })}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Custom Hook: Mock Sync ──────────────────────────────────────────────────

function useMockSync(dispatch: React.Dispatch<Action>) {
  useEffect(() => {
    const pollInterval = setInterval(() => {
      const actions = serverFlush();
      actions.forEach((a) => dispatch(a));
    }, 500);

    const remoteInterval = setInterval(() => {
      setTimeout(() => serverSimulateRemoteUser(), Math.random() * 2000);
    }, 5000);

    dispatch({ type: 'SET_USERS', payload: { users: ['remote-user'] } });

    return () => {
      clearInterval(pollInterval);
      clearInterval(remoteInterval);
    };
  }, [dispatch]);
}

// ─── Root Component ──────────────────────────────────────────────────────────

const COLUMN_CONFIG: { id: ColumnId; title: string }[] = [
  { id: 'todo', title: 'Todo' },
  { id: 'inProgress', title: 'In Progress' },
  { id: 'done', title: 'Done' },
];

function TodoBoardApp() {
  const [state, dispatch] = useReducer(boardReducer, initialState);

  useMockSync(dispatch);

  return (
    <div className={styles.app}>
      <BoardHeader currentUser={state.currentUser} connectedUsers={state.connectedUsers} />
      <div className={styles.board}>
        {COLUMN_CONFIG.map((col) => (
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
