import React, { useReducer, useEffect, useRef, useCallback } from 'react';
import styles from './S2_implementer.module.css';

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

type Action =
  | { type: 'INIT_BOARD'; payload: Task[] }
  | { type: 'ADD_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; targetColumn: ColumnId; targetIndex: number } }
  | { type: 'REORDER'; payload: { taskId: string; newOrder: number } }
  | { type: 'REMOTE_UPDATE'; payload: Task }
  | { type: 'CONFLICT'; payload: ConflictInfo }
  | { type: 'RESOLVE_CONFLICT'; payload: string }
  | { type: 'SET_CONNECTED'; payload: boolean };

const initialState: BoardState = {
  tasks: [],
  userId: Math.random().toString(36).substring(2, 9),
  conflicts: [],
  connected: false,
};

function reducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'INIT_BOARD':
      return { ...state, tasks: action.payload, connected: true };
    case 'ADD_TASK': {
      const newTask: Task = {
        id: Math.random().toString(36).substring(2, 9),
        title: action.payload.title,
        column: 'todo',
        order: state.tasks.filter(t => t.column === 'todo').length,
        version: 1,
      };
      return { ...state, tasks: [...state.tasks, newTask] };
    }
    case 'MOVE_TASK': {
      const { taskId, targetColumn, targetIndex } = action.payload;
      return {
        ...state,
        tasks: state.tasks.map(t =>
          t.id === taskId
            ? { ...t, column: targetColumn, order: targetIndex, version: t.version + 1 }
            : t
        ),
      };
    }
    case 'REORDER':
      return {
        ...state,
        tasks: state.tasks.map(t =>
          t.id === action.payload.taskId ? { ...t, order: action.payload.newOrder } : t
        ),
      };
    case 'REMOTE_UPDATE':
      return {
        ...state,
        tasks: state.tasks.map(t =>
          t.id === action.payload.id && action.payload.version > t.version ? action.payload : t
        ),
      };
    case 'CONFLICT':
      return {
        ...state,
        conflicts: [...state.conflicts, action.payload],
      };
    case 'RESOLVE_CONFLICT':
      return {
        ...state,
        conflicts: state.conflicts.filter(c => c.taskId !== action.payload),
      };
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };
    default:
      return state;
  }
}

interface MockWSServer {
  connect: (clientId: string, onMessage: (msg: any) => void) => void;
  disconnect: (clientId: string) => void;
  send: (clientId: string, message: any) => void;
}

function createMockWSServer(): MockWSServer {
  const clients = new Map<string, (msg: any) => void>();
  let tasks: Task[] = [
    { id: '1', title: 'Task 1', column: 'todo', order: 0, version: 1 },
    { id: '2', title: 'Task 2', column: 'inprogress', order: 0, version: 1 },
    { id: '3', title: 'Task 3', column: 'done', order: 0, version: 1 },
  ];

  return {
    connect: (clientId, onMessage) => {
      clients.set(clientId, onMessage);
      setTimeout(() => {
        onMessage({ type: 'INIT', payload: tasks });
      }, 100);
    },
    disconnect: (clientId) => {
      clients.delete(clientId);
    },
    send: (clientId, message) => {
      setTimeout(() => {
        if (message.type === 'MOVE_TASK') {
          const { taskId, targetColumn, version } = message.payload;
          const task = tasks.find(t => t.id === taskId);
          if (task) {
            if (version >= task.version) {
              task.column = targetColumn;
              task.version = version + 1;
              clients.forEach((cb, id) => {
                if (id !== clientId) {
                  cb({ type: 'REMOTE_UPDATE', payload: task });
                }
              });
            } else {
              const clientCallback = clients.get(clientId);
              if (clientCallback) {
                clientCallback({
                  type: 'CONFLICT',
                  payload: {
                    taskId,
                    localColumn: targetColumn,
                    remoteColumn: task.column,
                    timestamp: Date.now(),
                  },
                });
              }
            }
          }
        } else if (message.type === 'ADD_TASK') {
          const newTask: Task = {
            id: Math.random().toString(36).substring(2, 9),
            title: message.payload.title,
            column: 'todo',
            order: tasks.filter(t => t.column === 'todo').length,
            version: 1,
          };
          tasks.push(newTask);
          clients.forEach((cb) => {
            cb({ type: 'REMOTE_UPDATE', payload: newTask });
          });
        }
      }, 200);
    },
  };
}

const mockServer = createMockWSServer();

const ConflictBanner: React.FC<{
  conflicts: ConflictInfo[];
  onResolve: (taskId: string) => void;
  onRefresh: () => void;
}> = ({ conflicts, onResolve, onRefresh }) => {
  if (conflicts.length === 0) return null;
  return (
    <div className={styles.conflictBanner}>
      <span>Conflict detected on task {conflicts[0].taskId}</span>
      <button onClick={() => onResolve(conflicts[0].taskId)}>Dismiss</button>
      <button onClick={onRefresh}>Refresh</button>
    </div>
  );
};

const TaskCard: React.FC<{
  task: Task;
  isConflicted: boolean;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
}> = ({ task, isConflicted, onDragStart }) => {
  return (
    <div
      className={`${styles.taskCard} ${isConflicted ? styles.conflict : ''}`}
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
    >
      <span>{task.title}</span>
      <span className={styles.badge}>{task.column}</span>
    </div>
  );
};

const Column: React.FC<{
  columnId: ColumnId;
  title: string;
  tasks: Task[];
  conflictedTaskIds: string[];
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, columnId: ColumnId) => void;
}> = ({ columnId, title, tasks, conflictedTaskIds, onDragStart, onDragOver, onDrop }) => {
  return (
    <div
      className={styles.column}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, columnId)}
    >
      <h3>{title}</h3>
      {tasks
        .filter(t => t.column === columnId)
        .sort((a, b) => a.order - b.order)
        .map(task => (
          <TaskCard
            key={task.id}
            task={task}
            isConflicted={conflictedTaskIds.includes(task.id)}
            onDragStart={onDragStart}
          />
        ))}
    </div>
  );
};

const NewTaskInput: React.FC<{ onAdd: (title: string) => void }> = ({ onAdd }) => {
  const [title, setTitle] = React.useState('');
  return (
    <div className={styles.newTaskInput}>
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="New task..."
      />
      <button onClick={() => { if (title) { onAdd(title); setTitle(''); } }}>
        Add
      </button>
    </div>
  );
};

const App: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const serverRef = useRef(mockServer);

  useEffect(() => {
    const clientId = state.userId;
    serverRef.current.connect(clientId, (msg) => {
      if (msg.type === 'INIT') {
        dispatch({ type: 'INIT_BOARD', payload: msg.payload });
      } else if (msg.type === 'REMOTE_UPDATE') {
        dispatch({ type: 'REMOTE_UPDATE', payload: msg.payload });
      } else if (msg.type === 'CONFLICT') {
        dispatch({ type: 'CONFLICT', payload: msg.payload });
      }
    });
    return () => {
      serverRef.current.disconnect(clientId);
    };
  }, [state.userId]);

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData('text/plain', taskId);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetColumn: ColumnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    const task = state.tasks.find(t => t.id === taskId);
    if (task) {
      dispatch({ type: 'MOVE_TASK', payload: { taskId, targetColumn, targetIndex: 0 } });
      serverRef.current.send(state.userId, {
        type: 'MOVE_TASK',
        payload: { taskId, targetColumn, version: task.version },
      });
    }
  }, [state.tasks, state.userId]);

  const handleAddTask = useCallback((title: string) => {
    dispatch({ type: 'ADD_TASK', payload: { title } });
    serverRef.current.send(state.userId, { type: 'ADD_TASK', payload: { title } });
  }, [state.userId]);

  const conflictedTaskIds = state.conflicts.map(c => c.taskId);

  return (
    <div className={styles.app}>
      <ConflictBanner
        conflicts={state.conflicts}
        onResolve={(taskId) => dispatch({ type: 'RESOLVE_CONFLICT', payload: taskId })}
        onRefresh={() => window.location.reload()}
      />
      <h1>Collaborative Todo Board</h1>
      <div className={styles.connectionStatus}>
        {state.connected ? 'Connected' : 'Connecting...'}
      </div>
      <NewTaskInput onAdd={handleAddTask} />
      <div className={styles.board}>
        <Column
          columnId="todo"
          title="Todo"
          tasks={state.tasks}
          conflictedTaskIds={conflictedTaskIds}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        />
        <Column
          columnId="inprogress"
          title="In Progress"
          tasks={state.tasks}
          conflictedTaskIds={conflictedTaskIds}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        />
        <Column
          columnId="done"
          title="Done"
          tasks={state.tasks}
          conflictedTaskIds={conflictedTaskIds}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        />
      </div>
    </div>
  );
};

export default App;
