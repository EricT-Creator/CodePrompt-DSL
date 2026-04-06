import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ── Types ──

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
  tool: 'pen' | 'eraser';
  color: string;
  isDrawing: boolean;
}

type WhiteboardAction =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; color: string };

// ── Constants ──

const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 600;
const PEN_WIDTH = 3;
const ERASER_WIDTH = 20;
const MAX_UNDO = 50;

// ── Reducer ──

let strokeIdCounter = 0;

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  tool: 'pen',
  color: '#000000',
  isDrawing: false,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const newUndoStack = [...state.undoStack, [...state.strokes]];
      if (newUndoStack.length > MAX_UNDO) newUndoStack.shift();
      const newStroke: Stroke = {
        id: `stroke-${++strokeIdCounter}`,
        tool: state.tool,
        color: state.color,
        lineWidth: state.tool === 'pen' ? PEN_WIDTH : ERASER_WIDTH,
        points: [action.point],
      };
      return {
        ...state,
        currentStroke: newStroke,
        undoStack: newUndoStack,
        redoStack: [],
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
      if (!state.currentStroke) return { ...state, isDrawing: false };
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'UNDO': {
      if (state.undoStack.length === 0) return state;
      const prevStrokes = state.undoStack[state.undoStack.length - 1];
      return {
        ...state,
        redoStack: [...state.redoStack, [...state.strokes]],
        strokes: prevStrokes,
        undoStack: state.undoStack.slice(0, -1),
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        undoStack: [...state.undoStack, [...state.strokes]],
        strokes: nextStrokes,
        redoStack: state.redoStack.slice(0, -1),
      };
    }

    case 'CLEAR': {
      const newUndoStack = [...state.undoStack, [...state.strokes]];
      if (newUndoStack.length > MAX_UNDO) newUndoStack.shift();
      return {
        ...state,
        strokes: [],
        undoStack: newUndoStack,
        redoStack: [],
      };
    }

    case 'SET_TOOL':
      return { ...state, tool: action.tool };

    case 'SET_COLOR':
      return { ...state, color: action.color };

    default:
      return state;
  }
}

// ── Drawing Utilities ──

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length < 2) return;
  ctx.save();
  ctx.beginPath();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = stroke.lineWidth;

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

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[], current: Stroke | null): void {
  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
  if (current) {
    drawStroke(ctx, current);
  }
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: CANVAS_WIDTH + 40,
    margin: '0 auto',
    padding: 20,
    background: '#f0f2f5',
    minHeight: '100vh',
  },
  title: {
    textAlign: 'center',
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 16,
    color: '#2d3436',
  },
  toolbar: {
    display: 'flex',
    gap: 8,
    marginBottom: 12,
    alignItems: 'center',
    flexWrap: 'wrap',
    padding: '8px 12px',
    background: '#fff',
    borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  toolGroup: {
    display: 'flex',
    gap: 4,
    alignItems: 'center',
  },
  button: {
    padding: '6px 14px',
    borderRadius: 6,
    border: '1px solid #ddd',
    background: '#fff',
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: 500,
    transition: 'all 0.15s',
  },
  buttonActive: {
    background: '#2d3436',
    color: '#fff',
    borderColor: '#2d3436',
  },
  separator: {
    width: 1,
    height: 28,
    background: '#ddd',
    margin: '0 6px',
  },
  canvas: {
    display: 'block',
    borderRadius: 8,
    boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
    cursor: 'crosshair',
    background: '#fff',
  },
  colorInput: {
    width: 32,
    height: 32,
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    padding: 0,
  },
  label: {
    fontSize: 12,
    color: '#636e72',
    fontWeight: 600,
  },
};

// ── Toolbar Component ──

const Toolbar: React.FC<{
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}> = ({ state, dispatch }) => (
  <div style={styles.toolbar}>
    <span style={styles.label}>Tool:</span>
    <div style={styles.toolGroup}>
      <button
        style={{
          ...styles.button,
          ...(state.tool === 'pen' ? styles.buttonActive : {}),
        }}
        onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
      >
        ✏️ Pen
      </button>
      <button
        style={{
          ...styles.button,
          ...(state.tool === 'eraser' ? styles.buttonActive : {}),
        }}
        onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
      >
        🧹 Eraser
      </button>
    </div>

    <div style={styles.separator} />

    <span style={styles.label}>Color:</span>
    <input
      type="color"
      value={state.color}
      onChange={(e) => dispatch({ type: 'SET_COLOR', color: e.target.value })}
      style={styles.colorInput}
    />

    <div style={styles.separator} />

    <button
      style={{
        ...styles.button,
        opacity: state.undoStack.length === 0 ? 0.4 : 1,
      }}
      onClick={() => dispatch({ type: 'UNDO' })}
      disabled={state.undoStack.length === 0}
    >
      ↩ Undo
    </button>
    <button
      style={{
        ...styles.button,
        opacity: state.redoStack.length === 0 ? 0.4 : 1,
      }}
      onClick={() => dispatch({ type: 'REDO' })}
      disabled={state.redoStack.length === 0}
    >
      ↪ Redo
    </button>

    <div style={styles.separator} />

    <button
      style={{ ...styles.button, color: '#d63031', borderColor: '#d63031' }}
      onClick={() => dispatch({ type: 'CLEAR' })}
    >
      🗑 Clear
    </button>
  </div>
);

// ── Whiteboard (root) ──

const Whiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawAll(ctx, state.strokes, state.currentStroke);
  }, [state.strokes, state.currentStroke]);

  const getCanvasPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const point = getCanvasPoint(e);
      dispatch({ type: 'START_STROKE', point });
    },
    [getCanvasPoint]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!stateRef.current.isDrawing) return;
      const point = getCanvasPoint(e);
      dispatch({ type: 'ADD_POINT', point });
    },
    [getCanvasPoint]
  );

  const handleMouseUp = useCallback(() => {
    if (!stateRef.current.isDrawing) return;
    dispatch({ type: 'END_STROKE' });
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (stateRef.current.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  }, []);

  return (
    <div style={styles.container}>
      <div style={styles.title}>Canvas Drawing Whiteboard</div>
      <Toolbar state={state} dispatch={dispatch} />
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        style={styles.canvas}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />
    </div>
  );
};

export default Whiteboard;
