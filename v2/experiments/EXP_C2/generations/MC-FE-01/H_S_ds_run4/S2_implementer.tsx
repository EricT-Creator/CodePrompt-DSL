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
  columnOrder: { todo: string[]; inProgress: string[]; done: string[] };
  currentUser: string;
  connectedUsers: string[];
  optimisticQueue: PendingOp[];
  conflictHints: ConflictInfo[];
}

interface PendingOp {
  opId: string;
  type: 'MOVE' | 'REORDER' | 'ADD';
  taskId: string;
  timestamp: number;
}

interface ConflictInfo {
  taskId: string;
  yourAction: string;
  theirUser: string;
}

type BoardAction =
  | { type: 'ADD_TASK'; payload: { id: string; text: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; from: ColumnId; to: ColumnId; order: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; column: ColumnId; newOrder: number } }
  | { type: 'APPLY_REMOTE'; payload: { tasks: Task[]; columnOrder: Record<ColumnId, string[]> } }
  | { type: 'MARK_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; payload: { taskId: string } }
  | { type: 'CONFIRM_OP'; payload: { opId: string } }
  | { type: 'ROLLBACK_OP'; payload: { opId: string } };

const initialState: BoardState = {
  tasks: {},
  columnOrder: { todo: [], inProgress: [], done: [] },
  currentUser: 'user_alpha',
  connectedUsers: ['user_alpha', 'user_beta'],
  optimisticQueue: [],
  conflictHints: [],
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
      const newTodoOrder = [id, ...state.columnOrder.todo];
      return {
        ...state,
        tasks: newTasks,
        columnOrder: { ...state.columnOrder, todo: newTodoOrder },
        optimisticQueue: [...state.optimisticQueue, {
          opId: `add_${id}_${Date.now()}`,
          type: 'ADD',
          taskId: id,
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
        optimisticQueue: [...state.optimisticQueue, {
          opId: `move_${taskId}_${Date.now()}`,
          type: 'MOVE',
          taskId,
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
        optimisticQueue: [...state.optimisticQueue, {
          opId: `reorder_${taskId}_${Date.now()}`,
          type: 'REORDER',
          taskId,
          timestamp: Date.now(),
        }],
      };
    }
    case 'APPLY_REMOTE': {
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
    case 'MARK_CONFLICT': {
      return {
        ...state,
        conflictHints: [...state.conflictHints, action.payload],
      };
    }
    case 'DISMISS_CONFLICT': {
      return {
        ...state,
        conflictHints: state.conflictHints.filter(c => c.taskId !== action.payload.taskId),
      };
    }
    case 'CONFIRM_OP': {
      const { opId } = action.payload;
      return {
        ...state,
        optimisticQueue: state.optimisticQueue.filter(op => op.opId !== opId),
      };
    }
    case 'ROLLBACK_OP': {
      const { opId } = action.payload;
      return {
        ...state,
        optimisticQueue: state.optimisticQueue.filter(op => op.opId !== opId),
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
  remoteOpsQueue: [] as any[],
};

function useMockSync(dispatch: React.Dispatch<BoardAction>) {
  useEffect(() => {
    mockServer.canonicalTasks = {};
    mockServer.canonicalColumnOrder = { todo: [], inProgress: [], done: [] };
    mockServer.outbox = [];
    mockServer.remoteOpsQueue = [];

    const syncInterval = setInterval(() => {
      if (mockServer.outbox.length > 0) {
        const update = mockServer.outbox.shift();
        if (update) {
          dispatch({ type: 'APPLY_REMOTE', payload: update });
        }
      }
    }, 550);

    const remoteSim = setInterval(() => {
      const taskIds = Object.keys(mockServer.canonicalTasks);
      if (taskIds.length > 0) {
        const randomTaskId = taskIds[Math.floor(Math.random() * taskIds.length)];
        const columns: ColumnId[] = ['todo', 'inProgress', 'done'];
        const fromColumn = mockServer.canonicalTasks[randomTaskId].column;
        const remaining = columns.filter(col => col !== fromColumn);
        const toColumn = remaining[Math.floor(Math.random() * remaining.length)];
        const newOrder = Math.floor(Math.random() * (mockServer.canonicalColumnOrder[toColumn].length + 1));
        const updatedTask = {
          ...mockServer.canonicalTasks[randomTaskId],
          column: toColumn,
          order: newOrder,
          lastMovedBy: 'user_beta',
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
    }, 3600);

    return () => {
      clearInterval(syncInterval);
      clearInterval(remoteSim);
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
      draggable="true"
      className={`${styles.taskCard} ${isDragging ? styles.cardDragging : ''}`}
      onDragStart={(e) => onDragStart(e, task.id)}
      onDragOver={(e) => onDragOver(e, task.id)}
      onDrop={(e) => onDrop(e, task.id)}
      onDragEnd={() => {}}
    >
      <div className={styles.cardBody}>
        <div className={styles.taskText}>{task.text}</div>
        <div className={styles.assignee}>Moved by: {task.lastMovedBy}</div>
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
    <div className={styles.creatorSection}>
      <form onSubmit={handleSubmit} className={styles.creatorForm}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter new task..."
          className={styles.taskInput}
        />
        <button type="submit" className={styles.addButton}>Create</button>
      </form>
    </div>
  );
}

function ConflictBanner({ conflict, onDismiss }: { conflict: ConflictInfo; onDismiss: () => void }) {
  return (
    <div className={styles.conflictAlert}>
      <span className={styles.alertMessage}>⚠️ Conflict detected with {conflict.theirUser}</span>
      <button onClick={onDismiss} className={styles.dismissBtn}>OK</button>
    </div>
  );
}

function BoardHeader({ currentUser, connectedUsers }: { currentUser: string; connectedUsers: string[] }) {
  return (
    <div className={styles.boardHeaderSection}>
      <div className={styles.headerLeft}>
        <h1 className={styles.mainTitle}>Team Todo Board</h1>
        <p className={styles.subtitle}>Real-time collaboration</p>
      </div>
      <div className={styles.headerRight}>
        <div className={styles.userInfoPanel}>
          <span className={styles.currentUserLabel}>You: {currentUser}</span>
          <span className={styles.connectedUsersLabel}>Online: {connectedUsers.join(', ')}</span>
        </div>
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
    e.dataTransfer.effectAllowed = 'move';
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
    const taskElements = e.currentTarget.querySelectorAll(`.${styles.taskCard}`);
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
    const id = `task_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
    dispatch({ type: 'ADD_TASK', payload: { id, text } });
  };

  const handleDismissConflict = (taskId: string) => {
    dispatch({ type: 'DISMISS_CONFLICT', payload: { taskId } });
  };

  return (
    <div className={styles.boardContainer}>
      <BoardHeader currentUser={state.currentUser} connectedUsers={state.connectedUsers} />
      <TaskCreator onCreate={handleCreateTask} />
      <div className={styles.columnsWrapper}>
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
      {state.conflictHints.map(conflict => (
        <ConflictBanner
          key={conflict.taskId}
          conflict={conflict}
          onDismiss={() => handleDismissConflict(conflict.taskId)}
        />
      ))}
    </div>
  );
}