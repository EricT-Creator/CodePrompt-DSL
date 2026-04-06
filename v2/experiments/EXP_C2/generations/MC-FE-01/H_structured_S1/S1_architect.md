# Technical Design: Real-Time Collaborative Todo Board

## 1. Component Architecture

### Component Tree

- **TodoBoardApp** (root, default export) — holds all state via `useReducer`; renders board layout
  - **BoardHeader** — shows board title and connected-user avatars
  - **Column** (×3: Todo / In Progress / Done) — vertical list, serves as drag-drop target zone
    - **TaskCard** — individual draggable item; displays text, owner badge, optional conflict warning icon
  - **TaskCreator** — compact input form dispatching `ADD_TASK` actions
  - **ConflictBanner** — transient banner appearing when two users try to move the same card

Everything lives in a single `.tsx` file. Components are plain function components composed together.

## 2. Data Model

### Interfaces

**Task**
- `id: string` — unique identifier (UUID)
- `text: string` — task description
- `column: 'todo' | 'inProgress' | 'done'`
- `order: number` — position within column
- `lastMovedBy: string` — user who last moved this task
- `version: number` — incremented on each mutation for conflict detection

**BoardState**
- `tasks: Record<string, Task>`
- `columnOrder: { todo: string[]; inProgress: string[]; done: string[] }` — ordered id arrays
- `currentUser: string`
- `connectedUsers: string[]`
- `optimisticQueue: PendingOp[]`
- `conflictHints: ConflictInfo[]`

**PendingOp**
- `opId: string`
- `type: 'MOVE' | 'REORDER' | 'ADD'`
- `taskId: string`
- `timestamp: number`

**ConflictInfo**
- `taskId: string`
- `yourAction: string`
- `theirUser: string`

## 3. State Management Approach

A single `useReducer(reducer, initialState)` call at the root level manages the entire board. No external state libraries.

**Reducer actions:**
- `ADD_TASK` — insert new task at top of "todo" column
- `MOVE_TASK` — relocate task between columns
- `REORDER_TASK` — change position within the same column
- `APPLY_REMOTE` — integrate incoming changes from mock server
- `MARK_CONFLICT` — surface a conflict hint
- `DISMISS_CONFLICT` — user clears the conflict banner
- `CONFIRM_OP` — server acknowledged optimistic write
- `ROLLBACK_OP` — server rejected; undo local change

**Optimistic update strategy:** On drop, the reducer applies the change immediately and enqueues a `PendingOp`. The mock server later sends either `CONFIRM_OP` or `ROLLBACK_OP`. On rollback, state is rebuilt by replaying all ops minus the rejected one.

## 4. Key Implementation Approaches

### 4.1 HTML5 Drag and Drop

**Drag source (TaskCard):**
- `draggable="true"` attribute set on card root div
- `onDragStart`: stores `taskId` in `dataTransfer`, sets drag effect to `move`
- `onDragEnd`: resets visual state

**Drop target (Column / insertion zones):**
- `onDragOver`: calls `preventDefault()`, computes target insertion index by comparing `clientY` to card bounding rects
- `onDrop`: extracts task id from `dataTransfer`, dispatches `MOVE_TASK` or `REORDER_TASK` depending on source vs target column

No third-party drag libraries (react-dnd, dnd-kit, etc.) are used.

### 4.2 Mock Real-Time Sync

A module-level object (`mockServer`) maintains the canonical board state outside React. A `useEffect` in the root component sets up a `setInterval` (500ms tick):

- Each tick reads pending changes from `mockServer.outbox`
- A second `setTimeout`-based loop simulates a remote user occasionally moving random tasks
- Conflict detection occurs when two ops target the same task within a 2s window

No socket.io or WebSocket connections are established.

### 4.3 Conflict Resolution

When the mock server detects concurrent moves on the same task:
1. It applies "last-write-wins" to the canonical state.
2. It emits a `MARK_CONFLICT` event to the local user whose op arrived second.
3. The `ConflictBanner` displays which user moved the task and where.

### 4.4 CSS Modules Styling

All visual styling is done via CSS Modules (`.module.css` file import). Key class names: `.board`, `.column`, `.columnHeader`, `.card`, `.cardDragging`, `.dropIndicator`, `.conflictBanner`. No Tailwind, no inline style objects.

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|-----------|----------------|
| **[L]TS** | Full TypeScript with explicit interfaces |
| **[F]React** | React function components with hooks |
| **[Y]CSS_MODULES** | All styles from `.module.css` imports |
| **[!Y]NO_TW** | No Tailwind or utility-first CSS |
| **[!D]NO_DND_LIB** | Pure HTML5 drag events, no libraries |
| **[DRAG]HTML5** | `draggable`, `onDragStart/Over/Drop` |
| **[STATE]useReducer** | Single reducer, no external state libs |
| **[O]SFC** | All code in one `.tsx` file |
| **[EXP]DEFAULT** | `export default TodoBoardApp` |
| **[WS]MOCK** | `setInterval` + `setTimeout` mock server |
| **[!D]NO_SOCKETIO** | No socket.io or WS library imports |

## Constraint Checklist

1. [TS] Use TypeScript for the entire file with typed interfaces for Task, BoardState, and all action payloads.
2. [REACT] Build all UI as React function components using hooks.
3. [CSS_MOD] Import a `.module.css` file and apply all styles through CSS Modules class names — no inline style objects.
4. [NO_TW] Do not install or reference Tailwind CSS or any utility-first CSS framework.
5. [NO_DND] Do not import react-dnd, dnd-kit, @hello-pangea/dnd, or any drag-and-drop library.
6. [HTML5_DRAG] Implement all drag-and-drop via native HTML5 API: `draggable`, `onDragStart`, `onDragOver`, `onDrop`.
7. [REDUCER] Use a single `useReducer` for all state; do not use Redux, Zustand, Jotai, or Context-based state libs.
8. [SFC] Deliver everything in one `.tsx` file; define all sub-components in the same file.
9. [DEFAULT_EXPORT] The root component must be exported as `export default`.
10. [MOCK_WS] Simulate real-time sync with `setTimeout`/`setInterval` and a module-level mock server object.
11. [NO_SOCKETIO] Do not import or use socket.io, ws, or any WebSocket library.
