import React, { useReducer, useRef, useCallback, useEffect } from 'react';

/* ===== 画布白板 ===== */

type ToolType = 'pen' | 'eraser';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  tool: ToolType;
  color: string;
  size: number;
  points: Point[];
}

interface CanvasState {
  strokes: Stroke[];
  undoneStrokes: Stroke[];
  currentTool: ToolType;
  currentColor: string;
  currentSize: number;
  isDrawing: boolean;
  currentStroke: Stroke | null;
}

type CanvasAction =
  | { type: 'START_DRAW'; point: Point }
  | { type: 'DRAW'; point: Point }
  | { type: 'END_DRAW' }
  | { type: 'SET_TOOL'; tool: ToolType }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_SIZE'; size: number }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

const COLORS = ['#1a1a1a', '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22'];

const SIZES = [2, 4, 8, 12, 20];

const initialState: CanvasState = {
  strokes: [],
  undoneStrokes: [],
  currentTool: 'pen',
  currentColor: COLORS[0],
  currentSize: SIZES[1],
  isDrawing: false,
  currentStroke: null,
};

function canvasReducer(state: CanvasState, action: CanvasAction): CanvasState {
  switch (action.type) {
    case 'SET_TOOL':
      return { ...state, currentTool: action.tool };
    case 'SET_COLOR':
      return { ...state, currentColor: action.color, currentTool: 'pen' };
    case 'SET_SIZE':
      return { ...state, currentSize: action.size };
    case 'START_DRAW':
      return {
        ...state,
        isDrawing: true,
        undoneStrokes: [],
        currentStroke: {
          tool: state.currentTool,
          color: state.currentColor,
          size: state.currentSize,
          points: [action.point],
        },
      };
    case 'DRAW':
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.point],
        },
      };
    case 'END_DRAW':
      if (!state.currentStroke) return state;
      return {
        ...state,
        isDrawing: false,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
      };
    case 'UNDO': {
      if (state.strokes.length === 0) return state;
      const last = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        undoneStrokes: [...state.undoneStrokes, last],
      };
    }
    case 'REDO': {
      if (state.undoneStrokes.length === 0) return state;
      const redo = state.undoneStrokes[state.undoneStrokes.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, redo],
        undoneStrokes: state.undoneStrokes.slice(0, -1),
      };
    }
    case 'CLEAR':
      return {
        ...state,
        strokes: [],
        undoneStrokes: [],
        currentStroke: null,
        isDrawing: false,
      };
    default:
      return state;
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length === 0) return;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color;
  }
  ctx.lineWidth = stroke.size;

  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

  if (stroke.points.length === 1) {
    ctx.lineTo(stroke.points[0].x + 0.1, stroke.points[0].y + 0.1);
  } else {
    for (let i = 1; i < stroke.points.length - 1; i++) {
      const midX = (stroke.points[i].x + stroke.points[i + 1].x) / 2;
      const midY = (stroke.points[i].y + stroke.points[i + 1].y) / 2;
      ctx.quadraticCurveTo(stroke.points[i].x, stroke.points[i].y, midX, midY);
    }
    const last = stroke.points[stroke.points.length - 1];
    ctx.lineTo(last.x, last.y);
  }
  ctx.stroke();
  ctx.restore();
}

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[]) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
}

function drawCurrentStroke(ctx: CanvasRenderingContext2D, strokes: Stroke[], current: Stroke | null) {
  redrawAll(ctx, strokes);
  if (current) {
    drawStroke(ctx, current);
  }
}

const CollaborativeWhiteboard: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(canvasReducer, initialState);

  const getCanvasPoint = useCallback((e: React.PointerEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (canvas.width / rect.width),
      y: (e.clientY - rect.top) * (canvas.height / rect.height),
    };
  }, []);

  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const point = getCanvasPoint(e);
    dispatch({ type: 'START_DRAW', point });
  }, [getCanvasPoint]);

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing) return;
    const point = getCanvasPoint(e);
    dispatch({ type: 'DRAW', point });
  }, [state.isDrawing, getCanvasPoint]);

  const handlePointerUp = useCallback(() => {
    dispatch({ type: 'END_DRAW' });
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (state.isDrawing || state.currentStroke) {
      drawCurrentStroke(ctx, state.strokes, state.currentStroke);
    } else {
      redrawAll(ctx, state.strokes);
    }
  }, [state.strokes, state.currentStroke, state.isDrawing]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
      e.preventDefault();
      if (e.shiftKey) {
        dispatch({ type: 'REDO' });
      } else {
        dispatch({ type: 'UNDO' });
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown as unknown as EventListener);
    return () => window.removeEventListener('keydown', handleKeyDown as unknown as EventListener);
  }, [handleKeyDown]);

  const toolBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 14px',
    border: active ? '2px solid #4a90d9' : '1px solid #ddd',
    borderRadius: '6px',
    background: active ? '#e8f0fe' : '#fff',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: active ? 600 : 400,
    color: active ? '#4a90d9' : '#555',
    transition: 'all 0.15s ease',
  });

  const colorBtnStyle = (active: boolean, color: string): React.CSSProperties => ({
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    border: active ? '3px solid #4a90d9' : '2px solid #e0e0e0',
    background: color,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    transform: active ? 'scale(1.15)' : 'scale(1)',
  });

  const sizeBtnStyle = (active: boolean, size: number): React.CSSProperties => ({
    width: '32px',
    height: '32px',
    borderRadius: '6px',
    border: active ? '2px solid #4a90d9' : '1px solid #ddd',
    background: active ? '#e8f0fe' : '#fff',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.15s ease',
  });

  return (
    <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', maxWidth: '900px', margin: '0 auto', padding: '20px 16px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', color: '#1a1a1a' }}>画布白板</h2>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={toolBtnStyle(state.currentTool === 'pen')} onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}>✏️ 画笔</button>
          <button style={toolBtnStyle(state.currentTool === 'eraser')} onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}>🧹 橡皮擦</button>
        </div>

        <div style={{ width: '1px', height: '28px', background: '#e0e0e0' }} />

        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {COLORS.map((c) => (
            <button key={c} style={colorBtnStyle(state.currentColor === c && state.currentTool === 'pen', c)} onClick={() => dispatch({ type: 'SET_COLOR', color: c })} />
          ))}
        </div>

        <div style={{ width: '1px', height: '28px', background: '#e0e0e0' }} />

        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {SIZES.map((s) => (
            <button key={s} style={sizeBtnStyle(state.currentSize === s, s)} onClick={() => dispatch({ type: 'SET_SIZE', size: s })} title={`${s}px`}>
              <span style={{ display: 'block', width: `${Math.min(s, 18)}px`, height: `${Math.min(s, 18)}px`, borderRadius: '50%', background: '#333' }} />
            </button>
          ))}
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={toolBtnStyle(false)} onClick={() => dispatch({ type: 'UNDO' })} disabled={state.strokes.length === 0} title="撤销 (Ctrl+Z)">↩ 撤销</button>
          <button style={toolBtnStyle(false)} onClick={() => dispatch({ type: 'REDO' })} disabled={state.undoneStrokes.length === 0} title="重做 (Ctrl+Shift+Z)">↪ 重做</button>
          <button style={{ ...toolBtnStyle(false), color: '#e74c3c', borderColor: '#e74c3c' }} onClick={() => dispatch({ type: 'CLEAR' })}>🗑 清除</button>
        </div>
      </div>

      <div style={{ border: '1px solid #e0e0e0', borderRadius: '8px', overflow: 'hidden', background: '#fff' }}>
        <canvas
          ref={canvasRef}
          width={1600}
          height={900}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          style={{ width: '100%', display: 'block', cursor: state.currentTool === 'eraser' ? 'cell' : 'crosshair', touchAction: 'none' }}
        />
      </div>

      <p style={{ fontSize: '12px', color: '#aaa', marginTop: '8px' }}>
        {state.strokes.length} 笔画 · Ctrl+Z 撤销 · Ctrl+Shift+Z 重做
      </p>
    </div>
  );
};

export default CollaborativeWhiteboard;
