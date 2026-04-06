import React, { useReducer, useRef, useEffect, useCallback } from "react";

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  size: number;
  tool: "pen" | "eraser";
}

interface WhiteboardState {
  strokes: Stroke[];
  undoneStrokes: Stroke[];
  currentStroke: Stroke | null;
  color: string;
  brushSize: number;
  tool: "pen" | "eraser";
}

type Action =
  | { type: "START_STROKE"; point: Point }
  | { type: "ADD_POINT"; point: Point }
  | { type: "END_STROKE" }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" }
  | { type: "SET_COLOR"; color: string }
  | { type: "SET_BRUSH_SIZE"; size: number }
  | { type: "SET_TOOL"; tool: "pen" | "eraser" };

const COLORS = ["#1a1a2e", "#e74c3c", "#2ecc71", "#3498db", "#f39c12", "#9b59b6", "#1abc9c"];

const initialState: WhiteboardState = {
  strokes: [],
  undoneStrokes: [],
  currentStroke: null,
  color: COLORS[0],
  brushSize: 3,
  tool: "pen",
};

function reducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case "START_STROKE":
      return {
        ...state,
        currentStroke: {
          points: [action.point],
          color: state.tool === "eraser" ? "#ffffff" : state.color,
          size: state.tool === "eraser" ? state.brushSize * 4 : state.brushSize,
          tool: state.tool,
        },
      };
    case "ADD_POINT":
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.point],
        },
      };
    case "END_STROKE":
      if (!state.currentStroke) return state;
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        undoneStrokes: [],
        currentStroke: null,
      };
    case "UNDO":
      if (state.strokes.length === 0) return state;
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        undoneStrokes: [...state.undoneStrokes, state.strokes[state.strokes.length - 1]],
      };
    case "REDO":
      if (state.undoneStrokes.length === 0) return state;
      return {
        ...state,
        strokes: [...state.strokes, state.undoneStrokes[state.undoneStrokes.length - 1]],
        undoneStrokes: state.undoneStrokes.slice(0, -1),
      };
    case "CLEAR":
      return { ...state, strokes: [], undoneStrokes: [], currentStroke: null };
    case "SET_COLOR":
      return { ...state, color: action.color };
    case "SET_BRUSH_SIZE":
      return { ...state, brushSize: action.size };
    case "SET_TOOL":
      return { ...state, tool: action.tool };
    default:
      return state;
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length < 2) return;
  ctx.beginPath();
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.size;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  if (stroke.tool === "eraser") {
    ctx.globalCompositeOperation = "destination-out";
  } else {
    ctx.globalCompositeOperation = "source-over";
  }
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }
  ctx.stroke();
  ctx.globalCompositeOperation = "source-over";
}

const containerStyle: React.CSSProperties = {
  maxWidth: 820,
  margin: "30px auto",
  fontFamily: "system-ui, -apple-system, sans-serif",
};

const toolbarStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  padding: "10px 16px",
  backgroundColor: "#f4f4f8",
  borderRadius: "8px 8px 0 0",
  border: "1px solid #d0d0d0",
  borderBottom: "none",
  flexWrap: "wrap",
};

const canvasWrapStyle: React.CSSProperties = {
  border: "1px solid #d0d0d0",
  borderRadius: "0 0 8px 8px",
  overflow: "hidden",
  cursor: "crosshair",
};

const btnStyle: React.CSSProperties = {
  padding: "6px 14px",
  border: "1px solid #ccc",
  borderRadius: 4,
  backgroundColor: "#fff",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};

const btnActiveStyle: React.CSSProperties = {
  ...btnStyle,
  backgroundColor: "#1a1a2e",
  color: "#fff",
  borderColor: "#1a1a2e",
};

const colorSwatchStyle = (c: string, active: boolean): React.CSSProperties => ({
  width: 26,
  height: 26,
  borderRadius: "50%",
  backgroundColor: c,
  border: active ? "3px solid #333" : "2px solid #ccc",
  cursor: "pointer",
  boxSizing: "border-box",
});

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  const redrawCanvas = useCallback(() => {
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

  useEffect(() => {
    redrawCanvas();
  }, [redrawCanvas]);

  const getPos = (e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    if ("touches" in e) {
      const touch = e.touches[0] || e.changedTouches[0];
      return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
    }
    return { x: (e as React.MouseEvent).clientX - rect.left, y: (e as React.MouseEvent).clientY - rect.top };
  };

  const handlePointerDown = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawingRef.current = true;
    dispatch({ type: "START_STROKE", point: getPos(e) });
  };

  const handlePointerMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawingRef.current) return;
    e.preventDefault();
    dispatch({ type: "ADD_POINT", point: getPos(e) });
  };

  const handlePointerUp = () => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    dispatch({ type: "END_STROKE" });
  };

  return (
    <div style={containerStyle}>
      <div style={toolbarStyle}>
        <button
          style={state.tool === "pen" ? btnActiveStyle : btnStyle}
          onClick={() => dispatch({ type: "SET_TOOL", tool: "pen" })}
        >
          ✏️ Pen
        </button>
        <button
          style={state.tool === "eraser" ? btnActiveStyle : btnStyle}
          onClick={() => dispatch({ type: "SET_TOOL", tool: "eraser" })}
        >
          🧹 Eraser
        </button>

        <span style={{ color: "#888", fontSize: 13 }}>|</span>

        {COLORS.map((c) => (
          <div
            key={c}
            style={colorSwatchStyle(c, state.color === c && state.tool === "pen")}
            onClick={() => {
              dispatch({ type: "SET_COLOR", color: c });
              dispatch({ type: "SET_TOOL", tool: "pen" });
            }}
          />
        ))}

        <span style={{ color: "#888", fontSize: 13 }}>|</span>

        <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
          Size:
          <input
            type="range"
            min={1}
            max={20}
            value={state.brushSize}
            onChange={(e) => dispatch({ type: "SET_BRUSH_SIZE", size: Number(e.target.value) })}
            style={{ width: 80 }}
          />
          <span style={{ minWidth: 20, textAlign: "center" }}>{state.brushSize}</span>
        </label>

        <span style={{ color: "#888", fontSize: 13 }}>|</span>

        <button style={btnStyle} onClick={() => dispatch({ type: "UNDO" })} disabled={state.strokes.length === 0}>
          ↩ Undo
        </button>
        <button style={btnStyle} onClick={() => dispatch({ type: "REDO" })} disabled={state.undoneStrokes.length === 0}>
          ↪ Redo
        </button>
        <button
          style={{ ...btnStyle, borderColor: "#e74c3c", color: "#e74c3c" }}
          onClick={() => dispatch({ type: "CLEAR" })}
        >
          🗑 Clear
        </button>
      </div>

      <div style={canvasWrapStyle}>
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          style={{ display: "block", backgroundColor: "#fff" }}
          onMouseDown={handlePointerDown}
          onMouseMove={handlePointerMove}
          onMouseUp={handlePointerUp}
          onMouseLeave={handlePointerUp}
          onTouchStart={handlePointerDown}
          onTouchMove={handlePointerMove}
          onTouchEnd={handlePointerUp}
        />
      </div>
    </div>
  );
}
