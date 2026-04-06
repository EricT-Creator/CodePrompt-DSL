import React, { useReducer, useRef, useEffect, useCallback } from 'react';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  size: number;
  tool: 'pen' | 'eraser';
}

interface WhiteboardState {
  strokes: Stroke[];
  undone: Stroke[];
  currentStroke: Stroke | null;
  color: string;
  brushSize: number;
  tool: 'pen' | 'eraser';
}

type Action =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_BRUSH_SIZE'; size: number }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' };

const COLORS = ['#1a1a1a', '#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4'];

const initialState: WhiteboardState = {
  strokes: [],
  undone: [],
  currentStroke: null,
  color: '#1a1a1a',
  brushSize: 3,
  tool: 'pen',
};

function reducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE':
      return {
        ...state,
        currentStroke: {
          points: [action.point],
          color: state.tool === 'eraser' ? '#ffffff' : state.color,
          size: state.tool === 'eraser' ? state.brushSize * 4 : state.brushSize,
          tool: state.tool,
        },
      };
    case 'ADD_POINT':
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.point],
        },
      };
    case 'END_STROKE':
      if (!state.currentStroke) return state;
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        undone: [],
        currentStroke: null,
      };
    case 'UNDO':
      if (state.strokes.length === 0) return state;
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        undone: [...state.undone, state.strokes[state.strokes.length - 1]],
      };
    case 'REDO':
      if (state.undone.length === 0) return state;
      return {
        ...state,
        strokes: [...state.strokes, state.undone[state.undone.length - 1]],
        undone: state.undone.slice(0, -1),
      };
    case 'CLEAR':
      return { ...state, strokes: [], undone: [], currentStroke: null };
    case 'SET_COLOR':
      return { ...state, color: action.color };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    case 'SET_TOOL':
      return { ...state, tool: action.tool };
    default:
      return state;
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length === 0) return;
  ctx.beginPath();
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.size;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
  } else {
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }
  ctx.stroke();
  ctx.globalCompositeOperation = 'source-over';
}

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (const stroke of state.strokes) {
      drawStroke(ctx, stroke);
    }
    if (state.currentStroke) {
      drawStroke(ctx, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke]);

  useEffect(() => {
    redrawCanvas();
  }, [redrawCanvas]);

  const getCanvasPoint = (e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    if ('touches' in e) {
      const touch = e.touches[0] || (e as React.TouchEvent).changedTouches[0];
      return {
        x: (touch.clientX - rect.left) * scaleX,
        y: (touch.clientY - rect.top) * scaleY,
      };
    }
    return {
      x: ((e as React.MouseEvent).clientX - rect.left) * scaleX,
      y: ((e as React.MouseEvent).clientY - rect.top) * scaleY,
    };
  };

  const handlePointerDown = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawingRef.current = true;
    dispatch({ type: 'START_STROKE', point: getCanvasPoint(e) });
  };

  const handlePointerMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawingRef.current) return;
    e.preventDefault();
    dispatch({ type: 'ADD_POINT', point: getCanvasPoint(e) });
  };

  const handlePointerUp = () => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    dispatch({ type: 'END_STROKE' });
  };

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <div style={styles.toolGroup}>
          <button
            style={{
              ...styles.toolBtn,
              ...(state.tool === 'pen' ? styles.toolBtnActive : {}),
            }}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
          >
            ✏️ Pen
          </button>
          <button
            style={{
              ...styles.toolBtn,
              ...(state.tool === 'eraser' ? styles.toolBtnActive : {}),
            }}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
          >
            🧹 Eraser
          </button>
        </div>
        <div style={styles.colorPicker}>
          {COLORS.map(c => (
            <button
              key={c}
              style={{
                ...styles.colorSwatch,
                backgroundColor: c,
                outline: state.color === c ? '3px solid #3b82f6' : '1px solid #d1d5db',
                outlineOffset: '2px',
              }}
              onClick={() => dispatch({ type: 'SET_COLOR', color: c })}
            />
          ))}
        </div>
        <div style={styles.sizeControl}>
          <label style={styles.sizeLabel}>Size: {state.brushSize}px</label>
          <input
            type="range"
            min={1}
            max={20}
            value={state.brushSize}
            onChange={e => dispatch({ type: 'SET_BRUSH_SIZE', size: Number(e.target.value) })}
            style={styles.sizeSlider}
          />
        </div>
        <div style={styles.toolGroup}>
          <button
            style={styles.actionBtn}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.strokes.length === 0}
          >
            ↩ Undo
          </button>
          <button
            style={styles.actionBtn}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.undone.length === 0}
          >
            ↪ Redo
          </button>
          <button
            style={{ ...styles.actionBtn, color: '#ef4444' }}
            onClick={() => dispatch({ type: 'CLEAR' })}
          >
            🗑 Clear
          </button>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={styles.canvas}
        onMouseDown={handlePointerDown}
        onMouseMove={handlePointerMove}
        onMouseUp={handlePointerUp}
        onMouseLeave={handlePointerUp}
        onTouchStart={handlePointerDown}
        onTouchMove={handlePointerMove}
        onTouchEnd={handlePointerUp}
      />
      <div style={styles.statusBar}>
        Tool: {state.tool} | Color: {state.color} | Strokes: {state.strokes.length}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '840px',
    margin: '20px auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
  },
  toolbar: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '16px',
    alignItems: 'center',
    marginBottom: '12px',
    padding: '12px',
    background: '#fff',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
  },
  toolGroup: {
    display: 'flex',
    gap: '8px',
  },
  toolBtn: {
    padding: '6px 14px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    background: '#fff',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
  },
  toolBtnActive: {
    background: '#eff6ff',
    borderColor: '#3b82f6',
    color: '#2563eb',
  },
  colorPicker: {
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
  },
  colorSwatch: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    border: 'none',
    cursor: 'pointer',
    padding: 0,
  },
  sizeControl: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  sizeLabel: {
    fontSize: '12px',
    color: '#6b7280',
    whiteSpace: 'nowrap',
  },
  sizeSlider: {
    width: '80px',
  },
  actionBtn: {
    padding: '6px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    background: '#fff',
    cursor: 'pointer',
    fontSize: '13px',
  },
  canvas: {
    width: '100%',
    height: 'auto',
    display: 'block',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: '#ffffff',
    cursor: 'crosshair',
    touchAction: 'none',
  },
  statusBar: {
    marginTop: '8px',
    fontSize: '12px',
    color: '#9ca3af',
    textAlign: 'center',
  },
};

export default CollaborativeWhiteboard;
