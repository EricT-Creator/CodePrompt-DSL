import React, { useReducer, useRef, useEffect, useCallback } from 'react';

// ─── Types ───
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

type WhiteboardAction =
  | { type: 'COMMIT_STROKE'; payload: PathSegment }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number };

// ─── Constants ───
const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 600;
const PRESET_COLORS = [
  '#000000', '#ff4d4f', '#ff7a45', '#ffa940', '#ffc53d',
  '#73d13d', '#36cfc9', '#40a9ff', '#597ef7', '#9254de',
];

const STYLE_CONTENT = `
.whiteboard {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.toolGroup {
  display: flex;
  align-items: center;
  gap: 6px;
}
.toolBtn {
  padding: 8px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.toolBtn:hover {
  border-color: #1890ff;
  color: #1890ff;
}
.toolBtnActive {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}
.actionBtn {
  padding: 8px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.actionBtn:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}
.actionBtn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.colorPicker {
  display: flex;
  gap: 4px;
}
.colorSwatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.2s;
}
.colorSwatch:hover {
  transform: scale(1.15);
}
.colorSwatchActive {
  border-color: #333;
  transform: scale(1.15);
}
.separator {
  width: 1px;
  height: 28px;
  background: #e8e8e8;
}
.canvasWrapper {
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  overflow: hidden;
}
.canvas {
  display: block;
  background: #fff;
  cursor: crosshair;
}
.widthSlider {
  width: 80px;
  cursor: pointer;
}
.widthLabel {
  font-size: 12px;
  color: #888;
  min-width: 30px;
}
`;

// ─── Reducer ───
const initialState: WhiteboardState = {
  strokes: [],
  redoStack: [],
  currentTool: 'pen',
  currentColor: '#000000',
  lineWidth: 3,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'COMMIT_STROKE':
      return {
        ...state,
        strokes: [...state.strokes, action.payload],
        redoStack: [],
      };
    case 'UNDO': {
      if (state.strokes.length === 0) return state;
      const last = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, last],
      };
    }
    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const restored = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, restored],
        redoStack: state.redoStack.slice(0, -1),
      };
    }
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

// ─── Drawing helpers ───
function replayStrokes(ctx: CanvasRenderingContext2D, strokes: PathSegment[], width: number, height: number): void {
  ctx.clearRect(0, 0, width, height);
  for (const seg of strokes) {
    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    if (seg.tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.lineWidth = seg.lineWidth * 3;
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = seg.color;
      ctx.lineWidth = seg.lineWidth;
    }
    if (seg.points.length > 0) {
      ctx.beginPath();
      ctx.moveTo(seg.points[0].x, seg.points[0].y);
      for (let i = 1; i < seg.points.length; i++) {
        ctx.lineTo(seg.points[i].x, seg.points[i].y);
      }
      ctx.stroke();
    }
    ctx.restore();
  }
}

// ─── Sub-components (internal) ───

function ColorPicker({
  currentColor,
  onSelect,
}: {
  currentColor: string;
  onSelect: (color: string) => void;
}) {
  return (
    <div className="colorPicker">
      {PRESET_COLORS.map((c) => (
        <div
          key={c}
          className={`colorSwatch ${currentColor === c ? 'colorSwatchActive' : ''}`}
          style={{ backgroundColor: c }}
          onClick={() => onSelect(c)}
        />
      ))}
    </div>
  );
}

function Toolbar({
  state,
  dispatch,
}: {
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}) {
  return (
    <div className="toolbar">
      <div className="toolGroup">
        <button
          className={`toolBtn ${state.currentTool === 'pen' ? 'toolBtnActive' : ''}`}
          onClick={() => dispatch({ type: 'SET_TOOL', payload: 'pen' })}
        >
          ✏️ Pen
        </button>
        <button
          className={`toolBtn ${state.currentTool === 'eraser' ? 'toolBtnActive' : ''}`}
          onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
        >
          🧹 Eraser
        </button>
      </div>

      <div className="separator" />

      <ColorPicker
        currentColor={state.currentColor}
        onSelect={(c) => dispatch({ type: 'SET_COLOR', payload: c })}
      />

      <div className="separator" />

      <div className="toolGroup">
        <span className="widthLabel">{state.lineWidth}px</span>
        <input
          type="range"
          className="widthSlider"
          min={1}
          max={20}
          value={state.lineWidth}
          onChange={(e) => dispatch({ type: 'SET_LINE_WIDTH', payload: Number(e.target.value) })}
        />
      </div>

      <div className="separator" />

      <div className="toolGroup">
        <button
          className="actionBtn"
          onClick={() => dispatch({ type: 'UNDO' })}
          disabled={state.strokes.length === 0}
        >
          ↩ Undo
        </button>
        <button
          className="actionBtn"
          onClick={() => dispatch({ type: 'REDO' })}
          disabled={state.redoStack.length === 0}
        >
          ↪ Redo
        </button>
        <button
          className="actionBtn"
          onClick={() => dispatch({ type: 'CLEAR' })}
          disabled={state.strokes.length === 0}
        >
          🗑 Clear
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ───
export default function DrawingWhiteboard(): React.ReactElement {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const isDrawingRef = useRef(false);
  const currentSegmentRef = useRef<PathSegment | null>(null);

  // Init canvas context
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      ctxRef.current = canvas.getContext('2d');
    }
  }, []);

  // Replay on undo/redo/clear
  useEffect(() => {
    const ctx = ctxRef.current;
    if (ctx) {
      replayStrokes(ctx, state.strokes, CANVAS_WIDTH, CANVAS_HEIGHT);
    }
  }, [state.strokes]);

  const getPos = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const ctx = ctxRef.current;
      if (!ctx) return;
      isDrawingRef.current = true;
      const pos = getPos(e);
      const seg: PathSegment = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        tool: state.currentTool,
        color: state.currentColor,
        lineWidth: state.lineWidth,
        points: [pos],
      };
      currentSegmentRef.current = seg;

      ctx.save();
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      if (state.currentTool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.lineWidth = state.lineWidth * 3;
      } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = state.currentColor;
        ctx.lineWidth = state.lineWidth;
      }
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
    },
    [state.currentTool, state.currentColor, state.lineWidth, getPos]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!isDrawingRef.current) return;
      const ctx = ctxRef.current;
      const seg = currentSegmentRef.current;
      if (!ctx || !seg) return;
      const pos = getPos(e);
      seg.points.push(pos);
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
    },
    [getPos]
  );

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    const ctx = ctxRef.current;
    if (ctx) ctx.restore();
    const seg = currentSegmentRef.current;
    if (seg && seg.points.length > 1) {
      dispatch({ type: 'COMMIT_STROKE', payload: seg });
    }
    currentSegmentRef.current = null;
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (isDrawingRef.current) handleMouseUp();
  }, [handleMouseUp]);

  return (
    <>
      <style>{STYLE_CONTENT}</style>
      <div className="whiteboard">
        <Toolbar state={state} dispatch={dispatch} />
        <div className="canvasWrapper">
          <canvas
            ref={canvasRef}
            className="canvas"
            width={CANVAS_WIDTH}
            height={CANVAS_HEIGHT}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
          />
        </div>
      </div>
    </>
  );
}
