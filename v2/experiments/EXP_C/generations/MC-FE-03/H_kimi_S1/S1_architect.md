# MC-FE-03: Canvas Drawing Whiteboard — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Component Architecture

### 1.1 Top-Level Structure
```
Whiteboard (Container)
├── Toolbar
│   ├── ToolSelector (pen/eraser)
│   ├── ColorPicker
│   ├── StrokeWidthSlider
│   └── ActionButtons (undo/redo/clear)
└── CanvasArea
    └── DrawingCanvas (HTML5 canvas element)
```

### 1.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `Whiteboard` | State container, reducer dispatch, history management |
| `Toolbar` | UI controls layout |
| `ToolSelector` | Switch between pen/eraser tools |
| `ColorPicker` | Select stroke color |
| `StrokeWidthSlider` | Adjust line thickness |
| `ActionButtons` | Trigger undo/redo/clear actions |
| `DrawingCanvas` | Canvas element, event handlers, drawing logic |

---

## 2. Canvas Drawing Approach

### 2.1 Event Flow

**Mouse Events**:
1. `mousedown` → Start new path, record starting point
2. `mousemove` → Draw line segment to current point
3. `mouseup` → Close path, save to state

**Touch Events** (bonus):
- Mirror mouse events with `touchstart`, `touchmove`, `touchend`

### 2.2 Drawing Context

```typescript
const ctx = canvas.getContext('2d');

// Pen mode
ctx.globalCompositeOperation = 'source-over';
ctx.strokeStyle = selectedColor;
ctx.lineWidth = strokeWidth;
ctx.lineCap = 'round';
ctx.lineJoin = 'round';

// Eraser mode
ctx.globalCompositeOperation = 'destination-out';
```

### 2.3 Path Recording

Each stroke is recorded as:
```typescript
interface Stroke {
  id: string;
  tool: 'pen' | 'eraser';
  color: string;
  width: number;
  points: Point[];
}

interface Point {
  x: number;
  y: number;
}
```

---

## 3. State Model with useReducer

### 3.1 State Shape

```typescript
interface WhiteboardState {
  strokes: Stroke[];           // All committed strokes
  currentStroke: Stroke | null; // In-progress stroke
  tool: 'pen' | 'eraser';
  color: string;
  strokeWidth: number;
  history: HistoryState;
}

interface HistoryState {
  past: Stroke[][];    // Previous stroke arrays
  future: Stroke[][];  // Redo stack
}
```

### 3.2 Actions

| Action | Payload | Effect |
|--------|---------|--------|
| `START_STROKE` | point, tool, color, width | Initialize `currentStroke` |
| `ADD_POINT` | point | Append to `currentStroke.points` |
| `END_STROKE` | — | Commit to `strokes`, clear `currentStroke` |
| `SET_TOOL` | tool | Update active tool |
| `SET_COLOR` | color | Update pen color |
| `SET_WIDTH` | width | Update stroke width |
| `UNDO` | — | Pop from `past`, push current to `future` |
| `REDO` | — | Pop from `future`, restore to `strokes` |
| `CLEAR` | — | Save to `past`, empty `strokes` |

### 3.3 Reducer Pattern

```typescript
function whiteboardReducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE':
      return { ...state, currentStroke: createStroke(action) };
    case 'UNDO':
      const previous = state.history.past[state.history.past.length - 1];
      return {
        ...state,
        strokes: previous || [],
        history: {
          past: state.history.past.slice(0, -1),
          future: [state.strokes, ...state.history.future]
        }
      };
    // ... other cases
  }
}
```

---

## 4. Undo/Redo Stack Design

### 4.1 History Management

**Approach**: Store snapshots of `strokes` array

**Memory Optimization**:
- Limit history depth (e.g., max 50 undo levels)
- When limit reached, drop oldest entry

**State Transitions**:
```
Initial: [Stroke1, Stroke2]
  ↓ Draw Stroke3
Past: [[Stroke1, Stroke2]], Strokes: [S1, S2, S3], Future: []
  ↓ Undo
Past: [], Strokes: [S1, S2], Future: [[S1, S2, S3]]
  ↓ Redo
Past: [[S1, S2]], Strokes: [S1, S2, S3], Future: []
```

### 4.2 Canvas Redraw

On undo/redo:
1. Clear canvas: `ctx.clearRect(0, 0, width, height)`
2. Re-render all strokes from `strokes` array
3. This ensures canvas matches state exactly

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]TS` | All types defined; strict TypeScript |
| `[F]React` | Functional components only |
| `[!D]NO_CANVAS_LIB` | Raw HTML5 Canvas API |
| `[DRAW]CTX2D` | `getContext('2d')` for all drawing |
| `[STATE]useReducer_ONLY` | No useState for complex state; reducer only |
| `[D]NO_EXTERNAL` | No external libraries |
| `[O]SFC` | Single file default export |
| `[EXP]DEFAULT` | `export default Whiteboard` |
| `[OUT]CODE_ONLY` | Output will be code only (no markdown wrappers) |

---

## 6. File Structure

```
MC-FE-03/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
├── S2_developer/
│   └── Whiteboard.tsx
├── Whiteboard.module.css
└── types.ts
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
