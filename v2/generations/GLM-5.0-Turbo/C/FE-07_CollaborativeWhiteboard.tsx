import React, { useReducer, useRef, useCallback, useEffect } from 'react';

type Tool = 'pen' | 'eraser';
type Action =
  | { type: 'SET_TOOL'; payload: Tool }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_BRUSH_SIZE'; payload: number }
  | { type: 'ADD_STROKE'; payload: Stroke }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  tool: Tool;
  color: string;
  size: number;
  points: Point[];
}

interface CanvasState {
  tool: Tool;
  color: string;
  brushSize: number;
  strokes: Stroke[];
  redoStack: Stroke[];
  currentStroke: Stroke | null;
}

const COLORS = ['#1e293b', '#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#ec4899'];

function reducer(state: CanvasState, action: Action): CanvasState {
  switch (action.type) {
    case 'SET_TOOL':
      return { ...state, tool: action.payload };
    case 'SET_COLOR':
      return { ...state, color: action.payload, tool: 'pen' };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.payload };
    case 'ADD_STROKE':
      return {
        ...state,
        strokes: [...state.strokes, action.payload],
        redoStack: [],
        currentStroke: null,
      };
    case 'UNDO': {
      if (state.strokes.length === 0) return state;
      const last = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, last],
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
    case 'CLEAR':
      return {
        ...state,
        strokes: [],
        redoStack: [],
        currentStroke: null,
      };
    default:
      return state;
  }
}

function getCanvasPos(e: React.MouseEvent | React.TouchEvent | MouseEvent | TouchEvent, canvas: HTMLCanvasElement): Point {
  const rect = canvas.getBoundingClientRect();
  let clientX: number;
  let clientY: number;
  if ('touches' in e) {
    clientX = e.touches[0].clientX;
    clientY = e.touches[0].clientY;
  } else {
    clientX = (e as MouseEvent).clientX;
    clientY = (e as MouseEvent).clientY;
  }
  return {
    x: (clientX - rect.left) * (canvas.width / rect.width),
    y: (clientY - rect.top) * (canvas.height / rect.height),
  };
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length < 2) return;
  ctx.save();
  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
  }
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.size;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    const midX = (stroke.points[i - 1].x + stroke.points[i].x) / 2;
    const midY = (stroke.points[i - 1].y + stroke.points[i].y) / 2;
    ctx.quadraticCurveTo(stroke.points[i - 1].x, stroke.points[i - 1].y, midX, midY);
  }
  ctx.stroke();
  ctx.restore();
}

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[]) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
}

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(reducer, {
    tool: 'pen',
    color: COLORS[0],
    brushSize: 3,
    strokes: [],
    redoStack: [],
    currentStroke: null,
  });

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);
  const currentStrokeRef = useRef<Stroke | null>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  const getCtx = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const ctx = canvas.getContext('2d');
    return ctx;
  }, []);

  const startDraw = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      const canvas = canvasRef.current;
      const ctx = getCtx();
      if (!canvas || !ctx) return;
      e.preventDefault();
      drawingRef.current = true;
      const pos = getCanvasPos(e, canvas);
      const s = stateRef.current;
      const stroke: Stroke = {
        tool: s.tool,
        color: s.tool === 'eraser' ? '#000000' : s.color,
        size: s.tool === 'eraser' ? s.brushSize * 4 : s.brushSize,
        points: [pos],
      };
      currentStrokeRef.current = stroke;
    },
    [getCtx]
  );

  const moveDraw = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      if (!drawingRef.current || !currentStrokeRef.current) return;
      const canvas = canvasRef.current;
      const ctx = getCtx();
      if (!canvas || !ctx) return;
      e.preventDefault();
      const pos = getCanvasPos(e, canvas);
      const stroke = currentStrokeRef.current;
      const prevPoints = stroke.points;
      stroke.points = [...prevPoints, pos];
      redrawAll(ctx, [...stateRef.current.strokes, stroke]);
    },
    [getCtx]
  );

  const endDraw = useCallback(() => {
    if (!drawingRef.current || !currentStrokeRef.current) return;
    drawingRef.current = false;
    const stroke = currentStrokeRef.current;
    if (stroke.points.length >= 2) {
      dispatch({ type: 'ADD_STROKE', payload: stroke });
    }
    currentStrokeRef.current = null;
    const ctx = getCtx();
    if (ctx) {
      redrawAll(ctx, stateRef.current.strokes);
    }
  }, [getCtx]);

  useEffect(() => {
    const ctx = getCtx();
    if (ctx && canvasRef.current) {
      redrawAll(ctx, state.strokes);
    }
  }, [state.strokes, getCtx]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          dispatch({ type: 'REDO' });
        } else {
          dispatch({ type: 'UNDO' });
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div style={wrapperStyle}>
      <div style={toolbarStyle}>
        <div style={toolGroupStyle}>
          <button
            style={{ ...btnStyle, ...(state.tool === 'pen' ? btnActiveStyle : {}) }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
          >
            ✏️ Pen
          </button>
          <button
            style={{ ...btnStyle, ...(state.tool === 'eraser' ? btnActiveStyle : {}) }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
          >
            🧹 Eraser
          </button>
        </div>

        <div style={toolGroupStyle}>
          {COLORS.map((c) => (
            <button
              key={c}
              onClick={() => dispatch({ type: 'SET_COLOR', payload: c })}
              style={{
                ...colorBtnStyle,
                backgroundColor: c,
                ...(state.color === c && state.tool === 'pen' ? { outline: '3px solid #3b82f6', outlineOffset: 2 } : {}),
              }}
              title={c}
            />
          ))}
        </div>

        <div style={toolGroupStyle}>
          <label style={{ fontSize: 13, color: '#64748b' }}>Size:</label>
          <input
            type="range"
            min="1"
            max="20"
            value={state.brushSize}
            onChange={(e) => dispatch({ type: 'SET_BRUSH_SIZE', payload: Number(e.target.value) })}
            style={{ width: 80 }}
          />
          <span style={{ fontSize: 12, color: '#94a3b8', minWidth: 20 }}>{state.brushSize}px</span>
        </div>

        <div style={toolGroupStyle}>
          <button
            style={btnStyle}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.strokes.length === 0}
            title="Undo (Ctrl+Z)"
          >
            ↩ Undo
          </button>
          <button
            style={btnStyle}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.redoStack.length === 0}
            title="Redo (Ctrl+Shift+Z)"
          >
            ↪ Redo
          </button>
          <button
            style={{ ...btnStyle, color: '#ef4444' }}
            onClick={() => dispatch({ type: 'CLEAR' })}
            title="Clear All"
          >
            🗑 Clear
          </button>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        width={1200}
        height={700}
        style={canvasStyle}
        onMouseDown={startDraw}
        onMouseMove={moveDraw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
        onTouchStart={startDraw}
        onTouchMove={moveDraw}
        onTouchEnd={endDraw}
      />

      <div style={statusBarStyle}>
        <span>Strokes: {state.strokes.length}</span>
        <span>Redo: {state.redoStack.length}</span>
        <span>Tool: {state.tool}</span>
      </div>
    </div>
  );
}

const wrapperStyle: React.CSSProperties = {
  maxWidth: 1240,
  margin: '20px auto',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  background: '#fff',
  borderRadius: 12,
  border: '1px solid #e2e8f0',
  overflow: 'hidden',
  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
};

const toolbarStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 16,
  padding: '12px 16px',
  borderBottom: '1px solid #e2e8f0',
  background: '#f8fafc',
  flexWrap: 'wrap',
};

const toolGroupStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
};

const btnStyle: React.CSSProperties = {
  padding: '6px 12px',
  fontSize: 13,
  fontWeight: 500,
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  background: '#fff',
  color: '#334155',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: 4,
};

const btnActiveStyle: React.CSSProperties = {
  background: '#3b82f6',
  color: '#fff',
  borderColor: '#3b82f6',
};

const colorBtnStyle: React.CSSProperties = {
  width: 26,
  height: 26,
  borderRadius: '50%',
  border: '2px solid #e2e8f0',
  cursor: 'pointer',
  padding: 0,
};

const canvasStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  cursor: 'crosshair',
  background: '#ffffff',
};

const statusBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 16,
  padding: '8px 16px',
  fontSize: 12,
  color: '#94a3b8',
  borderTop: '1px solid #f1f5f9',
  background: '#fafbfc',
};
