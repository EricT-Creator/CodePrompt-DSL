import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ─── Interfaces ──────────────────────────────────────────────

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  id: string;
  tool: 'pen' | 'eraser';
  color: string;
  lineWidth: number;
  points: Point[];
}

interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  undoStack: Stroke[][];
  redoStack: Stroke[][];
  activeTool: 'pen' | 'eraser';
  activeColor: string;
  lineWidth: number;
  isDrawing: boolean;
  canvasWidth: number;
  canvasHeight: number;
}

type WhiteboardAction =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_LINE_WIDTH'; width: number };

// ─── Style Injection ─────────────────────────────────────────

const STYLE_ID = 'dwb-styles';
const CSS = `
.dwb-root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: #f0f2f5;
  min-height: 100vh;
}
.dwb-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.dwb-tool-btn {
  padding: 8px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.dwb-tool-btn:hover {
  background: #f3f4f6;
}
.dwb-tool-btn-active {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}
.dwb-tool-btn-active:hover {
  background: #4f46e5;
}
.dwb-separator {
  width: 1px;
  height: 28px;
  background: #e5e7eb;
}
.dwb-color-picker {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dwb-color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.15s;
}
.dwb-color-swatch-active {
  border-color: #1f2937;
}
.dwb-color-swatch:hover {
  border-color: #9ca3af;
}
.dwb-color-input {
  width: 28px;
  height: 28px;
  border: none;
  padding: 0;
  cursor: pointer;
  background: none;
}
.dwb-line-width {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}
.dwb-line-width input {
  width: 60px;
}
.dwb-canvas-area {
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  background: #fff;
  cursor: crosshair;
}
.dwb-action-btn {
  padding: 8px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.dwb-action-btn:hover {
  background: #f3f4f6;
}
.dwb-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
`;

function injectStyles() {
  if (typeof document !== 'undefined' && !document.getElementById(STYLE_ID)) {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }
}

// ─── Helpers ─────────────────────────────────────────────────

let _sid = 0;
function strokeId(): string {
  return 's-' + (++_sid) + '-' + Date.now();
}

const UNDO_LIMIT = 50;

const PRESET_COLORS = ['#1f2937', '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899'];

// ─── Reducer ─────────────────────────────────────────────────

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  activeTool: 'pen',
  activeColor: '#1f2937',
  lineWidth: 3,
  isDrawing: false,
  canvasWidth: 900,
  canvasHeight: 600,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const newStroke: Stroke = {
        id: strokeId(),
        tool: state.activeTool,
        color: state.activeColor,
        lineWidth: state.activeTool === 'eraser' ? state.lineWidth * 3 : state.lineWidth,
        points: [action.point],
      };
      return { ...state, currentStroke: newStroke, isDrawing: true };
    }

    case 'ADD_POINT': {
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.point],
        },
      };
    }

    case 'END_STROKE': {
      if (!state.currentStroke) return { ...state, isDrawing: false };
      let newUndoStack = [...state.undoStack, state.strokes];
      if (newUndoStack.length > UNDO_LIMIT) {
        newUndoStack = newUndoStack.slice(newUndoStack.length - UNDO_LIMIT);
      }
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        undoStack: newUndoStack,
        redoStack: [],
        isDrawing: false,
      };
    }

    case 'UNDO': {
      if (state.undoStack.length === 0) return state;
      const prevStrokes = state.undoStack[state.undoStack.length - 1];
      return {
        ...state,
        redoStack: [...state.redoStack, state.strokes],
        strokes: prevStrokes,
        undoStack: state.undoStack.slice(0, -1),
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        undoStack: [...state.undoStack, state.strokes],
        strokes: nextStrokes,
        redoStack: state.redoStack.slice(0, -1),
      };
    }

    case 'CLEAR_CANVAS': {
      if (state.strokes.length === 0) return state;
      let newUndoStack = [...state.undoStack, state.strokes];
      if (newUndoStack.length > UNDO_LIMIT) {
        newUndoStack = newUndoStack.slice(newUndoStack.length - UNDO_LIMIT);
      }
      return {
        ...state,
        strokes: [],
        undoStack: newUndoStack,
        redoStack: [],
      };
    }

    case 'SET_TOOL':
      return { ...state, activeTool: action.tool };

    case 'SET_COLOR':
      return { ...state, activeColor: action.color };

    case 'SET_LINE_WIDTH':
      return { ...state, lineWidth: action.width };

    default:
      return state;
  }
}

// ─── Drawing Helpers ─────────────────────────────────────────

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length < 2) return;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = stroke.lineWidth;

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color;
  }

  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }
  ctx.stroke();
  ctx.restore();
}

function fullRedraw(ctx: CanvasRenderingContext2D, width: number, height: number, strokes: Stroke[]) {
  ctx.clearRect(0, 0, width, height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
}

// ─── Sub-Components ──────────────────────────────────────────

function ColorPicker({
  activeColor,
  onSetColor,
}: {
  activeColor: string;
  onSetColor: (color: string) => void;
}) {
  return (
    <div className="dwb-color-picker">
      {PRESET_COLORS.map(c => (
        <div
          key={c}
          className={'dwb-color-swatch' + (c === activeColor ? ' dwb-color-swatch-active' : '')}
          style={{ background: c }}
          onClick={() => onSetColor(c)}
        />
      ))}
      <input
        type="color"
        className="dwb-color-input"
        value={activeColor}
        onChange={e => onSetColor(e.target.value)}
      />
    </div>
  );
}

function Toolbar({
  state,
  dispatch,
}: {
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}) {
  return (
    <div className="dwb-toolbar">
      <button
        className={'dwb-tool-btn' + (state.activeTool === 'pen' ? ' dwb-tool-btn-active' : '')}
        onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
      >
        ✏️ Pen
      </button>
      <button
        className={'dwb-tool-btn' + (state.activeTool === 'eraser' ? ' dwb-tool-btn-active' : '')}
        onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
      >
        🧹 Eraser
      </button>

      <div className="dwb-separator" />

      <ColorPicker
        activeColor={state.activeColor}
        onSetColor={color => dispatch({ type: 'SET_COLOR', color })}
      />

      <div className="dwb-separator" />

      <div className="dwb-line-width">
        <span>Width:</span>
        <input
          type="range"
          min={1}
          max={20}
          value={state.lineWidth}
          onChange={e => dispatch({ type: 'SET_LINE_WIDTH', width: Number(e.target.value) })}
        />
        <span>{state.lineWidth}</span>
      </div>

      <div className="dwb-separator" />

      <button
        className="dwb-action-btn"
        disabled={state.undoStack.length === 0}
        onClick={() => dispatch({ type: 'UNDO' })}
      >
        ↩ Undo
      </button>
      <button
        className="dwb-action-btn"
        disabled={state.redoStack.length === 0}
        onClick={() => dispatch({ type: 'REDO' })}
      >
        ↪ Redo
      </button>
      <button
        className="dwb-action-btn"
        disabled={state.strokes.length === 0}
        onClick={() => dispatch({ type: 'CLEAR_CANVAS' })}
      >
        🗑 Clear
      </button>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────

function DrawingWhiteboard() {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const lastPointRef = useRef<Point | null>(null);

  useEffect(() => {
    injectStyles();
  }, []);

  // Full redraw when strokes change (undo/redo/clear)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    fullRedraw(ctx, state.canvasWidth, state.canvasHeight, state.strokes);
  }, [state.strokes, state.canvasWidth, state.canvasHeight]);

  const getCanvasPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasPoint(e);
    lastPointRef.current = point;
    dispatch({ type: 'START_STROKE', point });
  }, [getCanvasPoint]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing || !state.currentStroke) return;
    const point = getCanvasPoint(e);
    dispatch({ type: 'ADD_POINT', point });

    // Incremental rendering
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx || !lastPointRef.current) return;

    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = state.currentStroke.lineWidth;

    if (state.currentStroke.tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = state.currentStroke.color;
    }

    ctx.beginPath();
    ctx.moveTo(lastPointRef.current.x, lastPointRef.current.y);
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    ctx.restore();

    lastPointRef.current = point;
  }, [state.isDrawing, state.currentStroke, getCanvasPoint]);

  const handleMouseUp = useCallback(() => {
    if (!state.isDrawing) return;
    lastPointRef.current = null;
    dispatch({ type: 'END_STROKE' });
  }, [state.isDrawing]);

  const handleMouseLeave = useCallback(() => {
    if (state.isDrawing) {
      lastPointRef.current = null;
      dispatch({ type: 'END_STROKE' });
    }
  }, [state.isDrawing]);

  return (
    <div className="dwb-root">
      <Toolbar state={state} dispatch={dispatch} />
      <div className="dwb-canvas-area">
        <canvas
          ref={canvasRef}
          width={state.canvasWidth}
          height={state.canvasHeight}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        />
      </div>
    </div>
  );
}

export default DrawingWhiteboard;
