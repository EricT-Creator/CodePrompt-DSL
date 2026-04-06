# MC-FE-03: Canvas Drawing Whiteboard - Technical Design Document

## 1. Component Architecture

### Core Components

**Whiteboard (Root Container)**
- Manages canvas ref and rendering context
- Coordinates tool state and drawing operations
- Handles global keyboard shortcuts (undo/redo)

**Toolbar**
- Tool selection buttons (pen, eraser)
- Color picker component
- Action buttons (undo, redo, clear)
- Current tool indicator

**CanvasArea**
- HTML5 Canvas element wrapper
- Mouse event handlers
- Coordinate transformation utilities

**ColorPicker**
- Preset color palette
- Custom color selection
- Current color indicator

### Component Relationships
```
Whiteboard
├── Toolbar
│   ├── ToolButton (Pen, Eraser)
│   ├── ColorPicker
│   └── ActionButton (Undo, Redo, Clear)
├── CanvasArea
│   └── <canvas> element
└── useReducer (state management)
```

## 2. Canvas Drawing Approach

### Event Flow

**Mouse Event Sequence:**
```
mousedown → Start new path
    ↓
mousemove → Add points to current path (throttled)
    ↓
mouseup → Finalize path, push to history
```

**Coordinate Transformation:**
```typescript
const getCanvasCoordinates = (
  canvas: HTMLCanvasElement,
  clientX: number,
  clientY: number
): { x: number; y: number } => {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY
  };
};
```

### Drawing Implementation

**Path Data Structure:**
```typescript
interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  width: number;
  tool: 'pen' | 'eraser';
}
```

**Rendering Strategy:**
- On each state change, clear canvas and redraw all strokes
- Use `requestAnimationFrame` for smooth rendering
- Eraser implemented as white strokes (or `globalCompositeOperation = 'destination-out'`)

**Stroke Rendering:**
```typescript
const drawStroke = (ctx: CanvasRenderingContext2D, stroke: Stroke): void => {
  if (stroke.points.length < 2) return;
  
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  
  // Quadratic bezier for smooth curves
  for (let i = 1; i < stroke.points.length - 1; i++) {
    const midX = (stroke.points[i].x + stroke.points[i + 1].x) / 2;
    const midY = (stroke.points[i].y + stroke.points[i + 1].y) / 2;
    ctx.quadraticCurveTo(stroke.points[i].x, stroke.points[i].y, midX, midY);
  }
  
  ctx.lineTo(stroke.points[stroke.points.length - 1].x, stroke.points[stroke.points.length - 1].y);
  ctx.strokeStyle = stroke.tool === 'eraser' ? '#ffffff' : stroke.color;
  ctx.lineWidth = stroke.width;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.stroke();
};
```

### Mouse Event Throttling

**Throttled Mouse Move:**
- Use `requestAnimationFrame` to limit point collection
- Minimum distance threshold between points (3-5 pixels)
- Prevents excessive point data and improves performance

## 3. State Model with useReducer

### State Shape

```typescript
interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  tool: 'pen' | 'eraser';
  color: string;
  strokeWidth: number;
  history: HistoryState;
}

interface HistoryState {
  past: Stroke[][];
  future: Stroke[][];
  maxHistory: number;
}
```

### Action Types

```typescript
type WhiteboardAction =
  | { type: 'START_STROKE'; payload: { x: number; y: number } }
  | { type: 'ADD_POINT'; payload: { x: number; y: number } }
  | { type: 'END_STROKE' }
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };
```

### Reducer Logic

**START_STROKE:**
- Create new stroke with current tool/color settings
- Set as currentStroke

**ADD_POINT:**
- Append point to currentStroke.points
- State mutation handled via spread operator

**END_STROKE:**
- Push currentStroke to strokes array
- Save strokes snapshot to history.past
- Clear currentStroke
- Clear history.future

**UNDO:**
- Pop from history.past
- Push current strokes to history.future
- Restore previous strokes state

**REDO:**
- Pop from history.future
- Push current strokes to history.past
- Restore next strokes state

## 4. Undo/Redo Stack Design

### History Management

**State Snapshots:**
- Store complete strokes array at each significant change
- Memory-efficient: only store references (strokes are immutable after completion)
- Max history limit: 50 states to prevent memory issues

**History Operations:**
```typescript
const MAX_HISTORY = 50;

const saveToHistory = (state: WhiteboardState): WhiteboardState => {
  const newPast = [...state.history.past, state.strokes];
  return {
    ...state,
    history: {
      ...state.history,
      past: newPast.length > MAX_HISTORY 
        ? newPast.slice(newPast.length - MAX_HISTORY) 
        : newPast,
      future: [] // Clear redo stack on new action
    }
  };
};

const undo = (state: WhiteboardState): WhiteboardState => {
  if (state.history.past.length === 0) return state;
  
  const previous = state.history.past[state.history.past.length - 1];
  const newPast = state.history.past.slice(0, -1);
  
  return {
    ...state,
    strokes: previous,
    history: {
      ...state.history,
      past: newPast,
      future: [state.strokes, ...state.history.future]
    }
  };
};
```

### Keyboard Shortcuts

- `Ctrl+Z`: Undo
- `Ctrl+Y` or `Ctrl+Shift+Z`: Redo
- Event listeners attached in useEffect with cleanup

## 5. Constraint Acknowledgment

### TS + React
**Addressed by:** All components and state use TypeScript interfaces. Functional components with proper prop types.

### Native Canvas 2D, no fabric/konva
**Addressed by:** Direct use of HTML5 `<canvas>` element and `CanvasRenderingContext2D` API. No Fabric.js, Konva, or other canvas abstraction libraries.

### useReducer only, no useState
**Addressed by:** All state managed through single `useReducer` hook. No `useState` calls anywhere in the component. Local component state eliminated in favor of reducer pattern.

### No external deps
**Addressed by:** Only React and TypeScript as dependencies. No additional npm packages.

### Single file, export default
**Addressed by:** All code in single `.tsx` file with `export default Whiteboard`. Internal types and helper functions defined within same file.

### Code only
**Addressed by:** Output contains only code (TypeScript/React). No markdown formatting in generated code file.
