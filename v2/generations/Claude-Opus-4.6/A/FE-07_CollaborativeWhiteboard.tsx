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
  undoneStrokes: Stroke[];
  currentStroke: Stroke | null;
  tool: 'pen' | 'eraser';
  color: string;
  brushSize: number;
  isDrawing: boolean;
}

type Action =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_BRUSH_SIZE'; size: number };

const COLORS = ['#000000', '#e53935', '#1e88e5', '#43a047', '#fb8c00', '#8e24aa', '#00acc1'];

const initialState: WhiteboardState = {
  strokes: [],
  undoneStrokes: [],
  currentStroke: null,
  tool: 'pen',
  color: '#000000',
  brushSize: 3,
  isDrawing: false,
};

function reducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE':
      return {
        ...state,
        isDrawing: true,
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
      if (!state.currentStroke) return { ...state, isDrawing: false };
      return {
        ...state,
        isDrawing: false,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        undoneStrokes: [],
      };
    case 'UNDO':
      if (state.strokes.length === 0) return state;
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        undoneStrokes: [...state.undoneStrokes, state.strokes[state.strokes.length - 1]],
      };
    case 'REDO':
      if (state.undoneStrokes.length === 0) return state;
      return {
        ...state,
        strokes: [...state.strokes, state.undoneStrokes[state.undoneStrokes.length - 1]],
        undoneStrokes: state.undoneStrokes.slice(0, -1),
      };
    case 'CLEAR':
      return { ...state, strokes: [], undoneStrokes: [], currentStroke: null };
    case 'SET_TOOL':
      return { ...state, tool: action.tool };
    case 'SET_COLOR':
      return { ...state, color: action.color };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    default:
      return state;
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length < 2) {
    const p = stroke.points[0];
    if (p) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, stroke.size / 2, 0, Math.PI * 2);
      ctx.fillStyle = stroke.color;
      ctx.fill();
    }
    return;
  }
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
    let clientX: number, clientY: number;
    if ('touches' in e) {
      clientX = e.touches[0]?.clientX ?? e.changedTouches[0]?.clientX ?? 0;
      clientY = e.touches[0]?.clientY ?? e.changedTouches[0]?.clientY ?? 0;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const handlePointerDown = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    const point = getCanvasPoint(e);
    dispatch({ type: 'START_STROKE', point });
  };

  const handlePointerMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!state.isDrawing) return;
    e.preventDefault();
    const point = getCanvasPoint(e);
    dispatch({ type: 'ADD_POINT', point });
  };

  const handlePointerUp = () => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  };

  return (
    <div style={containerStyle}>
      <h2 style={titleStyle}>Collaborative Whiteboard</h2>
      <div style={toolbarStyle}>
        <div style={toolGroupStyle}>
          <button
            style={state.tool === 'pen' ? activeToolBtnStyle : toolBtnStyle}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
          >
            ✏️ Pen
          </button>
          <button
            style={state.tool === 'eraser' ? activeToolBtnStyle : toolBtnStyle}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
          >
            🧹 Eraser
          </button>
        </div>
        <div style={toolGroupStyle}>
          {COLORS.map(c => (
            <button
              key={c}
              style={{
                ...colorBtnStyle,
                backgroundColor: c,
                border: state.color === c ? '3px solid #333' : '2px solid #ccc',
                transform: state.color === c ? 'scale(1.2)' : 'scale(1)',
              }}
              onClick={() => dispatch({ type: 'SET_COLOR', color: c })}
            />
          ))}
        </div>
        <div style={toolGroupStyle}>
          <label style={labelStyle}>Size: {state.brushSize}</label>
          <input
            type="range"
            min={1}
            max={20}
            value={state.brushSize}
            onChange={e => dispatch({ type: 'SET_BRUSH_SIZE', size: Number(e.target.value) })}
            style={sliderStyle}
          />
        </div>
        <div style={toolGroupStyle}>
          <button
            style={toolBtnStyle}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.strokes.length === 0}
          >
            ↩ Undo
          </button>
          <button
            style={toolBtnStyle}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.undoneStrokes.length === 0}
          >
            ↪ Redo
          </button>
          <button
            style={{ ...toolBtnStyle, color: '#e53935' }}
            onClick={() => dispatch({ type: 'CLEAR' })}
          >
            🗑 Clear
          </button>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        style={canvasStyle}
        onMouseDown={handlePointerDown}
        onMouseMove={handlePointerMove}
        onMouseUp={handlePointerUp}
        onMouseLeave={handlePointerUp}
        onTouchStart={handlePointerDown}
        onTouchMove={handlePointerMove}
        onTouchEnd={handlePointerUp}
      />
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  maxWidth: '840px',
  margin: '20px auto',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const titleStyle: React.CSSProperties = {
  textAlign: 'center',
  color: '#333',
  marginBottom: '12px',
};

const toolbarStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '12px',
  alignItems: 'center',
  padding: '10px 12px',
  background: '#f5f5f5',
  borderRadius: '8px 8px 0 0',
  border: '1px solid #ddd',
  borderBottom: 'none',
};

const toolGroupStyle: React.CSSProperties = {
  display: 'flex',
  gap: '6px',
  alignItems: 'center',
};

const toolBtnStyle: React.CSSProperties = {
  padding: '6px 12px',
  border: '1px solid #ccc',
  borderRadius: '6px',
  background: '#fff',
  cursor: 'pointer',
  fontSize: '13px',
};

const activeToolBtnStyle: React.CSSProperties = {
  ...toolBtnStyle,
  background: '#1976d2',
  color: '#fff',
  borderColor: '#1565c0',
};

const colorBtnStyle: React.CSSProperties = {
  width: '26px',
  height: '26px',
  borderRadius: '50%',
  cursor: 'pointer',
  padding: 0,
  transition: 'transform 0.15s',
};

const labelStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#555',
  minWidth: '50px',
};

const sliderStyle: React.CSSProperties = {
  width: '80px',
};

const canvasStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  border: '1px solid #ddd',
  borderRadius: '0 0 8px 8px',
  cursor: 'crosshair',
  touchAction: 'none',
  background: '#fff',
};

export default CollaborativeWhiteboard;
