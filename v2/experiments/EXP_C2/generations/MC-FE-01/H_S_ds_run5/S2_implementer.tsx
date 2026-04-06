import React, { useReducer, useState, useEffect, useRef, useCallback } from 'react';
import styles from './board.module.css';

type ColumnId = 'todo' | 'inProgress' | 'done';

interface Task {
  id: string;
  text: string;
  column: ColumnId;
  order: number;
  lastMovedBy: string;
  version: number;
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

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: { todo: string[]; inProgress: string[]; done: string[] };
  currentUser: string;
  connectedUsers: string[];
  optimisticQueue: PendingOp[];
  conflictHints: ConflictInfo[];
}

type Action =
  | { type: 'ADD_TASK'; payload: { text: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; fromColumn: ColumnId; toColumn: ColumnId; insertIndex: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; column: ColumnId; newIndex: number } }
  | { type: 'APPLY_REMOTE'; payload: { tasks: Task[]; columnOrder: Record<ColumnId, string[]> } }
  | { type: 'MARK_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; payload: { taskId: string } }
  | { type: 'CONFIRM_OP'; payload: { opId: string } }
  | { type: 'ROLLBACK_OP'; payload: { opId: string } };

const initialTasks: Task[] = [
  { id: 't1', text: 'Review design specs', column: 'todo', order: 0, lastMovedBy: 'alice', version: 1 },
  { id: 't2', text: 'Implement drag-drop logic', column: 'todo', order: 1, lastMovedBy: 'alice', version: 1 },
  { id: 't3', text: 'Write unit tests', column: 'inProgress', order: 0, lastMovedBy: 'bob', version: 1 },
  { id: 't4', text: 'Deploy to staging', column: 'done', order: 0, lastMovedBy: 'charlie', version: 1 },
];

const initialState: BoardState = {
  tasks: Object.fromEntries(initialTasks.map(t => [t.id, t])),
  columnOrder: {
    todo: ['t1', 't2'],
    inProgress: ['t3'],
    done: ['t4'],
  },
  currentUser: 'user' + Math.floor(Math.random() * 1000),
  connectedUsers: ['alice', 'bob', 'charlie'],
  optimisticQueue: [],
  conflictHints: [],
};

function boardReducer(state: BoardState, action: Action): BoardState {
  switch (action.type) {
    case 'ADD_TASK': {
      const newId = 'task_' + Date.now();
      const newTask: Task = {
        id: newId,
        text: action.payload.text,
        column: 'todo',
        order: state.columnOrder.todo.length,
        lastMovedBy: state.currentUser,
        version: 1,
      };
      const opId = 'add_' + Date.now();
      return {
        ...state,
        tasks: { ...state.tasks, [newId]: newTask },
        columnOrder: {
          ...state.columnOrder,
          todo: [...state.columnOrder.todo, newId],
        },
        optimisticQueue: [...state.optimisticQueue, { opId, type: 'ADD', taskId: newId, timestamp: Date.now() }],
      };
    }

    case 'MOVE_TASK': {
      const { taskId, fromColumn, toColumn, insertIndex } = action.payload;
      const task = state.tasks[taskId];
      if (!task) return state;

      const fromOrder = state.columnOrder[fromColumn].filter(id => id !== taskId);
      const toOrder = [...state.columnOrder[toColumn]];
      toOrder.splice(insertIndex, 0, taskId);

      const updatedTask = {
        ...task,
        column: toColumn,
        order: insertIndex,
        lastMovedBy: state.currentUser,
        version: task.version + 1,
      };

      const opId = 'move_' + Date.now();
      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columnOrder: {
          ...state.columnOrder,
          [fromColumn]: fromOrder,
          [toColumn]: toOrder,
        },
        optimisticQueue: [...state.optimisticQueue, { opId, type: 'MOVE', taskId, timestamp: Date.now() }],
      };
    }

    case 'REORDER_TASK': {
      const { taskId, column, newIndex } = action.payload;
      const columnTasks = [...state.columnOrder[column]];
      const oldIndex = columnTasks.indexOf(taskId);
      if (oldIndex === -1) return state;

      columnTasks.splice(oldIndex, 1);
      columnTasks.splice(newIndex, 0, taskId);

      const task = state.tasks[taskId];
      const updatedTask = { ...task, order: newIndex, lastMovedBy: state.currentUser, version: task.version + 1 };

      const opId = 'reorder_' + Date.now();
      return {
        ...state,
        tasks: { ...state.tasks, [taskId]: updatedTask },
        columnOrder: { ...state.columnOrder, [column]: columnTasks },
        optimisticQueue: [...state.optimisticQueue, { opId, type: 'REORDER', taskId, timestamp: Date.now() }],
      };
    }

    case 'APPLY_REMOTE': {
      const newTasks = { ...state.tasks };
      action.payload.tasks.forEach(t => {
        newTasks[t.id] = t;
      });
      return {
        ...state,
        tasks: newTasks,
        columnOrder: action.payload.columnOrder,
      };
    }

    case 'MARK_CONFLICT':
      return {
        ...state,
        conflictHints: [...state.conflictHints, action.payload],
      };

    case 'DISMISS_CONFLICT':
      return {
        ...state,
        conflictHints: state.conflictHints.filter(c => c.taskId !== action.payload.taskId),
      };

    case 'CONFIRM_OP':
      return {
        ...state,
        optimisticQueue: state.optimisticQueue.filter(op => op.opId !== action.payload.opId),
      };

    case 'ROLLBACK_OP': {
      const rejectedOp = state.optimisticQueue.find(op => op.opId === action.payload.opId);
      if (!rejectedOp) return state;

      let newState = initialState;
      state.optimisticQueue
        .filter(op => op.opId !== rejectedOp.opId)
        .forEach(op => {
        });
      return newState;
    }

    default:
      return state;
  }
}

const mockServer = {
  tasks: { ...initialState.tasks },
  columnOrder: { ...initialState.columnOrder },
  pendingOps: [] as any[],
  connectedUsers: ['alice', 'bob', 'charlie'],

  applyLocalOp(op: PendingOp) {
    this.pendingOps.push({ ...op, timestamp: Date.now() });
    setTimeout(() => {
      const idx = this.pendingOps.findIndex(p => p.opId === op.opId);
      if (idx > -1) {
        this.pendingOps.splice(idx, 1);
      }
    }, 800 + Math.random() * 1200);
  },

  generateRemoteUpdate() {
    if (Math.random() < 0.25) {
      const taskIds = Object.keys(this.tasks);
      if (taskIds.length > 0) {
        const taskId = taskIds[Math.floor(Math.random() * taskIds.length)];
        const columns: ColumnId[] = ['todo', 'inProgress', 'done'];
        const newColumn = columns[Math.floor(Math.random() * 3)];
        const task = this.tasks[taskId];
        if (task.column !== newColumn) {
          const oldColTasks = this.columnOrder[task.column].filter(id => id !== taskId);
          const newColTasks = [...this.columnOrder[newColumn], taskId];
          this.columnOrder = {
            ...this.columnOrder,
            [task.column]: oldColTasks,
            [newColumn]: newColTasks,
          };
          this.tasks[taskId] = {
            ...task,
            column: newColumn,
            order: newColTasks.length - 1,
            lastMovedBy: this.connectedUsers[Math.floor(Math.random() * this.connectedUsers.length)],
            version: task.version + 1,
          };
        }
      }
    }
    return { tasks: Object.values(this.tasks), columnOrder: this.columnOrder };
  },
};

function useMockSync(dispatch: React.Dispatch<Action>) {
  useEffect(() => {
    const interval = setInterval(() => {
      const update = mockServer.generateRemoteUpdate();
      dispatch({ type: 'APPLY_REMOTE', payload: update });
    }, 500);
    return () => clearInterval(interval);
  }, [dispatch]);
}

const BoardHeader: React.FC<{ currentUser: string; connectedUsers: string[] }> = ({ currentUser, connectedUsers }) => {
  return (
    <header className={styles.header}>
      <h1 className={styles.title}>Collaborative Todo Board</h1>
      <div className={styles.userInfo}>
        <span className={styles.currentUser}>You: {currentUser}</span>
        <span className={styles.connectedUsers}>
          Online: {connectedUsers.join(', ')}
        </span>
      </div>
    </header>
  );
};

const TaskCard: React.FC<{
  task: Task;
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onDragOver: (e: React.DragEvent, taskId: string) => void;
  onDrop: (e: React.DragEvent, taskId: string) => void;
  isDragging: boolean;
}> = ({ task, onDragStart, onDragOver, onDrop, isDragging }) => {
  const handleDragStart = (e: React.DragEvent) => {
    onDragStart(e, task.id);
    e.dataTransfer.setData('text/plain', task.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      draggable="true"
      className={`${styles.card} ${isDragging ? styles.cardDragging : ''}`}
      onDragStart={handleDragStart}
      onDragOver={e => onDragOver(e, task.id)}
      onDrop={e => onDrop(e, task.id)}
    >
      <div className={styles.cardContent}>
        <div className={styles.cardText}>{task.text}</div>
        <div className={styles.cardMeta}>
          <span className={styles.assignee}>@{task.lastMovedBy}</span>
          <span className={styles.version}>v{task.version}</span>
        </div>
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
  onDragStart: (e: React.DragEvent, taskId: string) => void;
  onCardDragOver: (e: React.DragEvent, taskId: string) => void;
  onCardDrop: (e: React.DragEvent, taskId: string) => void;
  draggingTaskId: string | null;
}> = ({
  title,
  columnId,
  taskIds,
  tasks,
  onDragOver,
  onDrop,
  onDragStart,
  onCardDragOver,
  onCardDrop,
  draggingTaskId,
}) => {
  return (
    <div
      className={styles.column}
      onDragOver={e => onDragOver(e, columnId)}
      onDrop={e => onDrop(e, columnId)}
    >
      <h3 className={styles.columnTitle}>{title}</h3>
      <div className={styles.columnContent}>
        {taskIds.map(id => {
          const task = tasks[id];
          if (!task) return null;
          return (
            <TaskCard
              key={id}
              task={task}
              onDragStart={onDragStart}
              onDragOver={onCardDragOver}
              onDrop={onCardDrop}
              isDragging={draggingTaskId === id}
            />
          );
        })}
      </div>
    </div>
  );
};

const TaskCreator: React.FC<{ onCreate: (text: string) => void }> = ({ onCreate }) => {
  const [input, setInput] = useState('');
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onCreate(input.trim());
      setInput('');
    }
  };

  return (
    <form className={styles.taskCreator} onSubmit={handleSubmit}>
      <input
        type="text"
        className={styles.taskInput}
        placeholder="Type a new task..."
        value={input}
        onChange={e => setInput(e.target.value)}
      />
      <button type="submit" className={styles.taskButton}>
        Add Task
      </button>
    </form>
  );
};

const ConflictBanner: React.FC<{
  conflict: ConflictInfo;
  tasks: Record<string, Task>;
  onDismiss: (taskId: string) => void;
}> = ({ conflict, tasks, onDismiss }) => {
  const task = tasks[conflict.taskId];
  if (!task) return null;

  return (
    <div className={styles.conflictBanner}>
      <div className={styles.conflictMessage}>
        <strong>Conflict:</strong> {conflict.yourAction} (you) vs {conflict.theirUser} on "{task.text}"
      </div>
      <button className={styles.dismissButton} onClick={() => onDismiss(conflict.taskId)}>
        Dismiss
      </button>
    </div>
  );
};

const TodoBoardApp: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const [draggingTaskId, setDraggingTaskId] = useState<string | null>(null);
  const dragOverColumn = useRef<ColumnId | null>(null);
  const dragOverTask = useRef<string | null>(null);

  useMockSync(dispatch);

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string) => {
    setDraggingTaskId(taskId);
    e.dataTransfer.setData('text/plain', taskId);
    e.currentTarget.classList.add(styles.cardDragging);
  }, []);

  const handleColumnDragOver = useCallback((e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    dragOverColumn.current = columnId;
  }, []);

  const handleCardDragOver = useCallback((e: React.DragEvent, taskId: string) => {
    e.preventDefault();
    dragOverTask.current = taskId;
  }, []);

  const handleColumnDrop = useCallback((e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    if (!taskId) return;

    const task = state.tasks[taskId];
    if (!task) return;

    if (task.column !== columnId) {
      dispatch({
        type: 'MOVE_TASK',
        payload: {
          taskId,
          fromColumn: task.column,
          toColumn: columnId,
          insertIndex: state.columnOrder[columnId].length,
        },
      });
    }
    setDraggingTaskId(null);
    dragOverColumn.current = null;
  }, [state.tasks, state.columnOrder]);

  const handleCardDrop = useCallback((e: React.DragEvent, targetTaskId: string) => {
    e.preventDefault();
    const draggedTaskId = e.dataTransfer.getData('text/plain');
    if (!draggedTaskId || draggedTaskId === targetTaskId) return;

    const draggedTask = state.tasks[draggedTaskId];
    if (!draggedTask) return;

    const targetIndex = state.columnOrder[draggedTask.column].indexOf(targetTaskId);
    if (targetIndex === -1) return;

    dispatch({
      type: 'REORDER_TASK',
      payload: {
        taskId: draggedTaskId,
        column: draggedTask.column,
        newIndex: targetIndex,
      },
    });
    setDraggingTaskId(null);
    dragOverTask.current = null;
  }, [state.tasks, state.columnOrder]);

  const handleCreateTask = useCallback((text: string) => {
    dispatch({ type: 'ADD_TASK', payload: { text } });
  }, []);

  const handleDismissConflict = useCallback((taskId: string) => {
    dispatch({ type: 'DISMISS_CONFLICT', payload: { taskId } });
  }, []);

  return (
    <div className={styles.board}>
      <BoardHeader currentUser={state.currentUser} connectedUsers={state.connectedUsers} />
      <div className={styles.columns}>
        <Column
          title="Todo"
          columnId="todo"
          taskIds={state.columnOrder.todo}
          tasks={state.tasks}
          onDragOver={handleColumnDragOver}
          onDrop={handleColumnDrop}
          onDragStart={handleDragStart}
          onCardDragOver={handleCardDragOver}
          onCardDrop={handleCardDrop}
          draggingTaskId={draggingTaskId}
        />
        <Column
          title="In Progress"
          columnId="inProgress"
          taskIds={state.columnOrder.inProgress}
          tasks={state.tasks}
          onDragOver={handleColumnDragOver}
          onDrop={handleColumnDrop}
          onDragStart={handleDragStart}
          onCardDragOver={handleCardDragOver}
          onCardDrop={handleCardDrop}
          draggingTaskId={draggingTaskId}
        />
        <Column
          title="Done"
          columnId="done"
          taskIds={state.columnOrder.done}
          tasks={state.tasks}
          onDragOver={handleColumnDragOver}
          onDrop={handleColumnDrop}
          onDragStart={handleDragStart}
          onCardDragOver={handleCardDragOver}
          onCardDrop={handleCardDrop}
          draggingTaskId={draggingTaskId}
        />
      </div>
      <TaskCreator onCreate={handleCreateTask} />
      {state.conflictHints.map(conflict => (
        <ConflictBanner
          key={conflict.taskId}
          conflict={conflict}
          tasks={state.tasks}
          onDismiss={handleDismissConflict}
        />
      ))}
    </div>
  );
};

export default TodoBoardApp;