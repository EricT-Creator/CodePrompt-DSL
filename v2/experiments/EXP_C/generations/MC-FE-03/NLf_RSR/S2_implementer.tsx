import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ===================== Interfaces =====================

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

// ===================== Action Types =====================

type WhiteboardAction =
  | { type: 'START_STROKE'; payload: { x: number; y: number } }
  | { type: 'ADD_POINT'; payload: { x: number; y: number } }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number }
  | { type: 'SET_CANVAS_SIZE'; payload: { width: number; height: number } };

// ===================== Reducer =====================

const UNDO_STACK_LIMIT = 50;

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      const newStroke: Stroke = {
        id: `stroke-${Date.now()}`,
        tool: state.activeTool,
        color: state.activeColor,
        lineWidth: state.lineWidth,
        points: [{ x: action.payload.x, y: action.payload.y }],
      };

      // Save current state to undo stack before starting new stroke
      const newUndoStack = [...state.undoStack, state.strokes];
      if (newUndoStack.length > UNDO_STACK_LIMIT) {
        newUndoStack.shift();
      }

      return {
        ...state,
        currentStroke: newStroke,
        undoStack: newUndoStack,
        redoStack: [], // Clear redo stack on new action
        isDrawing: true,
      };
    }

    case 'ADD_POINT': {
      if (!state.currentStroke) return state;

      const updatedStroke: Stroke = {
        ...state.currentStroke,
        points: [...state.currentStroke.points, action.payload],
      };

      return {
        ...state,
        currentStroke: updatedStroke,
      };
    }

    case 'END_STROKE': {
      if (!state.currentStroke) return state;

      const newStrokes = [...state.strokes, state.currentStroke];
      return {
        ...state,
        strokes: newStrokes,
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'UNDO': {
      if (state.undoStack.length === 0) return state;

      const previousStrokes = state.undoStack[state.undoStack.length - 1];
      const newUndoStack = state.undoStack.slice(0, -1);
      const newRedoStack = [...state.redoStack, state.strokes];

      return {
        ...state,
        strokes: previousStrokes,
        undoStack: newUndoStack,
        redoStack: newRedoStack,
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;

      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      const newRedoStack = state.redoStack.slice(0, -1);
      const newUndoStack = [...state.undoStack, state.strokes];

      return {
        ...state,
        strokes: nextStrokes,
        undoStack: newUndoStack,
        redoStack: newRedoStack,
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'CLEAR_CANVAS': {
      const newUndoStack = [...state.undoStack, state.strokes];
      if (newUndoStack.length > UNDO_STACK_LIMIT) {
        newUndoStack.shift();
      }

      return {
        ...state,
        strokes: [],
        undoStack: newUndoStack,
        redoStack: [],
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'SET_TOOL':
      return { ...state, activeTool: action.payload };

    case 'SET_COLOR':
      return { ...state, activeColor: action.payload };

    case 'SET_LINE_WIDTH':
      return { ...state, lineWidth: action.payload };

    case 'SET_CANVAS_SIZE':
      return {
        ...state,
        canvasWidth: action.payload.width,
        canvasHeight: action.payload.height,
      };

    default:
      return state;
  }
}

// ===================== Canvas Drawing Functions =====================

function drawStroke(
  ctx: CanvasRenderingContext2D,
  stroke: Stroke,
  isCurrent: boolean = false
) {
  if (stroke.points.length < 2) return;

  ctx.save();

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color;
  }

  ctx.lineWidth = stroke.lineWidth;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // Draw the stroke
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

  for (let i = 1; i < stroke.points.length; i++) {
    const point = stroke.points[i];
    ctx.lineTo(point.x, point.y);
  }

  if (isCurrent) {
    ctx.strokeStyle = stroke.color + '80'; // Add transparency for current stroke
  }

  ctx.stroke();
  ctx.restore();
}

function redrawCanvas(
  canvas: HTMLCanvasElement,
  strokes: Stroke[],
  currentStroke: Stroke | null
) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Draw background grid
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
  strokes.forEach(stroke => {
    drawStroke(ctx, stroke);
  });

  // Draw current stroke (if any)
  if (currentStroke) {
    drawStroke(ctx, currentStroke, true);
  }
}

// ===================== Components =====================

const ColorPicker: React.FC<{
  activeColor: string;
  onColorChange: (color: string) => void;
}> = ({ activeColor, onColorChange }) => {
  const colors = [
    '#000000', '#ff0000', '#00ff00', '#0000ff',
    '#ffff00', '#ff00ff', '#00ffff', '#ff8000',
    '#8000ff', '#008000', '#800000', '#008080'
  ];

  return (
    <div className="color-picker">
      <div className="color-swatches">
        {colors.map(color => (
          <button
            key={color}
            className={`color-swatch ${activeColor === color ? 'active' : ''}`}
            style={{ backgroundColor: color }}
            onClick={() => onColorChange(color)}
            title={color}
          />
        ))}
      </div>
      <div className="custom-color">
        <input
          type="color"
          value={activeColor}
          onChange={(e) => onColorChange(e.target.value)}
          className="color-input"
        />
        <span className="color-hex">{activeColor}</span>
      </div>
    </div>
  );
};

const ToolButton: React.FC<{
  tool: 'pen' | 'eraser';
  isActive: boolean;
  onClick: () => void;
  icon: string;
  label: string;
}> = ({ tool, isActive, onClick, icon, label }) => (
  <button
    className={`tool-button ${tool} ${isActive ? 'active' : ''}`}
    onClick={onClick}
    title={label}
  >
    <span className="tool-icon">{icon}</span>
    <span className="tool-label">{label}</span>
  </button>
);

const ActionButton: React.FC<{
  onClick: () => void;
  disabled?: boolean;
  icon: string;
  label: string;
}> = ({ onClick, disabled = false, icon, label }) => (
  <button
    className="action-button"
    onClick={onClick}
    disabled={disabled}
    title={label}
  >
    <span className="action-icon">{icon}</span>
    <span className="action-label">{label}</span>
  </button>
);

const Toolbar: React.FC<{
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}> = ({ state, dispatch }) => {
  return (
    <div className="toolbar">
      <div className="tool-section">
        <ToolButton
          tool="pen"
          isActive={state.activeTool === 'pen'}
          onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
          icon="✎"
          label="Pen"
        />
        <ToolButton
          tool="eraser"
          isActive={state.activeTool === 'eraser'}
          onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
          icon="⌫"
          label="Eraser"
        />
      </div>

      <div className="tool-section">
        <ColorPicker
          activeColor={state.activeColor}
          onColorChange={(color) => dispatch({ type: 'SET_COLOR', payload: color })}
        />
      </div>

      <div className="tool-section">
        <div className="line-width-control">
          <span className="control-label">Line Width: {state.lineWidth}px</span>
          <input
            type="range"
            min="1"
            max="50"
            value={state.lineWidth}
            onChange={(e) => dispatch({ type: 'SET_LINE_WIDTH', payload: parseInt(e.target.value) })}
            className="line-width-slider"
          />
        </div>
      </div>

      <div className="tool-section">
        <ActionButton
          onClick={() => dispatch({ type: 'UNDO' })}
          disabled={state.undoStack.length === 0}
          icon="↶"
          label="Undo"
        />
        <ActionButton
          onClick={() => dispatch({ type: 'REDO' })}
          disabled={state.redoStack.length === 0}
          icon="↷"
          label="Redo"
        />
        <ActionButton
          onClick={() => dispatch({ type: 'CLEAR_CANVAS' })}
          icon="🗑"
          label="Clear"
        />
      </div>
    </div>
  );
};

const CanvasArea: React.FC<{
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}> = ({ state, dispatch }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Redraw canvas when state changes
  useEffect(() => {
    if (canvasRef.current) {
      redrawCanvas(canvasRef.current, state.strokes, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke]);

  // Set canvas size on mount and resize
  useEffect(() => {
    const updateCanvasSize = () => {
      if (containerRef.current && canvasRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        canvasRef.current.width = width;
        canvasRef.current.height = height - 2; // Account for border
        dispatch({
          type: 'SET_CANVAS_SIZE',
          payload: { width, height: height - 2 },
        });
        redrawCanvas(canvasRef.current, state.strokes, state.currentStroke);
      }
    };

    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    return () => window.removeEventListener('resize', updateCanvasSize);
  }, [state.strokes, state.currentStroke, dispatch]);

  const getCanvasCoordinates = (clientX: number, clientY: number): Point => {
    if (!canvasRef.current) return { x: 0, y: 0 };
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const point = getCanvasCoordinates(e.clientX, e.clientY);
    dispatch({ type: 'START_STROKE', payload: point });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!state.isDrawing) return;

    const point = getCanvasCoordinates(e.clientX, e.clientY);
    dispatch({ type: 'ADD_POINT', payload: point });

    // Draw incremental stroke
    if (canvasRef.current && state.currentStroke) {
      const ctx = canvasRef.current.getContext('2d');
      if (ctx && state.currentStroke.points.length >= 2) {
        const points = state.currentStroke.points;
        const lastPoint = points[points.length - 2];
        const currentPoint = points[points.length - 1];

        drawStroke(ctx, {
          ...state.currentStroke,
          points: [lastPoint, currentPoint],
        });
      }
    }
  };

  const handleMouseUp = () => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  };

  const handleMouseLeave = () => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  };

  return (
    <div className="canvas-area" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className="drawing-canvas"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />
      <div className="canvas-stats">
        <span>Strokes: {state.strokes.length}</span>
        <span>Undo Stack: {state.undoStack.length}</span>
        <span>Redo Stack: {state.redoStack.length}</span>
        {state.isDrawing && <span className="drawing-status">Drawing...</span>}
      </div>
    </div>
  );
};

// ===================== Main Component =====================

const DrawingWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, {
    strokes: [],
    currentStroke: null,
    undoStack: [],
    redoStack: [],
    activeTool: 'pen',
    activeColor: '#000000',
    lineWidth: 5,
    isDrawing: false,
    canvasWidth: 800,
    canvasHeight: 600,
  });

  return (
    <div className="drawing-whiteboard">
      <style>{`
        .drawing-whiteboard {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          height: 100vh;
          display: flex;
          flex-direction: column;
          background-color: #f5f5f5;
        }

        .toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 20px;
          padding: 16px 24px;
          background-color: white;
          border-bottom: 1px solid #e0e0e0;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .tool-section {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 16px;
          border-right: 1px solid #f0f0f0;
        }

        .tool-section:last-child {
          border-right: none;
        }

        .tool-button {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          padding: 8px 16px;
          background-color: #f8f9fa;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 14px;
        }

        .tool-button:hover {
          background-color: #e9ecef;
          border-color: #bdbdbd;
        }

        .tool-button.active {
          background-color: #e3f2fd;
          border-color: #2196f3;
          color: #1976d2;
        }

        .tool-icon {
          font-size: 20px;
        }

        .tool-label {
          font-weight: 500;
        }

        .action-button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background-color: #f8f9fa;
          border: 1px solid #ddd;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 14px;
        }

        .action-button:hover:not(:disabled) {
          background-color: #e9ecef;
          border-color: #bdbdbd;
        }

        .action-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .color-picker {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .color-swatches {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          max-width: 200px;
        }

        .color-swatch {
          width: 32px;
          height: 32px;
          border: 2px solid transparent;
          border-radius: 4px;
          cursor: pointer;
          transition: transform 0.1s ease;
        }

        .color-swatch:hover {
          transform: scale(1.1);
        }

        .color-swatch.active {
          border-color: #333;
          box-shadow: 0 0 0 2px #2196f3;
        }

        .custom-color {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .color-input {
          width: 40px;
          height: 40px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .color-hex {
          font-family: monospace;
          font-size: 14px;
          color: #333;
          background-color: #f8f9fa;
          padding: 4px 8px;
          border-radius: 4px;
          min-width: 80px;
        }

        .line-width-control {
          display: flex;
          flex-direction: column;
          gap: 8px;
          min-width: 200px;
        }

        .control-label {
          font-size: 14px;
          color: #333;
          font-weight: 500;
        }

        .line-width-slider {
          width: 100%;
          height: 6px;
          -webkit-appearance: none;
          background: #ddd;
          border-radius: 3px;
          outline: none;
        }

        .line-width-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #2196f3;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .canvas-area {
          flex: 1;
          margin: 24px;
          border: 1px solid #ddd;
          border-radius: 8px;
          background-color: white;
          overflow: hidden;
          position: relative;
        }

        .drawing-canvas {
          display: block;
          width: 100%;
          height: calc(100% - 40px);
          cursor: crosshair;
        }

        .canvas-stats {
          display: flex;
          gap: 24px;
          padding: 8px 16px;
          background-color: #f8f9fa;
          border-top: 1px solid #ddd;
          font-size: 13px;
          color: #666;
        }

        .drawing-status {
          color: #2196f3;
          font-weight: 500;
        }

        .whiteboard-info {
          padding: 16px 24px;
          background-color: white;
          border-top: 1px solid #e0e0e0;
          font-size: 13px;
          color: #666;
          display: flex;
          justify-content: space-between;
        }

        .info-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .info-label {
          font-weight: 500;
          color: #333;
        }

        .info-value {
          font-family: monospace;
          background-color: #f5f5f5;
          padding: 2px 6px;
          border-radius: 4px;
        }
      `}</style>

      <Toolbar state={state} dispatch={dispatch} />
      <CanvasArea state={state} dispatch={dispatch} />

      <div className="whiteboard-info">
        <div className="info-item">
          <span className="info-label">Active Tool:</span>
          <span className="info-value">{state.activeTool}</span>
        </div>
        <div className="info-item">
          <span className="info-label">Color:</span>
          <span className="info-value" style={{ color: state.activeColor }}>
            {state.activeColor}
          </span>
        </div>
        <div className="info-item">
          <span className="info-label">Line Width:</span>
          <span className="info-value">{state.lineWidth}px</span>
        </div>
        <div className="info-item">
          <span className="info-label">Canvas Size:</span>
          <span className="info-value">
            {Math.round(state.canvasWidth)}×{Math.round(state.canvasHeight)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default DrawingWhiteboard;