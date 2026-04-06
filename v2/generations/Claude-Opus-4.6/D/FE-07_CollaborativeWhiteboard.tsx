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
  currentStroke: Stroke | null;
  undoStack: Stroke[][];
  redoStack: Stroke[][];
  color: string;
  brushSize: number;
  tool: "pen" | "eraser";
}

type Action =
  | { type: "START_STROKE"; point: Point }
  | { type: "ADD_POINT"; point: Point }
  | { type: "END_STROKE" }
  | { type: "SET_COLOR"; color: string }
  | { type: "SET_BRUSH_SIZE"; size: number }
  | { type: "SET_TOOL"; tool: "pen" | "eraser" }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" };

const COLORS = ["#000000", "#e74c3c", "#2ecc71", "#3498db", "#f39c12", "#9b59b6", "#1abc9c"];
const BRUSH_SIZES = [2, 4, 8, 14, 22];

function reducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case "START_STROKE":
      return {
        ...state,
        currentStroke: {
          points: [action.point],
          color: state.tool === "eraser" ? "#ffffff" : state.color,
          size: state.tool === "eraser" ? state.brushSize * 3 : state.brushSize,
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
        undoStack: [...state.undoStack, state.strokes],
        redoStack: [],
        currentStroke: null,
      };
    case "SET_COLOR":
      return { ...state, color: action.color };
    case "SET_BRUSH_SIZE":
      return { ...state, brushSize: action.size };
    case "SET_TOOL":
      return { ...state, tool: action.tool };
    case "UNDO":
      if (state.undoStack.length === 0) return state;
      return {
        ...state,
        redoStack: [...state.redoStack, state.strokes],
        strokes: state.undoStack[state.undoStack.length - 1],
        undoStack: state.undoStack.slice(0, -1),
      };
    case "REDO":
      if (state.redoStack.length === 0) return state;
      return {
        ...state,
        undoStack: [...state.undoStack, state.strokes],
        strokes: state.redoStack[state.redoStack.length - 1],
        redoStack: state.redoStack.slice(0, -1),
      };
    case "CLEAR":
      return {
        ...state,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: [],
        strokes: [],
      };
    default:
      return state;
  }
}

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  color: "#000000",
  brushSize: 4,
  tool: "pen",
};

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length < 2) return;
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.size;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.globalCompositeOperation = stroke.tool === "eraser" ? "destination-out" : "source-over";
  ctx.beginPath();
  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }
  ctx.stroke();
}

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalCompositeOperation = "source-over";
    state.strokes.forEach((s) => drawStroke(ctx, s));
    if (state.currentStroke) drawStroke(ctx, state.currentStroke);
  }, [state.strokes, state.currentStroke]);

  useEffect(() => {
    redraw();
  }, [redraw]);

  const getPoint = useCallback((e: React.MouseEvent | React.TouchEvent): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    if ("touches" in e) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top,
      };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const handleDown = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      isDrawing.current = true;
      dispatch({ type: "START_STROKE", point: getPoint(e) });
    },
    [getPoint]
  );

  const handleMove = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      if (!isDrawing.current) return;
      dispatch({ type: "ADD_POINT", point: getPoint(e) });
    },
    [getPoint]
  );

  const handleUp = useCallback(() => {
    if (!isDrawing.current) return;
    isDrawing.current = false;
    dispatch({ type: "END_STROKE" });
  }, []);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Collaborative Whiteboard</h2>
      <div style={styles.toolbar}>
        <div style={styles.toolGroup}>
          <button
            style={{
              ...styles.toolBtn,
              ...(state.tool === "pen" ? styles.toolBtnActive : {}),
            }}
            onClick={() => dispatch({ type: "SET_TOOL", tool: "pen" })}
          >
            ✏️ Pen
          </button>
          <button
            style={{
              ...styles.toolBtn,
              ...(state.tool === "eraser" ? styles.toolBtnActive : {}),
            }}
            onClick={() => dispatch({ type: "SET_TOOL", tool: "eraser" })}
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
                border: state.color === c ? "3px solid #333" : "2px solid #ccc",
                transform: state.color === c ? "scale(1.2)" : "scale(1)",
              }}
              onClick={() => dispatch({ type: "SET_COLOR", color: c })}
            />
          ))}
        </div>
        <div style={styles.toolGroup}>
          {BRUSH_SIZES.map((s) => (
            <button
              key={s}
              style={{
                ...styles.sizeBtn,
                ...(state.brushSize === s ? styles.sizeBtnActive : {}),
              }}
              onClick={() => dispatch({ type: "SET_BRUSH_SIZE", size: s })}
            >
              <span
                style={{
                  display: "inline-block",
                  width: `${Math.min(s, 18)}px`,
                  height: `${Math.min(s, 18)}px`,
                  borderRadius: "50%",
                  backgroundColor: "#333",
                }}
              />
            </button>
          ))}
        </div>
        <div style={styles.toolGroup}>
          <button
            style={styles.actionBtn}
            onClick={() => dispatch({ type: "UNDO" })}
            disabled={state.undoStack.length === 0}
          >
            ↩ Undo
          </button>
          <button
            style={styles.actionBtn}
            onClick={() => dispatch({ type: "REDO" })}
            disabled={state.redoStack.length === 0}
          >
            ↪ Redo
          </button>
          <button
            style={{ ...styles.actionBtn, backgroundColor: "#e74c3c", color: "#fff" }}
            onClick={() => dispatch({ type: "CLEAR" })}
          >
            🗑 Clear
          </button>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        style={styles.canvas}
        onMouseDown={handleDown}
        onMouseMove={handleMove}
        onMouseUp={handleUp}
        onMouseLeave={handleUp}
        onTouchStart={handleDown}
        onTouchMove={handleMove}
        onTouchEnd={handleUp}
      />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "860px",
    margin: "20px auto",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  title: {
    textAlign: "center",
    color: "#333",
    marginBottom: "12px",
  },
  toolbar: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "12px",
    padding: "12px",
    backgroundColor: "#f5f5f5",
    borderRadius: "8px",
  },
  toolGroup: {
    display: "flex",
    gap: "6px",
    alignItems: "center",
  },
  toolBtn: {
    padding: "8px 14px",
    border: "1px solid #ccc",
    borderRadius: "6px",
    backgroundColor: "#fff",
    cursor: "pointer",
    fontSize: "14px",
  },
  toolBtnActive: {
    backgroundColor: "#3498db",
    color: "#fff",
    borderColor: "#2980b9",
  },
  colorBtn: {
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    cursor: "pointer",
    padding: 0,
    transition: "transform 0.15s",
  },
  sizeBtn: {
    width: "32px",
    height: "32px",
    borderRadius: "50%",
    border: "1px solid #ccc",
    backgroundColor: "#fff",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  sizeBtnActive: {
    borderColor: "#3498db",
    backgroundColor: "#e8f4fc",
  },
  actionBtn: {
    padding: "8px 14px",
    border: "1px solid #ccc",
    borderRadius: "6px",
    backgroundColor: "#fff",
    cursor: "pointer",
    fontSize: "13px",
  },
  canvas: {
    display: "block",
    border: "2px solid #ddd",
    borderRadius: "8px",
    cursor: "crosshair",
    touchAction: "none",
    backgroundColor: "#fff",
  },
};

export default CollaborativeWhiteboard;
