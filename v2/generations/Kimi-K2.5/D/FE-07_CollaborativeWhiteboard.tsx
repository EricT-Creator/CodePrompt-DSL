import React, { useReducer, useRef, useCallback, useEffect } from 'react';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  size: number;
  isEraser: boolean;
}

interface State {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  color: string;
  brushSize: number;
  isEraser: boolean;
  history: Stroke[][];
  historyIndex: number;
}

type Action =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_BRUSH_SIZE'; size: number }
  | { type: 'SET_ERASER'; isEraser: boolean }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

const COLORS = ['#000000', '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffa500', '#800080', '#008000'];

const initialState: State = {
  strokes: [],
  currentStroke: null,
  color: '#000000',
  brushSize: 3,
  isEraser: false,
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
          color: state.isEraser ? '#ffffff' : state.color,
          size: state.brushSize,
          isEraser: state.isEraser,
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
    case 'SET_COLOR':
      return { ...state, color: action.color, isEraser: false };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    case 'SET_ERASER':
      return { ...state, isEraser: action.isEraser };
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

  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke) => {
    if (stroke.points.length < 2) return;
    ctx.beginPath();
    ctx.strokeStyle = stroke.isEraser ? '#ffffff' : stroke.color;
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
    let clientX, clientY;
    if ('touches' in e) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = (e as React.MouseEvent).clientX;
      clientY = (e as React.MouseEvent).clientY;
    }
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  }, []);

  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawingRef.current = true;
    dispatch({ type: 'START_STROKE', point: getPoint(e) });
  }, [getPoint]);

  const handleMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawingRef.current) return;
    e.preventDefault();
    dispatch({ type: 'ADD_POINT', point: getPoint(e) });
  }, [getPoint]);

  const handleEnd = useCallback(() => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    dispatch({ type: 'END_STROKE' });
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h2>协作白板</h2>
      <div style={{ marginBottom: '15px', display: 'flex', gap: '15px', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
          <span>颜色:</span>
          {COLORS.map(color => (
            <button
              key={color}
              onClick={() => dispatch({ type: 'SET_COLOR', color })}
              style={{
                width: '28px',
                height: '28px',
                backgroundColor: color,
                border: state.color === color && !state.isEraser ? '3px solid #333' : '2px solid #ddd',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            />
          ))}
        </div>
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
          <span>笔刷:</span>
          {[2, 5, 10, 20].map(size => (
            <button
              key={size}
              onClick={() => dispatch({ type: 'SET_BRUSH_SIZE', size })}
              style={{
                padding: '5px 12px',
                backgroundColor: state.brushSize === size ? '#2196f3' : '#f0f0f0',
                color: state.brushSize === size ? '#fff' : '#333',
                border: '1px solid #ddd',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              {size}px
            </button>
          ))}
        </div>
        <button
          onClick={() => dispatch({ type: 'SET_ERASER', isEraser: !state.isEraser })}
          style={{
            padding: '8px 16px',
            backgroundColor: state.isEraser ? '#ff5722' : '#f0f0f0',
            color: state.isEraser ? '#fff' : '#333',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          橡皮擦
        </button>
        <button
          onClick={() => dispatch({ type: 'UNDO' })}
          disabled={state.historyIndex <= 0}
          style={{
            padding: '8px 16px',
            backgroundColor: state.historyIndex > 0 ? '#4caf50' : '#ccc',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: state.historyIndex > 0 ? 'pointer' : 'not-allowed',
          }}
        >
          撤销
        </button>
        <button
          onClick={() => dispatch({ type: 'REDO' })}
          disabled={state.historyIndex >= state.history.length - 1}
          style={{
            padding: '8px 16px',
            backgroundColor: state.historyIndex < state.history.length - 1 ? '#4caf50' : '#ccc',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: state.historyIndex < state.history.length - 1 ? 'pointer' : 'not-allowed',
          }}
        >
          重做
        </button>
        <button
          onClick={() => dispatch({ type: 'CLEAR' })}
          style={{
            padding: '8px 16px',
            backgroundColor: '#f44336',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          清除画布
        </button>
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
          borderRadius: '4px',
          cursor: state.isEraser ? 'cell' : 'crosshair',
          backgroundColor: '#ffffff',
        }}
      />
    </div>
  );
}
