# MC-FE-01: Real-time Collaborative Todo Board - Technical Design Document

## 1. Component Architecture

### Core Components

**TodoBoard (Root Container)**
- Orchestrates the overall application state and WebSocket connection
- Manages optimistic updates and conflict resolution logic
- Coordinates between columns and handles global operations

**Column Component**
- Renders a single column (Todo/In Progress/Done)
- Handles drag-over events for drop targets
- Manages column-specific task ordering

**TaskCard Component**
- Individual task representation with drag capability
- Displays task metadata and conflict indicators
- Handles drag start/end events

**ConflictIndicator Component**
- Displays visual feedback when conflicts are detected
- Shows which user made the conflicting change
- Provides resolution hints to users

### Component Relationships
```
TodoBoard
├── WebSocketManager (connection handling)
├── Column (×3)
│   ├── TaskCard (×N)
│   └── DropZone
└── ConflictPanel (global conflict display)
```

## 2. Data Model

```typescript
interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'done';
  order: number;
  lastModifiedBy: string;
  lastModifiedAt: number;
  version: number;
}

interface Column {
  id: string;
  title: string;
  status: Task['status'];
  taskIds: string[];
}

interface BoardState {
  tasks: Record<string, Task>;
  columns: Record<string, Column>;
  columnOrder: string[];
}

interface OptimisticUpdate {
  taskId: string;
  previousState: Task;
  newState: Task;
  timestamp: number;
  pending: boolean;
}

interface Conflict {
  taskId: string;
  localChange: Task;
  remoteChange: Task;
  detectedAt: number;
  resolution?: 'local' | 'remote' | 'merged';
}

interface WebSocketMessage {
  type: 'TASK_MOVE' | 'TASK_CREATE' | 'TASK_DELETE' | 'TASK_UPDATE';
  payload: Task | { taskId: string; newStatus: string; newOrder: number };
  userId: string;
  timestamp: number;
}
```

## 3. State Management Approach

### useReducer Architecture

**State Shape:**
```typescript
interface AppState {
  board: BoardState;
  optimisticUpdates: OptimisticUpdate[];
  conflicts: Conflict[];
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
  currentUser: string;
}
```

**Action Types:**
- `MOVE_TASK_OPTIMISTIC`: Apply local change immediately
- `MOVE_TASK_CONFIRMED`: Server acknowledgment received
- `MOVE_TASK_REJECTED`: Server rejected, rollback
- `RECEIVE_REMOTE_UPDATE`: Apply remote user's change
- `DETECT_CONFLICT`: Both users modified same task
- `RESOLVE_CONFLICT`: User chooses resolution
- `WS_CONNECTED` / `WS_DISCONNECTED`: Connection state

### Optimistic Updates Flow

1. User drags task → dispatch `MOVE_TASK_OPTIMISTIC`
2. Store previous state in optimisticUpdates array
3. Send WebSocket message to server
4. On acknowledgment → remove from optimisticUpdates
5. On rejection → restore previous state
6. On conflict → add to conflicts array, show UI

### Conflict Resolution Strategy

- **Last-write-wins with visual indication**: Remote changes apply but user sees conflict banner
- **Manual resolution option**: User can choose to keep local or accept remote
- **Version vector**: Each task has version number for deterministic ordering

## 4. Key Implementation Approaches

### HTML5 Native Drag and Drop

**Drag Events:**
- `dragstart`: Capture task ID, set drag data with `dataTransfer.setData()`
- `dragover`: Prevent default, calculate drop position via `event.clientY`
- `drop`: Get task ID from dataTransfer, calculate new order index
- `dragend`: Cleanup drag state

**Position Calculation:**
```typescript
// Calculate insertion index based on mouse Y position
const getDropIndex = (container: HTMLElement, clientY: number): number => {
  const cards = Array.from(container.querySelectorAll('.task-card'));
  // Binary search for efficient position finding
  // Return appropriate index for insertion
};
```

### WebSocket Mock Implementation

**Mock Server Architecture:**
- Use `setInterval` to simulate network latency (50-200ms)
- Maintain in-memory state representing "server truth"
- Broadcast changes to all connected clients
- Simulate random conflicts for testing

**Connection Management:**
- Auto-reconnect with exponential backoff
- Message queue for offline changes
- Connection status indicator

### CSS Modules Styling

**Module Structure:**
- `TodoBoard.module.css`: Layout and container styles
- `Column.module.css`: Column-specific styles
- `TaskCard.module.css`: Card appearance and drag states
- `DragDrop.module.css`: Drag-over indicators and animations

**Key Classes:**
- `.dragging`: Applied during drag operation
- `.dragOver`: Applied to drop target
- `.conflict`: Visual indication of conflicting task
- `.optimistic`: Semi-transparent state for pending changes

## 5. Constraint Acknowledgment

### TS + React
**Addressed by:** Entire codebase uses TypeScript with strict typing. All components are React functional components with proper prop interfaces.

### CSS Modules only, no Tailwind
**Addressed by:** All styling uses `.module.css` files co-located with components. No utility classes or Tailwind directives. Global styles avoided except for CSS variables in `:root`.

### HTML5 native drag, no dnd libs
**Addressed by:** Implementation uses native HTML5 Drag and Drop API with `draggable` attribute and `onDragStart/Over/Drop/End` handlers. No react-dnd or similar libraries.

### useReducer only, no state libs
**Addressed by:** All state managed through single `useReducer` hook at board level. No Redux, Zustand, or Context API for state. Props passed down manually.

### Single file, export default
**Addressed by:** All components defined in single `.tsx` file with `export default TodoBoard` as entry point. Internal components defined as inner functions or separate interfaces in same file.

### Hand-written WS mock, no socket.io
**Addressed by:** WebSocket mock implemented using native `WebSocket` class wrapper with custom message protocol. No Socket.IO client or server libraries.
