import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ─── Types ───
interface Point {
  x: number;
  y: number;
}

interface PathSegment {
  id: string;
  tool: "pen" | "eraser";
  color: string;
  lineWidth: number;
  points: Point[];
}

interface WhiteboardState {
  strokes: PathSegment[];
  redoStack: PathSegment[];
  currentTool: "pen" | "eraser";
  currentColor: string;
  lineWidth: number;
}

type WhiteboardAction =
  | { type: "COMMIT_STROKE"; payload: PathSegment }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" }
  | { type: "SET_TOOL"; payload: "pen" | "eraser" }
  | { type: "SET_COLOR"; payload: string }
  | { type: "SET_LINE_WIDTH"; payload: number };

// ─── Reducer ───
const initialState: WhiteboardState = {
  strokes: [],
  redoStack: [],
  currentTool: "pen",
  currentColor: "#000000",
  lineWidth: 3,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case "COMMIT_STROKE":
      return {
        ...state,
        strokes: [...state.strokes, action.payload],
        redoStack: [],
      };
    case "UNDO": {
      if (state.strokes.length === 0) return state;
      const last = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, last],
      };
    }
    case "REDO": {
      if (state.redoStack.length === 0) return state;
      const last = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, last],
        redoStack: state.redoStack.slice(0, -1),
      };
    }
    case "CLEAR":
      return {
        ...state,
        strokes: [],
        redoStack: [...state.redoStack, ...state.strokes],
      };
    case "SET_TOOL":
      return { ...state, currentTool: action.payload };
    case "SET_COLOR":
      return { ...state, currentColor: action.payload };
    case "SET_LINE_WIDTH":
      return { ...state, lineWidth: action.payload };
    default:
      return state;
  }
}

// ─── Utilities ───
function generateId(): string {
  return Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
}

// ─── Styles ───
const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  padding: 24,
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  background: "#f5f5f5",
  minHeight: "100vh",
};

const toolbarStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  padding: "12px 16px",
  background: "#fff",
  borderRadius: 8,
  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
  marginBottom: 16,
  flexWrap: "wrap",
};

const btnBase: React.CSSProperties = {
  padding: "8px 16px",
  border: "1px solid #d9d9d9",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 13,
  background: "#fff",
  transition: "all 0.2s",
};

const btnActive: React.CSSProperties = {
  ...btnBase,
  background: "#1890ff",
  color: "#fff",
  borderColor: "#1890ff",
};

const canvasStyle: React.CSSProperties = {
  border: "1px solid #d9d9d9",
  borderRadius: 8,
  background: "#fff",
  cursor: "crosshair",
  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
};

const PRESET_COLORS = ["#000000", "#ff4d4f", "#fa8c16", "#fadb14", "#52c41a", "#1890ff", "#722ed1", "#eb2f96"];

const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 600;

// ─── Sub-components ───
interface ColorPickerProps {
  currentColor: string;
  onColorChange: (color: string) => void;
}

function ColorPicker({ currentColor, onColorChange }: ColorPickerProps) {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {PRESET_COLORS.map((color) => (
        <div
          key={color}
          onClick={() => onColorChange(color)}
          style={{
            width: 24,
            height: 24,
            borderRadius: "50%",
            background: color,
            border: currentColor === color ? "3px solid #333" : "2px solid #e0e0e0",
            cursor: "pointer",
            transition: "border 0.15s",
          }}
        />
      ))}
    </div>
  );
}

interface ToolbarProps {
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}

function Toolbar({ state, dispatch }: ToolbarProps) {
  return (
    <div style={toolbarStyle}>
      <button
        style={state.currentTool === "pen" ? btnActive : btnBase}
        onClick={() => dispatch({ type: "SET_TOOL", payload: "pen" })}
      >
        ✏️ Pen
      </button>
      <button
        style={state.currentTool === "eraser" ? btnActive : btnBase}
        onClick={() => dispatch({ type: "SET_TOOL", payload: "eraser" })}
      >
        🧹 Eraser
      </button>
      <div style={{ width: 1, height: 24, background: "#e0e0e0" }} />
      <ColorPicker
        currentColor={state.currentColor}
        onColorChange={(c) => dispatch({ type: "SET_COLOR", payload: c })}
      />
      <div style={{ width: 1, height: 24, background: "#e0e0e0" }} />
      <label style={{ fontSize: 12, color: "#666" }}>
        Width:
        <input
          type="range"
          min={1}
          max={20}
          value={state.lineWidth}
          onChange={(e) => dispatch({ type: "SET_LINE_WIDTH", payload: Number(e.target.value) })}
          style={{ marginLeft: 4, verticalAlign: "middle" }}
        />
        <span style={{ marginLeft: 4 }}>{state.lineWidth}px</span>
      </label>
      <div style={{ width: 1, height: 24, background: "#e0e0e0" }} />
      <button
        style={btnBase}
        onClick={() => dispatch({ type: "UNDO" })}
        disabled={state.strokes.length === 0}
      >
        ↩ Undo
      </button>
      <button
        style={btnBase}
        onClick={() => dispatch({ type: "REDO" })}
        disabled={state.redoStack.length === 0}
      >
        ↪ Redo
      </button>
      <button
        style={{ ...btnBase, borderColor: "#ff4d4f", color: "#ff4d4f" }}
        onClick={() => dispatch({ type: "CLEAR" })}
      >
        🗑 Clear
      </button>
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

  // Initialize canvas context
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctxRef.current = ctx;
  }, []);

  // Redraw from state (for undo/redo/clear)
  useEffect(() => {
    const ctx = ctxRef.current;
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const stroke of state.strokes) {
      if (stroke.points.length < 2) continue;
      ctx.beginPath();
      ctx.strokeStyle = stroke.tool === "eraser" ? "#ffffff" : stroke.color;
      ctx.lineWidth = stroke.tool === "eraser" ? stroke.lineWidth * 4 : stroke.lineWidth;
      ctx.globalCompositeOperation = stroke.tool === "eraser" ? "destination-out" : "source-over";
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      for (let i = 1; i < stroke.points.length; i++) {
        ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
  }, [state.strokes]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const ctx = ctxRef.current;
      if (!ctx) return;
      isDrawingRef.current = true;
      const rect = canvasRef.current!.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const segment: PathSegment = {
        id: generateId(),
        tool: state.currentTool,
        color: state.currentColor,
        lineWidth: state.lineWidth,
        points: [{ x, y }],
      };
      currentSegmentRef.current = segment;

      ctx.beginPath();
      ctx.strokeStyle = state.currentTool === "eraser" ? "#ffffff" : state.currentColor;
      ctx.lineWidth = state.currentTool === "eraser" ? state.lineWidth * 4 : state.lineWidth;
      ctx.globalCompositeOperation = state.currentTool === "eraser" ? "destination-out" : "source-over";
      ctx.moveTo(x, y);
    },
    [state.currentTool, state.currentColor, state.lineWidth]
  );

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current) return;
    const ctx = ctxRef.current;
    const segment = currentSegmentRef.current;
    if (!ctx || !segment) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    segment.points.push({ x, y });
    ctx.lineTo(x, y);
    ctx.stroke();
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    const ctx = ctxRef.current;
    if (ctx) ctx.globalCompositeOperation = "source-over";
    const segment = currentSegmentRef.current;
    if (segment && segment.points.length > 1) {
      dispatch({ type: "COMMIT_STROKE", payload: segment });
    }
    currentSegmentRef.current = null;
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (isDrawingRef.current) {
      handleMouseUp();
    }
  }, [handleMouseUp]);

  return (
    <div style={containerStyle}>
      <Toolbar state={state} dispatch={dispatch} />
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        style={canvasStyle}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />
      <div style={{ marginTop: 8, fontSize: 12, color: "#999" }}>
        Strokes: {state.strokes.length} | Redo stack: {state.redoStack.length}
      </div>
    </div>
  );
}
