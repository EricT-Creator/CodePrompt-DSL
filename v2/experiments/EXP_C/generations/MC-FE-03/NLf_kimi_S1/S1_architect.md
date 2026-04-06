# MC-FE-03: Canvas Drawing Whiteboard - Technical Design

## Overview

This document outlines the technical design for a canvas-based drawing whiteboard supporting pen tool, eraser, color picker, undo/redo, and clear canvas functionality using native browser APIs.

## 1. Component Architecture

### Main Component Structure

```
Whiteboard (Main Container)
├── Toolbar (Tool selection, color picker, actions)
│   ├── ToolButton (Pen) [active state]
│   ├── ToolButton (Eraser)
│   ├── ColorPicker (Palette or input)
│   ├── ActionButton (Undo)
│   ├── ActionButton (Redo)
│   └── ActionButton (Clear)
├── CanvasContainer (Responsive wrapper)
│   └── Canvas (Drawing surface)
└── StatusBar (Cursor position, tool info)
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `Whiteboard` | useReducer state management, canvas ref coordination |
| `Toolbar` | Render tool buttons, handle tool switching |
| `Canvas` | Drawing surface, mouse event handlers, 2D context operations |
| `ColorPicker` | Color selection UI |
| `ActionButton` | Undo/redo/clear triggers |

## 2. Canvas Drawing Approach

### Event Flow

**Mouse Event Sequence:**
```
mousedown → Start new stroke
    ↓
mousemove → Draw line segment (if drawing)
    ↓
mouseup → End stroke, save to history
```

**Coordinate Mapping:**
```typescript
const getCanvasCoordinates = (
  canvas: HTMLCanvasElement,
  event: MouseEvent
): { x: number; y: number } => {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  };
};
```

### Drawing Implementation

**Pen Tool:**
```typescript
// On mousedown
ctx.beginPath();
ctx.moveTo(startX, startY);
ctx.strokeStyle = currentColor;
ctx.lineWidth = penSize;
ctx.lineCap = 'round';
ctx.lineJoin = 'round';

// On mousemove
ctx.lineTo(currentX, currentY);
ctx.stroke();
```

**Eraser Tool:**
- Same path logic as pen
- Use `ctx.globalCompositeOperation = 'destination-out'`
- Or draw with background color for partial erase

## 3. State Model with useReducer

### State Shape

```typescript
interface WhiteboardState {
  // Tool state
  currentTool: 'pen' | 'eraser';
  currentColor: string;
  penSize: number;
  eraserSize: number;
  
  // Drawing state
  isDrawing: boolean;
  currentStroke: Point[] | null;
  
  // History for undo/redo
  strokes: Stroke[];           // Committed strokes
  redoStack: Stroke[];         // Strokes available for redo
  
  // Canvas state
  canvasSize: { width: number; height: number };
}

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  tool: 'pen' | 'eraser';
  color: string;
  size: number;
  timestamp: number;
}
```

### Action Types

```typescript
type WhiteboardAction =
  | { type: 'SELECT_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'SELECT_COLOR'; color: string }
  | { type: 'START_DRAWING'; point: Point }
  | { type: 'DRAW'; point: Point }
  | { type: 'END_DRAWING' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'RESIZE_CANVAS'; size: { width: number; height: number } };
```

## 4. Undo/Redo Stack Design

### History Management

**Stroke-Based Approach:**
- Each completed stroke (mouse up) is pushed to `strokes` array
- Undo: Pop from `strokes`, push to `redoStack`, redraw canvas
- Redo: Pop from `redoStack`, push to `strokes`, redraw canvas

**Canvas Redraw Algorithm:**
```typescript
const redrawCanvas = (
  ctx: CanvasRenderingContext2D,
  strokes: Stroke[],
  canvasSize: { width: number; height: number }
) => {
  // Clear canvas
  ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
  
  // Replay all strokes
  strokes.forEach(stroke => {
    ctx.beginPath();
    ctx.strokeStyle = stroke.tool === 'eraser' ? '#ffffff' : stroke.color;
    ctx.lineWidth = stroke.size;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    if (stroke.points.length > 0) {
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      stroke.points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
      ctx.stroke();
    }
  });
};
```

### State Transitions

| Action | strokes | redoStack | Effect |
|--------|---------|-----------|--------|
| End drawing | Push new stroke | Clear | New stroke committed |
| Undo | Pop last | Push popped | Remove last stroke |
| Redo | Push from redo | Pop | Restore stroke |
| Clear | Empty | Empty | Clear all history |
| New stroke after undo | Push new | Clear | Redo stack invalidated |

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **TypeScript + React** | All types defined (Point, Stroke, WhiteboardState, WhiteboardAction) |
| **Native Canvas 2D API** | Use `canvas.getContext('2d')` and context methods (beginPath, moveTo, lineTo, stroke); no fabric.js or konva |
| **useReducer only** | No useState hooks; all state managed through single reducer with dispatch |
| **No external npm packages** | Only React and TypeScript dependencies; Canvas API is browser native |
| **Single .tsx file** | All components, types, reducer, and helpers in one file with default export |
| **Output code only** | Design focuses on implementation approach; no explanatory text in final output |

## Summary

This design implements a drawing whiteboard using only the native HTML5 Canvas 2D API and React's useReducer hook. The stroke-based history system enables efficient undo/redo by storing point arrays rather than pixel data. Mouse events drive the drawing flow, with each completed stroke committed to the history stack. The reducer manages all state transitions including tool selection, drawing operations, and history navigation without any external canvas libraries.
