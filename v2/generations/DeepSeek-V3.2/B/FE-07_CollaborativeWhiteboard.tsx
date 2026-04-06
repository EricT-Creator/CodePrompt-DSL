import React, { useRef, useEffect, useReducer, useCallback } from 'react';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  width: number;
  type: 'pen' | 'eraser';
}

interface State {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  color: string;
  brushSize: number;
  isDrawing: boolean;
  history: Stroke[][];
  historyIndex: number;
  tool: 'pen' | 'eraser';
}

type Action =
  | { type: 'START_DRAWING'; x: number; y: number }
  | { type: 'DRAW'; x: number; y: number }
  | { type: 'STOP_DRAWING' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_BRUSH_SIZE'; size: number }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'ADD_TO_HISTORY' };

const initialState: State = {
  strokes: [],
  currentStroke: null,
  color: '#000000',
  brushSize: 3,
  isDrawing: false,
  history: [[]],
  historyIndex: 0,
  tool: 'pen',
};

const whiteboardReducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'START_DRAWING': {
      const newStroke: Stroke = {
        points: [{ x: action.x, y: action.y }],
        color: state.tool === 'eraser' ? '#FFFFFF' : state.color,
        width: state.brushSize,
        type: state.tool,
      };
      return {
        ...state,
        isDrawing: true,
        currentStroke: newStroke,
      };
    }
    
    case 'DRAW': {
      if (!state.currentStroke || !state.isDrawing) return state;
      
      const updatedStroke = {
        ...state.currentStroke,
        points: [...state.currentStroke.points, { x: action.x, y: action.y }],
      };
      
      return {
        ...state,
        currentStroke: updatedStroke,
      };
    }
    
    case 'STOP_DRAWING': {
      if (!state.currentStroke || !state.isDrawing) return state;
      
      const newStrokes = [...state.strokes, state.currentStroke];
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push(newStrokes);
      
      return {
        ...state,
        isDrawing: false,
        currentStroke: null,
        strokes: newStrokes,
        history: newHistory,
        historyIndex: state.historyIndex + 1,
      };
    }
    
    case 'SET_COLOR':
      return { ...state, color: action.color };
    
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.size };
    
    case 'SET_TOOL':
      return { ...state, tool: action.tool };
    
    case 'UNDO': {
      if (state.historyIndex <= 0) return state;
      const newIndex = state.historyIndex - 1;
      return {
        ...state,
        strokes: state.history[newIndex],
        historyIndex: newIndex,
      };
    }
    
    case 'REDO': {
      if (state.historyIndex >= state.history.length - 1) return state;
      const newIndex = state.historyIndex + 1;
      return {
        ...state,
        strokes: state.history[newIndex],
        historyIndex: newIndex,
      };
    }
    
    case 'CLEAR': {
      const newHistory = [...state.history, []];
      return {
        ...state,
        strokes: [],
        history: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }
    
    case 'ADD_TO_HISTORY': {
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push(state.strokes);
      return {
        ...state,
        history: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }
    
    default:
      return state;
  }
};

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const colors = [
    '#000000', '#FF0000', '#00FF00', '#0000FF',
    '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500',
  ];
  
  const brushSizes = [1, 3, 5, 8, 12];
  
  const getCanvasCoordinates = useCallback((clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  }, []);
  
  const handleMouseDown = (e: React.MouseEvent) => {
    const { x, y } = getCanvasCoordinates(e.clientX, e.clientY);
    dispatch({ type: 'START_DRAWING', x, y });
  };
  
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!state.isDrawing) return;
    const { x, y } = getCanvasCoordinates(e.clientX, e.clientY);
    dispatch({ type: 'DRAW', x, y });
  };
  
  const handleMouseUp = () => {
    if (state.isDrawing) {
      dispatch({ type: 'STOP_DRAWING' });
    }
  };
  
  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const { x, y } = getCanvasCoordinates(touch.clientX, touch.clientY);
      dispatch({ type: 'START_DRAWING', x, y });
      e.preventDefault();
    }
  };
  
  const handleTouchMove = (e: React.TouchEvent) => {
    if (!state.isDrawing || e.touches.length !== 1) return;
    const touch = e.touches[0];
    const { x, y } = getCanvasCoordinates(touch.clientX, touch.clientY);
    dispatch({ type: 'DRAW', x, y });
    e.preventDefault();
  };
  
  const handleTouchEnd = () => {
    if (state.isDrawing) {
      dispatch({ type: 'STOP_DRAWING' });
    }
  };
  
  const drawStrokes = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    state.strokes.forEach(stroke => {
      if (stroke.points.length < 2) return;
      
      ctx.beginPath();
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      
      for (let i = 1; i < stroke.points.length; i++) {
        ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
      }
      
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.stroke();
    });
    
    if (state.currentStroke && state.currentStroke.points.length >= 2) {
      const stroke = state.currentStroke;
      ctx.beginPath();
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      
      for (let i = 1; i < stroke.points.length; i++) {
        ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
      }
      
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.stroke();
    }
  }, [state.strokes, state.currentStroke]);
  
  useEffect(() => {
    drawStrokes();
  }, [drawStrokes]);
  
  useEffect(() => {
    const handleMouseUpGlobal = () => {
      if (state.isDrawing) {
        dispatch({ type: 'STOP_DRAWING' });
      }
    };
    
    const handleTouchEndGlobal = () => {
      if (state.isDrawing) {
        dispatch({ type: 'STOP_DRAWING' });
      }
    };
    
    document.addEventListener('mouseup', handleMouseUpGlobal);
    document.addEventListener('touchend', handleTouchEndGlobal);
    
    return () => {
      document.removeEventListener('mouseup', handleMouseUpGlobal);
      document.removeEventListener('touchend', handleTouchEndGlobal);
    };
  }, [state.isDrawing]);
  
  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Collaborative Whiteboard</h2>
      
      <div style={styles.toolbar}>
        <div style={styles.toolGroup}>
          <span style={styles.label}>Tool:</span>
          <button
            style={{
              ...styles.toolButton,
              ...(state.tool === 'pen' ? styles.activeTool : {}),
            }}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
          >
            ✏️ Pen
          </button>
          <button
            style={{
              ...styles.toolButton,
              ...(state.tool === 'eraser' ? styles.activeTool : {}),
            }}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
          >
            🧽 Eraser
          </button>
        </div>
        
        <div style={styles.toolGroup}>
          <span style={styles.label}>Color:</span>
          {colors.map(color => (
            <button
              key={color}
              style={{
                ...styles.colorButton,
                backgroundColor: color,
                border: state.color === color ? '3px solid #333' : '1px solid #ccc',
              }}
              onClick={() => dispatch({ type: 'SET_COLOR', color })}
              title={color}
            />
          ))}
        </div>
        
        <div style={styles.toolGroup}>
          <span style={styles.label}>Brush Size:</span>
          {brushSizes.map(size => (
            <button
              key={size}
              style={{
                ...styles.sizeButton,
                ...(state.brushSize === size ? styles.activeSize : {}),
              }}
              onClick={() => dispatch({ type: 'SET_BRUSH_SIZE', size })}
            >
              ●
            </button>
          ))}
        </div>
        
        <div style={styles.toolGroup}>
          <button
            style={styles.actionButton}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.historyIndex <= 0}
          >
            ↩️ Undo
          </button>
          <button
            style={styles.actionButton}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.historyIndex >= state.history.length - 1}
          >
            ↪️ Redo
          </button>
          <button
            style={styles.actionButton}
            onClick={() => dispatch({ type: 'CLEAR' })}
          >
            🗑️ Clear
          </button>
        </div>
      </div>
      
      <div style={styles.canvasContainer}>
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          style={styles.canvas}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        />
      </div>
      
      <div style={styles.status}>
        <div>Current tool: {state.tool}</div>
        <div>Color: {state.tool === 'eraser' ? 'White (Eraser)' : state.color}</div>
        <div>Brush size: {state.brushSize}px</div>
        <div>History: {state.historyIndex + 1}/{state.history.length}</div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '900px',
    margin: '0 auto',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    marginBottom: '20px',
    color: '#333',
  },
  toolbar: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '20px',
    marginBottom: '20px',
    padding: '15px',
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
  },
  toolGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  label: {
    fontWeight: 'bold',
    color: '#666',
    minWidth: '60px',
  },
  toolButton: {
    padding: '8px 16px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
    fontSize: '14px',
  },
  activeTool: {
    backgroundColor: '#e3f2fd',
    borderColor: '#2196f3',
  },
  colorButton: {
    width: '30px',
    height: '30px',
    borderRadius: '50%',
    border: '1px solid #ccc',
    cursor: 'pointer',
    padding: 0,
  },
  sizeButton: {
    padding: '5px 10px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
    fontSize: '16px',
  },
  activeSize: {
    backgroundColor: '#e3f2fd',
    borderColor: '#2196f3',
  },
  actionButton: {
    padding: '8px 16px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
    fontSize: '14px',
  },
  canvasContainer: {
    border: '2px solid #ddd',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '20px',
  },
  canvas: {
    display: 'block',
    backgroundColor: 'white',
    cursor: 'crosshair',
  },
  status: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '10px',
    padding: '15px',
    backgroundColor: '#f8f9fa',
    borderRadius: '4px',
    fontSize: '14px',
  },
};

export default CollaborativeWhiteboard;