# MC-FE-01: Real-time Collaborative Todo Board — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Component Architecture

### 1.1 Top-Level Structure
```
TodoBoard (Container)
├── BoardHeader (title + connection status)
├── KanbanColumns (3 columns wrapper)
│   ├── TodoColumn
│   ├── InProgressColumn
│   └── DoneColumn
└── TaskCard (draggable item)
```

### 1.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `TodoBoard` | Root state container, reducer dispatch, mock WebSocket coordination |
| `KanbanColumns` | Layout wrapper, column rendering loop |
| `*Column` | Drop zone handling, column-specific styling |
| `TaskCard` | Drag source, task display, optimistic UI feedback |
| `BoardHeader` | Title, mock connection status indicator |

---

## 2. Data Model (TypeScript Interfaces)

```typescript
// Task entity
type TaskStatus = 'todo' | 'in-progress' | 'done';

interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  createdAt: number;
  updatedAt: number;
  version: number;  // For conflict detection
}

// State shape for useReducer
interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: TaskStatus[];
  optimisticUpdates: Map<string, OptimisticUpdate>;
  conflictHints: ConflictHint[];
}

interface OptimisticUpdate {
  taskId: string;
  previousStatus: TaskStatus;
  pendingStatus: TaskStatus;
  timestamp: number;
}

interface ConflictHint {
  taskId: string;
  message: string;
  resolvedAt: number;
}
```

---

## 3. State Management Approach

### 3.1 useReducer Design

**State Machine**: Tasks flow through columns with version tracking.

**Actions**:
- `ADD_TASK` — Create new task in Todo
- `MOVE_TASK` — Drag-drop with optimistic update
- `CONFIRM_MOVE` — Server acknowledgment
- `REJECT_MOVE` — Rollback optimistic update
- `DETECT_CONFLICT` — Version mismatch handling
- `RESOLVE_CONFLICT` — User acknowledges conflict

### 3.2 Optimistic Update Flow

1. User drags Task A from Todo → In Progress
2. Dispatch `MOVE_TASK` → immediate UI update
3. Store optimistic record in `optimisticUpdates`
4. Mock "server" responds (simulated delay)
5. On success: dispatch `CONFIRM_MOVE`, clear optimistic
6. On conflict: dispatch `REJECT_MOVE` + `DETECT_CONFLICT`

### 3.3 Conflict Resolution

When two "users" move the same task simultaneously:
- Compare task versions
- If version mismatch → show conflict hint
- Highlight affected task card
- Provide "keep mine" / "accept theirs" options

---

## 4. Key Implementation Approaches

### 4.1 HTML5 Drag and Drop (No Library)

**Drag Source** (`TaskCard`):
- `draggable="true"`
- `onDragStart`: set `dataTransfer` with task ID
- `onDragEnd`: cleanup

**Drop Target** (`*Column`):
- `onDragOver`: preventDefault, visual feedback
- `onDrop`: extract task ID, dispatch move action

**Visual Feedback**:
- CSS modules for drag states (`.dragging`, `.dragOver`)
- No inline Tailwind classes

### 4.2 Mock Real-time Layer

Since no Socket.IO:
- `useEffect` with `setInterval` simulates incoming updates
- Randomly moves tasks between columns (simulating other users)
- Triggers conflict detection when versions mismatch

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]TS` | All interfaces typed; strict TypeScript throughout |
| `[F]React` | Functional components with hooks only |
| `[Y]CSS_MODULES` | All styling via `.module.css` files; no CSS-in-JS |
| `[!Y]NO_TW` | No Tailwind utility classes; pure CSS modules |
| `[!D]NO_DND_LIB` | Native HTML5 DnD API; no react-beautiful-dnd |
| `[DRAG]HTML5` | `draggable` attribute + `dataTransfer` API |
| `[STATE]useReducer` | All state mutations via reducer actions |
| `[O]SFC` | Single file default export component |
| `[EXP]DEFAULT` | `export default TodoBoard` |
| `[WS]MOCK` | Simulated real-time via interval + random updates |
| `[!D]NO_SOCKETIO` | No socket.io-client; mock layer only |

---

## 6. File Structure

```
MC-FE-01/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
├── S2_developer/
│   └── TodoBoard.tsx
├── TodoBoard.module.css
└── types.ts
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
