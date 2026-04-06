import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ── Interfaces ──────────────────────────────────────────────────────────────

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

// ── Constants ───────────────────────────────────────────────────────────────

const STYLE_ID = 'dwb-styles';
const P = 'dwb';
const MAX_UNDO = 50;

const PRESET_COLORS = [
  '#1a1a2e', '#e11d48', '#2563eb', '#059669', '#d97706',
  '#7c3aed', '#db2777', '#0891b2', '#65a30d', '#ea580c',
];

let strokeIdCounter = 0;
const genStrokeId = (): string => `s-${Date.now()}-${++strokeIdCounter}`;

// ── Styles ──────────────────────────────────────────────────────────────────

const cssText = `
.${P}-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1000px;
  margin: 20px auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  overflow: hidden;
}
.${P}-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
}
.${P}-tool-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
.${P}-tool-btn {
  padding: 8px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
  color: #333;
}
.${P}-tool-btn:hover {
  background: #f0f0f5;
}
.${P}-tool-btn-active {
  background: #4f46e5;
  color: #fff;
  border-color: #4f46e5;
}
.${P}-separator {
  width: 1px;
  height: 28px;
  background: #d0d5dd;
  margin: 0 6px;
}
.${P}-color-swatches {
  display: flex;
  gap: 4px;
  align-items: center;
}
.${P}-swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.1s, transform 0.1s;
}
.${P}-swatch:hover {
  transform: scale(1.15);
}
.${P}-swatch-active {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79,70,229,0.3);
}
.${P}-color-input {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  padding: 0;
}
.${P}-slider-group {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
}
.${P}-slider {
  width: 80px;
  accent-color: #4f46e5;
}
.${P}-action-btn {
  padding: 7px 12px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
  color: #333;
}
.${P}-action-btn:hover {
  background: #f0f0f5;
}
.${P}-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.${P}-canvas-area {
  display: flex;
  justify-content: center;
  background: #fafafa;
  padding: 10px;
}
.${P}-canvas {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: crosshair;
}
`;

// ── Reducer ─────────────────────────────────────────────────────────────────

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  activeTool: 'pen',
  activeColor: '#1a1a2e',
  lineWidth: 3,
  isDrawing: false,
  canvasWidth: 960,
  canvasHeight: 540,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const newStroke: Stroke = {
        id: genStrokeId(),
        tool: state.activeTool,
        color: state.activeColor,
        lineWidth: state.activeTool === 'eraser' ? state.lineWidth * 3 : state.lineWidth,
        points: [action.point],
      };
      return {
        ...state,
        currentStroke: newStroke,
        isDrawing: true,
      };
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
      if (!state.currentStroke || state.currentStroke.points.length < 2) {
        return { ...state, currentStroke: null, isDrawing: false };
      }
      let newUndoStack = [...state.undoStack, state.strokes];
      if (newUndoStack.length > MAX_UNDO) {
        newUndoStack = newUndoStack.slice(newUndoStack.length - MAX_UNDO);
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
      const newUndoStack = [...state.undoStack];
      const prevStrokes = newUndoStack.pop()!;
      return {
        ...state,
        strokes: prevStrokes,
        undoStack: newUndoStack,
        redoStack: [...state.redoStack, state.strokes],
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const newRedoStack = [...state.redoStack];
      const nextStrokes = newRedoStack.pop()!;
      return {
        ...state,
        strokes: nextStrokes,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: newRedoStack,
      };
    }

    case 'CLEAR_CANVAS': {
      if (state.strokes.length === 0) return state;
      let newUndoStack = [...state.undoStack, state.strokes];
      if (newUndoStack.length > MAX_UNDO) {
        newUndoStack = newUndoStack.slice(newUndoStack.length - MAX_UNDO);
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

// ── Drawing Helpers ─────────────────────────────────────────────────────────

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length < 2) return;

  ctx.save();
  ctx.beginPath();
  ctx.lineWidth = stroke.lineWidth;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color;
  }

  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }
  ctx.stroke();
  ctx.restore();
}

function fullRedraw(ctx: CanvasRenderingContext2D, strokes: Stroke[], width: number, height: number): void {
  ctx.clearRect(0, 0, width, height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
}

// ── Sub-Components ──────────────────────────────────────────────────────────

const ColorPicker: React.FC<{
  activeColor: string;
  onColorChange: (color: string) => void;
}> = ({ activeColor, onColorChange }) => (
  <div className={`${P}-color-swatches`}>
    {PRESET_COLORS.map(c => (
      <div
        key={c}
        className={`${P}-swatch ${activeColor === c ? `${P}-swatch-active` : ''}`}
        style={{ backgroundColor: c }}
        onClick={() => onColorChange(c)}
      />
    ))}
    <input
      type="color"
      className={`${P}-color-input`}
      value={activeColor}
      onChange={e => onColorChange(e.target.value)}
    />
  </div>
);

const ToolButton: React.FC<{
  label: string;
  active: boolean;
  onClick: () => void;
}> = ({ label, active, onClick }) => (
  <button
    className={`${P}-tool-btn ${active ? `${P}-tool-btn-active` : ''}`}
    onClick={onClick}
  >
    {label}
  </button>
);

const Toolbar: React.FC<{
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}> = ({ state, dispatch }) => (
  <div className={`${P}-toolbar`}>
    <div className={`${P}-tool-group`}>
      <ToolButton label="✏️ Pen" active={state.activeTool === 'pen'} onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })} />
      <ToolButton label="🧹 Eraser" active={state.activeTool === 'eraser'} onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })} />
    </div>
    <div className={`${P}-separator`} />
    <ColorPicker activeColor={state.activeColor} onColorChange={c => dispatch({ type: 'SET_COLOR', color: c })} />
    <div className={`${P}-separator`} />
    <div className={`${P}-slider-group`}>
      Size: {state.lineWidth}px
      <input
        type="range"
        className={`${P}-slider`}
        min={1}
        max={20}
        value={state.lineWidth}
        onChange={e => dispatch({ type: 'SET_LINE_WIDTH', width: parseInt(e.target.value, 10) })}
      />
    </div>
    <div className={`${P}-separator`} />
    <button className={`${P}-action-btn`} onClick={() => dispatch({ type: 'UNDO' })} disabled={state.undoStack.length === 0}>
      ↩ Undo
    </button>
    <button className={`${P}-action-btn`} onClick={() => dispatch({ type: 'REDO' })} disabled={state.redoStack.length === 0}>
      ↪ Redo
    </button>
    <button className={`${P}-action-btn`} onClick={() => dispatch({ type: 'CLEAR_CANVAS' })} disabled={state.strokes.length === 0}>
      🗑 Clear
    </button>
  </div>
);

// ── Canvas Area ─────────────────────────────────────────────────────────────

const CanvasArea: React.FC<{
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
}> = ({ state, dispatch, canvasRef }) => {
  const getCanvasPoint = useCallback((e: React.MouseEvent): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, [canvasRef]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const point = getCanvasPoint(e);
    dispatch({ type: 'START_STROKE', point });

    // Start incremental drawing
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx) {
      ctx.beginPath();
      ctx.lineWidth = state.activeTool === 'eraser' ? state.lineWidth * 3 : state.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      if (state.activeTool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
      } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = state.activeColor;
      }
      ctx.moveTo(point.x, point.y);
    }
  }, [canvasRef, dispatch, getCanvasPoint, state.activeTool, state.activeColor, state.lineWidth]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!state.isDrawing) return;
    const point = getCanvasPoint(e);
    dispatch({ type: 'ADD_POINT', point });

    // Incremental render
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx) {
      ctx.lineTo(point.x, point.y);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(point.x, point.y);
    }
  }, [canvasRef, dispatch, getCanvasPoint, state.isDrawing]);

  const handleMouseUp = useCallback(() => {
    if (!state.isDrawing) return;
    dispatch({ type: 'END_STROKE' });
  }, [dispatch, state.isDrawing]);

  return (
    <div className={`${P}-canvas-area`}>
      <canvas
        ref={canvasRef}
        className={`${P}-canvas`}
        width={state.canvasWidth}
        height={state.canvasHeight}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
    </div>
  );
};

// ── Main Component ──────────────────────────────────────────────────────────

const DrawingWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevStrokesLenRef = useRef(state.strokes.length);

  // Inject styles
  useEffect(() => {
    if (!document.getElementById(STYLE_ID)) {
      const style = document.createElement('style');
      style.id = STYLE_ID;
      style.textContent = cssText;
      document.head.appendChild(style);
    }
    return () => {
      const el = document.getElementById(STYLE_ID);
      if (el) el.remove();
    };
  }, []);

  // Full redraw on undo/redo/clear (strokes array replaced)
  useEffect(() => {
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;

    // Detect if we need a full redraw (undo/redo/clear changes the array identity)
    if (state.strokes.length !== prevStrokesLenRef.current || state.strokes.length === 0) {
      fullRedraw(ctx, state.strokes, state.canvasWidth, state.canvasHeight);
    }
    prevStrokesLenRef.current = state.strokes.length;
  }, [state.strokes, state.canvasWidth, state.canvasHeight]);

  return (
    <div className={`${P}-container`}>
      <Toolbar state={state} dispatch={dispatch} />
      <CanvasArea state={state} dispatch={dispatch} canvasRef={canvasRef} />
    </div>
  );
};

export default DrawingWhiteboard;
