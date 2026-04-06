import React, { useRef, useReducer, useCallback } from 'react';

type Tool = 'pen' | 'eraser';
type Color = '#000000' | '#ff0000' | '#00ff00' | '#0000ff' | '#ffff00';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: Color;
  size: number;
  tool: Tool;
}

interface State {
  strokes: Stroke[];
  currentTool: Tool;
  currentColor: Color;
  brushSize: number;
  isDrawing: boolean;
  currentStroke: Point[];
  history: Stroke[][];
  historyIndex: number;
}

type Action =
  | { type: 'SET_TOOL'; tool: Tool }
  | { type: 'SET_COLOR'; color: Color }
  | { type: 'SET_BRUSH_SIZE'; size: number }
  | { type: 'START_DRAWING'; point: Point }
  | { type: 'DRAW'; point: Point }
  | { type: 'END_DRAWING' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

const COLORS: Color[] = ['#000000', '#ff0000', '#00ff00', '#0000ff', '#ffff00'];

const initialState: State = {
  strokes: [],
  currentTool: 'pen',
  currentColor: '#000000',
  brushSize: 3,
  isDrawing: false,
  currentStroke: [],
  history: [[]],
  historyIndex: 0,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_TOOL':
      return { ...state, currentTool: action.tool };
    case 'SET_COLOR':
      return { ...state, currentColor: action.color };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    case 'START_DRAWING':
      return { ...state, isDrawing: true, currentStroke: [action.point] };
    case 'DRAW':
      return { ...state, currentStroke: [...state.currentStroke, action.point] };
    case 'END_DRAWING': {
      if (state.currentStroke.length === 0) return state;
      const newStroke: Stroke = {
        points: state.currentStroke,
        color: state.currentColor,
        size: state.brushSize,
        tool: state.currentTool,
      };
      const newStrokes = [...state.strokes, newStroke];
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push(newStrokes);
      return {
        ...state,
        strokes: newStrokes,
        isDrawing: false,
        currentStroke: [],
        history: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }
    case 'UNDO':
      if (state.historyIndex > 0) {
        const newIndex = state.historyIndex - 1;
        return {
          ...state,
          strokes: state.history[newIndex],
          historyIndex: newIndex,
        };
      }
      return state;
    case 'REDO':
      if (state.historyIndex < state.history.length - 1) {
        const newIndex = state.historyIndex + 1;
        return {
          ...state,
          strokes: state.history[newIndex],
          historyIndex: newIndex,
        };
      }
      return state;
    case 'CLEAR': {
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push([]);
      return {
        ...state,
        strokes: [],
        history: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }
    default:
      return state;
  }
}

export default function CollaborativeWhiteboard() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(reducer, initialState);

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

  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke) => {
    if (stroke.points.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    for (let i = 1; i < stroke.points.length; i++) {
      ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
    }
    ctx.strokeStyle = stroke.tool === 'eraser' ? '#ffffff' : stroke.color;
    ctx.lineWidth = stroke.size;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
  }, []);

  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    state.strokes.forEach(stroke => drawStroke(ctx, stroke));
  }, [state.strokes, drawStroke]);

  React.useEffect(() => {
    redrawCanvas();
    if (state.isDrawing && state.currentStroke.length > 0) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const tempStroke: Stroke = {
        points: state.currentStroke,
        color: state.currentColor,
        size: state.brushSize,
        tool: state.currentTool,
      };
      drawStroke(ctx, tempStroke);
    }
  }, [state.strokes, state.currentStroke, state.isDrawing, state.currentColor, state.brushSize, state.currentTool, redrawCanvas, drawStroke]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    dispatch({ type: 'START_DRAWING', point: getPoint(e) });
  }, [getPoint]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (state.isDrawing) {
      dispatch({ type: 'DRAW', point: getPoint(e) });
    }
  }, [state.isDrawing, getPoint]);

  const handleMouseUp = useCallback(() => {
    dispatch({ type: 'END_DRAWING' });
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    dispatch({ type: 'START_DRAWING', point: getPoint(e) });
  }, [getPoint]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    if (state.isDrawing) {
      dispatch({ type: 'DRAW', point: getPoint(e) });
    }
  }, [state.isDrawing, getPoint]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    dispatch({ type: 'END_DRAWING' });
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h2>Collaborative Whiteboard</h2>
      <div style={{ marginBottom: '10px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
          style={{
            padding: '8px 16px',
            background: state.currentTool === 'pen' ? '#2196f3' : '#e0e0e0',
            color: state.currentTool === 'pen' ? '#fff' : '#000',
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
            background: state.currentTool === 'eraser' ? '#2196f3' : '#e0e0e0',
            color: state.currentTool === 'eraser' ? '#fff' : '#000',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Eraser
        </button>
        <div style={{ display: 'flex', gap: '5px' }}>
          {COLORS.map(color => (
            <button
              key={color}
              onClick={() => dispatch({ type: 'SET_COLOR', color })}
              style={{
                width: '30px',
                height: '30px',
                background: color,
                border: state.currentColor === color ? '3px solid #333' : '1px solid #ccc',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            />
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label>Brush Size:</label>
          <input
            type="range"
            min="1"
            max="20"
            value={state.brushSize}
            onChange={(e) => dispatch({ type: 'SET_BRUSH_SIZE', size: parseInt(e.target.value) })}
          />
          <span>{state.brushSize}px</span>
        </div>
        <button
          onClick={() => dispatch({ type: 'UNDO' })}
          disabled={state.historyIndex === 0}
          style={{
            padding: '8px 16px',
            background: state.historyIndex === 0 ? '#ccc' : '#4caf50',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: state.historyIndex === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          Undo
        </button>
        <button
          onClick={() => dispatch({ type: 'REDO' })}
          disabled={state.historyIndex >= state.history.length - 1}
          style={{
            padding: '8px 16px',
            background: state.historyIndex >= state.history.length - 1 ? '#ccc' : '#4caf50',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: state.historyIndex >= state.history.length - 1 ? 'not-allowed' : 'pointer',
          }}
        >
          Redo
        </button>
        <button
          onClick={() => dispatch({ type: 'CLEAR' })}
          style={{
            padding: '8px 16px',
            background: '#f44336',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Clear
        </button>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{
          border: '2px solid #333',
          cursor: state.currentTool === 'pen' ? 'crosshair' : 'cell',
          touchAction: 'none',
        }}
      />
    </div>
  );
}
