import React, { useReducer, useRef, useCallback } from 'react';

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
  activeTool: 'pen' | 'eraser';
  activeColor: string;
  lineWidth: number;
  isDrawing: boolean;
  canvasWidth: number;
  canvasHeight: number;
}

type WhiteboardAction =
  | { type: 'START_STROKE'; payload: { x: number; y: number } }
  | { type: 'ADD_POINT'; payload: { x: number; y: number } }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number };

const COLORS = ['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF'];
const MAX_UNDO_STACK = 50;

function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE':
      return {
        ...state,
        currentStroke: {
          id: generateId(),
          tool: state.activeTool,
          color: state.activeColor,
          lineWidth: state.lineWidth,
          points: [{ x: action.payload.x, y: action.payload.y }],
        },
        isDrawing: true,
      };
    case 'ADD_POINT':
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, { x: action.payload.x, y: action.payload.y }],
        },
      };
    case 'END_STROKE':
      if (!state.currentStroke) return state;
      const newUndoStack = [...state.undoStack, state.strokes];
      const trimmedUndoStack = newUndoStack.length > MAX_UNDO_STACK ? newUndoStack.slice(1) : newUndoStack;
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        undoStack: trimmedUndoStack,
        redoStack: [],
        isDrawing: false,
      };
    case 'UNDO':
      if (state.undoStack.length === 0) return state;
      const prevStrokes = state.undoStack[state.undoStack.length - 1];
      return {
        ...state,
        strokes: prevStrokes,
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [...state.redoStack, state.strokes],
      };
    case 'REDO':
      if (state.redoStack.length === 0) return state;
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: nextStrokes,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: state.redoStack.slice(0, -1),
      };
    case 'CLEAR_CANVAS':
      return {
        ...state,
        strokes: [],
        undoStack: [...state.undoStack, state.strokes],
        redoStack: [],
      };
    case 'SET_TOOL':
      return { ...state, activeTool: action.payload };
    case 'SET_COLOR':
      return { ...state, activeColor: action.payload };
    case 'SET_LINE_WIDTH':
      return { ...state, lineWidth: action.payload };
    default:
      return state;
  }
}

export default function DrawingWhiteboard() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(whiteboardReducer, {
    strokes: [],
    currentStroke: null,
    undoStack: [],
    redoStack: [],
    activeTool: 'pen',
    activeColor: '#000000',
    lineWidth: 2,
    isDrawing: false,
    canvasWidth: 800,
    canvasHeight: 600,
  });

  const getCanvasCoordinates = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke) => {
    if (stroke.points.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    for (let i = 1; i < stroke.points.length; i++) {
      ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
    }
    ctx.strokeStyle = stroke.color;
    ctx.lineWidth = stroke.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    if (stroke.tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
    } else {
      ctx.globalCompositeOperation = 'source-over';
    }
    ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }, []);

  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    state.strokes.forEach(stroke => drawStroke(ctx, stroke));
  }, [state.strokes, drawStroke]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getCanvasCoordinates(e);
    dispatch({ type: 'START_STROKE', payload: coords });
  }, [getCanvasCoordinates]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing || !state.currentStroke) return;
    const coords = getCanvasCoordinates(e);
    dispatch({ type: 'ADD_POINT', payload: coords });
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const points = state.currentStroke.points;
    const prevPoint = points[points.length - 1];
    ctx.beginPath();
    ctx.moveTo(prevPoint.x, prevPoint.y);
    ctx.lineTo(coords.x, coords.y);
    ctx.strokeStyle = state.currentStroke.color;
    ctx.lineWidth = state.currentStroke.lineWidth;
    ctx.lineCap = 'round';
    if (state.currentStroke.tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
    }
    ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }, [state.isDrawing, state.currentStroke, getCanvasCoordinates]);

  const handleMouseUp = useCallback(() => {
    dispatch({ type: 'END_STROKE' });
    redrawCanvas();
  }, [redrawCanvas]);

  React.useEffect(() => {
    redrawCanvas();
  }, [state.strokes.length]);

  return (
    <div className="whiteboard-container">
      <style>{`
        .whiteboard-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }
        .toolbar { display: flex; gap: 16px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; padding: 12px; background: #f5f5f5; border-radius: 8px; }
        .tool-group { display: flex; gap: 8px; align-items: center; }
        .tool-button { padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .tool-button.active { background: #2196F3; color: white; border-color: #2196F3; }
        .tool-button:disabled { opacity: 0.5; cursor: not-allowed; }
        .color-picker { display: flex; gap: 4px; }
        .color-swatch { width: 28px; height: 28px; border: 2px solid transparent; border-radius: 4px; cursor: pointer; }
        .color-swatch.active { border-color: #333; }
        .line-width-slider { display: flex; align-items: center; gap: 8px; }
        .canvas-area { border: 2px solid #ddd; border-radius: 4px; display: inline-block; background: white; }
        canvas { cursor: crosshair; display: block; }
      `}</style>
      
      <div className="toolbar">
        <div className="tool-group">
          <button className={`tool-button ${state.activeTool === 'pen' ? 'active' : ''}`} onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}>Pen</button>
          <button className={`tool-button ${state.activeTool === 'eraser' ? 'active' : ''}`} onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}>Eraser</button>
        </div>
        
        <div className="tool-group color-picker">
          {COLORS.map(color => (
            <div
              key={color}
              className={`color-swatch ${state.activeColor === color ? 'active' : ''}`}
              style={{ backgroundColor: color }}
              onClick={() => dispatch({ type: 'SET_COLOR', payload: color })}
            />
          ))}
          <input type="color" value={state.activeColor} onChange={e => dispatch({ type: 'SET_COLOR', payload: e.target.value })} />
        </div>
        
        <div className="tool-group line-width-slider">
          <span>Width:</span>
          <input type="range" min="1" max="20" value={state.lineWidth} onChange={e => dispatch({ type: 'SET_LINE_WIDTH', payload: parseInt(e.target.value) })} />
          <span>{state.lineWidth}px</span>
        </div>
        
        <div className="tool-group">
          <button className="tool-button" onClick={() => dispatch({ type: 'UNDO' })} disabled={state.undoStack.length === 0}>Undo</button>
          <button className="tool-button" onClick={() => dispatch({ type: 'REDO' })} disabled={state.redoStack.length === 0}>Redo</button>
          <button className="tool-button" onClick={() => dispatch({ type: 'CLEAR_CANVAS' })}>Clear</button>
        </div>
      </div>
      
      <div className="canvas-area">
        <canvas
          ref={canvasRef}
          width={state.canvasWidth}
          height={state.canvasHeight}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
      </div>
    </div>
  );
}
