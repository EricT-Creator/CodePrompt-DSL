import React, { useReducer, useEffect, useRef, useCallback } from 'react';
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

interface ConflictInfo {
  taskId: string;
  localMove: { from: ColumnId; to: ColumnId };
  remoteMove: { from: ColumnId; to: ColumnId; by: string };
  timestamp: number;
}

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;
  userId: string;
  conflict: ConflictInfo | null;
}

type Action =
  | { type: 'ADD_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: ColumnId; toIndex: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; toIndex: number } }
  | { type: 'REMOTE_UPDATE'; payload: { task: Task } }
  | { type: 'SET_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT' }
  | { type: 'HYDRATE'; payload: BoardState };

const initialState: BoardState = {
  tasks: {
    't1': { id: 't1', title: 'Design mockups', column: 'todo', order: 0, version: 1, lastModifiedBy: 'system' },
    't2': { id: 't2', title: 'Setup repo', column: 'todo', order: 1, version: 1, lastModifiedBy: 'system' },
    't3': { id: 't3', title: 'Initial research', column: 'done', order: 0, version: 1, lastModifiedBy: 'system' },
  },
  columnOrder: {
    todo: ['t1', 't2'],
    inprogress: [],
    done: ['t3'],
  },
  userId: 'user-' + Math.random().toString(36).substr(2, 9),
  conflict: null,
};

function reducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const id = 't' + Date.now();
      const newTask: Task = {
        id,
        title: action.payload.title,
        column: 'todo',
        order: state.columnOrder.todo.length,
        version: 1,
        lastModifiedBy: state.userId,
      };
      return {
        ...state,
        tasks: { ...state.tasks, [id]: newTask },
        columnOrder: { ...state.columnOrder, todo: [...state.columnOrder.todo, id] },
      };
    }
    case 'MOVE_TASK': {
      const { taskId, toColumn, toIndex } = action.payload;
      const task = state.tasks[taskId];
      const fromColumn = task.column;
      
      const newColumnOrder = { ...state.columnOrder };
      newColumnOrder[fromColumn] = newColumnOrder[fromColumn].filter(id => id !== taskId);
      
      const targetColumn = [...newColumnOrder[toColumn]];
      targetColumn.splice(toIndex, 0, taskId);
      newColumnOrder[toColumn] = targetColumn;
      
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: {
            ...task,
            column: toColumn,
            order: toIndex,
            version: task.version + 1,
            lastModifiedBy: state.userId,
          },
        },
        columnOrder: newColumnOrder,
      };
    }
    case 'REORDER_TASK': {
      const { taskId, toIndex } = action.payload;
      const task = state.tasks[taskId];
      const column = task.column;
      
      const newColumn = [...state.columnOrder[column]].filter(id => id !== taskId);
      newColumn.splice(toIndex, 0, taskId);
      
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [taskId]: {
            ...task,
            order: toIndex,
            version: task.version + 1,
            lastModifiedBy: state.userId,
          },
        },
        columnOrder: { ...state.columnOrder, [column]: newColumn },
      };
    }
    case 'REMOTE_UPDATE': {
      const { task } = action.payload;
      const localTask = state.tasks[task.id];
      
      if (localTask && localTask.version > task.version) {
        return {
          ...state,
          conflict: {
            taskId: task.id,
            localMove: { from: localTask.column, to: localTask.column },
            remoteMove: { from: task.column, to: task.column, by: task.lastModifiedBy },
            timestamp: Date.now(),
          },
        };
      }
      
      const oldColumn = localTask?.column;
      const newColumn = task.column;
      
      let newColumnOrder = { ...state.columnOrder };
      if (oldColumn && oldColumn !== newColumn) {
        newColumnOrder[oldColumn] = newColumnOrder[oldColumn].filter(id => id !== task.id);
        newColumnOrder[newColumn] = [...newColumnOrder[newColumn], task.id];
      }
      
      return {
        ...state,
        tasks: { ...state.tasks, [task.id]: task },
        columnOrder: newColumnOrder,
      };
    }
    case 'SET_CONFLICT':
      return { ...state, conflict: action.payload };
    case 'DISMISS_CONFLICT':
      return { ...state, conflict: null };
    case 'HYDRATE':
      return action.payload;
    default:
      return state;
  }
}

class MockWebSocket {
  private callbacks: ((action: Action) => void)[] = [];
  private remoteState: BoardState | null = null;

  onMessage(callback: (action: Action) => void) {
    this.callbacks.push(callback);
  }

  send(action: Action) {
    setTimeout(() => {
      if (action.type === 'MOVE_TASK' && Math.random() < 0.1) {
        const conflictAction: Action = {
          type: 'REMOTE_UPDATE',
          payload: {
            task: {
              ...((action as any).payload.taskId ? (this as any).mockTask : {}),
              id: (action as any).payload.taskId,
              column: 'done',
              version: 999,
              lastModifiedBy: 'remote-user',
            } as Task,
          },
        };
        this.callbacks.forEach(cb => cb(conflictAction));
      }
    }, 50 + Math.random() * 150);
  }
}

function TaskCard({
  task,
  onDragStart,
}: {
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
}) {
  return (
    <div
      className={styles.card}
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
    >
      <div className={styles.cardTitle}>{task.title}</div>
      <div className={styles.cardMeta}>
        <span className={styles.badge}>{task.lastModifiedBy}</span>
      </div>
    </div>
  );
}

function Column({
  columnId,
  title,
  tasks,
  onDragOver,
  onDrop,
  children,
}: {
  columnId: ColumnId;
  title: string;
  tasks: Task[];
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, columnId: ColumnId) => void;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={styles.column}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, columnId)}
    >
      <div className={styles.columnHeader}>{title}</div>
      <div className={styles.columnContent}>
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onDragStart={children ? () => {} : () => {}} />
        ))}
        {children}
      </div>
    </div>
  );
}

function ConflictToast({
  conflict,
  onDismiss,
}: {
  conflict: ConflictInfo;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className={styles.conflictToast}>
      <div className={styles.conflictContent}>
        <strong>Conflict detected!</strong>
        <p>
          Task was moved by {conflict.remoteMove.by} while you were editing.
        </p>
        <button onClick={onDismiss}>Dismiss</button>
      </div>
    </div>
  );
}

function AddTaskInput({ onAdd }: { onAdd: (title: string) => void }) {
  const [value, setValue] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onAdd(value.trim());
      setValue('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.addTaskForm}>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Add new task..."
        className={styles.addTaskInput}
      />
      <button type="submit" className={styles.addTaskButton}>Add</button>
    </form>
  );
}

export default function TodoBoard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const wsRef = useRef<MockWebSocket | null>(null);
  const dragDataRef = useRef<{ taskId: string; sourceColumn: ColumnId } | null>(null);

  useEffect(() => {
    wsRef.current = new MockWebSocket();
    wsRef.current.onMessage((action) => {
      dispatch(action);
    });
    return () => {
      wsRef.current = null;
    };
  }, []);

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string) => {
    const task = state.tasks[taskId];
    dragDataRef.current = { taskId, sourceColumn: task.column };
    e.dataTransfer.setData('text/plain', taskId);
    e.dataTransfer.effectAllowed = 'move';
  }, [state.tasks]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetColumn: ColumnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;

    const task = state.tasks[taskId];
    if (!task) return;

    const sourceColumn = task.column;
    const columnEl = e.currentTarget as HTMLElement;
    const contentEl = columnEl.querySelector('.' + styles.columnContent) as HTMLElement;
    
    let toIndex = state.columnOrder[targetColumn].length;
    
    if (contentEl) {
      const cards = contentEl.querySelectorAll('.' + styles.card);
      const rect = contentEl.getBoundingClientRect();
      const relativeY = e.clientY - rect.top;
      
      for (let i = 0; i < cards.length; i++) {
        const cardRect = cards[i].getBoundingClientRect();
        const cardMiddle = cardRect.top + cardRect.height / 2 - rect.top;
        if (relativeY < cardMiddle) {
          toIndex = i;
          break;
        }
        toIndex = i + 1;
      }
    }

    if (sourceColumn === targetColumn) {
      const currentIndex = state.columnOrder[sourceColumn].indexOf(taskId);
      if (currentIndex !== toIndex && currentIndex + 1 !== toIndex) {
        dispatch({ type: 'REORDER_TASK', payload: { taskId, toIndex: toIndex > currentIndex ? toIndex - 1 : toIndex } });
      }
    } else {
      dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn: targetColumn, toIndex } });
    }

    if (wsRef.current) {
      wsRef.current.send({ type: 'MOVE_TASK', payload: { taskId, toColumn: targetColumn, toIndex } });
    }
  }, [state.tasks, state.columnOrder]);

  const handleAddTask = useCallback((title: string) => {
    dispatch({ type: 'ADD_TASK', payload: { title } });
  }, []);

  const handleDismissConflict = useCallback(() => {
    dispatch({ type: 'DISMISS_CONFLICT' });
  }, []);

  const todoTasks = state.columnOrder.todo.map(id => state.tasks[id]);
  const inProgressTasks = state.columnOrder.inprogress.map(id => state.tasks[id]);
  const doneTasks = state.columnOrder.done.map(id => state.tasks[id]);

  return (
    <div className={styles.board}>
      <Column
        columnId="todo"
        title="Todo"
        tasks={todoTasks}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <TaskCard task={{ id: 'drag-ghost', title: '', column: 'todo', order: 0, version: 0, lastModifiedBy: '' }} onDragStart={handleDragStart} />
        <AddTaskInput onAdd={handleAddTask} />
      </Column>
      <Column
        columnId="inprogress"
        title="In Progress"
        tasks={inProgressTasks}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <TaskCard task={{ id: 'drag-ghost-2', title: '', column: 'inprogress', order: 0, version: 0, lastModifiedBy: '' }} onDragStart={handleDragStart} />
      </Column>
      <Column
        columnId="done"
        title="Done"
        tasks={doneTasks}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <TaskCard task={{ id: 'drag-ghost-3', title: '', column: 'done', order: 0, version: 0, lastModifiedBy: '' }} onDragStart={handleDragStart} />
      </Column>
      {state.conflict && (
        <ConflictToast conflict={state.conflict} onDismiss={handleDismissConflict} />
      )}
    </div>
  );
}
