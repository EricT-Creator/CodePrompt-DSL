# Technical Design Document — Real-Time Collaborative Todo Board

## 1. Overview

This document describes the architecture for a real-time collaborative todo board where multiple users can create, move, and reorder tasks across three columns (Todo / In Progress / Done) using drag-and-drop. The system supports optimistic updates and provides conflict resolution hints when two users attempt to move the same task simultaneously.

## 2. Component Architecture

### 2.1 Component Tree

- **CollaborativeTodoBoard** (root): Owns all state via `useReducer`. Manages simulated real-time sync. Renders the header, user indicator, and three columns.
  - **BoardHeader**: Displays board title, connected user count, and a "new task" input.
  - **Column** (×3): Represents one of the three swim lanes. Receives tasks filtered by column status. Handles drag-over and drop events.
    - **TaskCard** (×N): Renders an individual task. Initiates drag via native HTML5 drag start. Shows conflict indicator when applicable.
  - **ConflictToast**: Displays transient conflict resolution hints when the simulated remote user moves the same task the local user is dragging.

### 2.2 Responsibilities

| Component | Responsibility |
|-----------|---------------|
| CollaborativeTodoBoard | State container, sync orchestration, dispatch hub |
| BoardHeader | Task creation input, user presence display |
| Column | Drop zone logic, column-level filtering |
| TaskCard | Drag initiation, visual feedback during drag |
| ConflictToast | Conflict notification rendering and auto-dismiss |

## 3. Data Model

### 3.1 Core Interfaces

- **Task**: `{ id: string; title: string; column: 'todo' | 'inProgress' | 'done'; order: number; version: number; lastMovedBy: string }`
- **User**: `{ id: string; name: string; color: string }`
- **BoardState**: `{ tasks: Task[]; users: User[]; localUserId: string; dragState: DragState | null; conflicts: ConflictInfo[]; pendingOptimistic: OptimisticOp[] }`
- **DragState**: `{ taskId: string; sourceColumn: string; overColumn: string | null; overIndex: number | null }`
- **ConflictInfo**: `{ taskId: string; localMove: MoveOp; remoteMove: MoveOp; timestamp: number }`
- **OptimisticOp**: `{ opId: string; type: 'move' | 'create'; payload: any; timestamp: number; confirmed: boolean }`

### 3.2 Versioning

Each task carries a `version` counter. When two operations target the same task and the version at the time of the local operation no longer matches the server version, a conflict is raised.

## 4. State Management Approach

All state is managed through a single `useReducer` hook at the root component.

### 4.1 Actions

- `CREATE_TASK` — adds a new task to the "todo" column with an optimistic ID.
- `MOVE_TASK` — relocates a task to a different column and/or position. Applied optimistically.
- `REORDER_TASK` — changes task position within the same column.
- `SET_DRAG_STATE` — updates the current drag target for visual feedback.
- `CLEAR_DRAG_STATE` — resets drag state on drop or cancel.
- `REMOTE_UPDATE` — incoming simulated remote change; reconciles with local optimistic ops.
- `CONFIRM_OP` — marks an optimistic operation as server-confirmed.
- `RAISE_CONFLICT` — adds a conflict entry when the remote update conflicts with a pending local op.
- `DISMISS_CONFLICT` — removes a conflict notification after timeout or user action.
- `SYNC_USERS` — updates the connected user list from the simulated server.

### 4.2 Reducer Logic

The reducer handles optimistic writes by maintaining a `pendingOptimistic` queue. When `REMOTE_UPDATE` arrives, it checks whether any pending ops conflict with the incoming change. If the same task was moved by both the local and remote user (detected by comparing `taskId` and `version`), a `RAISE_CONFLICT` side-effect is triggered.

## 5. Key Implementation Approaches

### 5.1 Drag-and-Drop (Native HTML5 API)

- **TaskCard** sets `draggable="true"` and attaches `onDragStart`, which stores the task ID and source column in `event.dataTransfer.setData()`.
- **Column** attaches `onDragOver` (calls `e.preventDefault()` to allow drop and dispatches `SET_DRAG_STATE` with hover index calculated from mouse Y position relative to task card bounding rects) and `onDrop` (reads data from `dataTransfer`, dispatches `MOVE_TASK` or `REORDER_TASK`).
- **Visual feedback**: The dragged card receives a CSS Modules class for reduced opacity. The drop target column receives a highlighted border class. An insertion line indicator appears between cards based on `overIndex`.
- `onDragEnd` dispatches `CLEAR_DRAG_STATE` regardless of whether the drop succeeded.

### 5.2 Real-Time Sync Simulation

A `useEffect` at the root component sets up a `setInterval` (every 2–4 seconds) that simulates a remote user performing random actions:
- Creating a new task (20% probability)
- Moving an existing task to a different column (60% probability)
- Reordering within a column (20% probability)

Each simulated action dispatches `REMOTE_UPDATE` to the reducer. A secondary `setTimeout` (500ms delay) simulates network latency for confirming local optimistic operations by dispatching `CONFIRM_OP`.

### 5.3 Optimistic Updates and Conflict Resolution

1. On local `MOVE_TASK`, the UI updates immediately and pushes the operation to `pendingOptimistic`.
2. When `REMOTE_UPDATE` arrives for the same task while a local op is pending, the reducer compares version numbers.
3. If versions diverge, a `ConflictInfo` is added. The ConflictToast displays: "User X also moved this task to [column]. Your change was applied. Click to revert."
4. Conflicts auto-dismiss after 5 seconds via a `setTimeout` in a `useEffect`.

### 5.4 Styling (CSS Modules)

All styles are defined in a CSS Module object created via a `<style>` tag injected within the single `.tsx` file, or alternatively as an object-map with class names applied via `className`. Since the constraint requires a single `.tsx` file, styles are defined as template-literal CSS injected into a `<style>` element rendered within the component, with unique class name prefixes to simulate CSS Modules scoping.

## 6. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | TypeScript with React | All components are typed React functional components. Interfaces are defined for Task, User, BoardState, DragState, ConflictInfo, and OptimisticOp. |
| 2 | CSS Modules for styling, no Tailwind | Styles use CSS Modules scoping. Since delivery is a single .tsx file, a `<style>` tag with unique prefixed class names is injected. No Tailwind classes appear anywhere. |
| 3 | Native HTML5 Drag and Drop API only, no dnd libraries | Drag-and-drop uses `draggable`, `onDragStart`, `onDragOver`, `onDrop`, `onDragEnd`, and `dataTransfer`. No external drag library is imported. |
| 4 | useReducer for all state, no Redux/Zustand/Jotai | A single `useReducer` at the root manages board state, drag state, optimistic ops, and conflicts. No external state library is used. |
| 5 | Single .tsx file with export default | The entire application — components, reducer, interfaces, styles — is contained in one file exported as `export default CollaborativeTodoBoard`. |
| 6 | Simulated real-time sync with setTimeout/setInterval, no socket.io | Real-time behavior is simulated via `setInterval` for remote actions and `setTimeout` for network latency. No WebSocket or socket library is used. |
