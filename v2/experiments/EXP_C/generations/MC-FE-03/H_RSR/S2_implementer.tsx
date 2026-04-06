import React, { useReducer, useRef, useEffect, useCallback } from 'react';
import styles from './DrawingWhiteboard.module.css';

interface Point {
  x: number;
  y: number;
}

interface PathSegment {
  id: string;
  tool: 'pen' | 'eraser';
  color: string;
  lineWidth: number;
  points: Point[];
}

interface WhiteboardState {
  strokes: PathSegment[];
  redoStack: PathSegment[];
  currentTool: 'pen' | 'eraser';
  currentColor: string;
  lineWidth: number;
}

type Action =
  | { type: 'COMMIT_STROKE'; payload: PathSegment }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number };

const initialState: WhiteboardState = {
  strokes: [],
  redoStack: [],
  currentTool: 'pen',
  currentColor: '#000000',
  lineWidth: 3
};

function whiteboardReducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'COMMIT_STROKE': {
      return {
        ...state,
        strokes: [...state.strokes, action.payload],
        redoStack: []
      };
    }

    case 'UNDO': {
      if (state.strokes.length === 0) return state;
      
      const lastStroke = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, lastStroke]
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      
      const lastRedo = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, lastRedo],
        redoStack: state.redoStack.slice(0, -1)
      };
    }

    case 'CLEAR': {
      return {
        ...state,
        strokes: [],
        redoStack: [...state.redoStack, ...state.strokes]
      };
    }

    case 'SET_TOOL': {
      return {
        ...state,
        currentTool: action.payload
      };
    }

    case 'SET_COLOR': {
      return {
        ...state,
        currentColor: action.payload
      };
    }

    case 'SET_LINE_WIDTH': {
      return {
        ...state,
        lineWidth: action.payload
      };
    }

    default:
      return state;
  }
}

const Toolbar: React.FC<{
  currentTool: 'pen' | 'eraser';
  currentColor: string;
  lineWidth: number;
  canUndo: boolean;
  canRedo: boolean;
  onToolChange: (tool: 'pen' | 'eraser') => void;
  onColorChange: (color: string) => void;
  onLineWidthChange: (width: number) => void;
  onUndo: () => void;
  onRedo: () => void;
  onClear: () => void;
}> = ({
  currentTool,
  currentColor,
  lineWidth,
  canUndo,
  canRedo,
  onToolChange,
  onColorChange,
  onLineWidthChange,
  onUndo,
  onRedo,
  onClear
}) => {
  const colors = [
    '#000000', '#FF3B30', '#FF9500', '#FFCC00',
    '#4CD964', '#5AC8FA', '#007AFF', '#5856D6',
    '#FF2D55', '#8E8E93'
  ];

  const lineWidths = [1, 3, 5, 8, 12];

  return (
    <div className={styles.toolbar}>
      <div className={styles.toolGroup}>
        <button
          className={`${styles.toolButton} ${currentTool === 'pen' ? styles.active : ''}`}
          onClick={() => onToolChange('pen')}
          title="Pen"
        >
          <span className={styles.toolIcon}>✏️</span>
          <span className={styles.toolLabel}>Pen</span>
        </button>
        <button
          className={`${styles.toolButton} ${currentTool === 'eraser' ? styles.active : ''}`}
          onClick={() => onToolChange('eraser')}
          title="Eraser"
        >
          <span className={styles.toolIcon}>🧽</span>
          <span className={styles.toolLabel}>Eraser</span>
        </button>
      </div>

      <div className={styles.toolGroup}>
        <div className={styles.colorPicker}>
          {colors.map((color) => (
            <button
              key={color}
              className={`${styles.colorSwatch} ${currentColor === color ? styles.selected : ''}`}
              style={{ backgroundColor: color }}
              onClick={() => onColorChange(color)}
              title={color}
            />
          ))}
        </div>
      </div>

      <div className={styles.toolGroup}>
        <div className={styles.lineWidthPicker}>
          {lineWidths.map((width) => (
            <button
              key={width}
              className={`${styles.lineWidthOption} ${lineWidth === width ? styles.selected : ''}`}
              onClick={() => onLineWidthChange(width)}
              title={`${width}px`}
            >
              <div
                className={styles.lineWidthPreview}
                style={{
                  width: width * 2,
                  height: width * 2,
                  backgroundColor: currentColor
                }}
              />
            </button>
          ))}
        </div>
      </div>

      <div className={styles.toolGroup}>
        <button
          className={`${styles.actionButton} ${!canUndo ? styles.disabled : ''}`}
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo"
        >
          <span className={styles.actionIcon}>↶</span>
          <span className={styles.actionLabel}>Undo</span>
        </button>
        <button
          className={`${styles.actionButton} ${!canRedo ? styles.disabled : ''}`}
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo"
        >
          <span className={styles.actionIcon}>↷</span>
          <span className={styles.actionLabel}>Redo</span>
        </button>
        <button
          className={styles.actionButton}
          onClick={onClear}
          title="Clear"
        >
          <span className={styles.actionIcon}>🗑️</span>
          <span className={styles.actionLabel}>Clear</span>
        </button>
      </div>
    </div>
  );
};

const Canvas: React.FC<{
  width: number;
  height: number;
  strokes: PathSegment[];
  currentTool: 'pen' | 'eraser';
  currentColor: string;
  lineWidth: number;
  onStrokeStart: (point: Point) => PathSegment;
  onStrokeMove: (segment: PathSegment, point: Point) => void;
  onStrokeEnd: (segment: PathSegment) => void;
}> = ({
  width,
  height,
  strokes,
  currentTool,
  currentColor,
  lineWidth,
  onStrokeStart,
  onStrokeMove,
  onStrokeEnd
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const isDrawingRef = useRef(false);
  const currentSegmentRef = useRef<PathSegment | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctxRef.current = ctx;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }, []);

  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    strokes.forEach((stroke) => {
      if (stroke.points.length < 2) return;

      ctx.beginPath();
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

      for (let i = 1; i < stroke.points.length; i++) {
        ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
      }

      if (stroke.tool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.strokeStyle = 'rgba(0,0,0,1)';
      } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = stroke.color;
      }

      ctx.lineWidth = stroke.lineWidth;
      ctx.stroke();
    });

    ctx.globalCompositeOperation = 'source-over';
  }, [strokes]);

  useEffect(() => {
    redrawCanvas();
  }, [redrawCanvas]);

  const getCanvasPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    isDrawingRef.current = true;
    const point = getCanvasPoint(e);
    currentSegmentRef.current = onStrokeStart(point);

    const ctx = ctxRef.current;
    if (ctx && currentSegmentRef.current) {
      ctx.beginPath();
      ctx.moveTo(point.x, point.y);
      
      if (currentSegmentRef.current.tool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.strokeStyle = 'rgba(0,0,0,1)';
      } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = currentSegmentRef.current.color;
      }
      
      ctx.lineWidth = currentSegmentRef.current.lineWidth;
    }
  }, [getCanvasPoint, onStrokeStart]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current || !currentSegmentRef.current) return;

    const point = getCanvasPoint(e);
    const updatedSegment = {
      ...currentSegmentRef.current,
      points: [...currentSegmentRef.current.points, point]
    };
    currentSegmentRef.current = updatedSegment;
    onStrokeMove(updatedSegment, point);

    const ctx = ctxRef.current;
    if (ctx) {
      ctx.lineTo(point.x, point.y);
      ctx.stroke();
    }
  }, [getCanvasPoint, onStrokeMove]);

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current || !currentSegmentRef.current) return;

    isDrawingRef.current = false;
    if (currentSegmentRef.current.points.length > 1) {
      onStrokeEnd(currentSegmentRef.current);
    }
    currentSegmentRef.current = null;

    const ctx = ctxRef.current;
    if (ctx) {
      ctx.globalCompositeOperation = 'source-over';
    }
  }, [onStrokeEnd]);

  const handleMouseLeave = useCallback(() => {
    if (isDrawingRef.current && currentSegmentRef.current) {
      handleMouseUp();
    }
  }, [handleMouseUp]);

  return (
    <canvas
      ref={canvasRef}
      className={styles.canvas}
      width={width}
      height={height}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
    />
  );
};

const DrawingWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  
  const canvasWidth = 800;
  const canvasHeight = 600;

  const handleStrokeStart = useCallback((point: Point): PathSegment => {
    const segment: PathSegment = {
      id: `stroke_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      tool: state.currentTool,
      color: state.currentTool === 'pen' ? state.currentColor : '#000000',
      lineWidth: state.lineWidth,
      points: [point]
    };
    return segment;
  }, [state.currentTool, state.currentColor, state.lineWidth]);

  const handleStrokeMove = useCallback((segment: PathSegment, point: Point) => {
    // No action needed during move - incremental drawing is handled by Canvas
  }, []);

  const handleStrokeEnd = useCallback((segment: PathSegment) => {
    dispatch({ type: 'COMMIT_STROKE', payload: segment });
  }, []);

  const handleToolChange = useCallback((tool: 'pen' | 'eraser') => {
    dispatch({ type: 'SET_TOOL', payload: tool });
  }, []);

  const handleColorChange = useCallback((color: string) => {
    dispatch({ type: 'SET_COLOR', payload: color });
  }, []);

  const handleLineWidthChange = useCallback((width: number) => {
    dispatch({ type: 'SET_LINE_WIDTH', payload: width });
  }, []);

  const handleUndo = useCallback(() => {
    dispatch({ type: 'UNDO' });
  }, []);

  const handleRedo = useCallback(() => {
    dispatch({ type: 'REDO' });
  }, []);

  const handleClear = useCallback(() => {
    dispatch({ type: 'CLEAR' });
  }, []);

  return (
    <div className={styles.whiteboard}>
      <div className={styles.header}>
        <h1 className={styles.title}>Canvas Drawing Whiteboard</h1>
        <div className={styles.stats}>
          <span className={styles.stat}>
            Strokes: {state.strokes.length}
          </span>
          <span className={styles.stat}>
            Redo Stack: {state.redoStack.length}
          </span>
        </div>
      </div>

      <Toolbar
        currentTool={state.currentTool}
        currentColor={state.currentColor}
        lineWidth={state.lineWidth}
        canUndo={state.strokes.length > 0}
        canRedo={state.redoStack.length > 0}
        onToolChange={handleToolChange}
        onColorChange={handleColorChange}
        onLineWidthChange={handleLineWidthChange}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onClear={handleClear}
      />

      <div className={styles.canvasContainer}>
        <Canvas
          width={canvasWidth}
          height={canvasHeight}
          strokes={state.strokes}
          currentTool={state.currentTool}
          currentColor={state.currentColor}
          lineWidth={state.lineWidth}
          onStrokeStart={handleStrokeStart}
          onStrokeMove={handleStrokeMove}
          onStrokeEnd={handleStrokeEnd}
        />
      </div>

      <div className={styles.instructions}>
        <p className={styles.instruction}>
          <strong>How to use:</strong> Click and drag to draw. Use the toolbar to switch between pen and eraser.
        </p>
        <p className={styles.instruction}>
          <strong>Undo/Redo:</strong> Use the buttons or keyboard shortcuts (Ctrl+Z / Ctrl+Shift+Z).
        </p>
      </div>
    </div>
  );
};

export default DrawingWhiteboard;