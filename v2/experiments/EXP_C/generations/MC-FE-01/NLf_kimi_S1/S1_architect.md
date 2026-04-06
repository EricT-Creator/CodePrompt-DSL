# MC-FE-01: Real-time Collaborative Todo Board - Technical Design

## Overview

This document outlines the technical design for a real-time collaborative todo board supporting drag-and-drop task management across three columns (Todo / In Progress / Done) with optimistic updates and conflict resolution hints.

## 1. Component Architecture

### Main Component Structure

```
TodoBoard (Main Container)
├── BoardHeader (Title, sync status indicator)
├── ColumnsContainer (Horizontal layout for 3 columns)
│   ├── Column (Todo)
│   │   ├── ColumnHeader (Title + task count)
│   │   └── TaskList (Droppable area)
│   │       └── TaskCard (Draggable items)
│   ├── Column (In Progress)
│   │   └── [Same structure]
│   └── Column (Done)
│       └── [Same structure]
├── NewTaskButton (Floating action button)
└── ConflictToast (Notification for simultaneous edits)
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `TodoBoard` | State management via useReducer, event coordination, sync simulation |
| `Column` | Droppable target, column-specific styling, task list rendering |
| `TaskCard` | Draggable source, drag event handlers, task display |
| `BoardHeader` | Title display, connection status, last sync timestamp |
| `ConflictToast` | Temporary notification when conflict detected |

## 2. Data Model

### TypeScript Interfaces

```typescript
interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'done';
  createdAt: number;
  updatedAt: number;
  version: number; // For conflict detection
  lastModifiedBy: string;
}

interface ColumnData {
  id: 'todo' | 'in-progress' | 'done';
  title: string;
  tasks: Task[];
}

interface BoardState {
  columns: ColumnData[];
  isSyncing: boolean;
  lastSyncAt: number | null;
  conflicts: Conflict[];
}

interface Conflict {
  taskId: string;
  localChange: Task;
  remoteChange: Task;
  detectedAt: number;
}

// Drag and Drop Types
interface DragItem {
  task: Task;
  sourceColumnId: string;
  sourceIndex: number;
}
```

## 3. State Management Approach

### useReducer Design

**State Shape:**
```typescript
type BoardState = {
  columns: ColumnData[];
  dragState: {
    isDragging: boolean;
    draggedItem: DragItem | null;
  };
  syncState: {
    isSyncing: boolean;
    pendingOperations: Operation[];
    conflicts: Conflict[];
  };
};
```

**Action Types:**
- `ADD_TASK` - Create new task in specified column
- `MOVE_TASK` - Move task between columns or reorder within column
- `UPDATE_TASK` - Edit task content
- `DELETE_TASK` - Remove task
- `DRAG_START` - Initiate drag operation
- `DRAG_END` - Complete or cancel drag
- `SYNC_START` - Begin sync simulation
- `SYNC_COMPLETE` - Sync finished successfully
- `CONFLICT_DETECTED` - Simultaneous edit detected
- `RESOLVE_CONFLICT` - User acknowledges conflict

### Optimistic Updates Flow

1. User initiates action (e.g., drag task to new column)
2. Dispatch optimistic action immediately → UI updates
3. Queue sync operation with setTimeout
4. On sync "response", verify no conflicts
5. If conflict detected, show toast and offer resolution

## 4. Key Implementation Approaches

### HTML5 Drag and Drop Integration

**Drag Start (TaskCard):**
- Set `draggable={true}` on task card
- On `dragstart`: store task data in `dataTransfer` using JSON serialization
- Set drag image and effectAllowed

**Drag Over (Column):**
- On `dragover`: prevent default to allow drop, set dropEffect
- Calculate insertion index based on mouse Y position
- Visual feedback via CSS classes

**Drop (Column):**
- On `drop`: parse task data from `dataTransfer`
- Determine new position within target column
- Dispatch MOVE_TASK action
- Remove drag-over styling

### Conflict Resolution Strategy

**Detection:**
- Each task has `version` and `lastModifiedBy` fields
- On simulated sync, compare local version with "server" version
- If versions diverge, create Conflict entry

**Resolution UI:**
- Toast notification showing conflict details
- Display both local and remote versions
- Options: Keep Local / Keep Remote / Merge Manually

### Sync Simulation

**Mock Implementation:**
```typescript
// Simulated network delay
const simulateSync = (operation: Operation): Promise<void> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Randomly inject conflicts for testing
      resolve();
    }, 300 + Math.random() * 700);
  });
};
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **TypeScript + React** | All components typed with interfaces; props and state fully annotated |
| **CSS Modules** | Create `TodoBoard.module.css` with scoped class names; no Tailwind classes used |
| **Native HTML5 DnD** | Implement dragstart/dragover/drop handlers without react-dnd or dnd-kit imports |
| **useReducer only** | Centralize all state logic in single reducer; no Redux/Zustand/Jotai |
| **Single .tsx file** | Export default TodoBoard as main component; helper functions defined in same file |
| **Mock with setTimeout** | Simulate real-time sync using setTimeout/setInterval; no socket.io or WebSocket |

## Summary

This design delivers a collaborative todo board using only native browser APIs and React hooks. The HTML5 Drag and Drop API provides drag functionality without external libraries, while useReducer manages complex state including optimistic updates and conflict tracking. CSS Modules ensure scoped, maintainable styling without utility-first frameworks.
