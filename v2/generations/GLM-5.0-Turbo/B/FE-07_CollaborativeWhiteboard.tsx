import React, { useReducer, useRef, useEffect, useCallback } from 'react';

/* ===== Types ===== */
interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  size: number;
  tool: 'pen' | 'eraser';
}

interface Tool {
  type: 'pen' | 'eraser';
  color: string;
  size: number;
}

/* ===== State ===== */
interface WhiteboardState {
  strokes: Stroke[];
  undone: Stroke[];
  tool: Tool;
}

type WhiteboardAction =
  | { type: 'STROKE_START'; point: Point }
  | { type: 'STROKE_MOVE'; point: Point }
  | { type: 'STROKE_END' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_TOOL'; tool: Partial<Tool> };

const PALETTE = ['#1a1a2e', '#e63946', '#457b9d', '#2a9d8f', '#e9c46a', '#f4a261', '#264653'];
const SIZES = [2, 4, 8, 12, 20];

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'STROKE_START':
    case 'STROKE_MOVE': {
      const point = action.point;
      const strokes = [...state.strokes];
      if (action.type === 'STROKE_START') {
        strokes.push({
          points: [point],
          color: state.tool.type === 'eraser' ? '#ffffff' : state.tool.color,
          size: state.tool.type === 'eraser' ? state.tool.size * 3 : state.tool.size,
          tool: state.tool.type,
        });
      } else {
        const last = strokes[strokes.length - 1];
        if (last) {
          last.points = [...last.points, point];
        }
      }
      return { ...state, strokes, undone: [] };
    }
    case 'STROKE_END':
      return state;
    case 'UNDO': {
      if (state.strokes.length === 0) return state;
      const strokes = state.strokes.slice(0, -1);
      const undone = [state.strokes[state.strokes.length - 1], ...state.undone];
      return { ...state, strokes, undone };
    }
    case 'REDO': {
      if (state.undone.length === 0) return state;
      const strokes = [...state.strokes, state.undone[0]];
      const undone = state.undone.slice(1);
      return { ...state, strokes, undone };
    }
    case 'CLEAR':
      return { ...state, strokes: [], undone: [] };
    case 'SET_TOOL':
      return { ...state, tool: { ...state.tool, ...action.tool } };
    default:
      return state;
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length < 2) return;
  ctx.beginPath();
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.size;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
  } else {
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    const mid: Point = {
      x: (stroke.points[i - 1].x + stroke.points[i].x) / 2,
      y: (stroke.points[i - 1].y + stroke.points[i].y) / 2,
    };
    ctx.quadraticCurveTo(stroke.points[i - 1].x, stroke.points[i - 1].y, mid.x, mid.y);
  }
  ctx.stroke();
  ctx.globalCompositeOperation = 'source-over';
}

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[], currentStroke: Stroke | null) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
  if (currentStroke) {
    drawStroke(ctx, currentStroke);
  }
}

function getCanvasPoint(canvas: HTMLCanvasElement, e: React.MouseEvent | React.TouchEvent): Point {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  let clientX: number, clientY: number;
  if ('touches' in e) {
    clientX = e.touches[0].clientX;
    clientY = e.touches[0].clientY;
  } else {
    clientX = e.clientX;
    clientY = e.clientY;
  }
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  };
}

const initialState: WhiteboardState = {
  strokes: [],
  undone: [],
  tool: { type: 'pen', color: PALETTE[0], size: 4 },
};

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);
  const currentStrokeRef = useRef<Stroke | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = parent.clientWidth * dpr;
      canvas.height = parent.clientHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      redrawAll(ctx, state.strokes, null);
    };

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawAll(ctx, state.strokes, currentStrokeRef.current);
  }, [state.strokes]);

  const getPoint = useCallback((e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    return getCanvasPoint(canvas, e);
  }, []);

  const handlePointerDown = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawing.current = true;
    const point = getPoint(e);
    dispatch({ type: 'STROKE_START', point });
    const newStroke: Stroke = {
      points: [point],
      color: state.tool.type === 'eraser' ? '#ffffff' : state.tool.color,
      size: state.tool.type === 'eraser' ? state.tool.size * 3 : state.tool.size,
      tool: state.tool.type,
    };
    currentStrokeRef.current = newStroke;
  }, [state.tool, getPoint]);

  const handlePointerMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing.current) return;
    e.preventDefault();
    const point = getPoint(e);
    dispatch({ type: 'STROKE_MOVE', point });
    if (currentStrokeRef.current) {
      currentStrokeRef.current = {
        ...currentStrokeRef.current,
        points: [...currentStrokeRef.current.points, point],
      };
    }
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawAll(ctx, state.strokes, currentStrokeRef.current);
  }, [state.strokes, getPoint]);

  const handlePointerUp = useCallback(() => {
    isDrawing.current = false;
    currentStrokeRef.current = null;
  }, []);

  useEffect(() => {
    const handleGlobalUp = () => {
      isDrawing.current = false;
      currentStrokeRef.current = null;
    };
    window.addEventListener('mouseup', handleGlobalUp);
    window.addEventListener('touchend', handleGlobalUp);
    return () => {
      window.removeEventListener('mouseup', handleGlobalUp);
      window.removeEventListener('touchend', handleGlobalUp);
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          dispatch({ type: 'REDO' });
        } else {
          dispatch({ type: 'UNDO' });
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <style>{`
        .whiteboard-root {
          max-width: 900px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .whiteboard-title {
          text-align: center;
          color: #333;
          margin-bottom: 12px;
          font-size: 20px;
        }
        .whiteboard-toolbar {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 16px;
          background: #f8f9fa;
          border: 1px solid #e0e0e0;
          border-bottom: none;
          border-radius: 8px 8px 0 0;
          flex-wrap: wrap;
        }
        .toolbar-group {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .toolbar-divider {
          width: 1px;
          height: 28px;
          background: #ddd;
        }
        .toolbar-label {
          font-size: 11px;
          color: #888;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-right: 4px;
        }
        .tool-btn {
          width: 36px;
          height: 36px;
          border: 2px solid transparent;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
          transition: border-color 0.15s, background 0.15s;
        }
        .tool-btn:hover {
          background: #eef1f5;
        }
        .tool-btn.active {
          border-color: #4a90d9;
          background: #e8f0fe;
        }
        .color-swatch {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          border: 2px solid transparent;
          cursor: pointer;
          transition: transform 0.15s, border-color 0.15s;
        }
        .color-swatch:hover {
          transform: scale(1.15);
        }
        .color-swatch.active {
          border-color: #333;
          box-shadow: 0 0 0 2px #fff, 0 0 0 4px #333;
        }
        .size-btn {
          width: 36px;
          height: 36px;
          border: 2px solid transparent;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: border-color 0.15s, background 0.15s;
        }
        .size-btn:hover {
          background: #eef1f5;
        }
        .size-btn.active {
          border-color: #4a90d9;
          background: #e8f0fe;
        }
        .size-dot {
          border-radius: 50%;
          background: #333;
        }
        .whiteboard-canvas-wrap {
          border: 1px solid #e0e0e0;
          border-radius: 0 0 8px 8px;
          overflow: hidden;
          background: #fff;
        }
        .whiteboard-canvas {
          display: block;
          width: 100%;
          height: 500px;
          cursor: crosshair;
          touch-action: none;
        }
      `}</style>
      <div className="whiteboard-root">
        <div className="whiteboard-title">🎨 Whiteboard</div>
        <div className="whiteboard-toolbar">
          <div className="toolbar-group">
            <span className="toolbar-label">Tool</span>
            <button
              className={`tool-btn${state.tool.type === 'pen' ? ' active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TOOL', tool: { type: 'pen' } })}
              title="Pen"
            >✏️</button>
            <button
              className={`tool-btn${state.tool.type === 'eraser' ? ' active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TOOL', tool: { type: 'eraser' } })}
              title="Eraser"
            >🧹</button>
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-group">
            <span className="toolbar-label">Color</span>
            {PALETTE.map(color => (
              <div
                key={color}
                className={`color-swatch${state.tool.color === color ? ' active' : ''}`}
                style={{ background: color }}
                onClick={() => dispatch({ type: 'SET_TOOL', tool: { color } })}
              />
            ))}
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-group">
            <span className="toolbar-label">Size</span>
            {SIZES.map(size => (
              <button
                key={size}
                className={`size-btn${state.tool.size === size ? ' active' : ''}`}
                onClick={() => dispatch({ type: 'SET_TOOL', tool: { size } })}
                title={`Size ${size}`}
              >
                <div className="size-dot" style={{ width: size + 4, height: size + 4 }} />
              </button>
            ))}
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-group">
            <button className="tool-btn" onClick={() => dispatch({ type: 'UNDO' })} title="Undo (Ctrl+Z)">↩️</button>
            <button className="tool-btn" onClick={() => dispatch({ type: 'REDO' })} title="Redo (Ctrl+Shift+Z)">↪️</button>
            <button className="tool-btn" onClick={() => dispatch({ type: 'CLEAR' })} title="Clear All">🗑️</button>
          </div>
        </div>
        <div className="whiteboard-canvas-wrap">
          <canvas
            ref={canvasRef}
            className="whiteboard-canvas"
            onMouseDown={handlePointerDown}
            onMouseMove={handlePointerMove}
            onTouchStart={handlePointerDown}
            onTouchMove={handlePointerMove}
          />
        </div>
      </div>
    </div>
  );
}
