# Technical Design: Real-Time Collaborative Todo Board

## 1. Component Architecture

### Component Hierarchy

- **App** (root, default export) — top-level container; holds `useReducer` state; renders the board grid
  - **BoardTitle** — static title bar showing "Collaborative Todo Board" and online user list
  - **Column** (×3: Todo / In Progress / Done) — vertical drop zone rendering an ordered list of task cards
    - **TaskCard** — draggable unit displaying task text, badge, and conflict warning
  - **CreateTaskInput** — text field that dispatches `ADD_TASK` on Enter
  - **ConflictPopup** — ephemeral popup when two users concurrently move the same card

All components are function components co-located in one `.tsx` file.

## 2. Data Model

### Interfaces

**Task**
- `id: string`
- `text: string`
- `column: 'todo' | 'inProgress' | 'done'`
- `sortIndex: number`
- `lastActor: string`
- `rev: number`

**BoardState**
- `taskMap: Record<string, Task>`
- `columnLists: Record<ColumnId, string[]>`
- `userId: string`
- `peerIds: string[]`
- `inflightOps: OpRecord[]`
- `conflictQueue: ConflictEvent[]`

**OpRecord**
- `id: string`, `action: string`, `taskId: string`, `timestamp: number`

**ConflictEvent**
- `taskId: string`, `rivalUser: string`, `detail: string`

## 3. State Management

A single `useReducer(reducer, defaultState)` at the root manages the entire application. No Redux, Zustand, Jotai, or other external state library.

**Reducer actions:**

| Action | Purpose |
|--------|---------|
| `ADD_TASK` | Insert task at top of Todo |
| `MOVE_TASK` | Cross-column drag result |
| `REORDER` | Same-column position change |
| `INGEST_REMOTE` | Apply mock-server update |
| `RAISE_CONFLICT` | Flag concurrent modification |
| `CLEAR_CONFLICT` | Dismiss popup |
| `CONFIRM` | Server ack |
| `REJECT` | Server nack → rollback |

### Optimistic Pattern

Local drops are applied immediately in the reducer and tracked as `OpRecord`. The mock server asynchronously confirms or rejects. Rejection triggers a full-state recalculation excluding the failed op.

## 4. Key Implementation Approaches

### 4.1 HTML5 Drag and Drop

Each `TaskCard` has `draggable="true"`.

- `onDragStart` — writes task id to `dataTransfer`, toggles CSS Module class for opacity
- `onDragEnd` — cleans up

Each `Column` implements:
- `onDragOver` — `preventDefault()`, calculates insertion point using child bounding rects
- `onDrop` — reads id, dispatches appropriate action

No react-dnd, dnd-kit, @hello-pangea/dnd, or any DnD library.

### 4.2 CSS Modules

All visual styling uses CSS Modules (`.module.css` imported as `styles` object). Classes include `.board`, `.column`, `.card`, `.cardActive`, `.dropHighlight`, `.popup`. No Tailwind CSS or utility-first framework.

### 4.3 Mock Real-Time Sync

A module-level `MockServer` object holds canonical state and an event queue:
- A `setInterval` (500ms) in a `useEffect` polls for remote updates
- `setTimeout` simulates a second user performing random moves
- Conflict detection: two ops on the same task within 2s window triggers a conflict event

No socket.io, no `WebSocket`, no networking library.

### 4.4 Conflict Hints

The `ConflictPopup` reads from `conflictQueue`. It shows the task name, the competing user, and the resolution outcome. Auto-dismisses or manual close.

## 5. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | TypeScript + React | Full TS with interfaces; React FC with hooks |
| 2 | CSS Modules, no Tailwind | `.module.css` import; zero utility classes |
| 3 | HTML5 DnD, no DnD library | Native drag API only |
| 4 | `useReducer`, no state libs | Single reducer at root |
| 5 | Single `.tsx`, default export | One file, `export default App` |
| 6 | Mock sync, no socket.io | `setInterval`/`setTimeout` mock |

## Constraint Checklist

1. [LANG] Use TypeScript for all source code with explicit type interfaces for data models and actions.
2. [FRAMEWORK] Build the UI with React function components and hooks exclusively.
3. [STYLE] Import a CSS Modules file and use its class names for all styling; never use inline style objects.
4. [NO_TAILWIND] Do not install, import, or reference Tailwind CSS or any utility-first CSS framework.
5. [NO_DND_LIB] Do not import react-dnd, dnd-kit, @hello-pangea/dnd, or any third-party drag-and-drop library.
6. [DRAG] Implement drag-and-drop using only the native HTML5 API: draggable attribute, onDragStart, onDragOver, onDrop.
7. [STATE] Manage all state through a single useReducer hook; do not use Redux, Zustand, Jotai, or Context-based stores.
8. [SINGLE_FILE] Place all components, types, and logic in one .tsx file.
9. [EXPORT] The root component must be the file's default export.
10. [MOCK_SYNC] Simulate real-time collaboration using setTimeout/setInterval with a module-level mock server.
11. [NO_SOCKET] Do not use socket.io, the native WebSocket constructor, or any WebSocket library.
