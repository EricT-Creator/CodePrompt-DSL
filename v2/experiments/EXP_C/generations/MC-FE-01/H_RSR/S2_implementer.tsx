import React, { useReducer, useEffect, useState } from 'react';
import styles from './TodoBoard.module.css';

type ColumnId = 'todo' | 'inprogress' | 'done';

interface Task {
  id: string;
  title: string;
  column: ColumnId;
  order: number;
  version: number;
  lastModifiedBy: string;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  userId: string;
  conflict: ConflictInfo | null;
}

interface ConflictInfo {
  taskId: string;
  localMove: { from: ColumnId; to: ColumnId };
  remoteMove: { from: ColumnId; to: ColumnId; by: string };
  timestamp: number;
}

type Action =
  | { type: 'ADD_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; toIndex: number } }
  | { type: 'REMOTE_UPDATE'; payload: { task: Task } }
  | { type: 'SET_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT' };

const initialState: BoardState = {
  tasks: {},
  columnOrder: {
    todo: [],
    inprogress: [],
    done: []
  },
  userId: `user_${Math.random().toString(36).substr(2, 9)}`,
  conflict: null
};

function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
      const newTask: Task = {
        id: taskId,
        title: action.payload.title,
        column: 'todo',
        order: state.columnOrder.todo.length,
        version: 1,
        lastModifiedBy: state.userId
      };
      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: newTask },
        columnOrder: {
          ...state.columnOrder,
          todo: [...state.columnOrder.todo, taskId]
        }
      };
    }

    case 'MOVE_TASK': {
      const { taskId, toColumn, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;

      const fromColumn = task.column;
      
      if (fromColumn === toColumn) {
        const columnTasks = [...state.columnOrder[fromColumn]];
        const currentIndex = columnTasks.indexOf(taskId);
        if (currentIndex === -1) return state;
        
        columnTasks.splice(currentIndex, 1);
        columnTasks.splice(toIndex, 0, taskId);
        
        return {
          ...state,
          tasks: {
            ...state.tasks,
            [taskId]: {
              ...task,
              version: task.version + 1,
              lastModifiedBy: state.userId
            }
          },
          columnOrder: {
            ...state.columnOrder,
            [toColumn]: columnTasks.map((id, idx) => ({ id, idx }))
              .sort((a, b) => a.idx - b.idx)
              .map(item => item.id)
          }
        };
      }

      const fromColumnTasks = [...state.columnOrder[fromColumn]].filter(id => id !== taskId);
      const toColumnTasks = [...state.columnOrder[toColumn]];
      toColumnTasks.splice(toIndex, 0, taskId);
      
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: {
            ...task,
            column: toColumn,
            version: task.version + 1,
            lastModifiedBy: state.userId
          }
        },
        columnOrder: {
          ...state.columnOrder,
          [fromColumn]: fromColumnTasks,
          [toColumn]: toColumnTasks
        }
      };
    }

    case 'REORDER_TASK': {
      const { taskId, toIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;

      const column = task.column;
      const columnTasks = [...state.columnOrder[column]];
      const currentIndex = columnTasks.indexOf(taskId);
      if (currentIndex === -1) return state;

      columnTasks.splice(currentIndex, 1);
      columnTasks.splice(toIndex, 0, taskId);
      
      return {
        ...state,
        columnOrder: {
          ...state.columnOrder,
          [column]: columnTasks
        }
      };
    }

    case 'REMOTE_UPDATE': {
      const remoteTask = action.payload.task;
      const localTask = state.tasks[remoteTask.id];
      
      if (!localTask) {
        return {
          ...state,
          tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
          columnOrder: {
            ...state.columnOrder,
            [remoteTask.column]: [...state.columnOrder[remoteTask.column], remoteTask.id]
          }
        };
      }

      if (remoteTask.version <= localTask.version) {
        return state;
      }

      const fromColumn = localTask.column;
      const toColumn = remoteTask.column;
      
      const fromColumnTasks = [...state.columnOrder[fromColumn]].filter(id => id !== remoteTask.id);
      const toColumnTasks = [...state.columnOrder[toColumn]];
      
      if (!toColumnTasks.includes(remoteTask.id)) {
        toColumnTasks.push(remoteTask.id);
      }
      
      return {
        ...state,
        tasks: { ...state.tasks, [remoteTask.id]: remoteTask },
        columnOrder: {
          ...state.columnOrder,
          [fromColumn]: fromColumnTasks,
          [toColumn]: toColumnTasks
        },
        conflict: {
          taskId: remoteTask.id,
          localMove: { from: fromColumn, to: fromColumn },
          remoteMove: { from: fromColumn, to: toColumn, by: remoteTask.lastModifiedBy },
          timestamp: Date.now()
        }
      };
    }

    case 'SET_CONFLICT': {
      return {
        ...state,
        conflict: action.payload
      };
    }

    case 'DISMISS_CONFLICT': {
      return {
        ...state,
        conflict: null
      };
    }

    default:
      return state;
  }
}

class MockWebSocket {
  private callbacks: ((action: any) => void)[] = [];
  private remoteState: BoardState;

  constructor(initialState: BoardState) {
    this.remoteState = { ...initialState };
  }

  send(action: any) {
    setTimeout(() => {
      this.remoteState = this.simulateRemoteUpdate(this.remoteState, action);
      
      const randomDelay = 50 + Math.random() * 150;
      setTimeout(() => {
        const taskId = action.payload?.taskId;
        if (taskId) {
          const remoteTask = this.remoteState.tasks[taskId];
          if (remoteTask) {
            this.callbacks.forEach(cb => cb({ type: 'REMOTE_UPDATE', payload: { task: remoteTask } }));
          }
        }
      }, randomDelay);
    }, 50);
  }

  onMessage(callback: (action: any) => void) {
    this.callbacks.push(callback);
  }

  disconnect() {
    this.callbacks = [];
  }

  private simulateRemoteUpdate(state: BoardState, action: any): BoardState {
    switch (action.type) {
      case 'MOVE_TASK': {
        const { taskId, toColumn } = action.payload;
        const task = state.tasks[taskId];
        if (!task) return state;

        return {
          ...state,
          tasks: {
            ...state.tasks,
            [taskId]: {
              ...task,
              column: toColumn,
              version: task.version + 1,
              lastModifiedBy: `remote_${Math.random().toString(36).substr(2, 5)}`
            }
          },
          columnOrder: {
            ...state.columnOrder,
            [task.column]: state.columnOrder[task.column].filter(id => id !== taskId),
            [toColumn]: [...state.columnOrder[toColumn], taskId]
          }
        };
      }
      default:
        return state;
    }
  }
}

interface TaskCardProps {
  task: Task;
  dispatch: React.Dispatch<Action>;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, dispatch }) => {
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    e.dataTransfer.setData('taskId', task.id);
    e.dataTransfer.setData('fromColumn', task.column);
    e.currentTarget.classList.add(styles.dragging);
  };

  const handleDragEnd = (e: React.DragEvent<HTMLDivElement>) => {
    e.currentTarget.classList.remove(styles.dragging);
  };

  return (
    <div
      className={styles.card}
      draggable="true"
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className={styles.cardHeader}>
        <span className={styles.cardTitle}>{task.title}</span>
        <span className={styles.assigneeBadge}>{task.lastModifiedBy}</span>
      </div>
      <div className={styles.cardMeta}>
        <span className={styles.version}>v{task.version}</span>
        <span className={styles.columnTag}>{task.column}</span>
      </div>
    </div>
  );
};

interface ColumnProps {
  columnId: ColumnId;
  title: string;
  taskIds: string[];
  tasks: Record<string, Task>;
  dispatch: React.Dispatch<Action>;
}

const Column: React.FC<ColumnProps> = ({ columnId, title, taskIds, tasks, dispatch }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const taskId = e.dataTransfer.getData('taskId');
    const fromColumn = e.dataTransfer.getData('fromColumn') as ColumnId;
    
    if (!taskId) return;
    
    const containerRect = e.currentTarget.getBoundingClientRect();
    const mouseY = e.clientY - containerRect.top;
    const taskHeight = 80;
    const visibleTaskCount = Math.floor(containerRect.height / taskHeight);
    const scrollPosition = e.currentTarget.scrollTop;
    const visibleStartIndex = Math.floor(scrollPosition / taskHeight);
    
    const relativeY = mouseY + scrollPosition;
    const toIndex = Math.min(
      Math.max(0, Math.floor(relativeY / taskHeight)),
      taskIds.length
    );
    
    if (fromColumn === columnId) {
      dispatch({ type: 'REORDER_TASK', payload: { taskId, toIndex } });
    } else {
      dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn: columnId, toIndex } });
    }
  };

  return (
    <div
      className={`${styles.column} ${isDragOver ? styles.dropZone : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={styles.columnHeader}>
        <h3 className={styles.columnTitle}>{title}</h3>
        <span className={styles.taskCount}>({taskIds.length})</span>
      </div>
      <div className={styles.taskList}>
        {taskIds.map((taskId, index) => {
          const task = tasks[taskId];
          if (!task) return null;
          return <TaskCard key={taskId} task={task} dispatch={dispatch} />;
        })}
      </div>
      {columnId === 'todo' && (
        <AddTaskInput dispatch={dispatch} />
      )}
    </div>
  );
};

interface AddTaskInputProps {
  dispatch: React.Dispatch<Action>;
}

const AddTaskInput: React.FC<AddTaskInputProps> = ({ dispatch }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      dispatch({ type: 'ADD_TASK', payload: { title: inputValue.trim() } });
      setInputValue('');
    }
  };

  return (
    <form className={styles.addTaskForm} onSubmit={handleSubmit}>
      <input
        type="text"
        className={styles.addTaskInput}
        placeholder="Add a new task..."
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
      />
      <button type="submit" className={styles.addTaskButton}>
        Add
      </button>
    </form>
  );
};

interface ConflictToastProps {
  conflict: ConflictInfo;
  onDismiss: () => void;
}

const ConflictToast: React.FC<ConflictToastProps> = ({ conflict, onDismiss }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss();
    }, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className={styles.conflictToast}>
      <div className={styles.conflictHeader}>
        <span className={styles.conflictIcon}>⚠️</span>
        <span className={styles.conflictTitle}>Conflict Detected</span>
      </div>
      <div className={styles.conflictBody}>
        <p>Another user moved task <strong>{conflict.taskId}</strong> to <strong>{conflict.remoteMove.to}</strong> while you were moving it.</p>
        <p className={styles.conflictUser}>Moved by: {conflict.remoteMove.by}</p>
      </div>
      <button className={styles.dismissButton} onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  );
};

const TodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const [websocket, setWebsocket] = useState<MockWebSocket | null>(null);

  useEffect(() => {
    const ws = new MockWebSocket(state);
    
    ws.onMessage((action) => {
      dispatch(action);
    });
    
    setWebsocket(ws);
    
    return () => {
      ws.disconnect();
    };
  }, []);

  const handleDismissConflict = () => {
    dispatch({ type: 'DISMISS_CONFLICT' });
  };

  return (
    <div className={styles.board}>
      <div className={styles.boardHeader}>
        <h1 className={styles.boardTitle}>Real-time Collaborative Todo Board</h1>
        <div className={styles.userInfo}>
          <span className={styles.userLabel}>You are:</span>
          <span className={styles.userId}>{state.userId}</span>
        </div>
      </div>
      
      <div className={styles.columnsContainer}>
        <Column
          columnId="todo"
          title="Todo"
          taskIds={state.columnOrder.todo}
          tasks={state.tasks}
          dispatch={dispatch}
        />
        <Column
          columnId="inprogress"
          title="In Progress"
          taskIds={state.columnOrder.inprogress}
          tasks={state.tasks}
          dispatch={dispatch}
        />
        <Column
          columnId="done"
          title="Done"
          taskIds={state.columnOrder.done}
          tasks={state.tasks}
          dispatch={dispatch}
        />
      </div>
      
      {state.conflict && (
        <ConflictToast
          conflict={state.conflict}
          onDismiss={handleDismissConflict}
        />
      )}
    </div>
  );
};

export default TodoBoard;