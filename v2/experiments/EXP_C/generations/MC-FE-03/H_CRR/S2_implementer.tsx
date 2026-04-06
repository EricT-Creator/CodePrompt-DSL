import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  id: string;
  tool: 'pen' | 'eraser';
  color: string;
  width: number;
  points: Point[];
}

interface HistoryState {
  past: Stroke[][];
  future: Stroke[][];
}

interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  tool: 'pen' | 'eraser';
  color: string;
  strokeWidth: number;
  history: HistoryState;
}

type WhiteboardAction =
  | { type: 'START_STROKE'; payload: { point: Point } }
  | { type: 'ADD_POINT'; payload: { point: Point } }
  | { type: 'END_STROKE' }
  | { type: 'SET_TOOL'; payload: { tool: 'pen' | 'eraser' } }
  | { type: 'SET_COLOR'; payload: { color: string } }
  | { type: 'SET_WIDTH'; payload: { width: number } }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

// ─── Constants ───────────────────────────────────────────────────────────────

const MAX_HISTORY = 50;

const COLORS = [
  '#000000', '#e03131', '#2f9e44', '#1971c2',
  '#f08c00', '#9c36b5', '#0c8599', '#e8590c',
];

let strokeIdCounter = 0;
const newStrokeId = (): string => `stroke_${++strokeIdCounter}`;

// ─── Styles ──────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: 900,
    margin: '0 auto',
    padding: 20,
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 14px',
    background: '#f8f9fa',
    borderRadius: '8px 8px 0 0',
    border: '1px solid #dee2e6',
    borderBottom: 'none',
    flexWrap: 'wrap' as const,
  },
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  label: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    color: '#868e96',
    marginRight: 2,
  },
  toolBtn: {
    padding: '6px 14px',
    border: '1px solid #dee2e6',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    background: '#fff',
  },
  toolBtnActive: {
    background: '#228be6',
    color: '#fff',
    borderColor: '#228be6',
  },
  colorSwatch: {
    width: 22,
    height: 22,
    borderRadius: '50%',
    border: '2px solid transparent',
    cursor: 'pointer',
  },
  colorSwatchActive: {
    border: '2px solid #228be6',
    boxShadow: '0 0 0 2px #fff, 0 0 0 4px #228be6',
  },
  slider: {
    width: 100,
  },
  actionBtn: {
    padding: '6px 12px',
    border: '1px solid #dee2e6',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    background: '#fff',
  },
  actionBtnDisabled: {
    opacity: 0.4,
    cursor: 'default',
  },
  canvasContainer: {
    border: '1px solid #dee2e6',
    borderRadius: '0 0 8px 8px',
    overflow: 'hidden',
    cursor: 'crosshair',
    touchAction: 'none' as const,
  },
  info: {
    fontSize: 12,
    color: '#868e96',
    marginTop: 8,
  },
};

// ─── Reducer ─────────────────────────────────────────────────────────────────

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  tool: 'pen',
  color: '#000000',
  strokeWidth: 3,
  history: { past: [], future: [] },
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const stroke: Stroke = {
        id: newStrokeId(),
        tool: state.tool,
        color: state.tool === 'eraser' ? 'eraser' : state.color,
        width: state.tool === 'eraser' ? state.strokeWidth * 4 : state.strokeWidth,
        points: [action.payload.point],
      };
      return { ...state, currentStroke: stroke };
    }

    case 'ADD_POINT': {
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.payload.point],
        },
      };
    }

    case 'END_STROKE': {
      if (!state.currentStroke) return state;
      if (state.currentStroke.points.length < 2) {
        return { ...state, currentStroke: null };
      }
      const pastEntry = state.strokes;
      const newPast = [...state.history.past, pastEntry];
      if (newPast.length > MAX_HISTORY) newPast.shift();
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        history: { past: newPast, future: [] },
      };
    }

    case 'SET_TOOL':
      return { ...state, tool: action.payload.tool };

    case 'SET_COLOR':
      return { ...state, color: action.payload.color };

    case 'SET_WIDTH':
      return { ...state, strokeWidth: action.payload.width };

    case 'UNDO': {
      if (state.history.past.length === 0) return state;
      const previous = state.history.past[state.history.past.length - 1];
      return {
        ...state,
        strokes: previous,
        history: {
          past: state.history.past.slice(0, -1),
          future: [state.strokes, ...state.history.future],
        },
      };
    }

    case 'REDO': {
      if (state.history.future.length === 0) return state;
      const next = state.history.future[0];
      return {
        ...state,
        strokes: next,
        history: {
          past: [...state.history.past, state.strokes],
          future: state.history.future.slice(1),
        },
      };
    }

    case 'CLEAR': {
      if (state.strokes.length === 0) return state;
      const pastEntry = state.strokes;
      const newPast = [...state.history.past, pastEntry];
      if (newPast.length > MAX_HISTORY) newPast.shift();
      return {
        ...state,
        strokes: [],
        history: { past: newPast, future: [] },
      };
    }

    default:
      return state;
  }
}

// ─── Drawing helpers ─────────────────────────────────────────────────────────

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length < 2) return;

  ctx.beginPath();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  if (stroke.tool === 'eraser' || stroke.color === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color;
  }

  ctx.lineWidth = stroke.width;
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }

  ctx.stroke();
  ctx.globalCompositeOperation = 'source-over';
}

function redrawCanvas(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  strokes: Stroke[],
  currentStroke: Stroke | null,
): void {
  ctx.clearRect(0, 0, width, height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
  if (currentStroke && currentStroke.points.length >= 2) {
    drawStroke(ctx, currentStroke);
  }
}

// ─── Main Component ──────────────────────────────────────────────────────────

const CANVAS_WIDTH = 860;
const CANVAS_HEIGHT = 500;

const Whiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);

  // Redraw on state change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawCanvas(ctx, CANVAS_WIDTH, CANVAS_HEIGHT, state.strokes, state.currentStroke);
  }, [state.strokes, state.currentStroke]);

  const getPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  const getTouchPoint = useCallback((e: React.TouchEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0];
    return {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
    };
  }, []);

  // Mouse events
  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      isDrawing.current = true;
      dispatch({ type: 'START_STROKE', payload: { point: getPoint(e) } });
    },
    [getPoint],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!isDrawing.current) return;
      dispatch({ type: 'ADD_POINT', payload: { point: getPoint(e) } });
    },
    [getPoint],
  );

  const handleMouseUp = useCallback(() => {
    if (!isDrawing.current) return;
    isDrawing.current = false;
    dispatch({ type: 'END_STROKE' });
  }, []);

  // Touch events
  const handleTouchStart = useCallback(
    (e: React.TouchEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      isDrawing.current = true;
      dispatch({ type: 'START_STROKE', payload: { point: getTouchPoint(e) } });
    },
    [getTouchPoint],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      if (!isDrawing.current) return;
      dispatch({ type: 'ADD_POINT', payload: { point: getTouchPoint(e) } });
    },
    [getTouchPoint],
  );

  const handleTouchEnd = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (!isDrawing.current) return;
    isDrawing.current = false;
    dispatch({ type: 'END_STROKE' });
  }, []);

  const canUndo = state.history.past.length > 0;
  const canRedo = state.history.future.length > 0;

  return (
    <div style={s.container}>
      {/* Toolbar */}
      <div style={s.toolbar}>
        {/* Tool selector */}
        <div style={s.group}>
          <span style={s.label}>Tool</span>
          <button
            style={{ ...s.toolBtn, ...(state.tool === 'pen' ? s.toolBtnActive : {}) }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: { tool: 'pen' } })}
          >
            ✏️ Pen
          </button>
          <button
            style={{ ...s.toolBtn, ...(state.tool === 'eraser' ? s.toolBtnActive : {}) }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: { tool: 'eraser' } })}
          >
            🧹 Eraser
          </button>
        </div>

        {/* Color picker */}
        <div style={s.group}>
          <span style={s.label}>Color</span>
          {COLORS.map((c) => (
            <div
              key={c}
              style={{
                ...s.colorSwatch,
                background: c,
                ...(state.color === c && state.tool === 'pen' ? s.colorSwatchActive : {}),
              }}
              onClick={() => dispatch({ type: 'SET_COLOR', payload: { color: c } })}
            />
          ))}
        </div>

        {/* Stroke width */}
        <div style={s.group}>
          <span style={s.label}>Size {state.strokeWidth}px</span>
          <input
            type="range"
            min={1}
            max={20}
            value={state.strokeWidth}
            onChange={(e) => dispatch({ type: 'SET_WIDTH', payload: { width: Number(e.target.value) } })}
            style={s.slider}
          />
        </div>

        {/* Actions */}
        <div style={s.group}>
          <button
            style={{ ...s.actionBtn, ...(!canUndo ? s.actionBtnDisabled : {}) }}
            onClick={() => canUndo && dispatch({ type: 'UNDO' })}
            disabled={!canUndo}
          >
            ↩ Undo
          </button>
          <button
            style={{ ...s.actionBtn, ...(!canRedo ? s.actionBtnDisabled : {}) }}
            onClick={() => canRedo && dispatch({ type: 'REDO' })}
            disabled={!canRedo}
          >
            ↪ Redo
          </button>
          <button
            style={{ ...s.actionBtn, ...(state.strokes.length === 0 ? s.actionBtnDisabled : {}) }}
            onClick={() => state.strokes.length > 0 && dispatch({ type: 'CLEAR' })}
            disabled={state.strokes.length === 0}
          >
            🗑 Clear
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div style={s.canvasContainer}>
        <canvas
          ref={canvasRef}
          width={CANVAS_WIDTH}
          height={CANVAS_HEIGHT}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          style={{ display: 'block', background: '#ffffff' }}
        />
      </div>

      <div style={s.info}>
        Strokes: {state.strokes.length} · History: {state.history.past.length} undo /{' '}
        {state.history.future.length} redo
      </div>
    </div>
  );
};

export default Whiteboard;
