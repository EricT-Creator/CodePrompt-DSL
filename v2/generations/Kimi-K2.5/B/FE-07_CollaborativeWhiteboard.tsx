import React, { useRef, useEffect, useReducer } from 'react';

type Tool = 'pen' | 'eraser';
type Point = { x: number; y: number };
type Stroke = { points: Point[]; color: string; size: number; tool: Tool };

interface State {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  tool: Tool;
  color: string;
  brushSize: number;
  history: Stroke[][];
  historyIndex: number;
}

type Action =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'SET_TOOL'; tool: Tool }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_BRUSH_SIZE'; size: number }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

const COLORS = ['#000000', '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffffff'];

const initialState: State = {
  strokes: [],
  currentStroke: null,
  tool: 'pen',
  color: '#000000',
  brushSize: 3,
  history: [[]],
  historyIndex: 0,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'START_STROKE':
      return {
        ...state,
        currentStroke: {
          points: [action.point],
          color: state.tool === 'eraser' ? '#ffffff' : state.color,
          size: state.brushSize,
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
      const newStrokes = [...state.strokes, state.currentStroke];
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      return {
        ...state,
        strokes: newStrokes,
        currentStroke: null,
        history: [...newHistory, newStrokes],
        historyIndex: newHistory.length,
      };
    case 'SET_TOOL':
      return { ...state, tool: action.tool };
    case 'SET_COLOR':
      return { ...state, color: action.color };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    case 'UNDO':
      if (state.historyIndex <= 0) return state;
      return {
        ...state,
        strokes: state.history[state.historyIndex - 1],
        historyIndex: state.historyIndex - 1,
      };
    case 'REDO':
      if (state.historyIndex >= state.history.length - 1) return state;
      return {
        ...state,
        strokes: state.history[state.historyIndex + 1],
        historyIndex: state.historyIndex + 1,
      };
    case 'CLEAR':
      const clearedHistory = state.history.slice(0, state.historyIndex + 1);
      return {
        ...state,
        strokes: [],
        history: [...clearedHistory, []],
        historyIndex: clearedHistory.length,
      };
    default:
      return state;
  }
}

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  const getPoint = (e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
  };

  const handleStart = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawingRef.current = true;
    dispatch({ type: 'START_STROKE', point: getPoint(e) });
  };

  const handleMove = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (!isDrawingRef.current) return;
    dispatch({ type: 'ADD_POINT', point: getPoint(e) });
  };

  const handleEnd = () => {
    if (isDrawingRef.current) {
      isDrawingRef.current = false;
      dispatch({ type: 'END_STROKE' });
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    [...state.strokes, state.currentStroke].filter(Boolean).forEach((stroke) => {
      if (!stroke || stroke.points.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.size;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      for (let i = 1; i < stroke.points.length; i++) {
        ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
      }
      ctx.stroke();
    });
  }, [state.strokes, state.currentStroke]);

  return (
    <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '16px' }}>Collaborative Whiteboard</h2>
      
      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
            style={{
              padding: '8px 16px',
              background: state.tool === 'pen' ? '#2196f3' : '#f5f5f5',
              color: state.tool === 'pen' ? 'white' : '#333',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Pen
          </button>
          <button
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
            style={{
              padding: '8px 16px',
              background: state.tool === 'eraser' ? '#2196f3' : '#f5f5f5',
              color: state.tool === 'eraser' ? 'white' : '#333',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Eraser
          </button>
        </div>

        <div style={{ display: 'flex', gap: '4px' }}>
          {COLORS.map((c) => (
            <button
              key={c}
              onClick={() => dispatch({ type: 'SET_COLOR', color: c })}
              style={{
                width: '28px',
                height: '28px',
                background: c,
                border: state.color === c ? '3px solid #333' : '2px solid #ddd',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            />
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Size:</span>
          <input
            type="range"
            min="1"
            max="20"
            value={state.brushSize}
            onChange={(e) => dispatch({ type: 'SET_BRUSH_SIZE', size: parseInt(e.target.value) })}
            style={{ width: '100px' }}
          />
          <span>{state.brushSize}px</span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.historyIndex <= 0}
            style={{
              padding: '8px 16px',
              background: state.historyIndex > 0 ? '#f5f5f5' : '#e0e0e0',
              border: 'none',
              borderRadius: '4px',
              cursor: state.historyIndex > 0 ? 'pointer' : 'not-allowed',
            }}
          >
            Undo
          </button>
          <button
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.historyIndex >= state.history.length - 1}
            style={{
              padding: '8px 16px',
              background: state.historyIndex < state.history.length - 1 ? '#f5f5f5' : '#e0e0e0',
              border: 'none',
              borderRadius: '4px',
              cursor: state.historyIndex < state.history.length - 1 ? 'pointer' : 'not-allowed',
            }}
          >
            Redo
          </button>
          <button
            onClick={() => dispatch({ type: 'CLEAR' })}
            style={{
              padding: '8px 16px',
              background: '#ff5722',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        onMouseDown={handleStart}
        onMouseMove={handleMove}
        onMouseUp={handleEnd}
        onMouseLeave={handleEnd}
        onTouchStart={handleStart}
        onTouchMove={handleMove}
        onTouchEnd={handleEnd}
        style={{
          border: '2px solid #ddd',
          borderRadius: '8px',
          cursor: 'crosshair',
          touchAction: 'none',
        }}
      />
    </div>
  );
}
