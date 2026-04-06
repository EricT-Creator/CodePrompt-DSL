# Technical Design Document: Real-time Collaborative Todo Board

**Task**: MC-FE-01  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]TS [F]React [Y]CSS_MODULES [!Y]NO_TW [!D]NO_DND_LIB [DRAG]HTML5 [STATE]useReducer [O]SFC [EXP]DEFAULT [WS]MOCK [!D]NO_SOCKETIO`

---

## 1. Component Architecture

### Top-Level Component: `TodoBoard`
Single Functional Component (SFC) exported as default. Owns the global state via `useReducer` and renders three column containers.

**Internal Sub-components** (defined in the same file or as inner functions):

| Component | Responsibility |
|-----------|---------------|
| `Column` | Renders a single column (Todo / In Progress / Done). Acts as a drop target using HTML5 drag events (`onDragOver`, `onDrop`). |
| `TaskCard` | Renders a single task. Acts as a drag source using `draggable` attribute and `onDragStart`. Displays task title, assignee badge, and conflict indicator. |
| `ConflictToast` | Ephemeral overlay shown when two users attempt to move the same task simultaneously. Displays the conflict hint and auto-dismisses. |
| `AddTaskInput` | Inline input at the bottom of the "Todo" column for creating new tasks. |

**Data flow**: Unidirectional. `TodoBoard` passes `state` and `dispatch` downward. Child components call `dispatch` to mutate state. WebSocket messages (mocked) also feed into `dispatch`.

### Rendering Tree

```
TodoBoard
├── Column (Todo)
│   ├── TaskCard × N
│   └── AddTaskInput
├── Column (In Progress)
│   └── TaskCard × N
├── Column (Done)
│   └── TaskCard × N
└── ConflictToast (conditional)
```

---

## 2. Data Model (TypeScript Interfaces)

```
interface Task {
  id: string;                  // UUID
  title: string;
  column: ColumnId;            // 'todo' | 'inprogress' | 'done'
  order: number;               // sort index within column
  version: number;             // optimistic concurrency token
  lastModifiedBy: string;      // user id
}

type ColumnId = 'todo' | 'inprogress' | 'done';

interface BoardState {
  tasks: Record<string, Task>;
  columnOrder: Record<ColumnId, string[]>;  // ordered task ids per column
  userId: string;
  conflict: ConflictInfo | null;
}

interface ConflictInfo {
  taskId: string;
  localMove: { from: ColumnId; to: ColumnId };
  remoteMove: { from: ColumnId; to: ColumnId; by: string };
  timestamp: number;
}
```

---

## 3. State Management Approach

### useReducer Design

**State shape**: `BoardState` as defined above.

**Action types**:

| Action | Payload | Effect |
|--------|---------|--------|
| `ADD_TASK` | `{ title: string }` | Appends a new task to the "Todo" column |
| `MOVE_TASK` | `{ taskId, toColumn, toIndex }` | Removes task from source column, inserts into target column at specified index. Increments `version`. |
| `REORDER_TASK` | `{ taskId, toIndex }` | Reorders task within the same column |
| `REMOTE_UPDATE` | `{ task: Task }` | Applies a remote user's change. If version conflict is detected, dispatches `SET_CONFLICT`. |
| `SET_CONFLICT` | `{ ConflictInfo }` | Stores conflict info for the toast |
| `DISMISS_CONFLICT` | — | Clears conflict info |

### Optimistic Updates

1. On drag-drop, `MOVE_TASK` is dispatched **immediately** (optimistic).
2. The mock WebSocket sends the same action to the "server."
3. If the server confirms, no further action.
4. If the server returns a conflict (version mismatch), `SET_CONFLICT` fires and the toast appears. The reducer rolls back the local move and applies the server's authoritative state.

### Conflict Resolution Hints

- Version number on each task acts as a concurrency token.
- When two users move the same task and version numbers diverge, the reducer detects this in `REMOTE_UPDATE` and surfaces a `ConflictInfo`.
- The UI displays which user moved the task and where, allowing the local user to re-drag if desired.

---

## 4. Key Implementation Approaches for Constrained Areas

### 4.1 Drag-and-Drop via HTML5 API

Since no DnD library is permitted, the implementation uses native HTML5 drag events:

- **`draggable="true"`** on `TaskCard`.
- **`onDragStart`**: Stores `taskId` and source column in `dataTransfer.setData()`.
- **`onDragOver`**: Calls `e.preventDefault()` to allow drop. Calculates insertion index by comparing `e.clientY` against sibling bounding rects.
- **`onDrop`**: Reads `taskId` from `dataTransfer`, dispatches `MOVE_TASK` with the calculated target column and index.
- **`onDragEnd`**: Cleans up any visual indicators.

**Reorder within column**: Same mechanism — if source and target column are identical, dispatch `REORDER_TASK` instead.

**Visual feedback**: During drag, a CSS class (`.dragging`) is applied via CSS Modules to dim the source card and highlight valid drop zones.

### 4.2 Mock WebSocket Layer

A `MockWebSocket` class simulates real-time collaboration:

- Internally uses `setTimeout` to simulate network latency (50–200ms random).
- Maintains a "remote state" that can diverge from local state to trigger conflict scenarios.
- Exposes `send(action)` and `onMessage(callback)` interface matching the real WebSocket contract.
- A `useEffect` in `TodoBoard` initializes the mock connection on mount and cleans up on unmount.

### 4.3 CSS Modules Styling

All styles scoped via CSS Modules (`.module.css` files). Key classes:

- `.board` — flex row container for columns
- `.column` — flex column with header, scrollable task list, and drop zone highlight
- `.card` — individual task card with shadow, border-radius
- `.card.dragging` — reduced opacity during drag
- `.dropZone` — visual indicator when dragging over a valid target
- `.conflictToast` — fixed-position overlay with fade-in/out animation

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: TypeScript | `[L]TS` | All components, interfaces, and state are fully typed in TypeScript. |
| Framework: React | `[F]React` | Built entirely with React functional components and hooks. |
| Styling: CSS Modules | `[Y]CSS_MODULES` | All styles use `.module.css` imports with locally scoped class names. |
| No Tailwind | `[!Y]NO_TW` | Zero Tailwind classes anywhere. All styling via CSS Modules only. |
| No DnD library | `[!D]NO_DND_LIB` | No react-beautiful-dnd, dnd-kit, or similar. Pure HTML5 drag API. |
| HTML5 drag API | `[DRAG]HTML5` | `draggable`, `onDragStart`, `onDragOver`, `onDrop` used directly. |
| State via useReducer | `[STATE]useReducer` | Single `useReducer` manages all board state. No useState for domain state, no Redux/Zustand. |
| Single Functional Component | `[O]SFC` | `TodoBoard` is the sole exported component. Sub-components are internal. |
| Default export | `[EXP]DEFAULT` | `export default function TodoBoard() {...}` |
| Mock WebSocket | `[WS]MOCK` | Custom `MockWebSocket` class simulates real-time communication. No actual server. |
| No Socket.IO | `[!D]NO_SOCKETIO` | Socket.IO library not used. Mock layer uses plain callback pattern. |
