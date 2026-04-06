import React, { useReducer, useEffect, useRef, useCallback } from 'react';
import styles from './styles.module.css';

interface Task {
  id: string;
  title: string;
  column: 'todo' | 'inprogress' | 'done';
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

type Action =
  | { type: 'INIT_BOARD'; payload: { tasks: Task[]; userId: string } }
  | { type: 'ADD_TASK'; payload: { task: Task } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; targetColumn: Task['column']; targetIndex: number } }
  | { type: 'REORDER'; payload: { taskId: string; targetIndex: number } }
  | { type: 'REMOTE_UPDATE'; payload: { task: Task } }
  | { type: 'CONFLICT'; payload: { taskId: string; localColumn: string; remoteColumn: string } }
  | { type: 'RESOLVE_CONFLICT'; payload: { taskId: string } }
  | { type: 'SET_CONNECTED'; payload: { connected: boolean } };

const initialState: BoardState = {
  tasks: [],
  userId: '',
  conflicts: [],
  connected: false,
};

function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'INIT_BOARD':
      return {
        ...state,
        tasks: action.payload.tasks,
        userId: action.payload.userId,
      };
    case 'ADD_TASK':
      return {
        ...state,
        tasks: [...state.tasks, action.payload.task],
      };
    case 'MOVE_TASK': {
      const { taskId, targetColumn, targetIndex } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task) return state;
      
      const filtered = state.tasks.filter(t => t.id !== taskId);
      const columnTasks = filtered.filter(t => t.column === targetColumn);
      const otherTasks = filtered.filter(t => t.column !== targetColumn);
      
      const updatedTask = {
        ...task,
        column: targetColumn,
        order: targetIndex,
        version: task.version + 1,
      };
      
      columnTasks.splice(targetIndex, 0, updatedTask);
      columnTasks.forEach((t, idx) => t.order = idx);
      
      return {
        ...state,
        tasks: [...columnTasks, ...otherTasks],
      };
    }
    case 'REORDER': {
      const { taskId, targetIndex } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task) return state;
      
      const columnTasks = state.tasks
        .filter(t => t.column === task.column && t.id !== taskId)
        .sort((a, b) => a.order - b.order);
      
      columnTasks.splice(targetIndex, 0, task);
      columnTasks.forEach((t, idx) => t.order = idx);
      
      const otherTasks = state.tasks.filter(t => t.column !== task.column);
      return {
        ...state,
        tasks: [...columnTasks, ...otherTasks],
      };
    }
    case 'REMOTE_UPDATE': {
      const updatedTask = action.payload.task;
      return {
        ...state,
        tasks: state.tasks.map(t => t.id === updatedTask.id ? updatedTask : t),
      };
    }
    case 'CONFLICT': {
      const { taskId, localColumn, remoteColumn } = action.payload;
      return {
        ...state,
        conflicts: [
          ...state.conflicts,
          { taskId, localColumn, remoteColumn, timestamp: Date.now() },
        ],
      };
    }
    case 'RESOLVE_CONFLICT': {
      return {
        ...state,
        conflicts: state.conflicts.filter(c => c.taskId !== action.payload.taskId),
      };
    }
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload.connected };
    default:
      return state;
  }
}

class MockWSServer {
  private tasks: Task[] = [];
  private clients: Array<(msg: WSMessage) => void> = [];
  
  constructor(initialTasks: Task[]) {
    this.tasks = initialTasks;
  }
  
  connect(callback: (msg: WSMessage) => void) {
    this.clients.push(callback);
    return () => {
      const index = this.clients.indexOf(callback);
      if (index > -1) this.clients.splice(index, 1);
    };
  }
  
  send(senderId: string, msg: WSMessage) {
    if (msg.type === 'MOVE_TASK') {
      const payload = msg.payload as { taskId: string; targetColumn: string; targetIndex: number };
      const task = this.tasks.find(t => t.id === payload.taskId);
      if (!task) return;
      
      if (task.version === (msg.version || 0)) {
        task.version += 1;
        task.column = payload.targetColumn as Task['column'];
        task.order = payload.targetIndex;
        
        this.broadcast(senderId, {
          type: 'REMOTE_UPDATE',
          payload: { task },
          senderId: 'server',
          version: task.version,
        });
      } else {
        this.sendTo(senderId, {
          type: 'CONFLICT',
          payload: { taskId: payload.taskId },
          senderId: 'server',
        });
      }
    } else if (msg.type === 'ADD_TASK') {
      const payload = msg.payload as { task: Task };
      this.tasks.push(payload.task);
      this.broadcast(senderId, {
        type: 'REMOTE_UPDATE',
        payload: { task: payload.task },
        senderId: 'server',
      });
    }
  }
  
  private broadcast(excludeSenderId: string, msg: WSMessage) {
    this.clients.forEach(callback => {
      setTimeout(() => callback(msg), 200);
    });
  }
  
  private sendTo(clientId: string, msg: WSMessage) {
    this.clients.forEach(callback => {
      setTimeout(() => callback(msg), 200);
    });
  }
}

const TaskCard: React.FC<{
  task: Task;
  dispatch: React.Dispatch<Action>;
  hasConflict: boolean;
}> = ({ task, dispatch, hasConflict }) => {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('text/plain', task.id);
    e.dataTransfer.effectAllowed = 'move';
  };
  
  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={`${styles.taskCard} ${hasConflict ? styles.conflict : ''}`}
    >
      <div className={styles.taskTitle}>{task.title}</div>
      <div className={styles.taskStatus}>{task.column}</div>
    </div>
  );
};

const Column: React.FC<{
  id: Task['column'];
  title: string;
  tasks: Task[];
  dispatch: React.Dispatch<Action>;
  conflicts: ConflictInfo[];
}> = ({ id, title, tasks, dispatch, conflicts }) => {
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    const elem = e.currentTarget as HTMLElement;
    elem.classList.add(styles.dropTarget);
  };
  
  const handleDragLeave = (e: React.DragEvent) => {
    const elem = e.currentTarget as HTMLElement;
    elem.classList.remove(styles.dropTarget);
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const elem = e.currentTarget as HTMLElement;
    elem.classList.remove(styles.dropTarget);
    
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;
    
    const rect = elem.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const childIndex = Math.floor(y / 60);
    const targetIndex = Math.min(childIndex, tasks.length);
    
    dispatch({
      type: 'MOVE_TASK',
      payload: { taskId, targetColumn: id, targetIndex },
    });
  };
  
  const sortedTasks = [...tasks].sort((a, b) => a.order - b.order);
  
  return (
    <div
      className={styles.column}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={styles.columnHeader}>
        <h3>{title}</h3>
        <span className={styles.taskCount}>({tasks.length})</span>
      </div>
      <div className={styles.taskList}>
        {sortedTasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            dispatch={dispatch}
            hasConflict={conflicts.some(c => c.taskId === task.id)}
          />
        ))}
      </div>
    </div>
  );
};

const ConflictBanner: React.FC<{
  conflicts: ConflictInfo[];
  dispatch: React.Dispatch<Action>;
}> = ({ conflicts, dispatch }) => {
  if (conflicts.length === 0) return null;
  
  const handleRefresh = () => {
    // In a real app, this would fetch the full board snapshot
    conflicts.forEach(conflict => {
      dispatch({ type: 'RESOLVE_CONFLICT', payload: { taskId: conflict.taskId } });
    });
  };
  
  return (
    <div className={styles.conflictBanner}>
      <span>Conflict detected for {conflicts.length} task(s)</span>
      <button onClick={handleRefresh}>Refresh</button>
    </div>
  );
};

const NewTaskInput: React.FC<{
  dispatch: React.Dispatch<Action>;
  userId: string;
}> = ({ dispatch, userId }) => {
  const [title, setTitle] = React.useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    
    const newTask: Task = {
      id: `task-${Date.now()}`,
      title: title.trim(),
      column: 'todo',
      order: 0,
      version: 1,
    };
    
    dispatch({ type: 'ADD_TASK', payload: { task: newTask } });
    setTitle('');
  };
  
  return (
    <form onSubmit={handleSubmit} className={styles.newTaskForm}>
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Enter new task title"
        className={styles.taskInput}
      />
      <button type="submit" className={styles.addButton}>
        Add Task
      </button>
    </form>
  );
};

const Board: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const wsServerRef = useRef<MockWSServer | null>(null);
  const disconnectRef = useRef<(() => void) | null>(null);
  
  useEffect(() => {
    const initialTasks: Task[] = [
      { id: '1', title: 'Design mockups', column: 'todo', order: 0, version: 1 },
      { id: '2', title: 'Implement components', column: 'todo', order: 1, version: 1 },
      { id: '3', title: 'Add drag and drop', column: 'inprogress', order: 0, version: 1 },
      { id: '4', title: 'Test conflict resolution', column: 'done', order: 0, version: 1 },
    ];
    
    const userId = `user-${Math.random().toString(36).substr(2, 9)}`;
    dispatch({ type: 'INIT_BOARD', payload: { tasks: initialTasks, userId } });
    
    const server = new MockWSServer(initialTasks);
    wsServerRef.current = server;
    
    const disconnect = server.connect((msg) => {
      if (msg.type === 'REMOTE_UPDATE') {
        const payload = msg.payload as { task: Task };
        if (msg.senderId !== userId) {
          dispatch({ type: 'REMOTE_UPDATE', payload: { task: payload.task } });
        }
      } else if (msg.type === 'CONFLICT') {
        const payload = msg.payload as { taskId: string };
        const task = state.tasks.find(t => t.id === payload.taskId);
        if (task) {
          dispatch({
            type: 'CONFLICT',
            payload: {
              taskId: payload.taskId,
              localColumn: task.column,
              remoteColumn: task.column,
            },
          });
        }
      }
    });
    
    disconnectRef.current = disconnect;
    dispatch({ type: 'SET_CONNECTED', payload: { connected: true } });
    
    return () => {
      if (disconnectRef.current) disconnectRef.current();
      dispatch({ type: 'SET_CONNECTED', payload: { connected: false } });
    };
  }, []);
  
  const sendMove = useCallback((taskId: string, targetColumn: Task['column'], targetIndex: number) => {
    const task = state.tasks.find(t => t.id === taskId);
    if (!task || !wsServerRef.current) return;
    
    wsServerRef.current.send(state.userId, {
      type: 'MOVE_TASK',
      payload: { taskId, targetColumn, targetIndex },
      senderId: state.userId,
      version: task.version,
    });
  }, [state.userId, state.tasks]);
  
  useEffect(() => {
    // For demo purposes, we'll send moves to the mock server
    // In a real app, this would be connected to actual WebSocket events
  }, [sendMove]);
  
  const columns: Array<{ id: Task['column']; title: string }> = [
    { id: 'todo', title: 'To Do' },
    { id: 'inprogress', title: 'In Progress' },
    { id: 'done', title: 'Done' },
  ];
  
  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1>Real-Time Collaborative Todo Board</h1>
        <div className={styles.userStatus}>
          <span className={`${styles.statusDot} ${state.connected ? styles.connected : styles.disconnected}`} />
          {state.userId ? `User: ${state.userId}` : 'Connecting...'}
        </div>
      </header>
      
      <ConflictBanner conflicts={state.conflicts} dispatch={dispatch} />
      
      <NewTaskInput dispatch={dispatch} userId={state.userId} />
      
      <div className={styles.board}>
        {columns.map(col => (
          <Column
            key={col.id}
            id={col.id}
            title={col.title}
            tasks={state.tasks.filter(t => t.column === col.id)}
            dispatch={dispatch}
            conflicts={state.conflicts}
          />
        ))}
      </div>
    </div>
  );
};

export default Board;