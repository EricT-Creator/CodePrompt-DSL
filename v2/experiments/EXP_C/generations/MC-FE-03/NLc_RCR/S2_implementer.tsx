import React, { useReducer, useRef, useCallback } from 'react';
import styles from './S2_implementer.module.css';

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

type Action =
  | { type: 'START_STROKE'; payload: { tool: 'pen' | 'eraser'; color: string; point: Point } }
  | { type: 'ADD_POINT'; payload: Point }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string };

const MAX_UNDO_STACK = 50;

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function reducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const newStroke: Stroke = {
        id: generateId(),
        tool: action.payload.tool,
        color: action.payload.color,
        lineWidth: action.payload.tool === 'eraser' ? 20 : 2,
        points: [action.payload.point],
      };
      const newUndoStack = [...state.undoStack, state.strokes].slice(-MAX_UNDO_STACK);
      return {
        ...state,
        strokes: state.strokes,
        currentStroke: newStroke,
        undoStack: newUndoStack,
        redoStack: [],
        isDrawing: true,
      };
    }
    case 'ADD_POINT':
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.payload],
        },
      };
    case 'END_STROKE':
      if (!state.currentStroke) return state;
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        isDrawing: false,
      };
    case 'UNDO':
      if (state.undoStack.length === 0) return state;
      const prevStrokes = state.undoStack[state.undoStack.length - 1];
      const newUndoStack = state.undoStack.slice(0, -1);
      return {
        ...state,
        strokes: prevStrokes,
        undoStack: newUndoStack,
        redoStack: [...state.redoStack, state.strokes],
      };
    case 'REDO':
      if (state.redoStack.length === 0) return state;
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      const newRedoStack = state.redoStack.slice(0, -1);
      return {
        ...state,
        strokes: nextStrokes,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: newRedoStack,
      };
    case 'CLEAR':
      return {
        ...state,
        strokes: [],
        currentStroke: null,
        undoStack: [...state.undoStack, state.strokes].slice(-MAX_UNDO_STACK),
        redoStack: [],
      };
    case 'SET_TOOL':
      return { ...state, tool: action.payload };
    case 'SET_COLOR':
      return { ...state, color: action.payload };
    default:
      return state;
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
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
}

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[], width: number, height: number): void {
  ctx.clearRect(0, 0, width, height);
  strokes.forEach(stroke => drawStroke(ctx, stroke));
}

const Toolbar: React.FC<{
  tool: 'pen' | 'eraser';
  color: string;
  canUndo: boolean;
  canRedo: boolean;
  dispatch: React.Dispatch<Action>;
}> = ({ tool, color, canUndo, canRedo, dispatch }) => {
  return (
    <div className={styles.toolbar}>
      <button
        className={tool === 'pen' ? styles.active : ''}
        onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
      >
        Pen
      </button>
      <button
        className={tool === 'eraser' ? styles.active : ''}
        onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
      >
        Eraser
      </button>
      <input
        type="color"
        value={color}
        onChange={(e) => dispatch({ type: 'SET_COLOR', payload: e.target.value })}
      />
      <button disabled={!canUndo} onClick={() => dispatch({ type: 'UNDO' })}>
        Undo
      </button>
      <button disabled={!canRedo} onClick={() => dispatch({ type: 'REDO' })}>
        Redo
      </button>
      <button onClick={() => dispatch({ type: 'CLEAR' })}>Clear</button>
    </div>
  );
};

const Whiteboard: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(reducer, {
    strokes: [],
    currentStroke: null,
    undoStack: [],
    redoStack: [],
    tool: 'pen',
    color: '#000000',
    isDrawing: false,
  });

  const getCanvasPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasPoint(e);
    dispatch({ type: 'START_STROKE', payload: { tool: state.tool, color: state.color, point } });
  }, [state.tool, state.color, getCanvasPoint]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing) return;
    const point = getCanvasPoint(e);
    dispatch({ type: 'ADD_POINT', payload: point });
    const canvas = canvasRef.current;
    if (canvas && state.currentStroke) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        drawStroke(ctx, state.currentStroke);
      }
    }
  }, [state.isDrawing, state.currentStroke, getCanvasPoint]);

  const handleMouseUp = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          redrawAll(ctx, [...state.strokes, state.currentStroke!], canvas.width, canvas.height);
        }
      }
    }
  }, [state.isDrawing, state.strokes, state.currentStroke]);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        redrawAll(ctx, state.strokes, canvas.width, canvas.height);
      }
    }
  }, [state.strokes]);

  return (
    <div className={styles.whiteboard}>
      <Toolbar
        tool={state.tool}
        color={state.color}
        canUndo={state.undoStack.length > 0}
        canRedo={state.redoStack.length > 0}
        dispatch={dispatch}
      />
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className={styles.canvas}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
    </div>
  );
};

export default Whiteboard;
