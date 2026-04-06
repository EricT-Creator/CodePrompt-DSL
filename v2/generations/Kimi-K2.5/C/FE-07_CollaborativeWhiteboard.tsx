import React, { useReducer, useRef, useCallback, useEffect } from 'react';

type Tool = 'pen' | 'eraser';
type Point = { x: number; y: number };
type Stroke = {
  points: Point[];
  color: string;
  size: number;
  tool: Tool;
};

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

const COLORS = ['#000000', '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ff8800'];

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
      return { ...state, color: action.color, tool: 'pen' };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    case 'UNDO':
      if (state.historyIndex <= 0) return state;
      const undoIndex = state.historyIndex - 1;
      return {
        ...state,
        strokes: state.history[undoIndex],
        historyIndex: undoIndex,
      };
    case 'REDO':
      if (state.historyIndex >= state.history.length - 1) return state;
      const redoIndex = state.historyIndex + 1;
      return {
        ...state,
        strokes: state.history[redoIndex],
        historyIndex: redoIndex,
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
  const isDrawing = useRef(false);

  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke) => {
    if (stroke.points.length < 2) return;
    
    ctx.beginPath();
    ctx.strokeStyle = stroke.tool === 'eraser' ? '#ffffff' : stroke.color;
    ctx.lineWidth = stroke.size;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    for (let i = 1; i < stroke.points.length; i++) {
      ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
    }
    ctx.stroke();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    state.strokes.forEach(stroke => drawStroke(ctx, stroke));
    
    if (state.currentStroke) {
      drawStroke(ctx, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke, drawStroke]);

  const getPoint = useCallback((e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  }, []);

  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawing.current = true;
    dispatch({ type: 'START_STROKE', point: getPoint(e) });
  }, [getPoint]);

  const handleMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing.current) return;
    e.preventDefault();
    dispatch({ type: 'ADD_POINT', point: getPoint(e) });
  }, [getPoint]);

  const handleEnd = useCallback(() => {
    if (!isDrawing.current) return;
    isDrawing.current = false;
    dispatch({ type: 'END_STROKE' });
  }, []);

  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.history.length - 1;

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '16px' }}>Collaborative Whiteboard</h2>
      
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
            style={{
              padding: '8px 16px',
              backgroundColor: state.tool === 'pen' ? '#4a90d9' : '#f0f0f0',
              color: state.tool === 'pen' ? '#fff' : '#333',
              border: '1px solid #ccc',
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
              backgroundColor: state.tool === 'eraser' ? '#4a90d9' : '#f0f0f0',
              color: state.tool === 'eraser' ? '#fff' : '#333',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Eraser
          </button>
        </div>

        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {COLORS.map(color => (
            <button
              key={color}
              onClick={() => dispatch({ type: 'SET_COLOR', color })}
              style={{
                width: '28px',
                height: '28px',
                backgroundColor: color,
                border: state.color === color && state.tool === 'pen' ? '3px solid #333' : '1px solid #ccc',
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

        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
          <button
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={!canUndo}
            style={{
              padding: '8px 16px',
              backgroundColor: canUndo ? '#f0f0f0' : '#e0e0e0',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: canUndo ? 'pointer' : 'not-allowed',
            }}
          >
            Undo
          </button>
          <button
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={!canRedo}
            style={{
              padding: '8px 16px',
              backgroundColor: canRedo ? '#f0f0f0' : '#e0e0e0',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: canRedo ? 'pointer' : 'not-allowed',
            }}
          >
            Redo
          </button>
          <button
            onClick={() => dispatch({ type: 'CLEAR' })}
            style={{
              padding: '8px 16px',
              backgroundColor: '#ff6b6b',
              color: '#fff',
              border: '1px solid #ff6b6b',
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
          border: '2px solid #333',
          borderRadius: '8px',
          cursor: 'crosshair',
          touchAction: 'none',
          backgroundColor: '#fff',
        }}
      />
    </div>
  );
}
