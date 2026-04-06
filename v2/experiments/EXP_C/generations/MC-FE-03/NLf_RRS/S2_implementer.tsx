import React, { useReducer, useEffect, useRef, useCallback } from 'react';

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

const PREFIX = 'dwb_';
const MAX_UNDO = 50;

const PRESET_COLORS = [
  '#1a1a2e', '#e74c3c', '#e67e22', '#f1c40f',
  '#2ecc71', '#3498db', '#9b59b6', '#ecf0f1',
];

const LINE_WIDTHS = [2, 4, 8, 14, 24];

let strokeIdCounter = 0;
const genStrokeId = (): string => `stroke-${Date.now()}-${++strokeIdCounter}`;

// ── Styles ──────────────────────────────────────────────────────────────────

const cssText = `
.${PREFIX}container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: #f0f2f5;
  min-height: 100vh;
}
.${PREFIX}toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.${PREFIX}toolGroup {
  display: flex;
  align-items: center;
  gap: 6px;
}
.${PREFIX}divider {
  width: 1px;
  height: 28px;
  background: #e0e0e0;
  margin: 0 4px;
}
.${PREFIX}toolBtn {
  padding: 8px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  transition: all 0.15s;
}
.${PREFIX}toolBtn:hover {
  background: #f5f5f5;
}
.${PREFIX}toolBtnActive {
  background: #5b6abf;
  color: #fff;
  border-color: #5b6abf;
}
.${PREFIX}toolBtnDisabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.${PREFIX}colorSwatch {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 0.1s;
}
.${PREFIX}colorSwatch:hover {
  transform: scale(1.15);
}
.${PREFIX}colorSwatchActive {
  border-color: #333;
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px #5b6abf;
}
.${PREFIX}colorInput {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  padding: 0;
}
.${PREFIX}widthBtn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}
.${PREFIX}widthBtnActive {
  border-color: #5b6abf;
  background: #eef0ff;
}
.${PREFIX}widthDot {
  border-radius: 50%;
  background: #333;
}
.${PREFIX}canvasWrap {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  overflow: hidden;
  cursor: crosshair;
}
.${PREFIX}canvas {
  display: block;
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
  lineWidth: 4,
  isDrawing: false,
  canvasWidth: 900,
  canvasHeight: 560,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const stroke: Stroke = {
        id: genStrokeId(),
        tool: state.activeTool,
        color: state.activeColor,
        lineWidth: state.lineWidth,
        points: [action.point],
      };
      return { ...state, currentStroke: stroke, isDrawing: true };
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
      let undoStack = [...state.undoStack, state.strokes];
      if (undoStack.length > MAX_UNDO) undoStack = undoStack.slice(1);
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        undoStack,
        redoStack: [],
        isDrawing: false,
      };
    }

    case 'UNDO': {
      if (state.undoStack.length === 0) return state;
      const undoStack = [...state.undoStack];
      const prev = undoStack.pop()!;
      return {
        ...state,
        redoStack: [...state.redoStack, state.strokes],
        strokes: prev,
        undoStack,
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const redoStack = [...state.redoStack];
      const next = redoStack.pop()!;
      return {
        ...state,
        undoStack: [...state.undoStack, state.strokes],
        strokes: next,
        redoStack,
      };
    }

    case 'CLEAR_CANVAS': {
      if (state.strokes.length === 0) return state;
      let undoStack = [...state.undoStack, state.strokes];
      if (undoStack.length > MAX_UNDO) undoStack = undoStack.slice(1);
      return {
        ...state,
        strokes: [],
        undoStack,
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

// ── Drawing helpers ─────────────────────────────────────────────────────────

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length < 2) return;
  ctx.save();
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
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

function redrawAll(ctx: CanvasRenderingContext2D, width: number, height: number, strokes: Stroke[], current: Stroke | null): void {
  ctx.clearRect(0, 0, width, height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
  if (current && current.points.length >= 2) {
    drawStroke(ctx, current);
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────

const ColorPicker: React.FC<{
  activeColor: string;
  onSelect: (c: string) => void;
}> = ({ activeColor, onSelect }) => (
  <div className={`${PREFIX}toolGroup`}>
    {PRESET_COLORS.map(c => (
      <div
        key={c}
        className={`${PREFIX}colorSwatch ${c === activeColor ? `${PREFIX}colorSwatchActive` : ''}`}
        style={{ background: c }}
        onClick={() => onSelect(c)}
      />
    ))}
    <input
      type="color"
      className={`${PREFIX}colorInput`}
      value={activeColor}
      onChange={e => onSelect(e.target.value)}
    />
  </div>
);

const ToolButton: React.FC<{
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}> = ({ label, active, disabled, onClick }) => {
  const cls = [
    `${PREFIX}toolBtn`,
    active ? `${PREFIX}toolBtnActive` : '',
    disabled ? `${PREFIX}toolBtnDisabled` : '',
  ].filter(Boolean).join(' ');
  return (
    <button className={cls} onClick={onClick} disabled={disabled}>
      {label}
    </button>
  );
};

// ── Main component ──────────────────────────────────────────────────────────

const DrawingWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const styleRef = useRef<HTMLStyleElement | null>(null);
  const lastPointRef = useRef<Point | null>(null);

  // Inject styles
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = cssText;
    document.head.appendChild(style);
    styleRef.current = style;
    return () => { style.remove(); };
  }, []);

  // Full redraw when strokes change (undo/redo/clear)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawAll(ctx, state.canvasWidth, state.canvasHeight, state.strokes, state.currentStroke);
  }, [state.strokes, state.canvasWidth, state.canvasHeight]);

  const getCanvasPoint = useCallback((e: React.MouseEvent): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const point = getCanvasPoint(e);
    lastPointRef.current = point;
    dispatch({ type: 'START_STROKE', point });
  }, [getCanvasPoint]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!state.isDrawing) return;
    const point = getCanvasPoint(e);
    dispatch({ type: 'ADD_POINT', point });

    // Incremental draw
    const canvas = canvasRef.current;
    if (!canvas || !lastPointRef.current) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.lineWidth = state.lineWidth;

    if (state.activeTool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = state.activeColor;
    }

    ctx.beginPath();
    ctx.moveTo(lastPointRef.current.x, lastPointRef.current.y);
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    ctx.restore();

    lastPointRef.current = point;
  }, [state.isDrawing, state.lineWidth, state.activeTool, state.activeColor, getCanvasPoint]);

  const handleMouseUp = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
      lastPointRef.current = null;
    }
  }, [state.isDrawing]);

  const handleMouseLeave = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
      lastPointRef.current = null;
    }
  }, [state.isDrawing]);

  return (
    <div className={`${PREFIX}container`}>
      <div className={`${PREFIX}toolbar`}>
        <div className={`${PREFIX}toolGroup`}>
          <ToolButton label="✏️ Pen" active={state.activeTool === 'pen'} onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })} />
          <ToolButton label="🧹 Eraser" active={state.activeTool === 'eraser'} onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })} />
        </div>

        <div className={`${PREFIX}divider`} />

        <ColorPicker activeColor={state.activeColor} onSelect={c => dispatch({ type: 'SET_COLOR', color: c })} />

        <div className={`${PREFIX}divider`} />

        <div className={`${PREFIX}toolGroup`}>
          {LINE_WIDTHS.map(w => (
            <div
              key={w}
              className={`${PREFIX}widthBtn ${state.lineWidth === w ? `${PREFIX}widthBtnActive` : ''}`}
              onClick={() => dispatch({ type: 'SET_LINE_WIDTH', width: w })}
            >
              <div className={`${PREFIX}widthDot`} style={{ width: Math.min(w, 18), height: Math.min(w, 18) }} />
            </div>
          ))}
        </div>

        <div className={`${PREFIX}divider`} />

        <div className={`${PREFIX}toolGroup`}>
          <ToolButton label="↩ Undo" disabled={state.undoStack.length === 0} onClick={() => dispatch({ type: 'UNDO' })} />
          <ToolButton label="↪ Redo" disabled={state.redoStack.length === 0} onClick={() => dispatch({ type: 'REDO' })} />
          <ToolButton label="🗑 Clear" disabled={state.strokes.length === 0} onClick={() => dispatch({ type: 'CLEAR_CANVAS' })} />
        </div>
      </div>

      <div className={`${PREFIX}canvasWrap`}>
        <canvas
          ref={canvasRef}
          className={`${PREFIX}canvas`}
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
};

export default DrawingWhiteboard;
