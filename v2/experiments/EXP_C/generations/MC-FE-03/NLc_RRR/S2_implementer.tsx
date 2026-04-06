import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ---- Types ----

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  id: string;
  tool: "pen" | "eraser";
  color: string;
  lineWidth: number;
  points: Point[];
}

interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  undoStack: Stroke[][];
  redoStack: Stroke[][];
  tool: "pen" | "eraser";
  color: string;
  isDrawing: boolean;
}

type WhiteboardAction =
  | { type: "START_STROKE"; point: Point }
  | { type: "ADD_POINT"; point: Point }
  | { type: "END_STROKE" }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" }
  | { type: "SET_TOOL"; tool: "pen" | "eraser" }
  | { type: "SET_COLOR"; color: string };

// ---- Constants ----

const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 600;
const PEN_WIDTH = 3;
const ERASER_WIDTH = 20;
const UNDO_LIMIT = 50;

// ---- Styles ----

const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "20px",
    backgroundColor: "#f0f2f5",
    minHeight: "100vh",
  },
  title: {
    fontSize: "22px",
    fontWeight: "bold",
    color: "#333",
    marginBottom: "16px",
  },
  toolbar: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
    marginBottom: "12px",
    padding: "10px 16px",
    backgroundColor: "#fff",
    borderRadius: "8px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  },
  toolButton: {
    padding: "8px 14px",
    border: "2px solid #ddd",
    borderRadius: "6px",
    backgroundColor: "#fff",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: "500",
    transition: "all 0.2s",
  },
  activeToolButton: {
    padding: "8px 14px",
    border: "2px solid #4a90d9",
    borderRadius: "6px",
    backgroundColor: "#e3f2fd",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: "500",
    color: "#1565c0",
  },
  actionButton: {
    padding: "8px 14px",
    border: "1px solid #ddd",
    borderRadius: "6px",
    backgroundColor: "#fff",
    cursor: "pointer",
    fontSize: "13px",
  },
  disabledButton: {
    padding: "8px 14px",
    border: "1px solid #eee",
    borderRadius: "6px",
    backgroundColor: "#f5f5f5",
    cursor: "not-allowed",
    fontSize: "13px",
    color: "#bbb",
  },
  colorPicker: {
    width: "36px",
    height: "36px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    padding: 0,
  },
  separator: {
    width: "1px",
    height: "30px",
    backgroundColor: "#ddd",
    margin: "0 4px",
  },
  canvas: {
    border: "1px solid #ddd",
    borderRadius: "8px",
    cursor: "crosshair",
    backgroundColor: "#fff",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
  },
  statusBar: {
    display: "flex",
    gap: "16px",
    marginTop: "8px",
    fontSize: "12px",
    color: "#888",
  },
};

// ---- Reducer ----

let strokeIdCounter = 0;

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  tool: "pen",
  color: "#000000",
  isDrawing: false,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case "START_STROKE": {
      const newUndoStack = [...state.undoStack, [...state.strokes]];
      if (newUndoStack.length > UNDO_LIMIT) {
        newUndoStack.shift();
      }
      const newStroke: Stroke = {
        id: `stroke-${++strokeIdCounter}`,
        tool: state.tool,
        color: state.tool === "eraser" ? "#000000" : state.color,
        lineWidth: state.tool === "eraser" ? ERASER_WIDTH : PEN_WIDTH,
        points: [action.point],
      };
      return {
        ...state,
        currentStroke: newStroke,
        undoStack: newUndoStack,
        redoStack: [],
        isDrawing: true,
      };
    }

    case "ADD_POINT": {
      if (!state.currentStroke) return state;
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.point],
        },
      };
    }

    case "END_STROKE": {
      if (!state.currentStroke) return { ...state, isDrawing: false };
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        isDrawing: false,
      };
    }

    case "UNDO": {
      if (state.undoStack.length === 0) return state;
      const prevStrokes = state.undoStack[state.undoStack.length - 1];
      return {
        ...state,
        redoStack: [...state.redoStack, [...state.strokes]],
        strokes: prevStrokes,
        undoStack: state.undoStack.slice(0, -1),
      };
    }

    case "REDO": {
      if (state.redoStack.length === 0) return state;
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        undoStack: [...state.undoStack, [...state.strokes]],
        strokes: nextStrokes,
        redoStack: state.redoStack.slice(0, -1),
      };
    }

    case "CLEAR": {
      const newUndoStack = [...state.undoStack, [...state.strokes]];
      if (newUndoStack.length > UNDO_LIMIT) {
        newUndoStack.shift();
      }
      return {
        ...state,
        strokes: [],
        undoStack: newUndoStack,
        redoStack: [],
      };
    }

    case "SET_TOOL":
      return { ...state, tool: action.tool };

    case "SET_COLOR":
      return { ...state, color: action.color };

    default:
      return state;
  }
}

// ---- Drawing Utilities ----

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length < 2) return;

  ctx.save();
  ctx.beginPath();
  ctx.lineWidth = stroke.lineWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  if (stroke.tool === "eraser") {
    ctx.globalCompositeOperation = "destination-out";
  } else {
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = stroke.color;
  }

  ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
  for (let i = 1; i < stroke.points.length; i++) {
    ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
  }
  ctx.stroke();
  ctx.restore();
}

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[]): void {
  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  for (const stroke of strokes) {
    drawStroke(ctx, stroke);
  }
}

// ---- Toolbar Component ----

const Toolbar: React.FC<{
  state: WhiteboardState;
  dispatch: React.Dispatch<WhiteboardAction>;
}> = ({ state, dispatch }) => (
  <div style={styles.toolbar}>
    <button
      style={state.tool === "pen" ? styles.activeToolButton : styles.toolButton}
      onClick={() => dispatch({ type: "SET_TOOL", tool: "pen" })}
    >
      ✏️ Pen
    </button>
    <button
      style={state.tool === "eraser" ? styles.activeToolButton : styles.toolButton}
      onClick={() => dispatch({ type: "SET_TOOL", tool: "eraser" })}
    >
      🧹 Eraser
    </button>

    <div style={styles.separator} />

    <input
      type="color"
      value={state.color}
      onChange={(e) => dispatch({ type: "SET_COLOR", color: e.target.value })}
      style={styles.colorPicker}
      title="Pick color"
    />

    <div style={styles.separator} />

    <button
      style={state.undoStack.length > 0 ? styles.actionButton : styles.disabledButton}
      onClick={() => dispatch({ type: "UNDO" })}
      disabled={state.undoStack.length === 0}
    >
      ↩ Undo
    </button>
    <button
      style={state.redoStack.length > 0 ? styles.actionButton : styles.disabledButton}
      onClick={() => dispatch({ type: "REDO" })}
      disabled={state.redoStack.length === 0}
    >
      ↪ Redo
    </button>

    <div style={styles.separator} />

    <button
      style={state.strokes.length > 0 ? styles.actionButton : styles.disabledButton}
      onClick={() => dispatch({ type: "CLEAR" })}
      disabled={state.strokes.length === 0}
    >
      🗑 Clear
    </button>
  </div>
);

// ---- Main Component ----

const Whiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const lastRedrawRef = useRef<string>("");

  const getCanvasPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const point = getCanvasPoint(e);
      dispatch({ type: "START_STROKE", point });
    },
    [getCanvasPoint]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!state.isDrawing) return;
      const point = getCanvasPoint(e);
      dispatch({ type: "ADD_POINT", point });
    },
    [state.isDrawing, getCanvasPoint]
  );

  const handleMouseUp = useCallback(() => {
    if (!state.isDrawing) return;
    dispatch({ type: "END_STROKE" });
  }, [state.isDrawing]);

  const handleMouseLeave = useCallback(() => {
    if (state.isDrawing) {
      dispatch({ type: "END_STROKE" });
    }
  }, [state.isDrawing]);

  // Full redraw on strokes change (undo/redo/clear)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const key = state.strokes.map((s) => s.id).join(",");
    if (key !== lastRedrawRef.current) {
      lastRedrawRef.current = key;
      redrawAll(ctx, state.strokes);
    }
  }, [state.strokes]);

  // Incremental draw for current stroke
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (state.currentStroke && state.currentStroke.points.length >= 2) {
      const pts = state.currentStroke.points;
      ctx.save();
      ctx.beginPath();
      ctx.lineWidth = state.currentStroke.lineWidth;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      if (state.currentStroke.tool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = state.currentStroke.color;
      }

      const from = pts[pts.length - 2];
      const to = pts[pts.length - 1];
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
      ctx.restore();
    }
  }, [state.currentStroke]);

  return (
    <div style={styles.container}>
      <div style={styles.title}>Canvas Drawing Whiteboard</div>
      <Toolbar state={state} dispatch={dispatch} />
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        style={styles.canvas}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />
      <div style={styles.statusBar}>
        <span>Tool: {state.tool}</span>
        <span>Color: {state.color}</span>
        <span>Strokes: {state.strokes.length}</span>
        <span>Undo: {state.undoStack.length}</span>
        <span>Redo: {state.redoStack.length}</span>
      </div>
    </div>
  );
};

export default Whiteboard;
