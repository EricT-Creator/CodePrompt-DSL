import React, { useReducer, useRef, useEffect } from 'react';
import styles from './styles.module.css';

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

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  tool: 'pen',
  color: '#000000',
  isDrawing: false,
};

function whiteboardReducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const { tool, color, point } = action.payload;
      const newStroke: Stroke = {
        id: Date.now().toString(),
        tool,
        color: tool === 'eraser' ? '#ffffff' : color,
        lineWidth: tool === 'eraser' ? 20 : 4,
        points: [point],
      };
      
      return {
        ...state,
        strokes: state.strokes,
        currentStroke: newStroke,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: [],
        isDrawing: true,
      };
    }
    
    case 'ADD_POINT': {
      if (!state.currentStroke) return state;
      const newPoint = action.payload;
      
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, newPoint],
        },
      };
    }
    
    case 'END_STROKE': {
      if (!state.currentStroke) return state;
      
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'UNDO': {
      if (state.undoStack.length === 0) return state;
      
      const previousStrokes = state.undoStack[state.undoStack.length - 1];
      const newUndoStack = state.undoStack.slice(0, -1);
      
      return {
        ...state,
        strokes: previousStrokes,
        undoStack: newUndoStack,
        redoStack: [...state.redoStack, state.strokes],
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      const newRedoStack = state.redoStack.slice(0, -1);
      
      return {
        ...state,
        strokes: nextStrokes,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: newRedoStack,
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'CLEAR': {
      return {
        ...state,
        strokes: [],
        undoStack: [...state.undoStack, state.strokes],
        redoStack: [],
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'SET_TOOL': {
      return {
        ...state,
        tool: action.payload,
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'SET_COLOR': {
      return {
        ...state,
        color: action.payload,
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    default:
      return state;
  }
}

const drawStroke = (ctx: CanvasRenderingContext2D, stroke: Stroke) => {
  if (stroke.points.length < 2) return;
  
  ctx.save();
  
  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = stroke.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color;
    ctx.lineWidth = stroke.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }
  
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  
  for (let i = 1; i < stroke.points.length; i++) {
    const point = stroke.points[i];
    ctx.lineTo(point.x, point.y);
  }
  
  ctx.stroke();
  ctx.restore();
};

const redrawAll = (canvas: HTMLCanvasElement, strokes: Stroke[], currentStroke: Stroke | null) => {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Draw background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  // Draw grid
  ctx.strokeStyle = '#f0f0f0';
  ctx.lineWidth = 1;
  
  const gridSize = 20;
  for (let x = 0; x < canvas.width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  
  for (let y = 0; y < canvas.height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
  
  // Draw all strokes
  strokes.forEach(stroke => drawStroke(ctx, stroke));
  
  // Draw current stroke in progress
  if (currentStroke) {
    drawStroke(ctx, currentStroke);
  }
};

const Toolbar: React.FC<{
  tool: 'pen' | 'eraser';
  color: string;
  dispatch: React.Dispatch<Action>;
  canUndo: boolean;
  canRedo: boolean;
  canClear: boolean;
}> = ({ tool, color, dispatch, canUndo, canRedo, canClear }) => {
  return (
    <div className={styles.toolbar}>
      <div className={styles.toolGroup}>
        <button
          className={`${styles.toolButton} ${tool === 'pen' ? styles.active : ''}`}
          onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
          title="Pen"
        >
          <span className={styles.toolIcon}>✏️</span>
          <span className={styles.toolLabel}>Pen</span>
        </button>
        <button
          className={`${styles.toolButton} ${tool === 'eraser' ? styles.active : ''}`}
          onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
          title="Eraser"
        >
          <span className={styles.toolIcon}>🧹</span>
          <span className={styles.toolLabel}>Eraser</span>
        </button>
      </div>
      
      <div className={styles.colorGroup}>
        <label className={styles.colorLabel}>Color:</label>
        <input
          type="color"
          value={color}
          onChange={(e) => dispatch({ type: 'SET_COLOR', payload: e.target.value })}
          className={styles.colorInput}
          disabled={tool === 'eraser'}
        />
      </div>
      
      <div className={styles.actionGroup}>
        <button
          className={styles.actionButton}
          onClick={() => dispatch({ type: 'UNDO' })}
          disabled={!canUndo}
          title="Undo"
        >
          ↶ Undo
        </button>
        <button
          className={styles.actionButton}
          onClick={() => dispatch({ type: 'REDO' })}
          disabled={!canRedo}
          title="Redo"
        >
          ↷ Redo
        </button>
        <button
          className={styles.actionButton}
          onClick={() => dispatch({ type: 'CLEAR' })}
          disabled={!canClear}
          title="Clear"
        >
          Clear
        </button>
      </div>
    </div>
  );
};

const Whiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement>): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    return { x, y };
  };
  
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasCoordinates(e);
    if (!point) return;
    
    dispatch({
      type: 'START_STROKE',
      payload: { tool: state.tool, color: state.color, point },
    });
  };
  
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing) return;
    
    const point = getCanvasCoordinates(e);
    if (!point) return;
    
    dispatch({ type: 'ADD_POINT', payload: point });
    
    // Draw the current segment for real-time feedback
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (canvas && ctx && state.currentStroke) {
      const currentStroke = state.currentStroke;
      if (currentStroke.points.length >= 2) {
        const lastPoint = currentStroke.points[currentStroke.points.length - 2];
        const currentPoint = currentStroke.points[currentStroke.points.length - 1];
        
        if (currentStroke.tool === 'eraser') {
          ctx.globalCompositeOperation = 'destination-out';
          ctx.strokeStyle = '#ffffff';
        } else {
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle = currentStroke.color;
        }
        
        ctx.lineWidth = currentStroke.lineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        ctx.beginPath();
        ctx.moveTo(lastPoint.x, lastPoint.y);
        ctx.lineTo(currentPoint.x, currentPoint.y);
        ctx.stroke();
      }
    }
  };
  
  const handleMouseUp = () => {
    if (!state.isDrawing) return;
    dispatch({ type: 'END_STROKE' });
  };
  
  const handleMouseLeave = () => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  };
  
  // Redraw canvas whenever state changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    // Ensure canvas size matches display size
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }
    
    redrawAll(canvas, state.strokes, state.currentStroke);
  }, [state.strokes, state.currentStroke]);
  
  const canUndo = state.undoStack.length > 0;
  const canRedo = state.redoStack.length > 0;
  const canClear = state.strokes.length > 0 || state.currentStroke !== null;
  
  return (
    <div className={styles.whiteboard}>
      <div className={styles.header}>
        <h1>Canvas Drawing Whiteboard</h1>
        <div className={styles.stats}>
          <span className={styles.statItem}>
            Strokes: {state.strokes.length}
          </span>
          <span className={styles.statItem}>
            Undo stack: {state.undoStack.length}
          </span>
          <span className={styles.statItem}>
            Redo stack: {state.redoStack.length}
          </span>
        </div>
      </div>
      
      <Toolbar
        tool={state.tool}
        color={state.color}
        dispatch={dispatch}
        canUndo={canUndo}
        canRedo={canRedo}
        canClear={canClear}
      />
      
      <div className={styles.canvasContainer}>
        <canvas
          ref={canvasRef}
          className={styles.canvas}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        />
        <div className={styles.instructions}>
          <p>• Click and drag to draw with the pen tool</p>
          <p>• Switch to eraser to remove strokes</p>
          <p>• Use Undo/Redo to navigate stroke history</p>
          <p>• Clear resets the entire canvas</p>
        </div>
      </div>
    </div>
  );
};

export default Whiteboard;