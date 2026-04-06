import React, { useReducer, useEffect, useRef } from 'react';

// ===================== Interfaces =====================

interface Point {
  x: number;
  y: number;
}

interface Task {
  id: string;
  title: string;
  column: 'todo' | 'inProgress' | 'done';
  order: number;
  version: number;
  lastMovedBy: string;
}

interface User {
  id: string;
  name: string;
  color: string;
}

interface DragState {
  taskId: string;
  sourceColumn: string;
  overColumn: string | null;
  overIndex: number | null;
}

interface ConflictInfo {
  taskId: string;
  localMove: MoveOp;
  remoteMove: MoveOp;
  timestamp: number;
}

interface MoveOp {
  taskId: string;
  fromColumn: string;
  toColumn: string;
  newOrder: number;
  version: number;
}

interface OptimisticOp {
  opId: string;
  type: 'move' | 'create';
  payload: any;
  timestamp: number;
  confirmed: boolean;
}

interface BoardState {
  tasks: Task[];
  users: User[];
  localUserId: string;
  dragState: DragState | null;
  conflicts: ConflictInfo[];
  pendingOptimistic: OptimisticOp[];
}

// ===================== Action Types =====================

type BoardAction =
  | { type: 'CREATE_TASK'; payload: { title: string } }
  | { type: 'MOVE_TASK'; payload: { taskId: string; toColumn: string; newOrder: number } }
  | { type: 'REORDER_TASK'; payload: { taskId: string; newOrder: number } }
  | { type: 'SET_DRAG_STATE'; payload: DragState }
  | { type: 'CLEAR_DRAG_STATE' }
  | { type: 'REMOTE_UPDATE'; payload: { taskId: string; column: string; order: number; version: number; movedBy: string } }
  | { type: 'CONFIRM_OP'; payload: { opId: string } }
  | { type: 'RAISE_CONFLICT'; payload: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; payload: { taskId: string } }
  | { type: 'SYNC_USERS'; payload: User[] };

// ===================== Reducer =====================

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'CREATE_TASK': {
      const newTask: Task = {
        id: `task-${Date.now()}`,
        title: action.payload.title,
        column: 'todo',
        order: state.tasks.filter(t => t.column === 'todo').length,
        version: 0,
        lastMovedBy: state.localUserId,
      };
      const optimisticOp: OptimisticOp = {
        opId: `op-${Date.now()}`,
        type: 'create',
        payload: { task: newTask },
        timestamp: Date.now(),
        confirmed: false,
      };
      return {
        ...state,
        tasks: [...state.tasks, newTask],
        pendingOptimistic: [...state.pendingOptimistic, optimisticOp],
      };
    }

    case 'MOVE_TASK': {
      const { taskId, toColumn, newOrder } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task) return state;

      const updatedTasks = state.tasks
        .filter(t => t.id !== taskId)
        .map(t => ({
          ...t,
          order: t.column === toColumn && t.order >= newOrder ? t.order + 1 : t.order,
        }));

      const movedTask: Task = {
        ...task,
        column: toColumn as Task['column'],
        order: newOrder,
        version: task.version + 1,
        lastMovedBy: state.localUserId,
      };

      const optimisticOp: OptimisticOp = {
        opId: `op-${Date.now()}`,
        type: 'move',
        payload: { taskId, fromColumn: task.column, toColumn, newOrder, version: task.version },
        timestamp: Date.now(),
        confirmed: false,
      };

      return {
        ...state,
        tasks: [...updatedTasks, movedTask],
        pendingOptimistic: [...state.pendingOptimistic, optimisticOp],
      };
    }

    case 'REORDER_TASK': {
      const { taskId, newOrder } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task || task.column !== 'todo') return state;

      const tasksInColumn = state.tasks.filter(t => t.column === task.column && t.id !== taskId);
      const reorderedTasks = tasksInColumn.map(t => ({
        ...t,
        order: t.order >= newOrder ? t.order + 1 : t.order,
      }));

      const updatedTask: Task = {
        ...task,
        order: newOrder,
        version: task.version + 1,
        lastMovedBy: state.localUserId,
      };

      const optimisticOp: OptimisticOp = {
        opId: `op-${Date.now()}`,
        type: 'move',
        payload: { taskId, fromColumn: task.column, toColumn: task.column, newOrder, version: task.version },
        timestamp: Date.now(),
        confirmed: false,
      };

      return {
        ...state,
        tasks: [...reorderedTasks, updatedTask],
        pendingOptimistic: [...state.pendingOptimistic, optimisticOp],
      };
    }

    case 'SET_DRAG_STATE':
      return { ...state, dragState: action.payload };

    case 'CLEAR_DRAG_STATE':
      return { ...state, dragState: null };

    case 'REMOTE_UPDATE': {
      const { taskId, column, order, version, movedBy } = action.payload;
      const conflictingOp = state.pendingOptimistic.find(
        op => op.type === 'move' && op.payload.taskId === taskId && !op.confirmed
      );

      if (conflictingOp) {
        const conflictInfo: ConflictInfo = {
          taskId,
          localMove: conflictingOp.payload,
          remoteMove: { taskId, fromColumn: column, toColumn: column, newOrder: order, version },
          timestamp: Date.now(),
        };
        return {
          ...state,
          tasks: state.tasks.map(t =>
            t.id === taskId
              ? { ...t, column: column as Task['column'], order, version, lastMovedBy: movedBy }
              : t
          ),
          conflicts: [...state.conflicts, conflictInfo],
        };
      }

      return {
        ...state,
        tasks: state.tasks.map(t =>
          t.id === taskId
            ? { ...t, column: column as Task['column'], order, version, lastMovedBy: movedBy }
            : t
        ),
      };
    }

    case 'CONFIRM_OP':
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.map(op =>
          op.opId === action.payload.opId ? { ...op, confirmed: true } : op
        ),
      };

    case 'RAISE_CONFLICT':
      return { ...state, conflicts: [...state.conflicts, action.payload] };

    case 'DISMISS_CONFLICT':
      return {
        ...state,
        conflicts: state.conflicts.filter(c => c.taskId !== action.payload.taskId),
      };

    case 'SYNC_USERS':
      return { ...state, users: action.payload };

    default:
      return state;
  }
}

// ===================== Components =====================

const BoardHeader: React.FC<{
  title: string;
  users: User[];
  onCreateTask: (title: string) => void;
}> = ({ title, users, onCreateTask }) => {
  const [inputValue, setInputValue] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onCreateTask(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <header className="board-header">
      <h1>{title}</h1>
      <div className="user-indicator">
        <span className="user-count">{users.length} users online</span>
        <div className="user-dots">
          {users.map(u => (
            <span
              key={u.id}
              className="user-dot"
              style={{ backgroundColor: u.color }}
              title={u.name}
            />
          ))}
        </div>
      </div>
      <form onSubmit={handleSubmit} className="new-task-form">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Add a new task..."
          className="new-task-input"
        />
        <button type="submit" className="new-task-button">Add</button>
      </form>
    </header>
  );
};

const TaskCard: React.FC<{
  task: Task;
  onDragStart: (taskId: string, sourceColumn: string) => void;
  hasConflict: boolean;
}> = ({ task, onDragStart, hasConflict }) => {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('taskId', task.id);
    e.dataTransfer.setData('sourceColumn', task.column);
    onDragStart(task.id, task.column);
  };

  return (
    <div
      draggable="true"
      onDragStart={handleDragStart}
      className={`task-card ${hasConflict ? 'task-conflict' : ''}`}
      style={{ opacity: hasConflict ? 0.7 : 1 }}
    >
      <div className="task-content">
        <h3 className="task-title">{task.title}</h3>
        <div className="task-meta">
          <span className="task-column">{task.column}</span>
          <span className="task-version">v{task.version}</span>
        </div>
      </div>
      {hasConflict && <div className="conflict-indicator">⚠️ Conflict</div>}
    </div>
  );
};

const Column: React.FC<{
  title: string;
  tasks: Task[];
  dragState: DragState | null;
  onDragOver: (column: string, overIndex: number | null) => void;
  onDrop: (taskId: string, toColumn: string, newOrder: number) => void;
  onDragStart: (taskId: string, sourceColumn: string) => void;
  conflicts: ConflictInfo[];
}> = ({ title, tasks, dragState, onDragOver, onDrop, onDragStart, conflicts }) => {
  const columnRef = useRef<HTMLDivElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!columnRef.current) return;

    const rect = columnRef.current.getBoundingClientRect();
    const mouseY = e.clientY - rect.top;
    const rowHeight = 60;
    const overIndex = Math.floor(mouseY / rowHeight);

    onDragOver(title, Math.min(overIndex, tasks.length));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    const sourceColumn = e.dataTransfer.getData('sourceColumn');
    
    if (sourceColumn === title) {
      const rect = columnRef.current?.getBoundingClientRect();
      const mouseY = e.clientY - (rect?.top || 0);
      const rowHeight = 60;
      const newOrder = Math.floor(mouseY / rowHeight);
      onDrop(taskId, title, Math.min(newOrder, tasks.length));
    } else {
      onDrop(taskId, title, tasks.length);
    }
  };

  const isDragOver = dragState?.overColumn === title;

  return (
    <div
      ref={columnRef}
      className={`column ${isDragOver ? 'column-drag-over' : ''}`}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <h2 className="column-title">{title} ({tasks.length})</h2>
      <div className="tasks-container">
        {tasks.map(task => {
          const hasConflict = conflicts.some(c => c.taskId === task.id);
          return (
            <TaskCard
              key={task.id}
              task={task}
              onDragStart={onDragStart}
              hasConflict={hasConflict}
            />
          );
        })}
      </div>
    </div>
  );
};

const ConflictToast: React.FC<{
  conflict: ConflictInfo;
  onDismiss: (taskId: string) => void;
}> = ({ conflict, onDismiss }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(conflict.taskId);
    }, 5000);
    return () => clearTimeout(timer);
  }, [conflict.taskId, onDismiss]);

  return (
    <div className="conflict-toast">
      <p>
        User {conflict.remoteMove.fromColumn} also moved this task to{' '}
        {conflict.remoteMove.toColumn}. Your change was applied. Click to revert.
      </p>
      <button
        className="dismiss-button"
        onClick={() => onDismiss(conflict.taskId)}
      >
        ×
      </button>
    </div>
  );
};

const CollaborativeTodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, {
    tasks: [
      { id: 'task-1', title: 'Design review', column: 'todo', order: 0, version: 0, lastMovedBy: 'user-1' },
      { id: 'task-2', title: 'API implementation', column: 'inProgress', order: 0, version: 0, lastMovedBy: 'user-1' },
      { id: 'task-3', title: 'Testing', column: 'done', order: 0, version: 0, lastMovedBy: 'user-1' },
    ],
    users: [
      { id: 'user-1', name: 'Alice', color: '#4caf50' },
      { id: 'user-2', name: 'Bob', color: '#2196f3' },
    ],
    localUserId: 'user-1',
    dragState: null,
    conflicts: [],
    pendingOptimistic: [],
  });

  // Simulate real-time sync
  useEffect(() => {
    const interval = setInterval(() => {
      const randomAction = Math.random();
      if (randomAction < 0.2) {
        // Create new task
        const titles = ['Code review', 'Documentation', 'Bug fix', 'Feature'];
        const randomTitle = titles[Math.floor(Math.random() * titles.length)];
        dispatch({
          type: 'REMOTE_UPDATE',
          payload: {
            taskId: `remote-${Date.now()}`,
            column: 'todo',
            order: state.tasks.filter(t => t.column === 'todo').length,
            version: 0,
            movedBy: 'user-2',
          },
        });
      } else if (randomAction < 0.8) {
        // Move existing task
        if (state.tasks.length > 0) {
          const randomTask = state.tasks[Math.floor(Math.random() * state.tasks.length)];
          const columns: Task['column'][] = ['todo', 'inProgress', 'done'];
          const randomColumn = columns.filter(c => c !== randomTask.column)[Math.floor(Math.random() * 2)] || columns[0];
          
          dispatch({
            type: 'REMOTE_UPDATE',
            payload: {
              taskId: randomTask.id,
              column: randomColumn,
              order: state.tasks.filter(t => t.column === randomColumn).length,
              version: randomTask.version + 1,
              movedBy: 'user-2',
            },
          });
        }
      } else {
        // Reorder task
        if (state.tasks.length > 0) {
          const randomTask = state.tasks[Math.floor(Math.random() * state.tasks.length)];
          dispatch({
            type: 'REMOTE_UPDATE',
            payload: {
              taskId: randomTask.id,
              column: randomTask.column,
              order: Math.max(0, randomTask.order - 1),
              version: randomTask.version + 1,
              movedBy: 'user-2',
            },
          });
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [state.tasks]);

  // Confirm optimistic ops after delay
  useEffect(() => {
    const unconfirmedOps = state.pendingOptimistic.filter(op => !op.confirmed);
    unconfirmedOps.forEach(op => {
      setTimeout(() => {
        dispatch({ type: 'CONFIRM_OP', payload: { opId: op.opId } });
      }, 500);
    });
  }, [state.pendingOptimistic]);

  const handleCreateTask = (title: string) => {
    dispatch({ type: 'CREATE_TASK', payload: { title } });
  };

  const handleDragStart = (taskId: string, sourceColumn: string) => {
    dispatch({
      type: 'SET_DRAG_STATE',
      payload: { taskId, sourceColumn, overColumn: null, overIndex: null },
    });
  };

  const handleDragOver = (column: string, overIndex: number | null) => {
    if (state.dragState) {
      dispatch({
        type: 'SET_DRAG_STATE',
        payload: { ...state.dragState, overColumn: column, overIndex },
      });
    }
  };

  const handleDrop = (taskId: string, toColumn: string, newOrder: number) => {
    const sourceColumn = state.dragState?.sourceColumn;
    if (sourceColumn === toColumn) {
      dispatch({ type: 'REORDER_TASK', payload: { taskId, newOrder } });
    } else {
      dispatch({ type: 'MOVE_TASK', payload: { taskId, toColumn, newOrder } });
    }
    dispatch({ type: 'CLEAR_DRAG_STATE' });
  };

  const handleDismissConflict = (taskId: string) => {
    dispatch({ type: 'DISMISS_CONFLICT', payload: { taskId } });
  };

  const todoTasks = state.tasks.filter(t => t.column === 'todo').sort((a, b) => a.order - b.order);
  const inProgressTasks = state.tasks.filter(t => t.column === 'inProgress').sort((a, b) => a.order - b.order);
  const doneTasks = state.tasks.filter(t => t.column === 'done').sort((a, b) => a.order - b.order);

  return (
    <div className="collaborative-todo-board">
      <style>{`
        .collaborative-todo-board {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .board-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 2px solid #e0e0e0;
        }

        .board-header h1 {
          margin: 0;
          color: #333;
        }

        .user-indicator {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .user-count {
          color: #666;
          font-size: 14px;
        }

        .user-dots {
          display: flex;
          gap: 4px;
        }

        .user-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
        }

        .new-task-form {
          display: flex;
          gap: 8px;
        }

        .new-task-input {
          padding: 8px 12px;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-size: 14px;
          min-width: 200px;
        }

        .new-task-button {
          padding: 8px 16px;
          background-color: #2196f3;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }

        .new-task-button:hover {
          background-color: #1976d2;
        }

        .columns-container {
          display: flex;
          gap: 20px;
        }

        .column {
          flex: 1;
          background-color: #f5f5f5;
          border-radius: 8px;
          padding: 16px;
          min-height: 500px;
          transition: all 0.2s ease;
        }

        .column-drag-over {
          background-color: #e3f2fd;
          border: 2px dashed #2196f3;
        }

        .column-title {
          margin: 0 0 16px 0;
          color: #444;
          font-size: 18px;
        }

        .tasks-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .task-card {
          background-color: white;
          border-radius: 6px;
          padding: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          cursor: grab;
          transition: all 0.2s ease;
          border-left: 4px solid #4caf50;
        }

        .task-card:active {
          cursor: grabbing;
          opacity: 0.6;
        }

        .task-content {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .task-title {
          margin: 0;
          font-size: 14px;
          color: #333;
        }

        .task-meta {
          display: flex;
          gap: 8px;
          font-size: 12px;
          color: #666;
        }

        .task-conflict {
          border-left-color: #ff9800;
        }

        .conflict-indicator {
          margin-top: 8px;
          font-size: 12px;
          color: #ff9800;
          font-weight: bold;
        }

        .conflict-toast {
          position: fixed;
          bottom: 20px;
          right: 20px;
          background-color: #ffebee;
          border: 1px solid #ef5350;
          border-radius: 6px;
          padding: 12px 16px;
          max-width: 300px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          animation: slideIn 0.3s ease;
        }

        .conflict-toast p {
          margin: 0;
          font-size: 13px;
          color: #d32f2f;
        }

        .dismiss-button {
          background: none;
          border: none;
          font-size: 18px;
          color: #d32f2f;
          cursor: pointer;
          padding: 0;
          margin-left: 8px;
        }

        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>

      <BoardHeader
        title="Collaborative Todo Board"
        users={state.users}
        onCreateTask={handleCreateTask}
      />

      <div className="columns-container">
        <Column
          title="todo"
          tasks={todoTasks}
          dragState={state.dragState}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
          conflicts={state.conflicts}
        />
        <Column
          title="inProgress"
          tasks={inProgressTasks}
          dragState={state.dragState}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
          conflicts={state.conflicts}
        />
        <Column
          title="done"
          tasks={doneTasks}
          dragState={state.dragState}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
          conflicts={state.conflicts}
        />
      </div>

      <div className="conflict-toasts-container">
        {state.conflicts.map(conflict => (
          <ConflictToast
            key={conflict.taskId}
            conflict={conflict}
            onDismiss={handleDismissConflict}
          />
        ))}
      </div>
    </div>
  );
};

export default CollaborativeTodoBoard;