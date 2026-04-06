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

const COLORS = ['#000000', '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'];

function reducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case 'COMMIT_STROKE':
      return {
        ...state,
        strokes: [...state.strokes, action.payload],
        redoStack: [],
      };
    case 'UNDO':
      if (state.strokes.length === 0) return state;
      const lastStroke = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, lastStroke],
      };
    case 'REDO':
      if (state.redoStack.length === 0) return state;
      const nextStroke = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, nextStroke],
        redoStack: state.redoStack.slice(0, -1),
      };
    case 'CLEAR':
      return {
        ...state,
        strokes: [],
        redoStack: [...state.redoStack, ...state.strokes],
      };
    case 'SET_TOOL':
      return { ...state, currentTool: action.payload };
    case 'SET_COLOR':
      return { ...state, currentColor: action.payload };
    case 'SET_LINE_WIDTH':
      return { ...state, lineWidth: action.payload };
    default:
      return state;
  }
}

export default function DrawingWhiteboard() {
  const [state, dispatch] = useReducer(reducer, {
    strokes: [],
    redoStack: [],
    currentTool: 'pen',
    currentColor: '#000000',
    lineWidth: 2,
  });

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);
  const currentSegmentRef = useRef<PathSegment | null>(null);

  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const stroke of state.strokes) {
      ctx.beginPath();
      ctx.strokeStyle = stroke.tool === 'eraser' ? '#ffffff' : stroke.color;
      ctx.lineWidth = stroke.tool === 'eraser' ? stroke.lineWidth * 5 : stroke.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      if (stroke.tool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
      } else {
        ctx.globalCompositeOperation = 'source-over';
      }

      if (stroke.points.length > 0) {
        ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
        for (let i = 1; i < stroke.points.length; i++) {
          ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
        }
      }
      ctx.stroke();
    }

    ctx.globalCompositeOperation = 'source-over';
  }, [state.strokes]);

  useEffect(() => {
    redrawCanvas();
  }, [redrawCanvas]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    isDrawingRef.current = true;
    currentSegmentRef.current = {
      id: 'stroke-' + Date.now(),
      tool: state.currentTool,
      color: state.currentColor,
      lineWidth: state.lineWidth,
      points: [{ x, y }],
    };

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.strokeStyle = state.currentTool === 'eraser' ? '#ffffff' : state.currentColor;
      ctx.lineWidth = state.currentTool === 'eraser' ? state.lineWidth * 5 : state.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      if (state.currentTool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
      } else {
        ctx.globalCompositeOperation = 'source-over';
      }
    }
  }, [state.currentTool, state.currentColor, state.lineWidth]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current || !currentSegmentRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    currentSegmentRef.current.points.push({ x, y });

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.lineTo(x, y);
      ctx.stroke();
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current || !currentSegmentRef.current) return;

    isDrawingRef.current = false;
    dispatch({ type: 'COMMIT_STROKE', payload: currentSegmentRef.current });
    currentSegmentRef.current = null;
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (isDrawingRef.current && currentSegmentRef.current) {
      isDrawingRef.current = false;
      dispatch({ type: 'COMMIT_STROKE', payload: currentSegmentRef.current });
      currentSegmentRef.current = null;
    }
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.toolGroup}>
          <button
            className={`${styles.toolButton} ${state.currentTool === 'pen' ? styles.active : ''}`}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
          >
            Pen
          </button>
          <button
            className={`${styles.toolButton} ${state.currentTool === 'eraser' ? styles.active : ''}`}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
          >
            Eraser
          </button>
        </div>

        <div className={styles.colorPicker}>
          {COLORS.map(color => (
            <button
              key={color}
              className={`${styles.colorSwatch} ${state.currentColor === color ? styles.active : ''}`}
              style={{ backgroundColor: color }}
              onClick={() => dispatch({ type: 'SET_COLOR', payload: color })}
            />
          ))}
        </div>

        <div className={styles.lineWidthGroup}>
          <label>Width:</label>
          <input
            type="range"
            min="1"
            max="20"
            value={state.lineWidth}
            onChange={(e) => dispatch({ type: 'SET_LINE_WIDTH', payload: parseInt(e.target.value) })}
          />
          <span>{state.lineWidth}px</span>
        </div>

        <div className={styles.actionGroup}>
          <button
            className={styles.actionButton}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={state.strokes.length === 0}
          >
            Undo
          </button>
          <button
            className={styles.actionButton}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={state.redoStack.length === 0}
          >
            Redo
          </button>
          <button
            className={`${styles.actionButton} ${styles.clearButton}`}
            onClick={() => dispatch({ type: 'CLEAR' })}
          >
            Clear
          </button>
        </div>
      </div>

      <div className={styles.canvasContainer}>
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          className={styles.canvas}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        />
      </div>
    </div>
  );
}
