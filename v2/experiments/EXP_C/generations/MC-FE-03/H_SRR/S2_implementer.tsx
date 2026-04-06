import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ── Types ──────────────────────────────────────────────────────────
type ToolType = "pen" | "eraser";

interface Point {
  x: number;
  y: number;
  timestamp: number;
}

interface Path {
  id: string;
  tool: ToolType;
  points: Point[];
  color: string;
  size: number;
}

interface HistoryEntry {
  paths: Path[];
}

interface WhiteboardState {
  isDrawing: boolean;
  currentTool: ToolType;
  currentColor: string;
  brushSize: number;
  paths: Path[];
  currentPath: Path | null;
  history: HistoryEntry[];
  historyIndex: number;
  mousePosition: Point | null;
  canvasWidth: number;
  canvasHeight: number;
}

type WhiteboardAction =
  | { type: "SET_TOOL"; payload: ToolType }
  | { type: "SET_COLOR"; payload: string }
  | { type: "SET_BRUSH_SIZE"; payload: number }
  | { type: "DRAW_START"; payload: Point }
  | { type: "DRAW_UPDATE"; payload: Point }
  | { type: "DRAW_END"; payload: Point }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR_CANVAS" }
  | { type: "SET_MOUSE"; payload: Point | null }
  | { type: "SET_SIZE"; payload: { w: number; h: number } };

// ── Helpers ────────────────────────────────────────────────────────
let _id = 0;
const uid = (): string => `p_${++_id}`;

const COLORS = ["#000000", "#f44336", "#e91e63", "#2196f3", "#4caf50", "#ff9800", "#9c27b0", "#795548", "#607d8b", "#ffffff"];

const initialState: WhiteboardState = {
  isDrawing: false,
  currentTool: "pen",
  currentColor: "#000000",
  brushSize: 3,
  paths: [],
  currentPath: null,
  history: [{ paths: [] }],
  historyIndex: 0,
  mousePosition: null,
  canvasWidth: 900,
  canvasHeight: 600,
};

// ── Reducer ────────────────────────────────────────────────────────
function reducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case "SET_TOOL":
      return { ...state, currentTool: action.payload };

    case "SET_COLOR":
      return { ...state, currentColor: action.payload };

    case "SET_BRUSH_SIZE":
      return { ...state, brushSize: action.payload };

    case "DRAW_START": {
      const newPath: Path = {
        id: uid(),
        tool: state.currentTool,
        points: [action.payload],
        color: state.currentTool === "eraser" ? "eraser" : state.currentColor,
        size: state.brushSize,
      };
      return { ...state, isDrawing: true, currentPath: newPath };
    }

    case "DRAW_UPDATE": {
      if (!state.isDrawing || !state.currentPath) return state;
      return {
        ...state,
        currentPath: { ...state.currentPath, points: [...state.currentPath.points, action.payload] },
      };
    }

    case "DRAW_END": {
      if (!state.isDrawing || !state.currentPath) return state;
      const finished: Path = { ...state.currentPath, points: [...state.currentPath.points, action.payload] };
      const newPaths = [...state.paths, finished];
      const trimmedHistory = state.history.slice(0, state.historyIndex + 1);
      const newHistory = [...trimmedHistory, { paths: newPaths }];
      if (newHistory.length > 50) newHistory.shift();
      return {
        ...state,
        isDrawing: false,
        currentPath: null,
        paths: newPaths,
        history: newHistory,
        historyIndex: newHistory.length - 1,
      };
    }

    case "UNDO": {
      if (state.historyIndex <= 0) return state;
      const idx = state.historyIndex - 1;
      return { ...state, paths: state.history[idx].paths, historyIndex: idx };
    }

    case "REDO": {
      if (state.historyIndex >= state.history.length - 1) return state;
      const idx = state.historyIndex + 1;
      return { ...state, paths: state.history[idx].paths, historyIndex: idx };
    }

    case "CLEAR_CANVAS": {
      const trimmedHistory = state.history.slice(0, state.historyIndex + 1);
      const newHistory = [...trimmedHistory, { paths: [] }];
      return { ...state, paths: [], history: newHistory, historyIndex: newHistory.length - 1 };
    }

    case "SET_MOUSE":
      return { ...state, mousePosition: action.payload };

    case "SET_SIZE":
      return { ...state, canvasWidth: action.payload.w, canvasHeight: action.payload.h };

    default:
      return state;
  }
}

// ── Drawing helpers ────────────────────────────────────────────────
function drawPath(ctx: CanvasRenderingContext2D, path: Path): void {
  if (path.points.length < 2) return;
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = path.size;

  if (path.tool === "eraser" || path.color === "eraser") {
    ctx.globalCompositeOperation = "destination-out";
    ctx.strokeStyle = "rgba(0,0,0,1)";
  } else {
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = path.color;
  }

  ctx.beginPath();
  ctx.moveTo(path.points[0].x, path.points[0].y);

  for (let i = 1; i < path.points.length - 1; i++) {
    const midX = (path.points[i].x + path.points[i + 1].x) / 2;
    const midY = (path.points[i].y + path.points[i + 1].y) / 2;
    ctx.quadraticCurveTo(path.points[i].x, path.points[i].y, midX, midY);
  }

  const last = path.points[path.points.length - 1];
  ctx.lineTo(last.x, last.y);
  ctx.stroke();
  ctx.restore();
}

function renderAll(ctx: CanvasRenderingContext2D, w: number, h: number, paths: Path[], current: Path | null): void {
  ctx.clearRect(0, 0, w, h);
  for (const p of paths) drawPath(ctx, p);
  if (current) drawPath(ctx, current);
}

// ── Component ──────────────────────────────────────────────────────
const CanvasWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef(0);

  const getPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top, timestamp: Date.now() };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      dispatch({ type: "DRAW_START", payload: getPoint(e) });
    },
    [getPoint]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const pt = getPoint(e);
      dispatch({ type: "SET_MOUSE", payload: pt });
      if (state.isDrawing) dispatch({ type: "DRAW_UPDATE", payload: pt });
    },
    [getPoint, state.isDrawing]
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (state.isDrawing) dispatch({ type: "DRAW_END", payload: getPoint(e) });
    },
    [getPoint, state.isDrawing]
  );

  const handleMouseLeave = useCallback(() => {
    dispatch({ type: "SET_MOUSE", payload: null });
    if (state.isDrawing && state.mousePosition) {
      dispatch({ type: "DRAW_END", payload: state.mousePosition });
    }
  }, [state.isDrawing, state.mousePosition]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        dispatch({ type: "UNDO" });
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "y") {
        e.preventDefault();
        dispatch({ type: "REDO" });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Render
  useEffect(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      renderAll(ctx, state.canvasWidth, state.canvasHeight, state.paths, state.currentPath);

      // Cursor preview
      if (state.mousePosition && !state.isDrawing) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(state.mousePosition.x, state.mousePosition.y, state.brushSize / 2, 0, Math.PI * 2);
        ctx.strokeStyle = state.currentTool === "eraser" ? "#999" : state.currentColor;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.restore();
      }
    });
  }, [state.paths, state.currentPath, state.mousePosition, state.brushSize, state.currentColor, state.currentTool, state.canvasWidth, state.canvasHeight, state.isDrawing]);

  const btnStyle = (active: boolean): React.CSSProperties => ({
    padding: "6px 14px",
    border: active ? "2px solid #1a73e8" : "1px solid #ccc",
    borderRadius: 4,
    background: active ? "#e8f0fe" : "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: active ? 600 : 400,
  });

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 920, margin: "0 auto" }}>
      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8, padding: 12, background: "#f5f5f5", borderRadius: "8px 8px 0 0", flexWrap: "wrap", alignItems: "center" }}>
        <button style={btnStyle(state.currentTool === "pen")} onClick={() => dispatch({ type: "SET_TOOL", payload: "pen" })}>
          ✏️ Pen
        </button>
        <button style={btnStyle(state.currentTool === "eraser")} onClick={() => dispatch({ type: "SET_TOOL", payload: "eraser" })}>
          🧹 Eraser
        </button>

        <span style={{ width: 1, height: 24, background: "#ccc" }} />

        {COLORS.map((c) => (
          <div
            key={c}
            onClick={() => dispatch({ type: "SET_COLOR", payload: c })}
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              background: c,
              border: state.currentColor === c ? "3px solid #1a73e8" : "2px solid #ddd",
              cursor: "pointer",
            }}
          />
        ))}

        <span style={{ width: 1, height: 24, background: "#ccc" }} />

        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}>
          Size:
          <input
            type="range"
            min={1}
            max={30}
            value={state.brushSize}
            onChange={(e) => dispatch({ type: "SET_BRUSH_SIZE", payload: Number(e.target.value) })}
            style={{ width: 80 }}
          />
          <span style={{ minWidth: 20, textAlign: "center" }}>{state.brushSize}</span>
        </label>

        <span style={{ width: 1, height: 24, background: "#ccc" }} />

        <button
          style={{ ...btnStyle(false), opacity: state.historyIndex <= 0 ? 0.4 : 1 }}
          disabled={state.historyIndex <= 0}
          onClick={() => dispatch({ type: "UNDO" })}
        >
          ↩ Undo
        </button>
        <button
          style={{ ...btnStyle(false), opacity: state.historyIndex >= state.history.length - 1 ? 0.4 : 1 }}
          disabled={state.historyIndex >= state.history.length - 1}
          onClick={() => dispatch({ type: "REDO" })}
        >
          ↪ Redo
        </button>
        <button style={{ ...btnStyle(false), color: "#d32f2f" }} onClick={() => dispatch({ type: "CLEAR_CANVAS" })}>
          🗑 Clear
        </button>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={state.canvasWidth}
        height={state.canvasHeight}
        style={{
          display: "block",
          border: "1px solid #ddd",
          cursor: state.currentTool === "eraser" ? "crosshair" : "default",
          background: "#fff",
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />

      {/* Status bar */}
      <div style={{ padding: "6px 12px", background: "#f5f5f5", borderRadius: "0 0 8px 8px", fontSize: 12, color: "#666", display: "flex", justifyContent: "space-between" }}>
        <span>
          Tool: {state.currentTool} | Color: {state.currentColor} | Size: {state.brushSize}
        </span>
        <span>
          {state.mousePosition ? `(${Math.round(state.mousePosition.x)}, ${Math.round(state.mousePosition.y)})` : "–"} | Paths: {state.paths.length} | History: {state.historyIndex + 1}/{state.history.length}
        </span>
      </div>
    </div>
  );
};

export default CanvasWhiteboard;
