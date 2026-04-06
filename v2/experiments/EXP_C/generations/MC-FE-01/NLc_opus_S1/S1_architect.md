# Technical Design Document — Real-Time Collaborative Todo Board

## 1. Overview

A browser-based collaborative Kanban board where multiple users manipulate tasks across three columns (Todo / In Progress / Done) in real time. The system uses optimistic updates with conflict resolution hints for concurrent edits.

## 2. Component Architecture

### 2.1 Top-Level: `App`
- Owns the WebSocket connection lifecycle.
- Holds the global `useReducer` store.
- Passes dispatch and state slices to children.

### 2.2 `Board`
- Renders three `Column` components.
- Listens for drag events to determine source/target columns and reorder indices.

### 2.3 `Column`
- Receives a column ID and its task list.
- Renders `TaskCard` items.
- Implements HTML5 native `dragover` / `drop` handlers to accept incoming cards and compute insertion index.

### 2.4 `TaskCard`
- Displays a single task's title and status badge.
- Sets `draggable="true"` and fires `dragstart` with its task ID encoded in `dataTransfer`.
- Shows a conflict indicator (pulsing border) when the server reports a concurrent move on this card.

### 2.5 `ConflictBanner`
- Appears at the top of the board when any optimistic update is rejected.
- Displays a short message identifying which task conflicted and offers a "Refresh" action.

### 2.6 `NewTaskInput`
- A simple text input + button that dispatches `ADD_TASK` and sends the corresponding WS message.

## 3. Data Model

### Interfaces

- **Task**: `{ id: string; title: string; column: 'todo' | 'inprogress' | 'done'; order: number; version: number }`
- **BoardState**: `{ tasks: Task[]; userId: string; conflicts: ConflictInfo[]; connected: boolean }`
- **ConflictInfo**: `{ taskId: string; localColumn: string; remoteColumn: string; timestamp: number }`
- **WSMessage**: `{ type: string; payload: Record<string, unknown>; senderId: string; version?: number }`

The `version` field on each task enables optimistic concurrency control: the server rejects moves whose version is stale.

## 4. State Management Approach

A single `useReducer` manages the entire board state. Action types:

| Action | Effect |
|--------|--------|
| `INIT_BOARD` | Replace full state from server snapshot |
| `ADD_TASK` | Append task to the Todo column |
| `MOVE_TASK` | Relocate task to target column/index, bump local version |
| `REORDER` | Change order within the same column |
| `REMOTE_UPDATE` | Apply an incoming remote change |
| `CONFLICT` | Push a `ConflictInfo` entry; mark affected task |
| `RESOLVE_CONFLICT` | Clear conflict state for a task |
| `SET_CONNECTED` | Toggle connection flag |

### Optimistic Update Flow

1. User drags a card → dispatch `MOVE_TASK` immediately (UI updates).
2. Send the move message via WS, including the task's current `version`.
3. Server validates version; if accepted, broadcasts to all clients (including sender) with incremented version.
4. If rejected (stale version), server sends a `CONFLICT` message → reducer rolls the task back to the server-authoritative position and pushes a `ConflictInfo`.

## 5. Key Implementation Approaches

### 5.1 HTML5 Native Drag-and-Drop

- `dragstart`: set `dataTransfer.setData('text/plain', taskId)` and `effectAllowed = 'move'`.
- `dragover`: call `preventDefault()` to allow drop; use `event.clientY` relative to sibling card rects to compute the insertion index.
- `drop`: read `taskId` from `dataTransfer`, dispatch `MOVE_TASK` with `{ taskId, targetColumn, targetIndex }`.
- No ghost image customization beyond the browser default — keeps complexity low.

### 5.2 Hand-Written WebSocket Mock

A `MockWSServer` class created inside a `useEffect`:

- Maintains an internal task list (source of truth) and a `Set<MessagePort>` for connected clients.
- Each "client" communicates via `BroadcastChannel` or a simple callback queue.
- On receiving a `MOVE_TASK`, checks version; if valid, updates its list, broadcasts `REMOTE_UPDATE` to all *other* clients; if stale, sends `CONFLICT` back to the sender.
- A `setTimeout`-based heartbeat simulates latency (~200 ms) to make conflicts observable.
- A secondary browser tab (or a second `useReducer` instance rendered side-by-side) simulates the second user for demonstration purposes.

### 5.3 Conflict Resolution Hints

- Conflict detection is version-based: each task carries a monotonically increasing `version`.
- When two users move the same task simultaneously, the first-to-arrive wins; the second receives a `CONFLICT` response.
- The losing client's reducer reverts that task to the server's position and surfaces a `ConflictBanner`.
- The user can dismiss the banner or click "Refresh" to re-fetch the full board snapshot.

### 5.4 CSS Modules Styling

- Each component imports its own `.module.css` file.
- Column backgrounds use subtle color coding (e.g., pastel blue, yellow, green).
- Drag-over feedback: a CSS class `.dropTarget` adds a dashed border.
- Conflict indicator: a `@keyframes pulse` animation on the task card border.

## 6. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **TS + React** | All components are React functional components with TypeScript. Interfaces defined in §3. |
| 2 | **CSS Modules only, no Tailwind** | Every component uses co-located `.module.css` files; no utility-class framework is referenced. |
| 3 | **HTML5 native drag, no dnd libs** | Drag interactions rely solely on `dragstart`, `dragover`, `drop`, and `dragend` events from the HTML Drag and Drop API. No `react-dnd`, `dnd-kit`, or similar. |
| 4 | **useReducer only, no state libs** | A single `useReducer` at the `App` level is the sole state container. No Redux, Zustand, Jotai, or other libraries. |
| 5 | **Single file, export default** | The entire application — components, reducer, types, WS mock — is co-located in one `.tsx` file with a single `export default App`. CSS Modules are the only separate file. |
| 6 | **Hand-written WS mock, no socket.io** | WebSocket behavior is simulated by a custom `MockWSServer` class using callbacks/timers within the same file. No `socket.io-client` or native `WebSocket` to an external server. |
