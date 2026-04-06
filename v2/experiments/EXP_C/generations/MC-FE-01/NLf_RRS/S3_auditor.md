# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-FE-01

## Constraint Review
- C1 (TS + React): PASS — import React, { useReducer, useEffect, useCallback, useRef } from 'react'
- C2 (CSS Modules, no Tailwind): FAIL — 使用内联样式字符串而不是CSS Modules
- C3 (HTML5 Drag, no dnd libs): PASS — 使用HTML5 Drag and Drop API（draggable, onDragStart, onDragOver等）
- C4 (useReducer only): PASS — 使用useReducer进行状态管理，无其他状态管理库
- C5 (Single file, export default): PASS — 单一.tsx文件并以export default CollaborativeTodoBoard导出
- C6 (Hand-written WS mock, no socket.io): PASS — 使用setTimeout/setInterval模拟实时同步

## Functionality Assessment (0-5)
Score: 4 — 实现了一个功能完整的协作式待办事项看板，包含拖放、冲突检测、乐观更新和远程同步模拟。主要功能都正常工作，但CSS实现不符合CSS Modules规范。

## Corrected Code
由于C2约束失败（未使用CSS Modules），以下是修复后的完整.tsx文件：

```tsx
import React, { useReducer, useEffect, useCallback, useRef } from 'react';
import styles from './CollaborativeTodoBoard.module.css';

// ── Interfaces ──────────────────────────────────────────────────────────────

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
  localMove: { column: string; taskId: string };
  remoteMove: { column: string; taskId: string; userName: string };
  timestamp: number;
}

interface OptimisticOp {
  opId: string;
  type: 'move' | 'create';
  payload: { taskId: string; toColumn?: string };
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
  newTaskTitle: string;
}

type BoardAction =
  | { type: 'CREATE_TASK'; title: string }
  | { type: 'MOVE_TASK'; taskId: string; toColumn: 'todo' | 'inProgress' | 'done'; toIndex: number }
  | { type: 'REORDER_TASK'; taskId: string; toIndex: number }
  | { type: 'SET_DRAG_STATE'; dragState: DragState }
  | { type: 'CLEAR_DRAG_STATE' }
  | { type: 'REMOTE_UPDATE'; task: Task; userName: string }
  | { type: 'CONFIRM_OP'; opId: string }
  | { type: 'RAISE_CONFLICT'; conflict: ConflictInfo }
  | { type: 'DISMISS_CONFLICT'; taskId: string }
  | { type: 'SYNC_USERS'; users: User[] }
  | { type: 'SET_NEW_TASK_TITLE'; title: string };

// ── Helpers ──────────────────────────────────────────────────────────────────

let idCounter = 0;
const genId = (): string => `task-${Date.now()}-${++idCounter}`;
const genOpId = (): string => `op-${Date.now()}-${++idCounter}`;

const COLUMNS: Array<'todo' | 'inProgress' | 'done'> = ['todo', 'inProgress', 'done'];
const COLUMN_LABELS: Record<string, string> = {
  todo: 'Todo',
  inProgress: 'In Progress',
  done: 'Done',
};

const REMOTE_USERS: User[] = [
  { id: 'remote-1', name: 'Alice', color: '#e74c3c' },
  { id: 'remote-2', name: 'Bob', color: '#2ecc71' },
];

const INITIAL_TASKS: Task[] = [
  { id: genId(), title: 'Set up project structure', column: 'todo', order: 0, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Design database schema', column: 'todo', order: 1, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Implement auth flow', column: 'inProgress', order: 0, version: 1, lastMovedBy: 'local' },
  { id: genId(), title: 'Write unit tests', column: 'done', order: 0, version: 1, lastMovedBy: 'local' },
];

// ── Reducer ─────────────────────────────────────────────────────────────────

const initialState: BoardState = {
  tasks: INITIAL_TASKS,
  users: [{ id: 'local', name: 'You', color: '#5b6abf' }, ...REMOTE_USERS],
  localUserId: 'local',
  dragState: null,
  conflicts: [],
  pendingOptimistic: [],
  newTaskTitle: '',
};

function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case 'CREATE_TASK': {
      const newTask: Task = {
        id: genId(),
        title: action.title,
        column: 'todo',
        order: state.tasks.filter(t => t.column === 'todo').length,
        version: 1,
        lastMovedBy: state.localUserId,
      };
      const op: OptimisticOp = {
        opId: genOpId(),
        type: 'create',
        payload: { taskId: newTask.id },
        timestamp: Date.now(),
        confirmed: false,
      };
      return {
        ...state,
        tasks: [...state.tasks, newTask],
        pendingOptimistic: [...state.pendingOptimistic, op],
        newTaskTitle: '',
      };
    }

    case 'MOVE_TASK': {
      const op: OptimisticOp = {
        opId: genOpId(),
        type: 'move',
        payload: { taskId: action.taskId, toColumn: action.toColumn },
        timestamp: Date.now(),
        confirmed: false,
      };
      const tasks = state.tasks.map(t => {
        if (t.id === action.taskId) {
          return { ...t, column: action.toColumn, order: action.toIndex, version: t.version + 1, lastMovedBy: state.localUserId };
        }
        return t;
      });
      return {
        ...state,
        tasks,
        pendingOptimistic: [...state.pendingOptimistic, op],
        dragState: null,
      };
    }

    case 'REORDER_TASK': {
      const tasks = state.tasks.map(t => {
        if (t.id === action.taskId) {
          return { ...t, order: action.toIndex };
        }
        return t;
      });
      return { ...state, tasks };
    }

    case 'SET_DRAG_STATE':
      return { ...state, dragState: action.dragState };

    case 'CLEAR_DRAG_STATE':
      return { ...state, dragState: null };

    case 'REMOTE_UPDATE': {
      const incoming = action.task;
      const pendingConflict = state.pendingOptimistic.find(
        op => !op.confirmed && op.payload.taskId === incoming.id
      );
      let conflicts = state.conflicts;
      if (pendingConflict) {
        const conflict: ConflictInfo = {
          taskId: incoming.id,
          localMove: { column: pendingConflict.payload.toColumn || '', taskId: incoming.id },
          remoteMove: { column: incoming.column, taskId: incoming.id, userName: action.userName },
          timestamp: Date.now(),
        };
        conflicts = [...conflicts, conflict];
      }
      const tasks = state.tasks.map(t => {
        if (t.id === incoming.id) {
          if (pendingConflict) return t;
          return incoming;
        }
        return t;
      });
      const hasTask = tasks.some(t => t.id === incoming.id);
      return {
        ...state,
        tasks: hasTask ? tasks : [...tasks, incoming],
        conflicts,
      };
    }

    case 'CONFIRM_OP':
      return {
        ...state,
        pendingOptimistic: state.pendingOptimistic.map(op =>
          op.opId === action.opId ? { ...op, confirmed: true } : op
        ),
      };

    case 'RAISE_CONFLICT':
      return { ...state, conflicts: [...state.conflicts, action.conflict] };

    case 'DISMISS_CONFLICT':
      return { ...state, conflicts: state.conflicts.filter(c => c.taskId !== action.taskId) };

    case 'SYNC_USERS':
      return { ...state, users: [state.users[0], ...action.users] };

    case 'SET_NEW_TASK_TITLE':
      return { ...state, newTaskTitle: action.title };

    default:
      return state;
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────

const BoardHeader: React.FC<{
  userCount: number;
  users: User[];
  newTaskTitle: string;
  onTitleChange: (v: string) => void;
  onAdd: () => void;
}> = ({ userCount, users, newTaskTitle, onTitleChange, onAdd }) => (
  <div className={styles.header}>
    <div>
      <div className={styles.headerTitle}>Collaborative Todo Board</div>
      <div className={styles.inputRow}>
        <input
          className={styles.input}
          placeholder="Add a new task..."
          value={newTaskTitle}
          onChange={e => onTitleChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && newTaskTitle.trim()) onAdd(); }}
        />
        <button className={styles.addBtn} onClick={onAdd}>Add</button>
      </div>
    </div>
    <div className={styles.userBadge}>
      {users.map(u => (
        <span key={u.id} className={styles.dot} style={{ background: u.color }} title={u.name} />
      ))}
      <span>{userCount} online</span>
    </div>
  </div>
);

const TaskCard: React.FC<{
  task: Task;
  isDragging: boolean;
  hasConflict: boolean;
  onDragStart: (e: React.DragEvent, taskId: string, column: string) => void;
}> = ({ task, isDragging, hasConflict, onDragStart }) => {
  const cls = [
    styles.card,
    isDragging ? styles.cardDragging : '',
    hasConflict ? styles.cardConflict : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={cls}
      draggable
      onDragStart={e => onDragStart(e, task.id, task.column)}
    >
      {task.title}
      <div className={styles.movedBy}>v{task.version}</div>
    </div>
  );
};

const Column: React.FC<{
  column: 'todo' | 'inProgress' | 'done';
  tasks: Task[];
  dragState: DragState | null;
  conflicts: ConflictInfo[];
  onDragStart: (e: React.DragEvent, taskId: string, column: string) => void;
  onDragOver: (e: React.DragEvent, column: string) => void;
  onDrop: (e: React.DragEvent, column: 'todo' | 'inProgress' | 'done') => void;
  onDragLeave: () => void;
}> = ({ column, tasks, dragState, conflicts, onDragStart, onDragOver, onDrop, onDragLeave }) => {
  const isOver = dragState?.overColumn === column;
  const sorted = [...tasks].sort((a, b) => a.order - b.order);
  const conflictIds = new Set(conflicts.map(c => c.taskId));

  return (
    <div
      className={`${styles.column} ${isOver ? styles.columnOver : ''}`}
      onDragOver={e => onDragOver(e, column)}
      onDrop={e => onDrop(e, column)}
      onDragLeave={onDragLeave}
    >
      <div className={styles.colTitle}>
        {COLUMN_LABELS[column]}
        <span className={styles.count}>{tasks.length}</span>
      </div>
      {sorted.map((task, idx) => (
        <React.Fragment key={task.id}>
          {isOver && dragState?.overIndex === idx && (
            <div className={styles.insertLine} />
          )}
          <TaskCard
            task={task}
            isDragging={dragState?.taskId === task.id}
            hasConflict={conflictIds.has(task.id)}
            onDragStart={onDragStart}
          />
        </React.Fragment>
      ))}
      {isOver && dragState?.overIndex != null && dragState.overIndex >= sorted.length && (
        <div className={styles.insertLine} />
      )}
    </div>
  );
};

const ConflictToast: React.FC<{ conflicts: ConflictInfo[]; onDismiss: (taskId: string) => void }> = ({ conflicts, onDismiss }) => {
  if (conflicts.length === 0) return null;
  const c = conflicts[0];
  return (
    <div className={styles.toast} onClick={() => onDismiss(c.taskId)}>
      <strong>{c.remoteMove.userName}</strong> also moved this task to <strong>{COLUMN_LABELS[c.remoteMove.column] || c.remoteMove.column}</strong>. Your change was applied. Click to dismiss.
    </div>
  );
};

// ── Main component ──────────────────────────────────────────────────────────

const CollaborativeTodoBoard: React.FC = () => {
  const [state, dispatch] = useReducer(boardReducer, initialState);
  const cardRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());

  // Simulate remote sync
  useEffect(() => {
    const interval = setInterval(() => {
      const rand = Math.random();
      const remoteUser = REMOTE_USERS[Math.floor(Math.random() * REMOTE_USERS.length)];

      if (rand < 0.2) {
        // Create
        const newTask: Task = {
          id: genId(),
          title: `Remote task by ${remoteUser.name}`,
          column: 'todo',
          order: 0,
          version: 1,
          lastMovedBy: remoteUser.id,
        };
        dispatch({ type: 'REMOTE_UPDATE', task: newTask, userName: remoteUser.name });
      } else if (rand < 0.8) {
        // Move
        const available = state.tasks.filter(t => t.column !== 'done');
        if (available.length > 0) {
          const target = available[Math.floor(Math.random() * available.length)];
          const possibleCols = COLUMNS.filter(c => c !== target.column);
          const newCol = possibleCols[Math.floor(Math.random() * possibleCols.length)];
          const updated: Task = { ...target, column: newCol, version: target.version + 1, lastMovedBy: remoteUser.id };
          dispatch({ type: 'REMOTE_UPDATE', task: updated, userName: remoteUser.name });
        }
      } else {
        // Reorder
        const col = COLUMNS[Math.floor(Math.random() * COLUMNS.length)];
        const colTasks = state.tasks.filter(t => t.column === col);
        if (colTasks.length > 1) {
          const target = colTasks[Math.floor(Math.random() * colTasks.length)];
          const updated: Task = { ...target, order: Math.floor(Math.random() * colTasks.length), version: target.version + 1, lastMovedBy: remoteUser.id };
          dispatch({ type: 'REMOTE_UPDATE', task: updated, userName: remoteUser.name });
        }
      }
    }, 2000 + Math.random() * 2000);

    return () => clearInterval(interval);
  }, [state.tasks]);

  // Confirm optimistic ops after delay
  useEffect(() => {
    const pending = state.pendingOptimistic.filter(op => !op.confirmed);
    pending.forEach(op => {
      const timer = setTimeout(() => {
        dispatch({ type: 'CONFIRM_OP', opId: op.opId });
      }, 500);
      return () => clearTimeout(timer);
    });
  }, [state.pendingOptimistic]);

  // Auto-dismiss conflicts
  useEffect(() => {
    if (state.conflicts.length > 0) {
      const timer = setTimeout(() => {
        dispatch({ type: 'DISMISS_CONFLICT', taskId: state.conflicts[0].taskId });
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [state.conflicts]);

  const handleDragStart = useCallback((e: React.DragEvent, taskId: string, column: string) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ taskId, sourceColumn: column }));
    e.dataTransfer.effectAllowed = 'move';
    dispatch({
      type: 'SET_DRAG_STATE',
      dragState: { taskId, sourceColumn: column, overColumn: null, overIndex: null },
    });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, column: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const container = e.currentTarget as HTMLElement;
    const cards = container.querySelectorAll(`.${styles.card}`);
    const mouseY = e.clientY;
    let insertIndex = cards.length;

    for (let i = 0; i < cards.length; i++) {
      const rect = cards[i].getBoundingClientRect();
      if (mouseY < rect.top + rect.height / 2) {
        insertIndex = i;
        break;
      }
    }

    dispatch({
      type: 'SET_DRAG_STATE',
      dragState: {
        taskId: state.dragState?.taskId || '',
        sourceColumn: state.dragState?.sourceColumn || '',
        overColumn: column,
        overIndex: insertIndex,
      },
    });
  }, [state.dragState]);

  const handleDrop = useCallback((e: React.DragEvent, column: 'todo' | 'inProgress' | 'done') => {
    e.preventDefault();
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
      const toIndex = state.dragState?.overIndex ?? 0;
      if (data.sourceColumn === column) {
        dispatch({ type: 'REORDER_TASK', taskId: data.taskId, toIndex });
      } else {
        dispatch({ type: 'MOVE_TASK', taskId: data.taskId, toColumn: column, toIndex });
      }
    } catch {
      dispatch({ type: 'CLEAR_DRAG_STATE' });
    }
  }, [state.dragState]);

  const handleDragEnd = useCallback(() => {
    dispatch({ type: 'CLEAR_DRAG_STATE' });
  }, []);

  const handleAddTask = useCallback(() => {
    if (state.newTaskTitle.trim()) {
      dispatch({ type: 'CREATE_TASK', title: state.newTaskTitle.trim() });
    }
  }, [state.newTaskTitle]);

  return (
    <div className={styles.board} onDragEnd={handleDragEnd}>
      <BoardHeader
        userCount={state.users.length}
        users={state.users}
        newTaskTitle={state.newTaskTitle}
        onTitleChange={v => dispatch({ type: 'SET_NEW_TASK_TITLE', title: v })}
        onAdd={handleAddTask}
      />
      <div className={styles.columns}>
        {COLUMNS.map(col => (
          <Column
            key={col}
            column={col}
            tasks={state.tasks.filter(t => t.column === col)}
            dragState={state.dragState}
            conflicts={state.conflicts}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onDragLeave={() => {
              if (state.dragState) {
                dispatch({
                  type: 'SET_DRAG_STATE',
                  dragState: { ...state.dragState, overColumn: null, overIndex: null },
                });
              }
            }}
          />
        ))}
      </div>
      <ConflictToast conflicts={state.conflicts} onDismiss={taskId => dispatch({ type: 'DISMISS_CONFLICT', taskId })} />
    </div>
  );
};

export default CollaborativeTodoBoard;
```

**注意**: 修复后的代码假设存在 `CollaborativeTodoBoard.module.css` 文件，其中包含所有CSS样式。原始的内联CSS字符串需要提取到该CSS Modules文件中。