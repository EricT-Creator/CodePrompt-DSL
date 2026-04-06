# Technical Design: Real-Time Collaborative Todo Board

## 1. Component Architecture

### Overview

The application is a single-page React board with three Kanban-style columns. All components are function components defined within one `.tsx` file.

### Component Tree

- **CollaborativeBoard** (root, default export) — manages all state via `useReducer`; renders the grid layout
  - **ColumnHeader** — displays column title and task count
  - **Column** (×3) — each column wraps an ordered list of cards and acts as a drop target
    - **TaskCard** — draggable card showing task text, creator name, and optional conflict indicator
  - **AddTaskForm** — inline input at the top of the Todo column
  - **ConflictAlert** — floating notification when concurrent edits collide

### Single-File Constraint

All component definitions, reducer logic, type declarations, and the mock sync layer reside in one `.tsx` file, exported via `export default`.

## 2. Data Model

### TypeScript Interfaces

**Task**
- `id: string` — UUID
- `text: string`
- `column: 'todo' | 'inProgress' | 'done'`
- `position: number` — ordering index within column
- `movedBy: string` — user id of last mover
- `version: number` — monotonic counter for conflict detection

**State**
- `tasks: Record<string, Task>`
- `columns: { todo: string[]; inProgress: string[]; done: string[] }` — ordered task ids
- `me: string` — current user identifier
- `onlineUsers: string[]`
- `pendingOps: PendingOperation[]`
- `conflicts: ConflictRecord[]`

**PendingOperation**
- `opId: string`
- `kind: 'add' | 'move' | 'reorder'`
- `taskId: string`
- `createdAt: number`

**ConflictRecord**
- `taskId: string`
- `otherUser: string`
- `message: string`

## 3. State Management

All state lives in a single `useReducer(boardReducer, initialState)` call at the root component. No Redux, Zustand, Jotai, or any other state management library is used.

### Action Types

| Action | Description |
|--------|-------------|
| `CREATE_TASK` | Add new task to Todo |
| `MOVE_TASK` | Drag across columns |
| `REORDER_TASK` | Drag within same column |
| `RECEIVE_REMOTE` | Process mock server update |
| `FLAG_CONFLICT` | Mark two concurrent ops on same task |
| `DISMISS_CONFLICT` | User clears conflict alert |
| `OP_CONFIRMED` | Server acknowledges local op |
| `OP_REJECTED` | Server rejects; rollback required |
| `UPDATE_PEERS` | Refresh connected user list |

### Optimistic Updates

When a user drops a card:
1. The reducer applies the change immediately (optimistic).
2. A `PendingOperation` is pushed into state.
3. The mock server processes it after a simulated delay.
4. On confirmation (`OP_CONFIRMED`), the pending entry is removed.
5. On rejection (`OP_REJECTED`), the reducer replays the state without that op.

## 4. Key Implementation Approaches

### 4.1 Drag and Drop — HTML5 Native API

**Why native:** The constraints require using the native HTML5 Drag and Drop API exclusively. No react-dnd, dnd-kit, @hello-pangea/dnd, or any other DnD library.

**Implementation approach:**

Each `TaskCard` receives `draggable="true"`:
- `onDragStart` — stores `taskId` and source column via `dataTransfer.setData()`; adds a visual class via CSS Modules
- `onDragEnd` — removes dragging styles

Each `Column` is a drop target:
- `onDragOver` — `preventDefault()` to allow dropping; calculates insertion index from cursor Y vs. child bounding rects
- `onDrop` — reads task id from `dataTransfer`, dispatches `MOVE_TASK` or `REORDER_TASK`

Insertion index computation: iterate over rendered card DOM elements, find the first card whose vertical midpoint is below the cursor Y.

### 4.2 CSS Modules Styling

All styles are authored in a `.module.css` file and imported as a `styles` object. Every element uses `className={styles.xxx}`. No Tailwind CSS or utility-first framework is used.

Key classes:
- `.board` — three-column flex layout
- `.column` — vertical flex container with min-height
- `.card` — border, padding, hover effect
- `.cardDragging` — reduced opacity during drag
- `.dropIndicator` — highlighted border on drag-over
- `.conflictAlert` — fixed-position toast

### 4.3 Mock WebSocket Sync

A module-level object (`fakeServer`) serves as the simulated backend:
- Maintains canonical state and an event outbox
- `useEffect` sets up a `setInterval` (every 500ms) that calls `fakeServer.poll()` to fetch remote events
- Simulates a second user's random actions via `setTimeout` with 1–3 second delays
- Detects conflicts when two ops target the same task within 2 seconds

No socket.io, no `new WebSocket()`, no external networking library.

### 4.4 Conflict Resolution Hints

When the fake server detects two concurrent moves on the same task:
1. It resolves via last-write-wins internally.
2. It pushes a `FLAG_CONFLICT` event to the losing client.
3. The `ConflictAlert` component displays the task name and which remote user also moved it.
4. The alert auto-dismisses after 5 seconds or on user click.

## 5. Constraint Acknowledgment

| # | Constraint | How Addressed |
|---|-----------|---------------|
| 1 | TypeScript with React | All code in TypeScript; all components are React function components |
| 2 | CSS Modules, no Tailwind | `.module.css` import for all styles; zero Tailwind references |
| 3 | HTML5 DnD only, no DnD libs | Native `draggable` + drag event handlers; no library imports |
| 4 | `useReducer` only, no state libs | Single `useReducer` at root; no Redux/Zustand/Jotai |
| 5 | Single `.tsx` file, default export | All components and logic in one file; `export default` |
| 6 | Mock sync, no socket.io | `setTimeout`/`setInterval` with module-level mock; no socket.io or WS library |
