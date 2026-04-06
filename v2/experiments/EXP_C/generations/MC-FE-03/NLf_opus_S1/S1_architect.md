# Technical Design Document — Canvas Drawing Whiteboard

## 1. Overview

This document describes the architecture for a canvas-based drawing whiteboard that supports pen tool, eraser, color picker, undo/redo, and clear canvas. Drawing captures mouse events (mousedown, mousemove, mouseup) to record paths, which are rendered onto an HTML5 Canvas via the native 2D context API.

## 2. Component Architecture

### 2.1 Component Tree

- **DrawingWhiteboard** (root): Owns all state via a single `useReducer`. Hosts the canvas ref. Orchestrates event handlers and rendering. Exported as default.
  - **Toolbar**: Renders tool selection (pen/eraser), color picker, undo/redo buttons, and clear button. Dispatches actions to the root reducer.
    - **ColorPicker**: A set of preset color swatches plus an HTML color input for custom selection.
    - **ToolButton** (×N): Individual tool/action buttons with active state highlighting.
  - **CanvasArea**: Wraps the `<canvas>` element. Attaches mouse event listeners. Translates mouse coordinates into drawing operations.

### 2.2 Responsibilities

| Component | Responsibility |
|-----------|---------------|
| DrawingWhiteboard | State container (useReducer), canvas ref management, rendering loop |
| Toolbar | Tool/action dispatching UI |
| ColorPicker | Color selection dispatch |
| CanvasArea | Mouse event capture, coordinate translation, canvas rendering |

## 3. Canvas Drawing Approach

### 3.1 Event Flow

1. **mousedown**: Begin a new stroke. Create a new `Stroke` object with the current tool, color, and line width. Add the starting point. Set `isDrawing = true`.
2. **mousemove**: If `isDrawing`, append the current mouse position to the active stroke's points array. Perform incremental rendering (draw a line segment from the previous point to the current point) for real-time visual feedback.
3. **mouseup**: Finalize the stroke. Push the completed stroke onto the history stack. Set `isDrawing = false`.

### 3.2 Coordinate Translation

Mouse event `clientX`/`clientY` are translated to canvas coordinates by subtracting the canvas element's bounding rect (`getBoundingClientRect()`) left/top values. This ensures accurate drawing regardless of canvas position on the page.

### 3.3 Rendering Strategy

- **Incremental rendering** during active drawing: Only the newest line segment is drawn to avoid redrawing all strokes on every mousemove.
- **Full redraw** after undo/redo/clear: The canvas is cleared, and all strokes in the current history stack are replayed from scratch. Each stroke is drawn as a continuous path using `beginPath()`, `moveTo()`, `lineTo()`, and `stroke()`.

### 3.4 Eraser Implementation

The eraser is implemented as a stroke with `globalCompositeOperation = 'destination-out'`. This punches through existing content, creating a true erase effect. The eraser stroke is stored in the history like any other stroke, making it compatible with undo/redo.

## 4. State Model with useReducer

### 4.1 State Shape

```
WhiteboardState {
  strokes: Stroke[]          // completed strokes (the "document")
  currentStroke: Stroke | null // stroke being drawn right now
  undoStack: Stroke[][]      // previous states for undo
  redoStack: Stroke[][]      // states popped by undo, for redo
  activeTool: 'pen' | 'eraser'
  activeColor: string
  lineWidth: number
  isDrawing: boolean
  canvasWidth: number
  canvasHeight: number
}
```

### 4.2 Interfaces

- **Point**: `{ x: number; y: number }`
- **Stroke**: `{ id: string; tool: 'pen' | 'eraser'; color: string; lineWidth: number; points: Point[] }`
- **WhiteboardAction**: Union type of all actions.

### 4.3 Actions

| Action | Effect |
|--------|--------|
| `START_STROKE` | Creates `currentStroke` with tool/color/width, adds first point, sets `isDrawing = true` |
| `ADD_POINT` | Appends a point to `currentStroke.points` |
| `END_STROKE` | Pushes current strokes to `undoStack`, moves `currentStroke` into `strokes`, clears `redoStack`, sets `isDrawing = false` |
| `UNDO` | Pops `strokes` state from `undoStack`, pushes current to `redoStack` |
| `REDO` | Pops from `redoStack`, pushes current to `undoStack` |
| `CLEAR_CANVAS` | Pushes current to `undoStack`, empties `strokes`, clears `redoStack` |
| `SET_TOOL` | Updates `activeTool` |
| `SET_COLOR` | Updates `activeColor` |
| `SET_LINE_WIDTH` | Updates `lineWidth` |

## 5. Undo/Redo Stack Design

### 5.1 Approach

The undo/redo system uses a snapshot-based approach:

- **undoStack**: An array of `Stroke[]` snapshots. Each entry is the complete strokes array before a modification.
- **redoStack**: An array of `Stroke[]` snapshots. Populated when the user undoes; cleared when a new stroke is drawn.

### 5.2 Operations

- **Undo**: If `undoStack` is non-empty, push current `strokes` to `redoStack`, pop from `undoStack` and set as current `strokes`. Trigger full canvas redraw.
- **Redo**: If `redoStack` is non-empty, push current `strokes` to `undoStack`, pop from `redoStack` and set as current `strokes`. Trigger full canvas redraw.
- **New stroke / Clear**: Push current `strokes` to `undoStack`, clear `redoStack`.

### 5.3 Stack Size Limit

To prevent excessive memory usage, the undo stack is capped at 50 entries. When exceeding the cap, the oldest entry is discarded.

## 6. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | TypeScript with React | All components are React functional components with full TypeScript typing. Point, Stroke, WhiteboardState, and WhiteboardAction are explicitly typed. |
| 2 | Native Canvas 2D context API only, no fabric.js/konva/p5.js | All drawing uses `canvas.getContext('2d')` methods: `beginPath`, `moveTo`, `lineTo`, `stroke`, `clearRect`, and `globalCompositeOperation`. No canvas library is imported. |
| 3 | useReducer for ALL state management, no useState | Every piece of state — strokes, tool selection, color, line width, drawing flag, undo/redo stacks — is managed within a single `useReducer`. Zero `useState` calls. |
| 4 | No external npm packages beyond React and TypeScript | Only React and TypeScript are used. Canvas operations, undo/redo, color picking, and coordinate math are all hand-written. |
| 5 | Single .tsx file with export default | All components, reducer, interfaces, and styles are contained in one .tsx file. `export default DrawingWhiteboard`. |
| 6 | Output code only, no explanation text | The final deliverable (in the implementation stage) will contain pure code with no prose. This design document serves as the planning artifact only. |
