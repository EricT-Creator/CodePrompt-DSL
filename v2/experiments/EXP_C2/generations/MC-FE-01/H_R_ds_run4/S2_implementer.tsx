import React, { useReducer, useEffect, useState } from 'react';
import styles from './TodoBoard.module.css';

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  order: number;
  lastMovedBy: string;
  version: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  currentUser: string;
  connectedUsers: string[];
  pendingOps: PendingOp[];
  conflicts: Conflict[];
}

interface PendingOp {
  opId: string;
  type: 'MOVE' | 'REORDER' | 'ADD';
  payload: any;
  timestamp: number;
}

interface Conflict {
  taskId: string;
  localUser: string;
  remoteUser: string;
  resolvedAt?: number;
}

type BoardAction =
  | { type: 'ADD_TASK'; payload: { id: string; text: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; from: ColumnId; to: ColumnId; order: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; column: ColumnId; newOrder: number } }
  | { type: 'REMOTE_UPDATE'; payload: { tasks: Task[]; columnOrder: Record<ColumnId, string[]> } }
  | { type: 'CONFLICT_DETECTED'; payload: Conflict }
  | { type: 'CONFLICT_DISMISSED'; payload: { taskId: string } }
  | { type: 'SYNC_ACK'; payload: { opId: string } }
  | { type: 'SET_USERS'; payload: { currentUser: string; connectedUsers: string[] } };

const initialState: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user_1',
  connectedUsers: ['user_1', 'user_2'],
  pendingOps: [],
  conflicts: [],
};

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const { id, text } = action.payload;
      const newTask: Task = {
        id,
        text,
        column: 'todo',
        order: 0,
        lastMovedBy: state.currentUser,
        version: 1,
      };
      const newTasks = { ...state.tasks, [id]: newTask };
      const newColumnOrder = {
        ...state.columnOrder,
        todo: [id, ...state.columnOrder.todo.map(id => {
          const task = state.tasks[id];
          return { ...task, order: task.order + 1 };
        })].map(t => typeof t === 'string' ? t : t.id),
      };
      return {
        ...state,
        tasks: newTasks,
        columnOrder: newColumnOrder,
        pendingOps: [...state.pendingOps, {
          opId: `add_${id}_${Date.now()}`,
          type: 'ADD',
          payload: { taskId: id, text },
          timestamp: Date.now(),
        }],
      };
    }
    case 'MOVE_TASK': {
      const { taskId, from, to, order } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      const updatedTask = {
        ...task,
        column: to,
        order,
        lastMovedBy: state.currentUser,
        version: task.version + 1,
      };
      const newTasks = { ...state.tasks, [taskId]: updatedTask };
      const newFromOrder = state.columnOrder[from].filter(id => id !== taskId);
      const toInsertAt = Math.min(order, state.columnOrder[to].length);
      const newToOrder = [...state.columnOrder[to]];
      newToOrder.splice(toInsertAt, 0, taskId);
      const newColumnOrder = {
        ...state.columnOrder,
        [from]: newFromOrder,
        [to]: newToOrder,
      };
      return {
        ...state,
        tasks: newTasks,
        columnOrder: newColumnOrder,
        pendingOps: [...state.pendingOps, {
          opId: `move_${taskId}_${Date.now()}`,
          type: 'MOVE',
          payload: { taskId, from, to, order },
          timestamp: Date.now(),
        }],
      };
    }
    case 'REORDER_TASK': {
      const { taskId, column, newOrder } = action.payload;
      const task = state.tasks[taskId];
      if (!task || task.column !== column) return state;
      const currentOrder = state.columnOrder[column];
      const currentIndex = currentOrder.indexOf(taskId);
      if (currentIndex === -1) return state;
      const newOrderArray = [...currentOrder];
      newOrderArray.splice(currentIndex, 1);
      newOrderArray.splice(newOrder, 0, taskId);
      const updatedTask = {
        ...task,
        order: newOrder,
        lastMovedBy: state.currentUser,
        version: task.version + 1,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columnOrder: { ...state.columnOrder, [column]: newOrderArray },
        pendingOps: [...state.pendingOps, {
          opId: `reorder_${taskId}_${Date.now()}`,
          type: 'REORDER',
          payload: { taskId, column, newOrder },
          timestamp: Date.now(),
        }],
      };
    }
    case 'REMOTE_UPDATE': {
      const { tasks, columnOrder } = action.payload;
      const mergedTasks = { ...state.tasks };
      tasks.forEach(task => {
        if (!mergedTasks[task.id] || task.version > mergedTasks[task.id].version) {
          mergedTasks[task.id] = task;
        }
      });
      return {
        ...state,
        tasks: mergedTasks,
        columnOrder,
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
        conflicts: state.conflicts.filter(c => c.taskId !== action.payload.taskId),
      };
    }
    case 'SYNC_ACK': {
      const { opId } = action.payload;
      return {
        ...state,
        pendingOps: state.pendingOps.filter(op => op.opId !== opId),
      };
    }
    case 'SET_USERS': {
      return {
        ...state,
        currentUser: action.payload.currentUser,
        connectedUsers: action.payload.connectedUsers,
      };
    }
    default:
      return state;
  }
}

const mockServer = {
  canonicalTasks: {} as Record<string, Task>,
  canonicalColumnOrder: { todo: [], inProgress: [], done: [] } as Record<ColumnId, string[]>,
  outbox: [] as any[],
  remoteUserOps: [] as any[],
  remoteTimer: null as NodeJS.Timeout | null,
};

function useMockSync(dispatch: React.Dispatch<BoardAction>) {
  useEffect(() => {
    mockServer.canonicalTasks = {};
    mockServer.canonicalColumnOrder = { todo: [], inProgress: [], done: [] };
    mockServer.outbox = [];
    mockServer.remoteUserOps = [];

    const syncInterval = setInterval(() => {
      while (mockServer.outbox.length > 0) {
        const update = mockServer.outbox.shift();
        if (update) {
          dispatch({ type: 'REMOTE_UPDATE', payload: update });
        }
      }
    }, 500);

    mockServer.remoteTimer = setInterval(() => {
      const taskIds = Object.keys(mockServer.canonicalTasks);
      if (taskIds.length > 0) {
        const randomTaskId = taskIds[Math.floor(Math.random() * taskIds.length)];
        const columns: ColumnId[] = ['todo', 'inProgress', 'done'];
        const fromColumn = mockServer.canonicalTasks[randomTaskId].column;
        const toColumn = columns.find(col => col !== fromColumn) || 'inProgress';
        const newOrder = Math.floor(Math.random() * (mockServer.canonicalColumnOrder[toColumn].length + 1));
        const updatedTask = {
          ...mockServer.canonicalTasks[randomTaskId],
          column: toColumn,
          order: newOrder,
          lastMovedBy: 'user_2',
          version: mockServer.canonicalTasks[randomTaskId].version + 1,
        };
        mockServer.canonicalTasks[randomTaskId] = updatedTask;
        const fromOrder = mockServer.canonicalColumnOrder[fromColumn].filter(id => id !== randomTaskId);
        const toInsertAt = Math.min(newOrder, mockServer.canonicalColumnOrder[toColumn].length);
        const newToOrder = [...mockServer.canonicalColumnOrder[toColumn]];
        newToOrder.splice(toInsertAt, 0, randomTaskId);
        mockServer.canonicalColumnOrder[fromColumn] = fromOrder;
        mockServer.canonicalColumnOrder[toColumn] = newToOrder;
        mockServer.outbox.push({
          tasks: [updatedTask],
          columnOrder: mockServer.canonicalColumnOrder,
        });
      }
    }, 3500);

    return () => {
      clearInterval(syncInterval);
      if (mockServer.remoteTimer) clearInterval(mockServer.remoteTimer);
    };
  }, [dispatch]);
}

function TaskCard({ task, onDragStart, onDragOver, onDrop, isDragging }: {
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDragOver: (e: React.DragEvent, taskId: string) => void;
  onDrop: (e: React.DragEvent, taskId: string) => void;
  isDragging: boolean;
}) {
  return (
    <div
      draggable
      className={`${styles.card} ${isDragging ? styles.cardDragging : ''}`}
      onDragStart={(e) => onDragStart(e, task.id)}
      onDragOver={(e) => onDragOver(e, task.id)}
      onDrop={(e) => onDrop(e, task.id)}
      onDragEnd={() => {}}
    >
      <div className={styles.cardContent}>
        <div className={styles.taskText}>{task.text}</div>
        <div className={styles.assignee}>By: {task.lastMovedBy}</div>
      </div>
    </div>
  );
}

function Column({
  id,
  title,
  taskIds,
  tasks,
  onDragOver,
  onDrop,
  currentDragTask,
}: {
  id: ColumnId;
  title: string;
  taskIds: string[];
  tasks: Record<string, Task>;
  onDragOver: (e: React.DragEvent, columnId: ColumnId) => void;
  onDrop: (e: React.DragEvent, columnId: ColumnId) => void;
  currentDragTask: string | null;
}) {
  return (
    <div
      className={styles.column}
      onDragOver={(e) => onDragOver(e, id)}
      onDrop={(e) => onDrop(e, id)}
    >
      <div className={styles.columnHeader}>{title}</div>
      <div className={styles.taskList}>
        {taskIds.map(taskId => {
          const task = tasks[taskId];
          if (!task) return null;
          return (
            <TaskCard
              key={taskId}
              task={task}
              onDragStart={() => {}}
              onDragOver={() => {}}
              onDrop={() => {}}
              isDragging={currentDragTask === taskId}
            />
          );
        })}
      </div>
    </div>
  );
}

function TaskCreator({ onCreate }: { onCreate: (text: string) => void }) {
  const [input, setInput] = useState('');
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onCreate(input.trim());
      setInput('');
    }
  };
  return (
    <form onSubmit={handleSubmit} className={styles.taskCreator}>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Add a new task..."
        className={styles.taskInput}
      />
      <button type="submit" className={styles.addButton}>+ Add</button>
    </form>
  );
}

function ConflictToast({ conflict, onDismiss }: { conflict: Conflict; onDismiss: () => void }) {
  return (
    <div className={styles.conflictToast}>
      <div className={styles.conflictMessage}>
        Conflict! User {conflict.remoteUser} also moved this task.
      </div>
      <button onClick={onDismiss} className={styles.dismissBtn}>OK</button>
    </div>
  );
}

function BoardHeader({ currentUser, connectedUsers }: { currentUser: string; connectedUsers: string[] }) {
  return (
    <div className={styles.boardHeader}>
      <h1 className={styles.boardTitle}>Collaborative Todo Board</h1>
      <div className={styles.userPanel}>
        <div className={styles.currentUser}>You: {currentUser}</div>
        <div className={styles.connectedUsers}>Online: {connectedUsers.join(', ')}</div>
      </div>
    </div>
  );
}

export default function TodoBoardApp() {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const [currentDragTask, setCurrentDragTask] = useState<string | null>(null);

  useMockSync(dispatch);

  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData('text/plain', taskId);
    setCurrentDragTask(taskId);
  };

  const handleDragOver = (e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;
    const task = state.tasks[taskId];
    if (!task) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const taskElements = e.currentTarget.querySelectorAll(`.${styles.card}`);
    let newOrder = taskElements.length;
    for (let i = 0; i < taskElements.length; i++) {
      const elemRect = taskElements[i].getBoundingClientRect();
      const midY = elemRect.top + elemRect.height / 2 - rect.top;
      if (y < midY) {
        newOrder = i;
        break;
      }
    }
    if (task.column === columnId) {
      dispatch({ type: 'REORDER_TASK', payload: { taskId, column: columnId, newOrder } });
    } else {
      dispatch({ type: 'MOVE_TASK', payload: { taskId, from: task.column, to: columnId, order: newOrder } });
    }
    setCurrentDragTask(null);
  };

  const handleCreateTask = (text: string) => {
    const id = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    dispatch({ type: 'ADD_TASK', payload: { id, text } });
  };

  const handleDismissConflict = (taskId: string) => {
    dispatch({ type: 'CONFLICT_DISMISSED', payload: { taskId } });
  };

  return (
    <div className={styles.board}>
      <BoardHeader currentUser={state.currentUser} connectedUsers={state.connectedUsers} />
      <TaskCreator onCreate={handleCreateTask} />
      <div className={styles.columns}>
        <Column
          id="todo"
          title="Todo"
          taskIds={state.columnOrder.todo}
          tasks={state.tasks}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          currentDragTask={currentDragTask}
        />
        <Column
          id="inProgress"
          title="In Progress"
          taskIds={state.columnOrder.inProgress}
          tasks={state.tasks}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          currentDragTask={currentDragTask}
        />
        <Column
          id="done"
          title="Done"
          taskIds={state.columnOrder.done}
          tasks={state.tasks}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          currentDragTask={currentDragTask}
        />
      </div>
      {state.conflicts.map(conflict => (
        <ConflictToast
          key={conflict.taskId}
          conflict={conflict}
          onDismiss={() => handleDismissConflict(conflict.taskId)}
        />
      ))}
    </div>
  );
}