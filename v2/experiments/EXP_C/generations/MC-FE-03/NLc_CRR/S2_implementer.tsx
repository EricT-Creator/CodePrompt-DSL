import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ─── Types ───

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  width: number;
  tool: "pen" | "eraser";
}

interface HistoryState {
  past: Stroke[][];
  future: Stroke[][];
  maxHistory: number;
}

interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  tool: "pen" | "eraser";
  color: string;
  strokeWidth: number;
  history: HistoryState;
  isDrawing: boolean;
}

type WhiteboardAction =
  | { type: "START_STROKE"; payload: Point }
  | { type: "ADD_POINT"; payload: Point }
  | { type: "END_STROKE" }
  | { type: "SET_TOOL"; payload: "pen" | "eraser" }
  | { type: "SET_COLOR"; payload: string }
  | { type: "SET_WIDTH"; payload: number }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" };

// ─── Constants ───

const MAX_HISTORY = 50;
const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 600;
const MIN_DISTANCE = 3;

const COLORS = [
  "#000000", "#ff4d4f", "#fa8c16", "#fadb14",
  "#52c41a", "#1890ff", "#722ed1", "#eb2f96",
  "#8c8c8c", "#ffffff",
];

const WIDTHS = [2, 4, 6, 10, 16];

// ─── CSS (inline styles as objects) ───

const cls: Record<string, React.CSSProperties> = {
  wrapper: {
    fontFamily: "system-ui, sans-serif",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: 16,
    background: "#f5f5f5",
    minHeight: "100vh",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "8px 16px",
    background: "#fff",
    borderRadius: 8,
    boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
    marginBottom: 12,
    flexWrap: "wrap" as const,
  },
  toolBtn: {
    padding: "6px 14px",
    border: "1px solid #d9d9d9",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 13,
    background: "#fff",
  },
  toolBtnActive: {
    background: "#1890ff",
    color: "#fff",
    borderColor: "#1890ff",
  },
  colorSwatch: {
    width: 24,
    height: 24,
    borderRadius: "50%",
    cursor: "pointer",
    border: "2px solid transparent",
    display: "inline-block",
  },
  colorSwatchActive: {
    border: "2px solid #1890ff",
    boxShadow: "0 0 0 2px rgba(24,144,255,0.3)",
  },
  widthBtn: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    border: "1px solid #d9d9d9",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#fff",
    fontSize: 11,
  },
  canvas: {
    border: "1px solid #d9d9d9",
    borderRadius: 6,
    cursor: "crosshair",
    background: "#ffffff",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
  },
  separator: {
    width: 1,
    height: 28,
    background: "#e8e8e8",
  },
  label: {
    fontSize: 11,
    color: "#999",
    marginRight: 4,
  },
};

// ─── Reducer ───

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  tool: "pen",
  color: "#000000",
  strokeWidth: 4,
  history: { past: [], future: [], maxHistory: MAX_HISTORY },
  isDrawing: false,
};

function reducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case "START_STROKE": {
      const stroke: Stroke = {
        points: [action.payload],
        color: state.color,
        width: state.strokeWidth,
        tool: state.tool,
      };
      return { ...state, currentStroke: stroke, isDrawing: true };
    }

    case "ADD_POINT": {
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.payload],
        },
      };
    }

    case "END_STROKE": {
      if (!state.currentStroke || state.currentStroke.points.length < 2) {
        return { ...state, currentStroke: null, isDrawing: false };
      }
      const newStrokes = [...state.strokes, state.currentStroke];
      const newPast = [...state.history.past, state.strokes];
      return {
        ...state,
        strokes: newStrokes,
        currentStroke: null,
        isDrawing: false,
        history: {
          ...state.history,
          past:
            newPast.length > MAX_HISTORY
              ? newPast.slice(newPast.length - MAX_HISTORY)
              : newPast,
          future: [],
        },
      };
    }

    case "SET_TOOL":
      return { ...state, tool: action.payload };
    case "SET_COLOR":
      return { ...state, color: action.payload };
    case "SET_WIDTH":
      return { ...state, strokeWidth: action.payload };

    case "UNDO": {
      if (state.history.past.length === 0) return state;
      const previous = state.history.past[state.history.past.length - 1];
      return {
        ...state,
        strokes: previous,
        history: {
          ...state.history,
          past: state.history.past.slice(0, -1),
          future: [state.strokes, ...state.history.future],
        },
      };
    }

    case "REDO": {
      if (state.history.future.length === 0) return state;
      const next = state.history.future[0];
      return {
        ...state,
        strokes: next,
        history: {
          ...state.history,
          past: [...state.history.past, state.strokes],
          future: state.history.future.slice(1),
        },
      };
    }

    case "CLEAR": {
      const newPast = [...state.history.past, state.strokes];
      return {
        ...state,
        strokes: [],
        currentStroke: null,
        history: {
          ...state.history,
          past:
            newPast.length > MAX_HISTORY
              ? newPast.slice(newPast.length - MAX_HISTORY)
              : newPast,
          future: [],
        },
      };
    }

    default:
      return state;
  }
}

// ─── Drawing helpers ───

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length < 2) return;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

  for (let i = 1; i < stroke.points.length - 1; i++) {
    const midX = (stroke.points[i].x + stroke.points[i + 1].x) / 2;
    const midY = (stroke.points[i].y + stroke.points[i + 1].y) / 2;
    ctx.quadraticCurveTo(stroke.points[i].x, stroke.points[i].y, midX, midY);
  }

  const last = stroke.points[stroke.points.length - 1];
  ctx.lineTo(last.x, last.y);

  if (stroke.tool === "eraser") {
    ctx.globalCompositeOperation = "destination-out";
  }
  ctx.strokeStyle = stroke.tool === "eraser" ? "rgba(0,0,0,1)" : stroke.color;
  ctx.lineWidth = stroke.width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();
  ctx.restore();
}

function getCanvasCoordinates(
  canvas: HTMLCanvasElement,
  clientX: number,
  clientY: number
): Point {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  };
}

function distance(a: Point, b: Point): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

// ─── Main component ───

const Whiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const lastPointRef = useRef<Point | null>(null);

  // Redraw all strokes whenever they change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const stroke of state.strokes) {
      drawStroke(ctx, stroke);
    }
    if (state.currentStroke) {
      drawStroke(ctx, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        dispatch({ type: "UNDO" });
      } else if (
        (e.ctrlKey || e.metaKey) &&
        (e.key === "y" || (e.key === "z" && e.shiftKey))
      ) {
        e.preventDefault();
        dispatch({ type: "REDO" });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const pt = getCanvasCoordinates(canvas, e.clientX, e.clientY);
      lastPointRef.current = pt;
      dispatch({ type: "START_STROKE", payload: pt });
    },
    []
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!state.isDrawing) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const pt = getCanvasCoordinates(canvas, e.clientX, e.clientY);
      if (lastPointRef.current && distance(lastPointRef.current, pt) < MIN_DISTANCE) return;
      lastPointRef.current = pt;
      dispatch({ type: "ADD_POINT", payload: pt });
    },
    [state.isDrawing]
  );

  const handleMouseUp = useCallback(() => {
    dispatch({ type: "END_STROKE" });
    lastPointRef.current = null;
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: "END_STROKE" });
      lastPointRef.current = null;
    }
  }, [state.isDrawing]);

  return (
    <div style={cls.wrapper}>
      {/* Toolbar */}
      <div style={cls.toolbar}>
        <span style={cls.label}>Tool:</span>
        <button
          style={{
            ...cls.toolBtn,
            ...(state.tool === "pen" ? cls.toolBtnActive : {}),
          }}
          onClick={() => dispatch({ type: "SET_TOOL", payload: "pen" })}
        >
          ✏️ Pen
        </button>
        <button
          style={{
            ...cls.toolBtn,
            ...(state.tool === "eraser" ? cls.toolBtnActive : {}),
          }}
          onClick={() => dispatch({ type: "SET_TOOL", payload: "eraser" })}
        >
          🧹 Eraser
        </button>

        <div style={cls.separator} />

        <span style={cls.label}>Color:</span>
        {COLORS.map((c) => (
          <span
            key={c}
            style={{
              ...cls.colorSwatch,
              background: c,
              ...(state.color === c ? cls.colorSwatchActive : {}),
              ...(c === "#ffffff" ? { border: "2px solid #d9d9d9" } : {}),
            }}
            onClick={() => dispatch({ type: "SET_COLOR", payload: c })}
          />
        ))}

        <div style={cls.separator} />

        <span style={cls.label}>Size:</span>
        {WIDTHS.map((w) => (
          <div
            key={w}
            style={{
              ...cls.widthBtn,
              ...(state.strokeWidth === w
                ? { borderColor: "#1890ff", background: "#e6f7ff" }
                : {}),
            }}
            onClick={() => dispatch({ type: "SET_WIDTH", payload: w })}
          >
            {w}
          </div>
        ))}

        <div style={cls.separator} />

        <button
          style={cls.toolBtn}
          onClick={() => dispatch({ type: "UNDO" })}
          disabled={state.history.past.length === 0}
        >
          ↩ Undo
        </button>
        <button
          style={cls.toolBtn}
          onClick={() => dispatch({ type: "REDO" })}
          disabled={state.history.future.length === 0}
        >
          ↪ Redo
        </button>
        <button
          style={{ ...cls.toolBtn, color: "#ff4d4f", borderColor: "#ff4d4f" }}
          onClick={() => dispatch({ type: "CLEAR" })}
        >
          🗑 Clear
        </button>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        style={cls.canvas}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />
    </div>
  );
};

export default Whiteboard;
