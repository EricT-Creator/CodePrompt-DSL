import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

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

interface WhiteboardState {
  currentTool: 'pen' | 'eraser';
  currentColor: string;
  penSize: number;
  eraserSize: number;
  isDrawing: boolean;
  currentStroke: Point[];
  strokes: Stroke[];
  redoStack: Stroke[];
  canvasSize: { width: number; height: number };
  cursorPos: Point | null;
}

type WhiteboardAction =
  | { type: 'SELECT_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'SELECT_COLOR'; color: string }
  | { type: 'SET_PEN_SIZE'; size: number }
  | { type: 'SET_ERASER_SIZE'; size: number }
  | { type: 'START_DRAWING'; point: Point }
  | { type: 'DRAW'; point: Point }
  | { type: 'END_DRAWING' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'RESIZE_CANVAS'; size: { width: number; height: number } }
  | { type: 'UPDATE_CURSOR'; pos: Point | null };

// ─── Constants ───────────────────────────────────────────────────────────────

const COLORS = ['#000000', '#e53935', '#1e88e5', '#43a047', '#fb8c00', '#8e24aa', '#00acc1', '#6d4c41'];
const PEN_SIZES = [2, 4, 6, 10, 16];
const ERASER_SIZES = [10, 20, 30, 50];

// ─── Styles ──────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    background: '#f5f5f5',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 16px',
    background: '#fff',
    borderBottom: '1px solid #e0e0e0',
    flexWrap: 'wrap',
  },
  toolGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  separator: {
    width: 1,
    height: 28,
    background: '#e0e0e0',
    margin: '0 4px',
  },
  toolBtn: {
    padding: '6px 14px',
    border: '1px solid #ddd',
    borderRadius: 6,
    background: '#fff',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
    color: '#555',
    transition: 'all 0.15s',
  },
  toolBtnActive: {
    background: '#e3f2fd',
    borderColor: '#1e88e5',
    color: '#1e88e5',
  },
  colorSwatch: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    border: '2px solid transparent',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  colorSwatchActive: {
    border: '2px solid #333',
    boxShadow: '0 0 0 2px #fff, 0 0 0 4px #333',
  },
  sizeBtn: {
    padding: '4px 10px',
    border: '1px solid #ddd',
    borderRadius: 4,
    background: '#fff',
    cursor: 'pointer',
    fontSize: 12,
    color: '#666',
  },
  sizeBtnActive: {
    background: '#e8eaf6',
    borderColor: '#5c6bc0',
    color: '#5c6bc0',
  },
  actionBtn: {
    padding: '6px 14px',
    border: '1px solid #ddd',
    borderRadius: 6,
    background: '#fff',
    cursor: 'pointer',
    fontSize: 13,
    color: '#555',
  },
  actionBtnDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
  },
  canvasContainer: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    padding: 16,
  },
  canvas: {
    background: '#ffffff',
    borderRadius: 8,
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
    cursor: 'crosshair',
  },
  statusBar: {
    padding: '6px 16px',
    background: '#fff',
    borderTop: '1px solid #e0e0e0',
    fontSize: 12,
    color: '#999',
    display: 'flex',
    justifyContent: 'space-between',
  },
  label: {
    fontSize: 11,
    color: '#999',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    marginRight: 4,
  },
};

// ─── Reducer ─────────────────────────────────────────────────────────────────

const initialState: WhiteboardState = {
  currentTool: 'pen',
  currentColor: '#000000',
  penSize: 4,
  eraserSize: 20,
  isDrawing: false,
  currentStroke: [],
  strokes: [],
  redoStack: [],
  canvasSize: { width: 900, height: 600 },
  cursorPos: null,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'SELECT_TOOL':
      return { ...state, currentTool: action.tool };

    case 'SELECT_COLOR':
      return { ...state, currentColor: action.color };

    case 'SET_PEN_SIZE':
      return { ...state, penSize: action.size };

    case 'SET_ERASER_SIZE':
      return { ...state, eraserSize: action.size };

    case 'START_DRAWING':
      return {
        ...state,
        isDrawing: true,
        currentStroke: [action.point],
      };

    case 'DRAW':
      if (!state.isDrawing) return state;
      return {
        ...state,
        currentStroke: [...state.currentStroke, action.point],
      };

    case 'END_DRAWING': {
      if (!state.isDrawing || state.currentStroke.length === 0) {
        return { ...state, isDrawing: false, currentStroke: [] };
      }
      const newStroke: Stroke = {
        points: state.currentStroke,
        tool: state.currentTool,
        color: state.currentColor,
        size: state.currentTool === 'pen' ? state.penSize : state.eraserSize,
        timestamp: Date.now(),
      };
      return {
        ...state,
        isDrawing: false,
        currentStroke: [],
        strokes: [...state.strokes, newStroke],
        redoStack: [], // clear redo on new stroke
      };
    }

    case 'UNDO': {
      if (state.strokes.length === 0) return state;
      const popped = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, popped],
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const restored = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, restored],
        redoStack: state.redoStack.slice(0, -1),
      };
    }

    case 'CLEAR_CANVAS':
      return {
        ...state,
        strokes: [],
        redoStack: [],
        currentStroke: [],
        isDrawing: false,
      };

    case 'RESIZE_CANVAS':
      return { ...state, canvasSize: action.size };

    case 'UPDATE_CURSOR':
      return { ...state, cursorPos: action.pos };

    default:
      return state;
  }
}

// ─── Canvas Drawing Helpers ──────────────────────────────────────────────────

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length === 0) return;

  ctx.save();
  ctx.beginPath();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = stroke.size;

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
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

function redrawCanvas(
  ctx: CanvasRenderingContext2D,
  strokes: Stroke[],
  size: { width: number; height: number },
): void {
  ctx.clearRect(0, 0, size.width, size.height);
  // White background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, size.width, size.height);
  strokes.forEach((stroke) => drawStroke(ctx, stroke));
}

function getCanvasCoordinates(canvas: HTMLCanvasElement, e: React.MouseEvent): Point {
  const rect = canvas.getBoundingClientRect();
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
  };
}

// ─── Main Component ──────────────────────────────────────────────────────────

const Whiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  // Redraw canvas when strokes change (for undo/redo/clear)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawCanvas(ctx, state.strokes, state.canvasSize);
  }, [state.strokes, state.canvasSize]);

  // Draw current stroke in real-time
  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const point = getCanvasCoordinates(canvas, e);
      isDrawingRef.current = true;
      dispatch({ type: 'START_DRAWING', point });

      // Draw immediate dot
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.save();
        ctx.beginPath();
        ctx.lineCap = 'round';
        ctx.lineWidth = state.currentTool === 'pen' ? state.penSize : state.eraserSize;
        if (state.currentTool === 'eraser') {
          ctx.globalCompositeOperation = 'destination-out';
          ctx.strokeStyle = 'rgba(0,0,0,1)';
        } else {
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle = state.currentColor;
        }
        ctx.moveTo(point.x, point.y);
        ctx.lineTo(point.x + 0.1, point.y + 0.1);
        ctx.stroke();
        ctx.restore();
      }
    },
    [state.currentTool, state.currentColor, state.penSize, state.eraserSize],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const point = getCanvasCoordinates(canvas, e);
      dispatch({ type: 'UPDATE_CURSOR', pos: point });

      if (!isDrawingRef.current) return;
      dispatch({ type: 'DRAW', point });

      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.save();
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.lineWidth = state.currentTool === 'pen' ? state.penSize : state.eraserSize;
        if (state.currentTool === 'eraser') {
          ctx.globalCompositeOperation = 'destination-out';
          ctx.strokeStyle = 'rgba(0,0,0,1)';
        } else {
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle = state.currentColor;
        }
        const prevPoints = state.currentStroke;
        if (prevPoints.length > 0) {
          const prev = prevPoints[prevPoints.length - 1];
          ctx.beginPath();
          ctx.moveTo(prev.x, prev.y);
          ctx.lineTo(point.x, point.y);
          ctx.stroke();
        }
        ctx.restore();
      }
    },
    [state.currentTool, state.currentColor, state.penSize, state.eraserSize, state.currentStroke],
  );

  const handleMouseUp = useCallback(() => {
    isDrawingRef.current = false;
    dispatch({ type: 'END_DRAWING' });
  }, []);

  const handleMouseLeave = useCallback(() => {
    dispatch({ type: 'UPDATE_CURSOR', pos: null });
    if (isDrawingRef.current) {
      isDrawingRef.current = false;
      dispatch({ type: 'END_DRAWING' });
    }
  }, []);

  return (
    <div style={s.wrapper}>
      {/* Toolbar */}
      <div style={s.toolbar}>
        {/* Tools */}
        <div style={s.toolGroup}>
          <span style={s.label}>Tool</span>
          <button
            style={{ ...s.toolBtn, ...(state.currentTool === 'pen' ? s.toolBtnActive : {}) }}
            onClick={() => dispatch({ type: 'SELECT_TOOL', tool: 'pen' })}
          >
            ✏️ Pen
          </button>
          <button
            style={{ ...s.toolBtn, ...(state.currentTool === 'eraser' ? s.toolBtnActive : {}) }}
            onClick={() => dispatch({ type: 'SELECT_TOOL', tool: 'eraser' })}
          >
            🧹 Eraser
          </button>
        </div>

        <div style={s.separator} />

        {/* Colors */}
        <div style={s.toolGroup}>
          <span style={s.label}>Color</span>
          {COLORS.map((color) => (
            <div
              key={color}
              style={{
                ...s.colorSwatch,
                background: color,
                ...(state.currentColor === color ? s.colorSwatchActive : {}),
              }}
              onClick={() => dispatch({ type: 'SELECT_COLOR', color })}
            />
          ))}
        </div>

        <div style={s.separator} />

        {/* Size */}
        <div style={s.toolGroup}>
          <span style={s.label}>Size</span>
          {(state.currentTool === 'pen' ? PEN_SIZES : ERASER_SIZES).map((sz) => {
            const active = state.currentTool === 'pen' ? state.penSize === sz : state.eraserSize === sz;
            return (
              <button
                key={sz}
                style={{ ...s.sizeBtn, ...(active ? s.sizeBtnActive : {}) }}
                onClick={() =>
                  dispatch(
                    state.currentTool === 'pen'
                      ? { type: 'SET_PEN_SIZE', size: sz }
                      : { type: 'SET_ERASER_SIZE', size: sz },
                  )
                }
              >
                {sz}px
              </button>
            );
          })}
        </div>

        <div style={s.separator} />

        {/* Actions */}
        <div style={s.toolGroup}>
          <button
            style={{ ...s.actionBtn, ...(state.strokes.length === 0 ? s.actionBtnDisabled : {}) }}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.strokes.length === 0}
          >
            ↩ Undo
          </button>
          <button
            style={{ ...s.actionBtn, ...(state.redoStack.length === 0 ? s.actionBtnDisabled : {}) }}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.redoStack.length === 0}
          >
            ↪ Redo
          </button>
          <button style={s.actionBtn} onClick={() => dispatch({ type: 'CLEAR_CANVAS' })}>
            🗑 Clear
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div style={s.canvasContainer}>
        <canvas
          ref={canvasRef}
          width={state.canvasSize.width}
          height={state.canvasSize.height}
          style={s.canvas}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        />
      </div>

      {/* Status Bar */}
      <div style={s.statusBar}>
        <span>
          {state.currentTool === 'pen' ? '✏️ Pen' : '🧹 Eraser'} | {state.currentColor} |{' '}
          {state.currentTool === 'pen' ? state.penSize : state.eraserSize}px
        </span>
        <span>
          {state.cursorPos
            ? `(${Math.round(state.cursorPos.x)}, ${Math.round(state.cursorPos.y)})`
            : '—'}{' '}
          | Strokes: {state.strokes.length}
        </span>
      </div>
    </div>
  );
};

export default Whiteboard;
