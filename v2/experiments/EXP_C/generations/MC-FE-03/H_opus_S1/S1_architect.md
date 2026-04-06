# Technical Design Document: Canvas Drawing Whiteboard

**Task**: MC-FE-03  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]TS [F]React [!D]NO_CANVAS_LIB [DRAW]CTX2D [STATE]useReducer_ONLY [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [OUT]CODE_ONLY`

---

## 1. Component Architecture

### Top-Level Component: `DrawingWhiteboard`
Single Functional Component (SFC) exported as default. Manages all drawing state through a single `useReducer` hook. Renders a toolbar and a `<canvas>` element.

**Internal Sub-components**:

| Component | Responsibility |
|-----------|---------------|
| `Toolbar` | Renders tool buttons (pen, eraser, clear) and the color picker. Dispatches tool/color change actions. |
| `ColorPicker` | A set of preset color swatches. Clicking dispatches `SET_COLOR`. |
| `Canvas` | The `<canvas>` element wrapper. Attaches mouse event listeners and performs all drawing via Canvas 2D context. |

### Rendering Tree

```
DrawingWhiteboard
├── Toolbar
│   ├── Tool Buttons (Pen / Eraser)
│   ├── ColorPicker
│   └── Action Buttons (Undo / Redo / Clear)
└── Canvas (<canvas> element)
```

**Key Design Decisions**:
- The `<canvas>` element is the sole rendering surface. React does not manage individual strokes — the canvas is imperatively drawn.
- `useReducer` manages the **logical state** (stroke history, current tool, color). The canvas is redrawn from state whenever undo/redo/clear occurs.
- A `useRef` holds the canvas element reference and the 2D rendering context.

---

## 2. Canvas Drawing Approach (Event Flow)

### Mouse Event Pipeline

```
mousedown → begin new path segment
mousemove (while pressed) → extend path, draw incrementally
mouseup → finalize path, commit to history
```

### Detailed Flow

1. **`onMouseDown`**:
   - Record `isDrawing = true` (stored in a ref, not state — to avoid re-renders during drawing).
   - Capture starting point `{ x: e.offsetX, y: e.offsetY }`.
   - Begin a new `PathSegment` with current tool and color.
   - Call `ctx.beginPath()` and `ctx.moveTo(x, y)`.

2. **`onMouseMove`**:
   - Guard: if `!isDrawing`, return.
   - Append `{ x, y }` to the current segment's points array.
   - Draw incrementally: `ctx.lineTo(x, y); ctx.stroke()`.
   - For eraser: use `ctx.globalCompositeOperation = 'destination-out'` with a larger line width.

3. **`onMouseUp`**:
   - Set `isDrawing = false`.
   - Dispatch `COMMIT_STROKE` action with the completed `PathSegment`.
   - This pushes the stroke onto the undo stack and clears the redo stack.

### Incremental vs Full Redraw

- **During drawing**: Strokes are drawn incrementally (line segment by line segment) for responsiveness.
- **On undo/redo/clear**: The entire canvas is cleared and all strokes in the current history are replayed from scratch. This ensures visual consistency with the logical state.

---

## 3. State Model with useReducer

### State Shape

```
interface Point {
  x: number;
  y: number;
}

interface PathSegment {
  id: string;                 // unique stroke id
  tool: 'pen' | 'eraser';
  color: string;              // hex color (ignored for eraser)
  lineWidth: number;
  points: Point[];
}

interface WhiteboardState {
  strokes: PathSegment[];     // committed strokes (current visible state)
  redoStack: PathSegment[];   // strokes available for redo
  currentTool: 'pen' | 'eraser';
  currentColor: string;
  lineWidth: number;
}
```

### Action Types

| Action | Payload | Effect |
|--------|---------|--------|
| `COMMIT_STROKE` | `PathSegment` | Push stroke to `strokes`, clear `redoStack` |
| `UNDO` | — | Pop last stroke from `strokes`, push to `redoStack` |
| `REDO` | — | Pop from `redoStack`, push to `strokes` |
| `CLEAR` | — | Move all `strokes` to `redoStack` (allows undo of clear) |
| `SET_TOOL` | `'pen' \| 'eraser'` | Update `currentTool` |
| `SET_COLOR` | `string` | Update `currentColor` |
| `SET_LINE_WIDTH` | `number` | Update `lineWidth` |

### Reducer Pure Function

The reducer is a pure function — it never mutates the existing state. Each action returns a new state object. This is critical for undo/redo correctness.

---

## 4. Undo/Redo Stack Design

### Dual-Stack Model

```
[strokes]           [redoStack]
  stroke_1             (empty initially)
  stroke_2
  stroke_3  ← UNDO → stroke_3 moves here
  stroke_2  ← UNDO → stroke_2 moves here
  stroke_2  ← REDO → stroke_2 moves back
```

**Rules**:
- `UNDO`: Transfer last element from `strokes` to `redoStack`.
- `REDO`: Transfer last element from `redoStack` to `strokes`.
- `COMMIT_STROKE`: Push new stroke to `strokes` and **clear** `redoStack` (new drawing invalidates the redo history).
- `CLEAR`: Transfer entire `strokes` array to `redoStack` as a single batch, enabling "undo clear."

### Canvas Sync

After any state change that affects `strokes`, a `useEffect` triggers a full canvas redraw:

1. `ctx.clearRect(0, 0, width, height)` — wipe canvas.
2. Iterate through `state.strokes` and replay each `PathSegment`:
   - Set `ctx.strokeStyle`, `ctx.lineWidth`, `ctx.globalCompositeOperation`.
   - `ctx.beginPath()`, then `moveTo` + `lineTo` for each point, then `ctx.stroke()`.

This effect is keyed on `[state.strokes]`.

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: TypeScript | `[L]TS` | Full TypeScript typing for state, actions, path segments, and event handlers. |
| Framework: React | `[F]React` | Built with React functional component, `useReducer`, `useRef`, `useEffect`, `useCallback`. |
| No canvas library | `[!D]NO_CANVAS_LIB` | No fabric.js, Konva, p5.js, or similar. Pure Canvas 2D API. |
| Canvas 2D context | `[DRAW]CTX2D` | All drawing via `canvas.getContext('2d')` — `beginPath`, `lineTo`, `stroke`, `clearRect`, `globalCompositeOperation`. |
| useReducer only | `[STATE]useReducer_ONLY` | Single `useReducer` for all domain state. No `useState` for strokes/tool/color. Only `useRef` for imperative canvas reference and `isDrawing` flag. |
| No external dependencies | `[D]NO_EXTERNAL` | Only React and TypeScript. No utility libraries. |
| Single Functional Component | `[O]SFC` | `DrawingWhiteboard` is the sole exported component. Sub-components are internal. |
| Default export | `[EXP]DEFAULT` | `export default function DrawingWhiteboard() {...}` |
| Code only output | `[OUT]CODE_ONLY` | Final deliverable is pure code, no prose. (This S1 document is the design phase; S2 will produce code only.) |
