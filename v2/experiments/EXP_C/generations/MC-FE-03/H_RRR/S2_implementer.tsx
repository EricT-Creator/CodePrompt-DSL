import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ── Data Model ──
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

// ── Actions ──
type WhiteboardAction =
  | { type: "COMMIT_STROKE"; payload: PathSegment }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" }
  | { type: "SET_TOOL"; payload: "pen" | "eraser" }
  | { type: "SET_COLOR"; payload: string }
  | { type: "SET_LINE_WIDTH"; payload: number };

// ── Reducer ──
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

// ── Styles ──
const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  height: "100vh",
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  backgroundColor: "#f5f5f5",
};

const toolbarStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  padding: "12px 20px",
  backgroundColor: "#ffffff",
  borderBottom: "1px solid #e0e0e0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  flexWrap: "wrap",
};

const toolGroupStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
};

const toolButtonStyle: React.CSSProperties = {
  padding: "8px 14px",
  border: "1px solid #d0d0d0",
  borderRadius: "6px",
  backgroundColor: "#fff",
  cursor: "pointer",
  fontSize: "13px",
  fontWeight: 500,
  transition: "all 0.15s",
};

const toolButtonActiveStyle: React.CSSProperties = {
  ...toolButtonStyle,
  backgroundColor: "#1890ff",
  color: "#fff",
  borderColor: "#1890ff",
};

const actionButtonStyle: React.CSSProperties = {
  ...toolButtonStyle,
  backgroundColor: "#fafafa",
};

const disabledButtonStyle: React.CSSProperties = {
  ...actionButtonStyle,
  opacity: 0.4,
  cursor: "not-allowed",
};

const canvasContainerStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  padding: "16px",
  overflow: "hidden",
};

const canvasStyle: React.CSSProperties = {
  backgroundColor: "#ffffff",
  borderRadius: "8px",
  boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
  cursor: "crosshair",
};

const colorSwatchStyle = (color: string, isActive: boolean): React.CSSProperties => ({
  width: "28px",
  height: "28px",
  borderRadius: "50%",
  backgroundColor: color,
  border: isActive ? "3px solid #1890ff" : "2px solid #ccc",
  cursor: "pointer",
  transition: "border 0.15s",
});

const labelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#888",
  fontWeight: 500,
  textTransform: "uppercase" as const,
  letterSpacing: "0.5px",
};

const separatorStyle: React.CSSProperties = {
  width: "1px",
  height: "28px",
  backgroundColor: "#e0e0e0",
  margin: "0 4px",
};

// ── Color Presets ──
const COLOR_PRESETS = ["#000000", "#ff4d4f", "#1890ff", "#52c41a", "#faad14", "#722ed1", "#eb2f96", "#ffffff"];

// ── Helper ──
function generateStrokeId(): string {
  return `s-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ── Replay strokes ──
function replayStrokes(ctx: CanvasRenderingContext2D, strokes: PathSegment[], width: number, height: number): void {
  ctx.clearRect(0, 0, width, height);
  for (const seg of strokes) {
    if (seg.points.length < 2) continue;
    ctx.save();
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    if (seg.tool === "eraser") {
      ctx.globalCompositeOperation = "destination-out";
      ctx.lineWidth = seg.lineWidth * 4;
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = seg.color;
      ctx.lineWidth = seg.lineWidth;
    }
    ctx.beginPath();
    ctx.moveTo(seg.points[0].x, seg.points[0].y);
    for (let i = 1; i < seg.points.length; i++) {
      ctx.lineTo(seg.points[i].x, seg.points[i].y);
    }
    ctx.stroke();
    ctx.restore();
  }
}

// ── Toolbar ──
function Toolbar({
  state,
  dispatch,
}: {
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}) {
  return (
    <div style={toolbarStyle}>
      <div style={toolGroupStyle}>
        <span style={labelStyle}>Tool</span>
        <button
          style={state.currentTool === "pen" ? toolButtonActiveStyle : toolButtonStyle}
          onClick={() => dispatch({ type: "SET_TOOL", payload: "pen" })}
        >
          ✏️ Pen
        </button>
        <button
          style={state.currentTool === "eraser" ? toolButtonActiveStyle : toolButtonStyle}
          onClick={() => dispatch({ type: "SET_TOOL", payload: "eraser" })}
        >
          🧹 Eraser
        </button>
      </div>

      <div style={separatorStyle} />

      <div style={toolGroupStyle}>
        <span style={labelStyle}>Color</span>
        <ColorPicker currentColor={state.currentColor} dispatch={dispatch} />
      </div>

      <div style={separatorStyle} />

      <div style={toolGroupStyle}>
        <span style={labelStyle}>Size</span>
        <input
          type="range"
          min={1}
          max={20}
          value={state.lineWidth}
          onChange={(e) =>
            dispatch({ type: "SET_LINE_WIDTH", payload: Number(e.target.value) })
          }
          style={{ width: "80px" }}
        />
        <span style={{ fontSize: "12px", color: "#666" }}>{state.lineWidth}px</span>
      </div>

      <div style={separatorStyle} />

      <div style={toolGroupStyle}>
        <span style={labelStyle}>Actions</span>
        <button
          style={state.strokes.length > 0 ? actionButtonStyle : disabledButtonStyle}
          onClick={() => dispatch({ type: "UNDO" })}
          disabled={state.strokes.length === 0}
        >
          ↩ Undo
        </button>
        <button
          style={state.redoStack.length > 0 ? actionButtonStyle : disabledButtonStyle}
          onClick={() => dispatch({ type: "REDO" })}
          disabled={state.redoStack.length === 0}
        >
          ↪ Redo
        </button>
        <button
          style={state.strokes.length > 0 ? actionButtonStyle : disabledButtonStyle}
          onClick={() => dispatch({ type: "CLEAR" })}
          disabled={state.strokes.length === 0}
        >
          🗑 Clear
        </button>
      </div>
    </div>
  );
}

// ── ColorPicker ──
function ColorPicker({
  currentColor,
  dispatch,
}: {
  currentColor: string;
  dispatch: React.Dispatch<WhiteboardAction>;
}) {
  return (
    <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
      {COLOR_PRESETS.map((color) => (
        <div
          key={color}
          style={colorSwatchStyle(color, currentColor === color)}
          onClick={() => dispatch({ type: "SET_COLOR", payload: color })}
        />
      ))}
    </div>
  );
}

// ── Canvas Component ──
function CanvasArea({
  state,
  dispatch,
}: {
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);
  const currentSegmentRef = useRef<PathSegment | null>(null);

  const CANVAS_WIDTH = 1000;
  const CANVAS_HEIGHT = 650;

  // Replay on strokes change (undo/redo/clear)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    replayStrokes(ctx, state.strokes, CANVAS_WIDTH, CANVAS_HEIGHT);
  }, [state.strokes]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      isDrawingRef.current = true;

      const segment: PathSegment = {
        id: generateStrokeId(),
        tool: state.currentTool,
        color: state.currentColor,
        lineWidth: state.lineWidth,
        points: [{ x, y }],
      };
      currentSegmentRef.current = segment;

      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      if (state.currentTool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.lineWidth = state.lineWidth * 4;
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = state.currentColor;
        ctx.lineWidth = state.lineWidth;
      }
      ctx.beginPath();
      ctx.moveTo(x, y);
    },
    [state.currentTool, state.currentColor, state.lineWidth]
  );

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current || !currentSegmentRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    currentSegmentRef.current.points.push({ x, y });
    ctx.lineTo(x, y);
    ctx.stroke();
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;

    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.restore();
    }

    if (currentSegmentRef.current && currentSegmentRef.current.points.length > 1) {
      dispatch({ type: "COMMIT_STROKE", payload: currentSegmentRef.current });
    }
    currentSegmentRef.current = null;
  }, [dispatch]);

  const handleMouseLeave = useCallback(() => {
    if (isDrawingRef.current) {
      handleMouseUp();
    }
  }, [handleMouseUp]);

  return (
    <div style={canvasContainerStyle}>
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
    </div>
  );
}

// ── Main Component ──
export default function DrawingWhiteboard() {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);

  return (
    <div style={containerStyle}>
      <Toolbar state={state} dispatch={dispatch} />
      <CanvasArea state={state} dispatch={dispatch} />
    </div>
  );
}
