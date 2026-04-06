import React, { useReducer, useRef, useEffect, useCallback } from 'react';

type Tool = 'pen' | 'eraser';
type Action =
  | { type: 'SET_TOOL'; payload: Tool }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_BRUSH_SIZE'; payload: number }
  | { type: 'ADD_STROKE'; payload: ImageData }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

interface State {
  tool: Tool;
  color: string;
  brushSize: number;
  history: ImageData[];
  redoStack: ImageData[];
}

const COLORS = ['#000000', '#ff0000', '#0066ff', '#00aa00', '#ff8800', '#8800cc', '#ffffff'];

const initialState: State = {
  tool: 'pen',
  color: '#000000',
  brushSize: 3,
  history: [],
  redoStack: [],
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_TOOL':
      return { ...state, tool: action.payload };
    case 'SET_COLOR':
      return { ...state, color: action.payload, tool: 'pen' };
    case 'SET_BRUSH_SIZE':
      return { ...state, brushSize: action.payload };
    case 'ADD_STROKE':
      return {
        ...state,
        history: [...state.history, action.payload],
        redoStack: [],
      };
    case 'UNDO': {
      if (state.history.length <= 1) return state;
      const newHistory = state.history.slice(0, -1);
      return {
        ...state,
        history: newHistory,
        redoStack: [...state.redoStack, state.history[state.history.length - 1]],
      };
    }
    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const popped = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        history: [...state.history, popped],
        redoStack: state.redoStack.slice(0, -1),
      };
    }
    case 'CLEAR':
      return { ...state, history: [], redoStack: [] };
    default:
      return state;
  }
}

const CollaborativeWhiteboard: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);
  const [state, dispatch] = useReducer(reducer, initialState);

  const getCtx = useCallback(() => {
    return canvasRef.current?.getContext('2d') ?? null;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const container = canvas.parentElement;
    if (!container) return;
    canvas.width = container.clientWidth;
    canvas.height = 500;
    const ctx = getCtx();
    if (!ctx) return;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    dispatch({ type: 'ADD_STROKE', payload: img });
  }, [getCtx]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = getCtx();
    if (!ctx) return;
    if (state.history.length > 0) {
      const last = state.history[state.history.length - 1];
      ctx.putImageData(last, 0, 0);
    } else {
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
      dispatch({ type: 'ADD_STROKE', payload: img });
    }
  }, [state.history.length, getCtx]);

  const getPos = (e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    if ('touches' in e) {
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const startDraw = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    drawingRef.current = true;
    const ctx = getCtx();
    if (!ctx) return;
    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
  };

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!drawingRef.current) return;
    e.preventDefault();
    const ctx = getCtx();
    if (!ctx) return;
    const pos = getPos(e);
    ctx.lineWidth = state.tool === 'eraser' ? state.brushSize * 4 : state.brushSize;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = state.tool === 'eraser' ? '#ffffff' : state.color;
    ctx.globalCompositeOperation = state.tool === 'eraser' ? 'source-over' : 'source-over';
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  };

  const endDraw = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    const ctx = getCtx();
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    ctx.closePath();
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    dispatch({ type: 'ADD_STROKE', payload: img });
  };

  const handleUndo = () => dispatch({ type: 'UNDO' });
  const handleRedo = () => dispatch({ type: 'REDO' });
  const handleClear = () => {
    const ctx = getCtx();
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    dispatch({ type: 'CLEAR' });
    dispatch({ type: 'ADD_STROKE', payload: img });
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Drawing Whiteboard</h2>
      <div style={styles.toolbar}>
        <div style={styles.toolGroup}>
          <button
            style={{ ...styles.toolBtn, ...(state.tool === 'pen' ? styles.toolBtnActive : {}) }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
          >
            ✏️ Pen
          </button>
          <button
            style={{ ...styles.toolBtn, ...(state.tool === 'eraser' ? styles.toolBtnActive : {}) }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
          >
            🧹 Eraser
          </button>
        </div>
        <div style={styles.toolGroup}>
          {COLORS.map((c) => (
            <button
              key={c}
              style={{
                ...styles.colorBtn,
                backgroundColor: c,
                border: state.color === c && state.tool === 'pen' ? '3px solid #1976d2' : '3px solid #e0e0e0',
                outline: 'none',
              }}
              onClick={() => dispatch({ type: 'SET_COLOR', payload: c })}
              title={c}
            />
          ))}
        </div>
        <div style={styles.toolGroup}>
          <label style={styles.label}>Size:</label>
          <input
            type="range"
            min="1"
            max="20"
            value={state.brushSize}
            onChange={(e) => dispatch({ type: 'SET_BRUSH_SIZE', payload: Number(e.target.value) })}
            style={styles.rangeInput}
          />
          <span style={styles.rangeValue}>{state.brushSize}px</span>
        </div>
        <div style={styles.toolGroup}>
          <button style={styles.actionBtn} onClick={handleUndo} disabled={state.history.length <= 1}>
            ↩️ Undo
          </button>
          <button style={styles.actionBtn} onClick={handleRedo} disabled={state.redoStack.length === 0}>
            ↪️ Redo
          </button>
          <button style={{ ...styles.actionBtn, ...styles.clearBtn }} onClick={handleClear}>
            🗑️ Clear
          </button>
        </div>
      </div>
      <div style={styles.canvasWrapper}>
        <canvas
          ref={canvasRef}
          style={styles.canvas}
          onMouseDown={startDraw}
          onMouseMove={draw}
          onMouseUp={endDraw}
          onMouseLeave={endDraw}
          onTouchStart={startDraw}
          onTouchMove={draw}
          onTouchEnd={endDraw}
        />
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { maxWidth: 900, margin: '40px auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  title: { fontSize: 20, fontWeight: 600, marginBottom: 12, color: '#1a1a1a' },
  toolbar: { display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', marginBottom: 12, padding: '12px', background: '#f5f5f5', borderRadius: 8 },
  toolGroup: { display: 'flex', alignItems: 'center', gap: 6 },
  toolBtn: { padding: '6px 14px', border: '1px solid #ccc', borderRadius: 6, cursor: 'pointer', fontSize: 13, background: '#fff' },
  toolBtnActive: { background: '#e3f2fd', borderColor: '#1976d2', color: '#1976d2' },
  colorBtn: { width: 28, height: 28, borderRadius: '50%', cursor: 'pointer' },
  label: { fontSize: 13, color: '#555' },
  rangeInput: { width: 80, cursor: 'pointer' },
  rangeValue: { fontSize: 12, color: '#888', minWidth: 32 },
  actionBtn: { padding: '6px 12px', border: '1px solid #ccc', borderRadius: 6, cursor: 'pointer', fontSize: 13, background: '#fff' },
  clearBtn: { color: '#d32f2f', borderColor: '#ef9a9a' },
  canvasWrapper: { border: '2px solid #e0e0e0', borderRadius: 8, overflow: 'hidden', background: '#fff' },
  canvas: { display: 'block', width: '100%', touchAction: 'none' },
};

export default CollaborativeWhiteboard;
