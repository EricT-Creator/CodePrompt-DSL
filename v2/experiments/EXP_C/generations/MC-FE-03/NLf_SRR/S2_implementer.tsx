import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ── CSS ────────────────────────────────────────────────────────────────
const css = `
  .wb { display:flex; flex-direction:column; height:100vh; font-family:system-ui,sans-serif; background:#f5f5f5; }
  .toolbar { display:flex; align-items:center; gap:12px; padding:10px 16px; background:#fff; border-bottom:1px solid #ddd; flex-wrap:wrap; }
  .toolGroup { display:flex; align-items:center; gap:4px; }
  .toolBtn { padding:6px 12px; border:1px solid #ddd; background:#fff; border-radius:6px; cursor:pointer; font-size:13px; }
  .toolBtn:hover { background:#f0f0f0; }
  .toolBtnActive { background:#4a90d9; color:#fff; border-color:#4a90d9; }
  .colorSwatch { width:28px; height:28px; border-radius:50%; border:2px solid #ddd; cursor:pointer; }
  .colorSwatchActive { border-color:#333; box-shadow:0 0 0 2px #4a90d9; }
  .slider { width:80px; }
  .historyBtn { padding:6px 10px; border:1px solid #ddd; background:#fff; border-radius:6px; cursor:pointer; font-size:14px; }
  .historyBtn:hover:not(:disabled) { background:#f0f0f0; }
  .historyBtn:disabled { opacity:.4; cursor:not-allowed; }
  .canvasWrap { flex:1; display:flex; align-items:center; justify-content:center; overflow:hidden; }
  .canvas { background:#fff; box-shadow:0 2px 12px rgba(0,0,0,.1); cursor:crosshair; }
  .label { font-size:11px; color:#888; }
`;

// ── Types ──────────────────────────────────────────────────────────────
interface Point { x: number; y: number; }
interface DrawingPath {
  id: string;
  tool: "pen" | "eraser";
  color: string;
  lineWidth: number;
  points: Point[];
}

interface DrawingState {
  tool: "pen" | "eraser";
  color: string;
  lineWidth: number;
  paths: DrawingPath[];
  currentPath: DrawingPath | null;
  isDrawing: boolean;
  historyStack: DrawingPath[][];
  historyIndex: number;
}

type Action =
  | { type: "SET_TOOL"; payload: "pen" | "eraser" }
  | { type: "SET_COLOR"; payload: string }
  | { type: "SET_LINE_WIDTH"; payload: number }
  | { type: "START_DRAWING"; payload: Point }
  | { type: "ADD_POINT"; payload: Point }
  | { type: "END_DRAWING" }
  | { type: "CLEAR_CANVAS" }
  | { type: "UNDO" }
  | { type: "REDO" };

// ── Constants ──────────────────────────────────────────────────────────
const COLORS = ["#000000","#e53935","#fb8c00","#fdd835","#43a047","#1e88e5","#8e24aa","#ffffff"];
let pathIdCounter = 0;
const newId = () => `p${++pathIdCounter}`;
const MAX_HISTORY = 50;

// ── Reducer ────────────────────────────────────────────────────────────
const initialState: DrawingState = {
  tool: "pen",
  color: "#000000",
  lineWidth: 3,
  paths: [],
  currentPath: null,
  isDrawing: false,
  historyStack: [[]],
  historyIndex: 0,
};

function reducer(state: DrawingState, action: Action): DrawingState {
  switch (action.type) {
    case "SET_TOOL":
      return { ...state, tool: action.payload };
    case "SET_COLOR":
      return { ...state, color: action.payload };
    case "SET_LINE_WIDTH":
      return { ...state, lineWidth: action.payload };
    case "START_DRAWING": {
      const p: DrawingPath = {
        id: newId(),
        tool: state.tool,
        color: state.tool === "eraser" ? "#ffffff" : state.color,
        lineWidth: state.tool === "eraser" ? state.lineWidth * 3 : state.lineWidth,
        points: [action.payload],
      };
      return { ...state, isDrawing: true, currentPath: p };
    }
    case "ADD_POINT": {
      if (!state.currentPath) return state;
      return {
        ...state,
        currentPath: {
          ...state.currentPath,
          points: [...state.currentPath.points, action.payload],
        },
      };
    }
    case "END_DRAWING": {
      if (!state.currentPath || state.currentPath.points.length < 2) {
        return { ...state, isDrawing: false, currentPath: null };
      }
      const newPaths = [...state.paths, state.currentPath];
      const trimmedHistory = state.historyStack.slice(0, state.historyIndex + 1);
      const newHistory = [...trimmedHistory, newPaths].slice(-MAX_HISTORY);
      return {
        ...state,
        isDrawing: false,
        currentPath: null,
        paths: newPaths,
        historyStack: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }
    case "CLEAR_CANVAS": {
      const trimmedHistory = state.historyStack.slice(0, state.historyIndex + 1);
      const newHistory = [...trimmedHistory, []].slice(-MAX_HISTORY);
      return {
        ...state,
        paths: [],
        currentPath: null,
        isDrawing: false,
        historyStack: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }
    case "UNDO": {
      if (state.historyIndex <= 0) return state;
      const idx = state.historyIndex - 1;
      return { ...state, historyIndex: idx, paths: state.historyStack[idx] };
    }
    case "REDO": {
      if (state.historyIndex >= state.historyStack.length - 1) return state;
      const idx = state.historyIndex + 1;
      return { ...state, historyIndex: idx, paths: state.historyStack[idx] };
    }
    default:
      return state;
  }
}

// ── Drawing helpers ────────────────────────────────────────────────────
function drawPath(ctx: CanvasRenderingContext2D, path: DrawingPath) {
  if (path.points.length < 2) return;
  ctx.save();
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.lineWidth = path.lineWidth;
  if (path.tool === "eraser") {
    ctx.globalCompositeOperation = "destination-out";
    ctx.strokeStyle = "rgba(0,0,0,1)";
  } else {
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = path.color;
  }
  ctx.beginPath();
  ctx.moveTo(path.points[0].x, path.points[0].y);
  for (let i = 1; i < path.points.length; i++) {
    const prev = path.points[i - 1];
    const curr = path.points[i];
    const mx = (prev.x + curr.x) / 2;
    const my = (prev.y + curr.y) / 2;
    ctx.quadraticCurveTo(prev.x, prev.y, mx, my);
  }
  ctx.stroke();
  ctx.restore();
}

function redrawAll(ctx: CanvasRenderingContext2D, w: number, h: number, paths: DrawingPath[], current: DrawingPath | null) {
  ctx.clearRect(0, 0, w, h);
  paths.forEach((p) => drawPath(ctx, p));
  if (current) drawPath(ctx, current);
}

// ── Main Component ─────────────────────────────────────────────────────
export default function CanvasWhiteboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const W = 960;
  const H = 640;

  const getPos = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    dispatch({ type: "START_DRAWING", payload: getPos(e) });
  }, [getPos]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing) return;
    dispatch({ type: "ADD_POINT", payload: getPos(e) });
  }, [state.isDrawing, getPos]);

  const handleMouseUp = useCallback(() => {
    if (state.isDrawing) dispatch({ type: "END_DRAWING" });
  }, [state.isDrawing]);

  const handleMouseLeave = useCallback(() => {
    if (state.isDrawing) dispatch({ type: "END_DRAWING" });
  }, [state.isDrawing]);

  useEffect(() => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    redrawAll(ctx, W, H, state.paths, state.currentPath);
  }, [state.paths, state.currentPath]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.key === "z") { e.preventDefault(); dispatch({ type: "UNDO" }); }
      else if (ctrl && e.key === "y") { e.preventDefault(); dispatch({ type: "REDO" }); }
      else if (e.key === "b" || e.key === "B") dispatch({ type: "SET_TOOL", payload: "pen" });
      else if (e.key === "e" || e.key === "E") dispatch({ type: "SET_TOOL", payload: "eraser" });
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.historyStack.length - 1;

  return (
    <>
      <style>{css}</style>
      <div className="wb">
        <div className="toolbar">
          <div className="toolGroup">
            <button className={`toolBtn ${state.tool === "pen" ? "toolBtnActive" : ""}`} onClick={() => dispatch({ type: "SET_TOOL", payload: "pen" })}>🖊 Pen</button>
            <button className={`toolBtn ${state.tool === "eraser" ? "toolBtnActive" : ""}`} onClick={() => dispatch({ type: "SET_TOOL", payload: "eraser" })}>⌫ Eraser</button>
          </div>
          <div className="toolGroup">
            {COLORS.map((c) => (
              <div
                key={c}
                className={`colorSwatch ${state.color === c ? "colorSwatchActive" : ""}`}
                style={{ background: c }}
                onClick={() => dispatch({ type: "SET_COLOR", payload: c })}
              />
            ))}
          </div>
          <div className="toolGroup">
            <span className="label">Size</span>
            <input
              type="range"
              className="slider"
              min={1}
              max={20}
              value={state.lineWidth}
              onChange={(e) => dispatch({ type: "SET_LINE_WIDTH", payload: Number(e.target.value) })}
            />
            <span className="label">{state.lineWidth}px</span>
          </div>
          <div className="toolGroup">
            <button className="historyBtn" disabled={!canUndo} onClick={() => dispatch({ type: "UNDO" })}>↩</button>
            <button className="historyBtn" disabled={!canRedo} onClick={() => dispatch({ type: "REDO" })}>↪</button>
          </div>
          <button className="toolBtn" onClick={() => dispatch({ type: "CLEAR_CANVAS" })}>🗑 Clear</button>
        </div>
        <div className="canvasWrap">
          <canvas
            ref={canvasRef}
            className="canvas"
            width={W}
            height={H}
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
