# Technical Design Document — Canvas Drawing Whiteboard

## 1. Overview

A browser-based drawing whiteboard using the HTML5 Canvas 2D API. Users can draw freehand paths with a pen tool, erase strokes, pick colors, undo/redo actions, and clear the canvas. All state is managed exclusively through `useReducer`.

## 2. Component Architecture

### 2.1 `Whiteboard` (root, export default)
- Creates a `<canvas>` element and stores its ref.
- Connects mouse event handlers (`onMouseDown`, `onMouseMove`, `onMouseUp`) to the canvas.
- Holds the `useReducer` store and passes dispatch to child toolbar.
- On every state change, triggers a full canvas redraw from the stroke history.

### 2.2 `Toolbar`
- Renders tool selection buttons (Pen / Eraser), a color picker input, undo/redo buttons, and a clear button.
- All interactions dispatch actions; no local state.

### 2.3 Internal Utilities (not components)
- `drawStroke(ctx, stroke)`: iterates over a stroke's points array and calls Canvas line-drawing commands.
- `redrawAll(ctx, strokes)`: clears the canvas then redraws every stroke in order — the canonical render path.

## 3. Canvas Drawing Approach

### Event Flow

1. **mousedown**: Dispatch `START_STROKE` with `{ tool, color, point: {x, y} }`. Sets `isDrawing = true` (tracked in reducer state).
2. **mousemove**: If `isDrawing`, dispatch `ADD_POINT` with `{ x, y }`. After reducer updates, call `drawStroke` for the current in-progress stroke to provide real-time visual feedback.
3. **mouseup**: Dispatch `END_STROKE`. The current stroke is finalized in the strokes array.

### Coordinate Handling
- `event.clientX/Y` minus `canvas.getBoundingClientRect().left/top` yields canvas-local coordinates.
- Canvas `width`/`height` attributes are set to match CSS pixel dimensions to avoid scaling artifacts.

### Eraser Behavior
- The eraser is modeled as a stroke with `globalCompositeOperation = 'destination-out'` and a wider line width.
- On redraw, eraser strokes are replayed in order, so erasing is non-destructive and compatible with undo.

### Redraw Strategy
- After undo/redo/clear, `redrawAll` iterates through the current strokes array and replays every stroke.
- For real-time drawing performance, only the latest segment is drawn incrementally; a full redraw happens only on state-change events that alter stroke history (undo, redo, clear).

## 4. State Model with useReducer

### State Shape

```
WhiteboardState {
  strokes: Stroke[]           // committed strokes
  currentStroke: Stroke | null // in-progress stroke
  undoStack: Stroke[][]       // previous strokes snapshots
  redoStack: Stroke[][]       // forward snapshots
  tool: 'pen' | 'eraser'
  color: string               // hex color
  isDrawing: boolean
}

Stroke {
  id: string
  tool: 'pen' | 'eraser'
  color: string
  lineWidth: number
  points: Point[]
}

Point { x: number; y: number }
```

### Actions

| Action | Behavior |
|--------|----------|
| `START_STROKE` | Push current `strokes` onto `undoStack`, clear `redoStack`, create `currentStroke` |
| `ADD_POINT` | Append point to `currentStroke.points` |
| `END_STROKE` | Move `currentStroke` into `strokes`, set `currentStroke = null`, `isDrawing = false` |
| `UNDO` | Pop last snapshot from `undoStack` → becomes `strokes`; push old `strokes` onto `redoStack` |
| `REDO` | Pop from `redoStack` → becomes `strokes`; push old `strokes` onto `undoStack` |
| `CLEAR` | Snapshot current `strokes` to `undoStack`, set `strokes = []`, clear `redoStack` |
| `SET_TOOL` | Switch `tool` between pen and eraser |
| `SET_COLOR` | Update active `color` |

## 5. Undo/Redo Stack Design

- **Snapshot-based**: each undo entry is a full copy of the `strokes` array at that point in time. This is simple and correct; for a whiteboard with moderate stroke counts, memory is acceptable.
- **Undo**: restores the previous strokes snapshot. The current strokes are pushed to the redo stack.
- **Redo**: restores the next strokes snapshot. The current strokes are pushed back to the undo stack.
- **Branching**: any new stroke action after an undo clears the redo stack (standard behavior).
- **Clear**: treated as a special action that pushes the current state to the undo stack and sets strokes to an empty array, so clear itself is undoable.

### Stack Size Limit
- An optional cap (e.g., 50 entries) on the undo stack prevents unbounded memory growth. Oldest entries are evicted when the cap is reached.

## 6. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **TS + React** | Functional React component in TypeScript. All types are explicitly defined interfaces. |
| 2 | **Native Canvas 2D, no fabric/konva** | Drawing uses `canvas.getContext('2d')` directly — `beginPath`, `lineTo`, `stroke`, `clearRect`. No canvas abstraction libraries. |
| 3 | **useReducer only, no useState** | Every piece of state (strokes, tool, color, undo/redo stacks, drawing flag) lives in the single `useReducer`. No `useState` calls anywhere. |
| 4 | **No external deps** | Zero third-party imports. Color picker uses the native `<input type="color">` element. |
| 5 | **Single file, export default** | All components, reducer, types, and utility functions are in one `.tsx` file with `export default Whiteboard`. |
| 6 | **Code only** | The deliverable is pure source code with no prose, comments beyond JSDoc, or markdown explanation. |
