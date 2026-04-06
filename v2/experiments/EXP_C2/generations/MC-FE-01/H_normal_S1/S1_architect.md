# Technical Design: Real-Time Collaborative Todo Board

## 1. Component Architecture

### Component Tree

- **TodoBoardApp** (root, default export) — owns global state via `useReducer`, orchestrates layout
  - **BoardHeader** — displays title, connected-user indicators
  - **Column** (×3: Todo / In Progress / Done) — renders a vertical list of task cards, acts as drag target
    - **TaskCard** — individual draggable card; shows task text, assignee badge, conflict warning
  - **TaskCreator** — inline form at the top of the "Todo" column; dispatches `ADD_TASK`
  - **ConflictToast** — floating notification when a remote user touches the same task being dragged locally

All components are **function components** defined inside one `.tsx` file, composed as a single-file component (SFC).

## 2. Data Model

### Core Interfaces

**Task**
- `id: string` — UUID
- `text: string`
- `column: 'todo' | 'inProgress' | 'done'`
- `order: number` — sort index within column
- `lastMovedBy: string` — user id of last mover
- `version: number` — monotonically increasing for conflict detection

**BoardState**
- `tasks: Record<string, Task>`
- `columnOrder: Record<ColumnId, string[]>` — ordered task ids per column
- `currentUser: string`
- `connectedUsers: string[]`
- `pendingOptimistic: OptimisticOp[]`
- `conflicts: ConflictHint[]`

**OptimisticOp**
- `opId: string`
- `type: 'MOVE' | 'REORDER' | 'ADD'`
- `payload: any`
- `timestamp: number`

**ConflictHint**
- `taskId: string`
- `localUser: string`
- `remoteUser: string`
- `resolvedAt?: number`

## 3. State Management Approach

All mutable state lives in a single `useReducer(boardReducer, initialState)` at the root component. Action types:

| Action | Trigger |
|--------|---------|
| `ADD_TASK` | User creates a new task |
| `MOVE_TASK` | Drag-drop across columns |
| `REORDER_TASK` | Drag-drop within a column |
| `REMOTE_UPDATE` | Mock WebSocket receives a change |
| `CONFLICT_DETECTED` | Two users moved the same task |
| `CONFLICT_DISMISSED` | User acknowledges conflict toast |
| `SYNC_ACK` | Server confirms optimistic op |
| `SET_USERS` | Mock reports user list update |

**Optimistic update flow**: On local drag, the reducer immediately applies the move and pushes an `OptimisticOp`. The mock server confirms or rejects after a delay. On rejection (conflict), the reducer rolls back by replaying state without that op.

## 4. Key Implementation Approaches

### 4.1 Drag and Drop (HTML5 API)

Each `TaskCard` receives `draggable="true"` and handlers:

- `onDragStart` — sets `dataTransfer.setData('text/plain', taskId)`, adds a CSS class for visual feedback
- `onDragEnd` — cleans up

Each `Column` and each `TaskCard` within it act as drop targets:

- `onDragOver` — calls `e.preventDefault()` to allow drop; calculates insertion index from mouse Y relative to sibling rects
- `onDrop` — reads `dataTransfer`, dispatches `MOVE_TASK` or `REORDER_TASK`

Insertion position is computed by iterating over rendered card bounding rects and finding the midpoint threshold.

### 4.2 Real-Time Sync (Mock)

A `useMockSync` custom hook (defined in the same file) uses `setInterval` to poll a module-level "server" object every 500ms. The server object:

- Maintains a canonical task list
- Accepts local ops and queues remote ops (simulated second user moves via `setTimeout` with random delays)
- Returns diffs on each poll tick

This avoids any WebSocket library while still simulating multi-user behavior.

### 4.3 Conflict Resolution

When the mock server detects two ops targeting the same `taskId` within a 2-second window, it emits a `CONFLICT_DETECTED` action. The UI shows a `ConflictToast` with both users' names and the task title. The "last write wins" policy applies server-side, but the toast gives the local user a hint to re-check.

### 4.4 Styling

All styles are authored in a co-located `.module.css` file (imported as `styles`). Class names map to each component:

- `.board` — flex row for columns
- `.column` — flex column with min-height
- `.card` — padding, border, drag-over highlight
- `.cardDragging` — opacity reduction
- `.conflictToast` — fixed-position notification

No Tailwind utilities or utility-first classes are used anywhere.

## 5. Constraint Acknowledgment

| Constraint | How Addressed |
|-----------|---------------|
| **[L]TS** | Entire file is TypeScript; interfaces defined for all data structures |
| **[F]React** | Functional React components using hooks |
| **[Y]CSS_MODULES** | All styling via `.module.css` imports; no inline style objects |
| **[!Y]NO_TW** | Zero Tailwind dependencies; only CSS Modules class names |
| **[!D]NO_DND_LIB** | No react-dnd, dnd-kit, or similar; only native HTML5 drag events |
| **[DRAG]HTML5** | Uses `draggable`, `onDragStart`, `onDragOver`, `onDrop` |
| **[STATE]useReducer** | Single `useReducer` at root; no Redux/Zustand/Jotai |
| **[O]SFC** | Entire component tree in one `.tsx` file with `export default` |
| **[EXP]DEFAULT** | Root component exported as `export default` |
| **[WS]MOCK** | Simulated sync using `setTimeout`/`setInterval` and module-level state |
| **[!D]NO_SOCKETIO** | No socket.io or WebSocket library imported |
