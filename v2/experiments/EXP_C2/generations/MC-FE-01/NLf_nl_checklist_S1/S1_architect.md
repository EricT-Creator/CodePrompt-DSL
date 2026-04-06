# Technical Design: Real-Time Collaborative Todo Board

## 1. Component Architecture

### Component Overview

The application is a Kanban-style board rendered entirely within one `.tsx` file. All components are React function components.

- **KanbanBoard** (root, default export) — owns the `useReducer` store; lays out three columns side by side
  - **ColumnPanel** (×3: Todo / In Progress / Done) — a vertical drop zone with an ordered card list
    - **TaskItem** — a draggable card displaying the task's text, owner, and conflict warning
  - **TaskForm** — simple text input that creates new tasks via `ADD_TASK` dispatch
  - **ConflictToast** — overlay shown when another user simultaneously touches the same card

## 2. Data Model

### TypeScript Interfaces

**Task**
- `id: string` — UUID
- `text: string` — task description
- `column: 'todo' | 'inProgress' | 'done'`
- `rank: number` — position within column
- `editor: string` — last user to modify
- `version: number` — optimistic-concurrency counter

**Store**
- `tasks: Record<string, Task>`
- `lists: Record<ColumnKey, string[]>` — per-column ordered id arrays
- `myId: string`
- `activePeers: string[]`
- `pendingWrites: WriteOp[]`
- `conflictMessages: ConflictMsg[]`

**WriteOp**
- `wid: string`, `type: 'add' | 'move' | 'reorder'`, `taskId: string`, `ts: number`

**ConflictMsg**
- `taskId: string`, `otherUser: string`, `info: string`

## 3. State Management

The entire board state is managed by a single `useReducer(reducer, init)` in the root component. No Redux, Zustand, Jotai, or any external state library.

### Actions

| Action | Trigger |
|--------|---------|
| `ADD_TASK` | TaskForm submit |
| `MOVE_TASK` | Cross-column drop |
| `REORDER` | Same-column drop |
| `REMOTE_EVENT` | Mock server pushes a change |
| `SHOW_CONFLICT` | Concurrent edits detected |
| `HIDE_CONFLICT` | User dismisses toast |
| `WRITE_OK` | Server confirms local write |
| `WRITE_FAIL` | Server rejects; rollback |

### Optimistic Flow

On drop, the reducer applies the move immediately and logs a `WriteOp`. The mock backend confirms/rejects after a delay. On failure, the reducer reconstructs state by replaying all writes minus the rejected one.

## 4. Key Implementation Approaches

### 4.1 HTML5 Native Drag-and-Drop

Each `TaskItem` sets `draggable="true"`:
- `onDragStart` — writes task id into `dataTransfer`, toggles a CSS Modules `.dragging` class
- `onDragEnd` — reverts styles

Each `ColumnPanel`:
- `onDragOver` — calls `e.preventDefault()`; computes insertion index from cursor Y vs. card bounding rects
- `onDrop` — reads `dataTransfer`, dispatches `MOVE_TASK` or `REORDER`

No react-dnd, dnd-kit, @hello-pangea/dnd, or any DnD library is imported.

### 4.2 CSS Modules

A `.module.css` file is imported as `styles`. All DOM elements use `className={styles.xxx}`. No Tailwind CSS or utility-first framework. Key classes: `.kanban`, `.panel`, `.card`, `.dragging`, `.dropTarget`, `.toast`.

### 4.3 Mock Real-Time Sync

A module-level `SimServer` object acts as the canonical backend:
- `useEffect` creates a `setInterval` (500ms) polling `SimServer.getEvents()`
- `setTimeout` with random delays simulates a remote user moving tasks
- Conflict detection: two ops on the same task within a 2s window

No socket.io, no `new WebSocket()`, no networking library.

### 4.4 Conflict Resolution

On conflict detection, the backend pushes a `SHOW_CONFLICT` event. The `ConflictToast` component shows task name, competing user, and resolution. Dismisses after 5s or on click.

## 5. Constraint Acknowledgment

| # | Constraint | How Addressed |
|---|-----------|---------------|
| 1 | TypeScript + React | Full TS with typed interfaces and function components |
| 2 | CSS Modules, no Tailwind | `.module.css` import, `styles.xxx` usage |
| 3 | HTML5 DnD, no library | Native `draggable` + drag event handlers |
| 4 | `useReducer`, no state libs | Single reducer at root |
| 5 | Single `.tsx`, default export | One file, `export default KanbanBoard` |
| 6 | Mock sync, no socket.io | `setInterval`/`setTimeout` mock server object |

## Constraint Checklist

1. All source code must be written in TypeScript with explicit type annotations for every interface, state shape, and action type.
2. The user interface must be composed entirely of React function components using hooks such as useReducer, useEffect, and useCallback.
3. All visual styling must be applied through CSS Modules by importing a .module.css file; inline style objects and style attributes are not permitted.
4. Tailwind CSS and any utility-first CSS framework must not be present in the project in any form.
5. No third-party drag-and-drop library including react-dnd, dnd-kit, and hello-pangea/dnd may be used; all drag behavior must rely solely on the native HTML5 Drag and Drop API.
6. Drag-and-drop must be implemented using the draggable attribute together with onDragStart, onDragOver, and onDrop event handlers.
7. Application state must be managed exclusively by a single useReducer call at the root component, without any external state management library such as Redux, Zustand, or Jotai.
8. The entire application including all components, types, and utilities must be contained in a single .tsx file.
9. The main component must be exported using export default so it can be directly imported.
10. Real-time collaboration must be simulated with setTimeout and setInterval operating on an in-memory mock server object rather than actual network connections.
11. The socket.io library, the native WebSocket constructor, and any other WebSocket or real-time communication library must not be imported or used.
