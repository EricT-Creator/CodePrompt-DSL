import React, { useReducer, useEffect, useState, useRef } from 'react';
import styles from './TodoBoard.module.css';

// Types
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
  | { type: 'ADD_TASK'; payload: { text: string; userId: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; fromColumn: ColumnId; toColumn: ColumnId; newOrder: number; userId: string } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; column: ColumnId; newOrder: number; userId: string } }
  | { type: 'REMOTE_UPDATE'; payload: { tasks: Task[]; columnOrder: Record<ColumnId, string[]> } }
  | { type: 'CONFLICT_DETECTED'; payload: ConflictHint }
  | { type: 'CONFLICT_DISMISSED'; payload: { taskId: string } }
  | { type: 'SYNC_ACK'; payload: { opId: string } }
  | { type: 'SET_USERS'; payload: { users: string[] } };

// Mock server
let mockServer = {
  tasks: [] as Task[],
  columnOrder: { todo: [] as string[], inProgress: [] as string[], done: [] as string[] },
  pendingOps: [] as OptimisticOp[],
  remoteUserOps: [] as OptimisticOp[],
  
  applyOp(op: OptimisticOp) {
    this.pendingOps.push(op);
    setTimeout(() => {
      const index = this.pendingOps.findIndex(o => o.opId === op.opId);
      if (index !== -1) {
        this.pendingOps.splice(index, 1);
        // Simulate remote user
        if (Math.random() < 0.3) {
          const remoteOp: OptimisticOp = {
            opId: `remote_${Date.now()}`,
            type: op.type,
            payload: { ...op.payload, userId: 'user2' },
            timestamp: Date.now()
          };
          this.remoteUserOps.push(remoteOp);
        }
      }
    }, 500);
  },
  
  getDiffs() {
    const diffs = {
      tasks: [...this.tasks],
      columnOrder: { ...this.columnOrder },
      remoteOps: [...this.remoteUserOps]
    };
    this.remoteUserOps = [];
    return diffs;
  }
};

// Initial state
const initialState: BoardState = {
  tasks: {
    '1': { id: '1', text: 'Design review', column: 'todo', order: 0, lastMovedBy: 'user1', version: 1 },
    '2': { id: '2', text: 'Implement drag', column: 'todo', order: 1, lastMovedBy: 'user1', version: 1 },
    '3': { id: '3', text: 'Write tests', column: 'inProgress', order: 0, lastMovedBy: 'user1', version: 1 },
    '4': { id: '4', text: 'Deploy to prod', column: 'done', order: 0, lastMovedBy: 'user1', version: 1 }
  },
  columnOrder: {
    todo: ['1', '2'],
    inProgress: ['3'],
    done: ['4']
  },
  currentUser: 'user1',
  connectedUsers: ['user1', 'user2'],
  pendingOptimistic: [],
  conflicts: []
};

// Reducer
function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const { text, userId } = action.payload;
      const newTask: Task = {
        id: `task_${Date.now()}`,
        text,
        column: 'todo',
        order: state.columnOrder.todo.length,
        lastMovedBy: userId,
        version: 1
      };
      
      const newTasks = { ...state.tasks, [newTask.id]: newTask };
      const newColumnOrder = {
        ...state.columnOrder,
        todo: [...state.columnOrder.todo, newTask.id]
      };
      
      const newOp: OptimisticOp = {
        opId: `add_${Date.now()}`,
        type: 'ADD',
        payload: { task: newTask },
        timestamp: Date.now()
      };
      
      return {
        ...state,
        tasks: newTasks,
        columnOrder: newColumnOrder,
        pendingOptimistic: [...state.pendingOptimistic, newOp]
      };
    }
    
    case 'MOVE_TASK': {
      const { taskId, fromColumn, toColumn, newOrder, userId } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;
      
      // Remove from old column
      const oldColumnTasks = state.columnOrder[fromColumn].filter(id => id !== taskId);
      // Add to new column at position
      const newColumnTasks = [...state.columnOrder[toColumn]];
      newColumnTasks.splice(newOrder, 0, taskId);
      
      const updatedTask: Task = {
        ...task,
        column: toColumn,
        order: newOrder,
        lastMovedBy: userId,
        version: task.version + 1
      };
      
      const newTasks = { ...state.tasks, [taskId]: updatedTask };
      const newColumnOrder = {
        ...state.columnOrder,
        [fromColumn]: oldColumnTasks,
        [toColumn]: newColumnTasks
      };
      
      const newOp: OptimisticOp = {
        opId: `move_${Date.now()}`,
        type: 'MOVE',
        payload: { taskId, fromColumn, toColumn, newOrder, userId },
        timestamp: Date.now()
      };
      
      return {
        ...state,
        tasks: newTasks,
        columnOrder: newColumnOrder,
        pendingOptimistic: [...state.pendingOptimistic, newOp]
      };
    }
    
    case 'REORDER_TASK': {
      const { taskId, column, newOrder, userId } = action.payload;
      const task = state.tasks[taskId];
      if (!task || task.column !== column) return state;
      
      const columnTasks = state.columnOrder[column].filter(id => id !== taskId);
      columnTasks.splice(newOrder, 0, taskId);
      
      const updatedTask: Task = {
        ...task,
        order: newOrder,
        lastMovedBy: userId,
        version: task.version + 1
      };
      
      const newTasks = { ...state.tasks, [taskId]: updatedTask };
      const newColumnOrder = { ...state.columnOrder, [column]: columnTasks };
      
      const newOp: OptimisticOp = {
        opId: `reorder_${Date.now()}`,
        type: 'REORDER',
        payload: { taskId, column, newOrder, userId },
        timestamp: Date.now()
      };
      
      return {
        ...state,
        tasks: newTasks,
        columnOrder: newColumnOrder,
        pendingOptimistic: [...state.pendingOptimistic, newOp]
      };
    }
    
    case 'REMOTE_UPDATE': {
      const { tasks, columnOrder } = action.payload;
      const newTasks = { ...state.tasks };
      tasks.forEach(task => {
        newTasks[task.id] = task;
      });
      
      return {
        ...state,
        tasks: newTasks,
        columnOrder: { ...state.columnOrder, ...columnOrder }
      };
    }
    
    case 'CONFLICT_DETECTED': {
      return {
        ...state,
        conflicts: [...state.conflicts, action.payload]
      };
    }
    
    case 'CONFLICT_DISMISSED': {
      return {
        ...state,
        conflicts: state.conflicts.filter(c => c.taskId !== action.payload.taskId)
      };
    }
    
    case 'SYNC_ACK': {
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.filter(op => op.opId !== action.payload.opId)
      };
    }
    
    case 'SET_USERS': {
      return {
        ...state,
        connectedUsers: action.payload.users
      };
    }
    
    default:
      return state;
  }
}

// Custom hook for mock sync
function useMockSync(dispatch: React.Dispatch<Action>) {
  useEffect(() => {
    const interval = setInterval(() => {
      const diffs = mockServer.getDiffs();
      if (diffs.remoteOps.length > 0) {
        diffs.remoteOps.forEach(op => {
          if (op.type === 'MOVE') {
            dispatch({ 
              type: 'REMOTE_UPDATE', 
              payload: { 
                tasks: [{
                  id: op.payload.taskId,
                  text: 'Remote task',
                  column: op.payload.toColumn,
                  order: op.payload.newOrder,
                  lastMovedBy: op.payload.userId,
                  version: 1
                }],
                columnOrder: { [op.payload.toColumn]: [op.payload.taskId] }
              }
            });
          }
        });
      }
    }, 500);
    
    return () => clearInterval(interval);
  }, [dispatch]);
}

// Components
const BoardHeader: React.FC<{ title: string; connectedUsers: string[] }> = ({ title, connectedUsers }) => {
  return (
    <header className={styles.header}>
      <h1 className={styles.title}>{title}</h1>
      <div className={styles.userIndicator}>
        <span>Connected: {connectedUsers.join(', ')}</span>
      </div>
    </header>
  );
};

const TaskCard: React.FC<{
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDragEnd: () => void;
  isDragging: boolean;
}> = ({ task, onDragStart, onDragEnd, isDragging }) => {
  return (
    <div
      className={`${styles.card} ${isDragging ? styles.cardDragging : ''}`}
      draggable="true"
      onDragStart={e => onDragStart(e, task.id)}
      onDragEnd={onDragEnd}
    >
      <div className={styles.cardContent}>
        <span className={styles.taskText}>{task.text}</span>
        <span className={styles.assigneeBadge}>{task.lastMovedBy}</span>
      </div>
    </div>
  );
};

const Column: React.FC<{
  title: string;
  columnId: ColumnId;
  taskIds: string[];
  tasks: Record<string, Task>;
  onDragOver: (e: React.DragEvent, columnId: ColumnId) => void;
  onDrop: (e: React.DragEvent, columnId: ColumnId) => void;
  onTaskDragStart: (e: React.DragEvent, taskId: string) => void;
  onTaskDragEnd: () => void;
  draggingTaskId: string | null;
}> = ({ title, columnId, taskIds, tasks, onDragOver, onDrop, onTaskDragStart, onTaskDragEnd, draggingTaskId }) => {
  return (
    <div
      className={styles.column}
      onDragOver={e => onDragOver(e, columnId)}
      onDrop={e => onDrop(e, columnId)}
    >
      <h3 className={styles.columnTitle}>{title}</h3>
      <div className={styles.taskList}>
        {taskIds.map((taskId, index) => {
          const task = tasks[taskId];
          if (!task) return null;
          return (
            <TaskCard
              key={taskId}
              task={task}
              onDragStart={onTaskDragStart}
              onDragEnd={onTaskDragEnd}
              isDragging={draggingTaskId === taskId}
            />
          );
        })}
      </div>
    </div>
  );
};

const TaskCreator: React.FC<{ onSubmit: (text: string) => void }> = ({ onSubmit }) => {
  const [text, setText] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      onSubmit(text.trim());
      setText('');
    }
  };
  
  return (
    <form className={styles.taskCreator} onSubmit={handleSubmit}>
      <input
        type="text"
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="New task..."
        className={styles.taskInput}
      />
      <button type="submit" className={styles.addButton}>Add</button>
    </form>
  );
};

const ConflictToast: React.FC<{ conflict: ConflictHint; onDismiss: () => void }> = ({ conflict, onDismiss }) => {
  return (
    <div className={styles.conflictToast}>
      <div className={styles.toastContent}>
        <span>Conflict detected! Task modified by {conflict.remoteUser} while you were editing.</span>
        <button className={styles.dismissButton} onClick={onDismiss}>Dismiss</button>
      </div>
    </div>
  );
};

// Main component
const TodoBoardApp: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const [draggingTaskId, setDraggingTaskId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<ColumnId | null>(null);
  
  useMockSync(dispatch);
  
  useEffect(() => {
    // Send pending ops to server
    state.pendingOptimistic.forEach(op => {
      mockServer.applyOp(op);
      setTimeout(() => {
        dispatch({ type: 'SYNC_ACK', payload: { opId: op.opId } });
      }, 1000);
    });
  }, [state.pendingOptimistic]);
  
  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData('text/plain', taskId);
    setDraggingTaskId(taskId);
  };
  
  const handleDragEnd = () => {
    setDraggingTaskId(null);
  };
  
  const handleDragOver = (e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    setDragOverColumn(columnId);
  };
  
  const handleDrop = (e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;
    
    const task = state.tasks[taskId];
    if (!task) return;
    
    const taskElements = document.querySelectorAll(`.${styles.card}`);
    let newOrder = 0;
    
    for (let i = 0; i < taskElements.length; i++) {
      const rect = taskElements[i].getBoundingClientRect();
      if (e.clientY < rect.top + rect.height / 2) {
        newOrder = i;
        break;
      }
      newOrder = i + 1;
    }
    
    if (task.column === columnId) {
      dispatch({
        type: 'REORDER_TASK',
        payload: { taskId, column: columnId, newOrder, userId: state.currentUser }
      });
    } else {
      dispatch({
        type: 'MOVE_TASK',
        payload: { taskId, fromColumn: task.column, toColumn: columnId, newOrder, userId: state.currentUser }
      });
    }
    
    setDragOverColumn(null);
  };
  
  const handleAddTask = (text: string) => {
    dispatch({
      type: 'ADD_TASK',
      payload: { text, userId: state.currentUser }
    });
  };
  
  const handleDismissConflict = (taskId: string) => {
    dispatch({
      type: 'CONFLICT_DISMISSED',
      payload: { taskId }
    });
  };
  
  return (
    <div className={styles.board}>
      <BoardHeader title="Real-Time Todo Board" connectedUsers={state.connectedUsers} />
      
      <div className={styles.columnsContainer}>
        <Column
          title="Todo"
          columnId="todo"
          taskIds={state.columnOrder.todo}
          tasks={state.tasks}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onTaskDragStart={handleDragStart}
          onTaskDragEnd={handleDragEnd}
          draggingTaskId={draggingTaskId}
        />
        
        <Column
          title="In Progress"
          columnId="inProgress"
          taskIds={state.columnOrder.inProgress}
          tasks={state.tasks}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onTaskDragStart={handleDragStart}
          onTaskDragEnd={handleDragEnd}
          draggingTaskId={draggingTaskId}
        />
        
        <Column
          title="Done"
          columnId="done"
          taskIds={state.columnOrder.done}
          tasks={state.tasks}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onTaskDragStart={handleDragStart}
          onTaskDragEnd={handleDragEnd}
          draggingTaskId={draggingTaskId}
        />
      </div>
      
      <div className={styles.taskCreatorContainer}>
        <TaskCreator onSubmit={handleAddTask} />
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
};

export default TodoBoardApp;