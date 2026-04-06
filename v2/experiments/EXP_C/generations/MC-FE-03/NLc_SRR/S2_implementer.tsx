import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ── Types ──────────────────────────────────────────────────────────────

interface Point {
  x: number;
  y: number;
  timestamp: number;
}

interface DrawCommand {
  type: 'pen' | 'eraser' | 'clear';
  points: Point[];
  color: string;
  lineWidth: number;
}

interface CanvasState {
  tool: 'pen' | 'eraser';
  color: string;
  lineWidth: number;
  isDrawing: boolean;
  currentPath: Point[];
  history: DrawCommand[];
  historyIndex: number;
  canvasSize: { width: number; height: number };
}

type CanvasAction =
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number }
  | { type: 'START_DRAWING'; payload: Point }
  | { type: 'ADD_POINT'; payload: Point }
  | { type: 'STOP_DRAWING' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'SET_CANVAS_SIZE'; payload: { width: number; height: number } };

// ── CSS ────────────────────────────────────────────────────────────────

const css = `
.wb-container{display:flex;flex-direction:column;height:100vh;background:#f0f2f5;font-family:system-ui,-apple-system,sans-serif}
.wb-toolbar{display:flex;align-items:center;gap:12px;padding:10px 16px;background:#fff;border-bottom:1px solid #e2e8f0;flex-wrap:wrap}
.wb-toolbar-group{display:flex;align-items:center;gap:6px;padding:0 8px;border-right:1px solid #e2e8f0}
.wb-toolbar-group:last-child{border-right:none}
.wb-tool-btn{padding:8px 14px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;transition:all .15s;display:flex;align-items:center;gap:4px}
.wb-tool-btn:hover{background:#f1f5f9}
.wb-tool-btn.active{background:#3b82f6;color:#fff;border-color:#3b82f6}
.wb-color-input{width:32px;height:32px;border:2px solid #d1d5db;border-radius:6px;cursor:pointer;padding:0;background:none}
.wb-range-label{font-size:12px;color:#64748b;min-width:40px}
.wb-range{width:100px}
.wb-canvas-area{flex:1;display:flex;justify-content:center;align-items:center;padding:16px;overflow:auto}
.wb-canvas{border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.1);cursor:crosshair;background:#fff}
.wb-canvas.eraser{cursor:cell}
.wb-status{display:flex;align-items:center;justify-content:space-between;padding:6px 16px;background:#fff;border-top:1px solid #e2e8f0;font-size:12px;color:#64748b}
`;

// ── Reducer ─────────────────────────────────────────────────────────────

const initialState: CanvasState = {
  tool: 'pen',
  color: '#000000',
  lineWidth: 3,
  isDrawing: false,
  currentPath: [],
  history: [],
  historyIndex: -1,
  canvasSize: { width: 900, height: 600 },
};

function canvasReducer(state: CanvasState, action: CanvasAction): CanvasState {
  switch (action.type) {
    case 'SET_TOOL':
      return { ...state, tool: action.payload };
    case 'SET_COLOR':
      return { ...state, color: action.payload };
    case 'SET_LINE_WIDTH':
      return { ...state, lineWidth: action.payload };
    case 'START_DRAWING':
      return { ...state, isDrawing: true, currentPath: [action.payload] };
    case 'ADD_POINT':
      return { ...state, currentPath: [...state.currentPath, action.payload] };
    case 'STOP_DRAWING': {
      if (state.currentPath.length < 2) return { ...state, isDrawing: false, currentPath: [] };
      const cmd: DrawCommand = {
        type: state.tool,
        points: state.currentPath,
        color: state.color,
        lineWidth: state.lineWidth,
      };
      // Truncate redo history
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push(cmd);
      // Limit to 50 steps
      const trimmed = newHistory.length > 50 ? newHistory.slice(newHistory.length - 50) : newHistory;
      return {
        ...state,
        isDrawing: false,
        currentPath: [],
        history: trimmed,
        historyIndex: trimmed.length - 1,
      };
    }
    case 'CLEAR_CANVAS': {
      const clearCmd: DrawCommand = { type: 'clear', points: [], color: '', lineWidth: 0 };
      const h = state.history.slice(0, state.historyIndex + 1);
      h.push(clearCmd);
      return { ...state, history: h, historyIndex: h.length - 1 };
    }
    case 'UNDO':
      if (state.historyIndex < 0) return state;
      return { ...state, historyIndex: state.historyIndex - 1 };
    case 'REDO':
      if (state.historyIndex >= state.history.length - 1) return state;
      return { ...state, historyIndex: state.historyIndex + 1 };
    case 'SET_CANVAS_SIZE':
      return { ...state, canvasSize: action.payload };
    default:
      return state;
  }
}

// ── Drawing helpers ────────────────────────────────────────────────────

function drawCommand(ctx: CanvasRenderingContext2D, cmd: DrawCommand) {
  if (cmd.type === 'clear') {
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    return;
  }

  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = cmd.lineWidth;

  if (cmd.type === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = cmd.color;
  }

  const pts = cmd.points;
  if (pts.length < 2) {
    ctx.restore();
    return;
  }

  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);

  for (let i = 1; i < pts.length - 1; i++) {
    const cx = (pts[i].x + pts[i + 1].x) / 2;
    const cy = (pts[i].y + pts[i + 1].y) / 2;
    ctx.quadraticCurveTo(pts[i].x, pts[i].y, cx, cy);
  }

  ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
  ctx.stroke();
  ctx.restore();
}

function replayHistory(ctx: CanvasRenderingContext2D, history: DrawCommand[], upTo: number) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  for (let i = 0; i <= upTo; i++) {
    drawCommand(ctx, history[i]);
  }
}

// ── Colors palette ─────────────────────────────────────────────────────

const PRESET_COLORS = ['#000000', '#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#ffffff'];

// ── Component ──────────────────────────────────────────────────────────

const CanvasWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(canvasReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  // Redraw on history change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (state.historyIndex < 0) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    } else {
      replayHistory(ctx, state.history, state.historyIndex);
    }
  }, [state.historyIndex, state.history]);

  // Draw current stroke in real-time
  useEffect(() => {
    if (!state.isDrawing || state.currentPath.length < 2) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw the last segment
    const pts = state.currentPath;
    const len = pts.length;
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = state.lineWidth;

    if (state.tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.strokeStyle = 'rgba(0,0,0,1)';
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = state.color;
    }

    ctx.beginPath();
    if (len === 2) {
      ctx.moveTo(pts[0].x, pts[0].y);
      ctx.lineTo(pts[1].x, pts[1].y);
    } else {
      const p0 = pts[len - 3];
      const p1 = pts[len - 2];
      const p2 = pts[len - 1];
      const cx = (p1.x + p2.x) / 2;
      const cy = (p1.y + p2.y) / 2;
      ctx.moveTo((p0.x + p1.x) / 2, (p0.y + p1.y) / 2);
      ctx.quadraticCurveTo(p1.x, p1.y, cx, cy);
    }
    ctx.stroke();
    ctx.restore();
  }, [state.currentPath, state.isDrawing, state.tool, state.color, state.lineWidth]);

  const getPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top, timestamp: Date.now() };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      isDrawingRef.current = true;
      dispatch({ type: 'START_DRAWING', payload: getPoint(e) });
    },
    [getPoint],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!isDrawingRef.current) return;
      dispatch({ type: 'ADD_POINT', payload: getPoint(e) });
    },
    [getPoint],
  );

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    dispatch({ type: 'STOP_DRAWING' });
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (isDrawingRef.current) {
      isDrawingRef.current = false;
      dispatch({ type: 'STOP_DRAWING' });
    }
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          dispatch({ type: 'REDO' });
        } else {
          dispatch({ type: 'UNDO' });
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const canUndo = state.historyIndex >= 0;
  const canRedo = state.historyIndex < state.history.length - 1;

  return (
    <>
      <style>{css}</style>
      <div className="wb-container">
        {/* Toolbar */}
        <div className="wb-toolbar">
          <div className="wb-toolbar-group">
            <button
              className={`wb-tool-btn${state.tool === 'pen' ? ' active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
            >
              ✏️ Pen
            </button>
            <button
              className={`wb-tool-btn${state.tool === 'eraser' ? ' active' : ''}`}
              onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
            >
              🧹 Eraser
            </button>
          </div>

          <div className="wb-toolbar-group">
            {PRESET_COLORS.map((c) => (
              <div
                key={c}
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 4,
                  background: c,
                  border: state.color === c ? '2px solid #3b82f6' : '1px solid #d1d5db',
                  cursor: 'pointer',
                }}
                onClick={() => dispatch({ type: 'SET_COLOR', payload: c })}
              />
            ))}
            <input
              type="color"
              className="wb-color-input"
              value={state.color}
              onChange={(e) => dispatch({ type: 'SET_COLOR', payload: e.target.value })}
            />
          </div>

          <div className="wb-toolbar-group">
            <span className="wb-range-label">{state.lineWidth}px</span>
            <input
              type="range"
              className="wb-range"
              min={1}
              max={30}
              value={state.lineWidth}
              onChange={(e) => dispatch({ type: 'SET_LINE_WIDTH', payload: Number(e.target.value) })}
            />
          </div>

          <div className="wb-toolbar-group">
            <button className="wb-tool-btn" onClick={() => dispatch({ type: 'UNDO' })} disabled={!canUndo}>
              ↩ Undo
            </button>
            <button className="wb-tool-btn" onClick={() => dispatch({ type: 'REDO' })} disabled={!canRedo}>
              ↪ Redo
            </button>
            <button className="wb-tool-btn" onClick={() => dispatch({ type: 'CLEAR_CANVAS' })} style={{ color: '#ef4444' }}>
              🗑 Clear
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="wb-canvas-area">
          <canvas
            ref={canvasRef}
            className={`wb-canvas${state.tool === 'eraser' ? ' eraser' : ''}`}
            width={state.canvasSize.width}
            height={state.canvasSize.height}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
          />
        </div>

        {/* Status */}
        <div className="wb-status">
          <span>Tool: {state.tool} | Color: {state.color} | Width: {state.lineWidth}px</span>
          <span>
            History: {state.historyIndex + 1} / {state.history.length}
          </span>
        </div>
      </div>
    </>
  );
};

export default CanvasWhiteboard;
