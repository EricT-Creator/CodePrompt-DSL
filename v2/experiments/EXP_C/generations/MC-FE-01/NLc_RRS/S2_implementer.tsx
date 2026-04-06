import React, { useReducer, useEffect, useCallback, useRef } from 'react';

// ── Types ──

type ColumnId = 'todo' | 'inprogress' | 'done';

interface Task {
  id: string;
  title: string;
  column: ColumnId;
  order: number;
  version: number;
}

interface ConflictInfo {
  taskId: string;
  localColumn: string;
  remoteColumn: string;
  timestamp: number;
}

interface BoardState {
  tasks: Task[];
  userId: string;
  conflicts: ConflictInfo[];
  connected: boolean;
}

interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  senderId: string;
  version?: number;
}

type BoardAction =
  | { type: 'INIT_BOARD'; tasks: Task[] }
  | { type: 'ADD_TASK'; title: string }
  | { type: 'MOVE_TASK'; taskId: string; targetColumn: ColumnId; targetIndex: number }
  | { type: 'REORDER'; taskId: string; targetIndex: number }
  | { type: 'REMOTE_UPDATE'; task: Task }
  | { type: 'CONFLICT'; conflict: ConflictInfo; serverTask: Task }
  | { type: 'RESOLVE_CONFLICT'; taskId: string }
  | { type: 'SET_CONNECTED'; connected: boolean };

// ── Styles (CSS Modules inlined as objects since single file) ──

const styles: Record<string, React.CSSProperties> = {
  app: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: 1200,
    margin: '0 auto',
    padding: 20,
    background: '#f0f2f5',
    minHeight: '100vh',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: 20,
  },
  connectionBadge: {
    display: 'inline-block',
    padding: '4px 12px',
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
  },
  board: {
    display: 'flex',
    gap: 16,
    alignItems: 'flex-start',
  },
  column: {
    flex: 1,
    minWidth: 250,
    borderRadius: 8,
    padding: 12,
    minHeight: 400,
  },
  columnTitle: {
    fontSize: 16,
    fontWeight: 700,
    marginBottom: 12,
    textAlign: 'center' as const,
  },
  card: {
    background: '#fff',
    borderRadius: 6,
    padding: '10px 14px',
    marginBottom: 8,
    cursor: 'grab',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    transition: 'box-shadow 0.15s',
    borderLeft: '4px solid transparent',
  },
  cardConflict: {
    borderColor: '#e74c3c',
    animation: 'pulse 1s ease-in-out infinite',
  },
  dropTarget: {
    border: '2px dashed #3498db',
    background: 'rgba(52,152,219,0.05)',
  },
  conflictBanner: {
    background: '#ffeaa7',
    border: '1px solid #fdcb6e',
    borderRadius: 8,
    padding: '10px 16px',
    marginBottom: 16,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  newTaskContainer: {
    display: 'flex',
    gap: 8,
    marginBottom: 20,
    justifyContent: 'center',
  },
  input: {
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ccc',
    fontSize: 14,
    width: 300,
  },
  button: {
    padding: '8px 16px',
    borderRadius: 6,
    border: 'none',
    background: '#3498db',
    color: '#fff',
    fontSize: 14,
    cursor: 'pointer',
    fontWeight: 600,
  },
  userLabel: {
    fontSize: 11,
    color: '#999',
    marginTop: 4,
  },
  splitView: {
    display: 'flex',
    gap: 24,
  },
  splitPanel: {
    flex: 1,
    border: '2px solid #ddd',
    borderRadius: 12,
    padding: 16,
    background: '#fff',
  },
  panelTitle: {
    textAlign: 'center' as const,
    fontSize: 14,
    fontWeight: 700,
    marginBottom: 12,
    color: '#555',
  },
};

const columnColors: Record<ColumnId, string> = {
  todo: '#dfe6e9',
  inprogress: '#ffeaa7',
  done: '#55efc4',
};

const columnLabels: Record<ColumnId, string> = {
  todo: 'Todo',
  inprogress: 'In Progress',
  done: 'Done',
};

// ── Reducer ──

let globalIdCounter = 0;
const genId = (): string => `task-${++globalIdCounter}-${Date.now()}`;

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'INIT_BOARD':
      return { ...state, tasks: action.tasks };

    case 'ADD_TASK': {
      const todoTasks = state.tasks.filter((t) => t.column === 'todo');
      const newTask: Task = {
        id: genId(),
        title: action.title,
        column: 'todo',
        order: todoTasks.length,
        version: 1,
      };
      return { ...state, tasks: [...state.tasks, newTask] };
    }

    case 'MOVE_TASK': {
      const tasks = state.tasks.map((t) => {
        if (t.id === action.taskId) {
          return {
            ...t,
            column: action.targetColumn,
            order: action.targetIndex,
            version: t.version + 1,
          };
        }
        return t;
      });
      return { ...state, tasks };
    }

    case 'REORDER': {
      const tasks = state.tasks.map((t) => {
        if (t.id === action.taskId) {
          return { ...t, order: action.targetIndex };
        }
        return t;
      });
      return { ...state, tasks };
    }

    case 'REMOTE_UPDATE': {
      const exists = state.tasks.find((t) => t.id === action.task.id);
      if (exists) {
        const tasks = state.tasks.map((t) =>
          t.id === action.task.id ? action.task : t
        );
        return { ...state, tasks };
      }
      return { ...state, tasks: [...state.tasks, action.task] };
    }

    case 'CONFLICT': {
      const tasks = state.tasks.map((t) =>
        t.id === action.serverTask.id ? action.serverTask : t
      );
      return {
        ...state,
        tasks,
        conflicts: [...state.conflicts, action.conflict],
      };
    }

    case 'RESOLVE_CONFLICT':
      return {
        ...state,
        conflicts: state.conflicts.filter((c) => c.taskId !== action.taskId),
      };

    case 'SET_CONNECTED':
      return { ...state, connected: action.connected };

    default:
      return state;
  }
}

// ── Mock WebSocket Server ──

type WSCallback = (msg: WSMessage) => void;

class MockWSServer {
  private tasks: Task[] = [];
  private clients: Map<string, WSCallback> = new Map();
  private latency = 200;

  constructor(initialTasks: Task[]) {
    this.tasks = JSON.parse(JSON.stringify(initialTasks));
  }

  connect(clientId: string, callback: WSCallback): void {
    this.clients.set(clientId, callback);
    setTimeout(() => {
      callback({
        type: 'INIT_BOARD',
        payload: { tasks: JSON.parse(JSON.stringify(this.tasks)) },
        senderId: 'server',
      });
    }, 50);
  }

  disconnect(clientId: string): void {
    this.clients.delete(clientId);
  }

  send(clientId: string, msg: WSMessage): void {
    setTimeout(() => {
      this.processMessage(clientId, msg);
    }, this.latency);
  }

  private processMessage(senderId: string, msg: WSMessage): void {
    if (msg.type === 'MOVE_TASK') {
      const { taskId, targetColumn, targetIndex, version } = msg.payload as {
        taskId: string;
        targetColumn: ColumnId;
        targetIndex: number;
        version: number;
      };
      const task = this.tasks.find((t) => t.id === taskId);
      if (!task) return;

      if (task.version !== version) {
        const senderCb = this.clients.get(senderId);
        if (senderCb) {
          senderCb({
            type: 'CONFLICT',
            payload: {
              taskId,
              localColumn: targetColumn,
              remoteColumn: task.column,
              serverTask: JSON.parse(JSON.stringify(task)),
            },
            senderId: 'server',
          });
        }
        return;
      }

      task.column = targetColumn;
      task.order = targetIndex;
      task.version += 1;

      this.clients.forEach((cb, cId) => {
        if (cId !== senderId) {
          cb({
            type: 'REMOTE_UPDATE',
            payload: { task: JSON.parse(JSON.stringify(task)) },
            senderId: 'server',
          });
        }
      });

      const senderCb = this.clients.get(senderId);
      if (senderCb) {
        senderCb({
          type: 'VERSION_ACK',
          payload: { taskId, newVersion: task.version },
          senderId: 'server',
        });
      }
    } else if (msg.type === 'ADD_TASK') {
      const { task } = msg.payload as { task: Task };
      this.tasks.push(JSON.parse(JSON.stringify(task)));
      this.clients.forEach((cb, cId) => {
        if (cId !== senderId) {
          cb({
            type: 'REMOTE_UPDATE',
            payload: { task: JSON.parse(JSON.stringify(task)) },
            senderId: 'server',
          });
        }
      });
    }
  }
}

// ── Components ──

const ConflictBanner: React.FC<{
  conflicts: ConflictInfo[];
  onRefresh: () => void;
  onDismiss: (taskId: string) => void;
}> = ({ conflicts, onRefresh, onDismiss }) => {
  if (conflicts.length === 0) return null;
  return (
    <div style={styles.conflictBanner}>
      <div>
        <strong>⚠ Conflict detected:</strong>{' '}
        {conflicts.map((c) => (
          <span key={c.taskId} style={{ marginRight: 8 }}>
            Task {c.taskId.slice(0, 8)} was moved by another user.{' '}
            <button
              style={{ ...styles.button, padding: '2px 8px', fontSize: 12 }}
              onClick={() => onDismiss(c.taskId)}
            >
              Dismiss
            </button>
          </span>
        ))}
      </div>
      <button style={styles.button} onClick={onRefresh}>
        Refresh
      </button>
    </div>
  );
};

const TaskCard: React.FC<{
  task: Task;
  hasConflict: boolean;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
}> = ({ task, hasConflict, onDragStart }) => {
  const cardStyle: React.CSSProperties = {
    ...styles.card,
    ...(hasConflict
      ? {
          borderLeftColor: '#e74c3c',
          boxShadow: '0 0 8px rgba(231,76,60,0.4)',
        }
      : {}),
  };

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      style={cardStyle}
    >
      <div style={{ fontWeight: 500, fontSize: 14 }}>{task.title}</div>
      <div style={styles.userLabel}>v{task.version}</div>
    </div>
  );
};

const NewTaskInput: React.FC<{
  onAdd: (title: string) => void;
}> = ({ onAdd }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const handleAdd = () => {
    const val = inputRef.current?.value.trim();
    if (val) {
      onAdd(val);
      if (inputRef.current) inputRef.current.value = '';
    }
  };
  return (
    <div style={styles.newTaskContainer}>
      <input
        ref={inputRef}
        style={styles.input}
        placeholder="New task title..."
        onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
      />
      <button style={styles.button} onClick={handleAdd}>
        Add Task
      </button>
    </div>
  );
};

const Column: React.FC<{
  columnId: ColumnId;
  tasks: Task[];
  conflicts: ConflictInfo[];
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDrop: (e: React.DragEvent, columnId: ColumnId) => void;
}> = ({ columnId, tasks, conflicts, onDragStart, onDrop }) => {
  const [isOver, setIsOver] = React.useState(false);
  const conflictIds = new Set(conflicts.map((c) => c.taskId));

  const sorted = [...tasks].sort((a, b) => a.order - b.order);

  return (
    <div
      style={{
        ...styles.column,
        background: columnColors[columnId],
        ...(isOver ? styles.dropTarget : {}),
      }}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={(e) => {
        setIsOver(false);
        onDrop(e, columnId);
      }}
    >
      <div style={styles.columnTitle}>{columnLabels[columnId]}</div>
      {sorted.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          hasConflict={conflictIds.has(task.id)}
          onDragStart={onDragStart}
        />
      ))}
    </div>
  );
};

const BoardView: React.FC<{
  state: BoardState;
  dispatch: React.Dispatch<BoardAction>;
  wsRef: React.MutableRefObject<MockWSServer | null>;
  userId: string;
}> = ({ state, dispatch, wsRef, userId }) => {
  const handleDragStart = useCallback(
    (e: React.DragEvent, taskId: string) => {
      e.dataTransfer.setData('text/plain', taskId);
      e.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent, targetColumn: ColumnId) => {
      e.preventDefault();
      const taskId = e.dataTransfer.getData('text/plain');
      if (!taskId) return;

      const task = state.tasks.find((t) => t.id === taskId);
      if (!task) return;
      if (task.column === targetColumn) return;

      const targetTasks = state.tasks.filter((t) => t.column === targetColumn);
      const targetIndex = targetTasks.length;

      dispatch({ type: 'MOVE_TASK', taskId, targetColumn, targetIndex });

      if (wsRef.current) {
        wsRef.current.send(userId, {
          type: 'MOVE_TASK',
          payload: {
            taskId,
            targetColumn,
            targetIndex,
            version: task.version,
          },
          senderId: userId,
        });
      }
    },
    [state.tasks, dispatch, wsRef, userId]
  );

  const handleAddTask = useCallback(
    (title: string) => {
      dispatch({ type: 'ADD_TASK', title });
    },
    [dispatch]
  );

  const columns: ColumnId[] = ['todo', 'inprogress', 'done'];

  return (
    <div>
      <NewTaskInput onAdd={handleAddTask} />
      <div style={styles.board}>
        {columns.map((col) => (
          <Column
            key={col}
            columnId={col}
            tasks={state.tasks.filter((t) => t.column === col)}
            conflicts={state.conflicts}
            onDragStart={handleDragStart}
            onDrop={handleDrop}
          />
        ))}
      </div>
    </div>
  );
};

// ── App ──

const initialTasks: Task[] = [
  { id: 'seed-1', title: 'Design mockups', column: 'todo', order: 0, version: 1 },
  { id: 'seed-2', title: 'Setup CI/CD', column: 'todo', order: 1, version: 1 },
  { id: 'seed-3', title: 'Write API docs', column: 'inprogress', order: 0, version: 1 },
  { id: 'seed-4', title: 'Code review', column: 'inprogress', order: 1, version: 1 },
  { id: 'seed-5', title: 'Deploy v1.0', column: 'done', order: 0, version: 1 },
];

const App: React.FC = () => {
  const [stateA, dispatchA] = useReducer(boardReducer, {
    tasks: [],
    userId: 'user-A',
    conflicts: [],
    connected: false,
  });

  const [stateB, dispatchB] = useReducer(boardReducer, {
    tasks: [],
    userId: 'user-B',
    conflicts: [],
    connected: false,
  });

  const wsServerRef = useRef<MockWSServer | null>(null);

  useEffect(() => {
    const server = new MockWSServer(initialTasks);
    wsServerRef.current = server;

    server.connect('user-A', (msg: WSMessage) => {
      if (msg.type === 'INIT_BOARD') {
        dispatchA({
          type: 'INIT_BOARD',
          tasks: msg.payload.tasks as Task[],
        });
        dispatchA({ type: 'SET_CONNECTED', connected: true });
      } else if (msg.type === 'REMOTE_UPDATE') {
        dispatchA({
          type: 'REMOTE_UPDATE',
          task: msg.payload.task as Task,
        });
      } else if (msg.type === 'CONFLICT') {
        dispatchA({
          type: 'CONFLICT',
          conflict: {
            taskId: msg.payload.taskId as string,
            localColumn: msg.payload.localColumn as string,
            remoteColumn: msg.payload.remoteColumn as string,
            timestamp: Date.now(),
          },
          serverTask: msg.payload.serverTask as Task,
        });
      }
    });

    server.connect('user-B', (msg: WSMessage) => {
      if (msg.type === 'INIT_BOARD') {
        dispatchB({
          type: 'INIT_BOARD',
          tasks: msg.payload.tasks as Task[],
        });
        dispatchB({ type: 'SET_CONNECTED', connected: true });
      } else if (msg.type === 'REMOTE_UPDATE') {
        dispatchB({
          type: 'REMOTE_UPDATE',
          task: msg.payload.task as Task,
        });
      } else if (msg.type === 'CONFLICT') {
        dispatchB({
          type: 'CONFLICT',
          conflict: {
            taskId: msg.payload.taskId as string,
            localColumn: msg.payload.localColumn as string,
            remoteColumn: msg.payload.remoteColumn as string,
            timestamp: Date.now(),
          },
          serverTask: msg.payload.serverTask as Task,
        });
      }
    });

    return () => {
      server.disconnect('user-A');
      server.disconnect('user-B');
    };
  }, []);

  const handleRefreshA = useCallback(() => {
    dispatchA({
      type: 'INIT_BOARD',
      tasks: stateA.tasks,
    });
    dispatchA({
      type: 'RESOLVE_CONFLICT',
      taskId: stateA.conflicts[0]?.taskId ?? '',
    });
  }, [stateA]);

  const handleRefreshB = useCallback(() => {
    dispatchB({
      type: 'INIT_BOARD',
      tasks: stateB.tasks,
    });
    dispatchB({
      type: 'RESOLVE_CONFLICT',
      taskId: stateB.conflicts[0]?.taskId ?? '',
    });
  }, [stateB]);

  return (
    <div style={styles.app}>
      <div style={styles.header}>
        <h1 style={{ margin: 0, fontSize: 24 }}>
          Real-Time Collaborative Todo Board
        </h1>
        <p style={{ color: '#666', fontSize: 13 }}>
          Two simulated users side by side. Drag cards between columns.
        </p>
      </div>

      <div style={styles.splitView}>
        <div style={styles.splitPanel}>
          <div style={styles.panelTitle}>
            👤 User A{' '}
            <span
              style={{
                ...styles.connectionBadge,
                background: stateA.connected ? '#00b894' : '#d63031',
                color: '#fff',
              }}
            >
              {stateA.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <ConflictBanner
            conflicts={stateA.conflicts}
            onRefresh={handleRefreshA}
            onDismiss={(taskId) =>
              dispatchA({ type: 'RESOLVE_CONFLICT', taskId })
            }
          />
          <BoardView
            state={stateA}
            dispatch={dispatchA}
            wsRef={wsServerRef}
            userId="user-A"
          />
        </div>

        <div style={styles.splitPanel}>
          <div style={styles.panelTitle}>
            👤 User B{' '}
            <span
              style={{
                ...styles.connectionBadge,
                background: stateB.connected ? '#00b894' : '#d63031',
                color: '#fff',
              }}
            >
              {stateB.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <ConflictBanner
            conflicts={stateB.conflicts}
            onRefresh={handleRefreshB}
            onDismiss={(taskId) =>
              dispatchB({ type: 'RESOLVE_CONFLICT', taskId })
            }
          />
          <BoardView
            state={stateB}
            dispatch={dispatchB}
            wsRef={wsServerRef}
            userId="user-B"
          />
        </div>
      </div>
    </div>
  );
};

export default App;
