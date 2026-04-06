import React, { useReducer, useRef, useEffect, useCallback } from 'react';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  brushSize: number;
  type: 'pen' | 'eraser';
}

interface WhiteboardState {
  strokes: Stroke[];
  history: Stroke[][];
  redoStack: Stroke[][];
  currentColor: string;
  currentBrushSize: number;
  currentTool: 'pen' | 'eraser';
  isDrawing: boolean;
}

type Action =
  | { type: 'START_DRAWING'; point: Point }
  | { type: 'CONTINUE_DRAWING'; point: Point }
  | { type: 'STOP_DRAWING' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_BRUSH_SIZE'; size: number }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

const initialState: WhiteboardState = {
  strokes: [],
  history: [],
  redoStack: [],
  currentColor: '#000000',
  currentBrushSize: 3,
  currentTool: 'pen',
  isDrawing: false,
};

const colors = ['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFA500'];

const whiteboardReducer = (state: WhiteboardState, action: Action): WhiteboardState => {
  switch (action.type) {
    case 'START_DRAWING': {
      const newStroke: Stroke = {
        points: [action.point],
        color: state.currentTool === 'pen' ? state.currentColor : '#FFFFFF',
        brushSize: state.currentBrushSize,
        type: state.currentTool,
      };
      return {
        ...state,
        strokes: [...state.strokes, newStroke],
        history: [...state.history, state.strokes],
        redoStack: [],
        isDrawing: true,
      };
    }

    case 'CONTINUE_DRAWING': {
      if (state.strokes.length === 0 || !state.isDrawing) return state;
      const lastStrokeIndex = state.strokes.length - 1;
      const updatedStrokes = [...state.strokes];
      updatedStrokes[lastStrokeIndex] = {
        ...updatedStrokes[lastStrokeIndex],
        points: [...updatedStrokes[lastStrokeIndex].points, action.point],
      };
      return {
        ...state,
        strokes: updatedStrokes,
      };
    }

    case 'STOP_DRAWING': {
      return {
        ...state,
        isDrawing: false,
      };
    }

    case 'SET_COLOR': {
      return {
        ...state,
        currentColor: action.color,
      };
    }

    case 'SET_BRUSH_SIZE': {
      return {
        ...state,
        currentBrushSize: action.size,
      };
    }

    case 'SET_TOOL': {
      return {
        ...state,
        currentTool: action.tool,
      };
    }

    case 'UNDO': {
      if (state.history.length === 0) return state;
      const previousState = state.history[state.history.length - 1];
      const newHistory = state.history.slice(0, -1);
      return {
        ...state,
        strokes: previousState,
        history: newHistory,
        redoStack: [...state.redoStack, state.strokes],
        isDrawing: false,
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const nextState = state.redoStack[state.redoStack.length - 1];
      const newRedoStack = state.redoStack.slice(0, -1);
      return {
        ...state,
        strokes: nextState,
        history: [...state.history, state.strokes],
        redoStack: newRedoStack,
        isDrawing: false,
      };
    }

    case 'CLEAR': {
      return {
        ...state,
        strokes: [],
        history: [...state.history, state.strokes],
        redoStack: [],
        isDrawing: false,
      };
    }

    default:
      return state;
  }
};

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const getCanvasCoordinates = useCallback((clientX: number, clientY: number): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const point = getCanvasCoordinates(e.clientX, e.clientY);
    dispatch({ type: 'START_DRAWING', point });
  }, [getCanvasCoordinates]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!state.isDrawing) return;
    e.preventDefault();
    const point = getCanvasCoordinates(e.clientX, e.clientY);
    dispatch({ type: 'CONTINUE_DRAWING', point });
  }, [state.isDrawing, getCanvasCoordinates]);

  const handleMouseUp = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: 'STOP_DRAWING' });
    }
  }, [state.isDrawing]);

  const handleTouchStart = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const touch = e.touches[0];
    const point = getCanvasCoordinates(touch.clientX, touch.clientY);
    dispatch({ type: 'START_DRAWING', point });
  }, [getCanvasCoordinates]);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!state.isDrawing) return;
    e.preventDefault();
    const touch = e.touches[0];
    const point = getCanvasCoordinates(touch.clientX, touch.clientY);
    dispatch({ type: 'CONTINUE_DRAWING', point });
  }, [state.isDrawing, getCanvasCoordinates]);

  const handleTouchEnd = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: 'STOP_DRAWING' });
    }
  }, [state.isDrawing]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    state.strokes.forEach((stroke) => {
      if (stroke.points.length < 2) return;
      
      ctx.beginPath();
      ctx.lineWidth = stroke.brushSize;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = stroke.color;
      
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      
      for (let i = 1; i < stroke.points.length; i++) {
        ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
      }
      
      ctx.stroke();
    });
  }, [state.strokes]);

  useEffect(() => {
    const handleDocumentMouseMove = (e: MouseEvent) => handleMouseMove(e);
    const handleDocumentMouseUp = () => handleMouseUp();
    const handleDocumentTouchMove = (e: TouchEvent) => handleTouchMove(e);
    const handleDocumentTouchEnd = () => handleTouchEnd();

    document.addEventListener('mousemove', handleDocumentMouseMove);
    document.addEventListener('mouseup', handleDocumentMouseUp);
    document.addEventListener('touchmove', handleDocumentTouchMove, { passive: false });
    document.addEventListener('touchend', handleDocumentTouchEnd);
    document.addEventListener('touchcancel', handleDocumentTouchEnd);

    return () => {
      document.removeEventListener('mousemove', handleDocumentMouseMove);
      document.removeEventListener('mouseup', handleDocumentMouseUp);
      document.removeEventListener('touchmove', handleDocumentTouchMove);
      document.removeEventListener('touchend', handleDocumentTouchEnd);
      document.removeEventListener('touchcancel', handleDocumentTouchEnd);
    };
  }, [handleMouseMove, handleMouseUp, handleTouchMove, handleTouchEnd]);

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    canvas.width = container.clientWidth - 40;
    canvas.height = 500;
    
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    
    const strokesCopy = [...state.strokes];
    dispatch({ type: 'CLEAR' });
    setTimeout(() => {
      dispatch({ type: 'SET_COLOR', color: state.currentColor });
      dispatch({ type: 'SET_BRUSH_SIZE', size: state.currentBrushSize });
      dispatch({ type: 'SET_TOOL', tool: state.currentTool });
      strokesCopy.forEach(stroke => {
        if (stroke.points.length > 0) {
          dispatch({ type: 'START_DRAWING', point: stroke.points[0] });
          stroke.points.slice(1).forEach(point => {
            dispatch({ type: 'CONTINUE_DRAWING', point });
          });
          dispatch({ type: 'STOP_DRAWING' });
        }
      });
    }, 0);
  }, [state.strokes, state.currentColor, state.currentBrushSize, state.currentTool]);

  useEffect(() => {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    return () => window.removeEventListener('resize', resizeCanvas);
  }, [resizeCanvas]);

  return (
    <div
      ref={containerRef}
      style={{
        maxWidth: '1000px',
        margin: '0 auto',
        padding: '20px',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <h2 style={{ textAlign: 'center', color: '#333', marginBottom: '20px' }}>
        Collaborative Drawing Whiteboard
      </h2>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '300px' }}>
          <div
            style={{
              border: '2px solid #ddd',
              borderRadius: '8px',
              overflow: 'hidden',
              backgroundColor: '#f8f9fa',
              marginBottom: '20px',
            }}
          >
            <canvas
              ref={canvasRef}
              onMouseDown={handleMouseDown}
              onTouchStart={handleTouchStart}
              style={{
                display: 'block',
                width: '100%',
                height: '500px',
                cursor: state.currentTool === 'pen' ? 'crosshair' : 'cell',
                backgroundColor: '#fff',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '10px' }}>
            <button
              onClick={() => dispatch({ type: 'UNDO' })}
              disabled={state.history.length === 0}
              style={{
                padding: '10px 20px',
                backgroundColor: state.history.length === 0 ? '#ccc' : '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: state.history.length === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              Undo
            </button>
            <button
              onClick={() => dispatch({ type: 'REDO' })}
              disabled={state.redoStack.length === 0}
              style={{
                padding: '10px 20px',
                backgroundColor: state.redoStack.length === 0 ? '#ccc' : '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: state.redoStack.length === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              Redo
            </button>
            <button
              onClick={() => dispatch({ type: 'CLEAR' })}
              style={{
                padding: '10px 20px',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Clear Canvas
            </button>
          </div>
        </div>

        <div style={{ flex: '0 0 250px' }}>
          <div
            style={{
              backgroundColor: '#f8f9fa',
              padding: '20px',
              borderRadius: '8px',
              border: '1px solid #ddd',
            }}
          >
            <h3 style={{ marginTop: 0, color: '#333', borderBottom: '2px solid #ddd', paddingBottom: '10px' }}>
              Tools
            </h3>

            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '10px', color: '#555' }}>Tool Selection</h4>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
                  style={{
                    flex: 1,
                    padding: '10px',
                    backgroundColor: state.currentTool === 'pen' ? '#007bff' : '#6c757d',
                    color: 'white',
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
                    flex: 1,
                    padding: '10px',
                    backgroundColor: state.currentTool === 'eraser' ? '#007bff' : '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Eraser
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '10px', color: '#555' }}>Brush Size</h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={state.currentBrushSize}
                  onChange={(e) => dispatch({ type: 'SET_BRUSH_SIZE', size: parseInt(e.target.value) })}
                  style={{ flex: 1 }}
                />
                <span style={{ minWidth: '30px', textAlign: 'center' }}>{state.currentBrushSize}px</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px' }}>
                <span style={{ fontSize: '12px', color: '#666' }}>Small</span>
                <span style={{ fontSize: '12px', color: '#666' }}>Large</span>
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '10px', color: '#555' }}>Color Palette</h4>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {colors.map((color) => (
                  <button
                    key={color}
                    onClick={() => dispatch({ type: 'SET_COLOR', color })}
                    style={{
                      width: '40px',
                      height: '40px',
                      backgroundColor: color,
                      border: state.currentColor === color ? '3px solid #333' : '2px solid #ddd',
                      borderRadius: '50%',
                      cursor: 'pointer',
                    }}
                    title={color}
                  />
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '10px', color: '#555' }}>Current Tool</h4>
              <div style={{ 
                padding: '10px', 
                backgroundColor: '#e9ecef', 
                borderRadius: '4px',
                borderLeft: `4px solid ${state.currentTool === 'pen' ? state.currentColor : '#FFFFFF'}`,
              }}>
                <div><strong>Type:</strong> {state.currentTool === 'pen' ? 'Pen' : 'Eraser'}</div>
                <div><strong>Color:</strong> 
                  <span 
                    style={{ 
                      display: 'inline-block',
                      width: '12px',
                      height: '12px',
                      backgroundColor: state.currentTool === 'pen' ? state.currentColor : '#FFFFFF',
                      border: '1px solid #ccc',
                      marginLeft: '5px',
                      verticalAlign: 'middle',
                    }}
                  />
                  {state.currentTool === 'pen' ? state.currentColor : 'White'}
                </div>
                <div><strong>Size:</strong> {state.currentBrushSize}px</div>
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#e3f2fd', 
              padding: '15px', 
              borderRadius: '4px',
              fontSize: '14px',
              color: '#1976d2',
            }}>
              <h5 style={{ marginTop: 0, marginBottom: '10px' }}>Instructions</h5>
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                <li>Click and drag to draw</li>
                <li>Use Undo/Redo to navigate history</li>
                <li>Select colors from palette</li>
                <li>Adjust brush size with slider</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div style={{ 
        marginTop: '20px', 
        padding: '15px', 
        backgroundColor: '#f8f9fa', 
        borderRadius: '8px',
        fontSize: '14px',
        color: '#666',
      }}>
        <div><strong>Canvas Statistics:</strong></div>
        <div>Strokes: {state.strokes.length}</div>
        <div>History Steps: {state.history.length}</div>
        <div>Redo Steps: {state.redoStack.length}</div>
        <div>Current Tool: {state.currentTool === 'pen' ? 'Pen' : 'Eraser'}</div>
      </div>
    </div>
  );
};

export default CollaborativeWhiteboard;