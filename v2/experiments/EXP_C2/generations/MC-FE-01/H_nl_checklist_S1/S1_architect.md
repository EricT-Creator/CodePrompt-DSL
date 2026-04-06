# Technical Design: Real-Time Collaborative Todo Board

## 1. Component Architecture

### Component Hierarchy

- **TodoBoard** (root, default export) — houses the `useReducer` and orchestrates the three-column layout
  - **Header** — board title and a list of connected usernames
  - **Column** (rendered three times: Todo, In Progress, Done) — each column is a vertical drop zone containing an ordered list of cards
    - **Card** — a draggable task card showing description, owner, and an optional conflict icon
  - **NewTaskInput** — text input at the top of the Todo column that dispatches an `ADD_TASK` action
  - **ConflictNotification** — a brief overlay that appears when two users act on the same card simultaneously

All of these are defined as function components within a single `.tsx` file.

## 2. Data Model

### TypeScript Interfaces

**Task**
- `id: string` — UUID generated client-side
- `text: string`
- `column: 'todo' | 'inProgress' | 'done'`
- `order: number`
- `lastEditor: string` — user id
- `version: number` — conflict-detection counter

**AppState**
- `tasks: Record<string, Task>`
- `columns: Record<ColumnKey, string[]>` — per-column ordered task-id arrays
- `userId: string`
- `peers: string[]`
- `pendingOps: LocalOp[]`
- `activeConflicts: Conflict[]`

**LocalOp**
- `id: string`, `kind: 'add' | 'move' | 'reorder'`, `taskId: string`, `ts: number`

**Conflict**
- `taskId: string`, `otherUser: string`, `description: string`

## 3. State Management

All mutable application state is managed through a single `useReducer(reducer, initState)` at the root component.

**Action catalogue:**

| Action | Purpose |
|--------|---------|
| `ADD_TASK` | Create task in Todo column |
| `MOVE_TASK` | Cross-column drag-and-drop |
| `REORDER` | Same-column position change |
| `REMOTE_CHANGE` | Ingest update from mock server |
| `CONFLICT` | Flag concurrent modification |
| `CLEAR_CONFLICT` | User dismisses the notification |
| `ACK` | Server confirms local op |
| `NACK` | Server rejects; triggers rollback |

No Redux, Zustand, Jotai, or any external state management library.

### Optimistic Updates

When a user drops a card, the reducer applies the move instantly and records a `LocalOp`. The mock server processes ops with a simulated 300–800ms latency. If two ops collide on the same task, the server sends `NACK` to the later client, whose reducer replays state without that op to rollback.

## 4. Key Implementation Approaches

### 4.1 Native HTML5 Drag-and-Drop

Every `Card` element sets `draggable="true"`.

- **onDragStart**: stores the card's `taskId` and source column via `dataTransfer.setData`. A CSS Modules class `.dragging` is toggled for visual feedback.
- **onDragOver** (on Column and sibling Cards): `preventDefault()` to allow drop. The insertion index is determined by measuring each card's bounding rect midpoint against the cursor Y position.
- **onDrop**: reads the dragged task id from `dataTransfer`, dispatches `MOVE_TASK` (cross-column) or `REORDER` (same column).
- **onDragEnd**: resets the dragging class.

No drag-and-drop library is used.

### 4.2 Mock Real-Time Synchronization

A module-scope object (`mockBackend`) holds the authoritative board state and an outbox queue.

- `useEffect` in the root component creates a `setInterval` (every 500ms) that polls `mockBackend.flush()` for remote changes, dispatching `REMOTE_CHANGE` for each.
- The backend object uses `setTimeout` with random delays to simulate a second user performing occasional moves.
- When two ops target the same task within a 2-second window, the backend pushes a conflict event.

No socket.io, no WebSocket API, no external networking library.

### 4.3 Conflict Hints

The `ConflictNotification` component reads `activeConflicts` from state. Each hint shows the contested task's title and which remote user also moved it. After 5 seconds or on click, a `CLEAR_CONFLICT` action dismisses it.

### 4.4 Styling with CSS Modules

A companion `.module.css` file is imported as `styles`. Every DOM element references `styles.xxx` class names. Key classes: `.board`, `.column`, `.columnTitle`, `.card`, `.cardDragging`, `.dropZone`, `.notification`. No utility-first CSS framework is involved.

## 5. Constraint Acknowledgment

| Constraint | Addressed By |
|-----------|-------------|
| **[L]TS** | Full TypeScript with interfaces for Task, AppState, actions |
| **[F]React** | Function components, hooks |
| **[Y]CSS_MODULES** | `.module.css` import, `styles.className` usage |
| **[!Y]NO_TW** | No Tailwind anywhere |
| **[!D]NO_DND_LIB** | No react-dnd / dnd-kit / similar |
| **[DRAG]HTML5** | Native `draggable`, `onDragStart/Over/Drop` |
| **[STATE]useReducer** | Single `useReducer`, no external state lib |
| **[O]SFC** | One `.tsx` file |
| **[EXP]DEFAULT** | `export default TodoBoard` |
| **[WS]MOCK** | `setInterval` + `setTimeout` mock server |
| **[!D]NO_SOCKETIO** | No socket.io or WS library |

## Constraint Checklist

1. The entire application must be written in TypeScript, with explicit type annotations for all data structures and action types.
2. All user interface elements must be built as React function components using standard React hooks.
3. Every visual style must come from an imported CSS Modules file; no inline style objects or style attributes are permitted.
4. Tailwind CSS and any other utility-first CSS framework must not be installed or referenced.
5. No third-party drag-and-drop library such as react-dnd, dnd-kit, or hello-pangea/dnd may be imported; all drag behavior must use the browser's native HTML5 Drag and Drop API.
6. The drag-and-drop implementation must use draggable attributes and the onDragStart, onDragOver, and onDrop event handlers provided by the HTML5 specification.
7. All application state must be managed through a single useReducer hook at the root component, with no Redux, Zustand, Jotai, or other state management library.
8. The complete application must be delivered in one single tsx file containing all component definitions.
9. The root component must be the file's default export.
10. Real-time synchronization must be simulated using setTimeout and setInterval with an in-memory mock server object, not actual network connections.
11. Socket.io, the native WebSocket constructor, and any other WebSocket or networking library must not be imported or used.
