import React, { useReducer, useRef, useEffect, useCallback } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

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

type Action =
  | { type: "START_STROKE"; point: Point }
  | { type: "ADD_POINT"; point: Point }
  | { type: "END_STROKE" }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" }
  | { type: "SET_TOOL"; tool: "pen" | "eraser" }
  | { type: "SET_COLOR"; color: string };

// ─── Styles ──────────────────────────────────────────────────────────────────

const css = `
.wbContainer { display: flex; flex-direction: column; height: 100vh; background: #1e1e2e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.toolbar { display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: #2a2a3c; border-bottom: 1px solid #3a3a4c; flex-wrap: wrap; }
.toolBtn { padding: 7px 16px; border: 1px solid #4a4a5c; border-radius: 8px; background: #353548; color: #cdd6f4; font-size: 13px; cursor: pointer; transition: all 0.15s; font-weight: 500; }
.toolBtn:hover { background: #45456a; }
.toolBtnActive { background: #585890; border-color: #7c7cb8; color: #fff; }
.toolBtnDanger { border-color: #e64553; color: #e64553; }
.toolBtnDanger:hover { background: #e6455322; }
.separator { width: 1px; height: 28px; background: #4a4a5c; margin: 0 4px; }
.colorPicker { width: 34px; height: 34px; border: 2px solid #4a4a5c; border-radius: 8px; cursor: pointer; background: none; padding: 0; }
.colorPicker::-webkit-color-swatch-wrapper { padding: 2px; }
.colorPicker::-webkit-color-swatch { border: none; border-radius: 4px; }
.canvasArea { flex: 1; display: flex; align-items: center; justify-content: center; padding: 16px; }
.canvas { border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.3); cursor: crosshair; background: #fff; }
.statusBar { display: flex; justify-content: space-between; padding: 6px 16px; background: #2a2a3c; color: #6c7086; font-size: 12px; border-top: 1px solid #3a3a4c; }
`;

// ─── Constants ───────────────────────────────────────────────────────────────

const CANVAS_WIDTH = 1200;
const CANVAS_HEIGHT = 700;
const UNDO_LIMIT = 50;
const PEN_WIDTH = 3;
const ERASER_WIDTH = 24;

// ─── Reducer ─────────────────────────────────────────────────────────────────

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  tool: "pen",
  color: "#1e1e2e",
  isDrawing: false,
};

function whiteboardReducer(state: WhiteboardState, action: Action): WhiteboardState {
  switch (action.type) {
    case "START_STROKE": {
      const newStroke: Stroke = {
        id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        tool: state.tool,
        color: state.color,
        lineWidth: state.tool === "pen" ? PEN_WIDTH : ERASER_WIDTH,
        points: [action.point],
      };
      let undoStack = [...state.undoStack, [...state.strokes]];
      if (undoStack.length > UNDO_LIMIT) {
        undoStack = undoStack.slice(undoStack.length - UNDO_LIMIT);
      }
      return {
        ...state,
        currentStroke: newStroke,
        undoStack,
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
      const prev = state.undoStack[state.undoStack.length - 1];
      return {
        ...state,
        redoStack: [...state.redoStack, state.strokes],
        strokes: prev,
        undoStack: state.undoStack.slice(0, -1),
      };
    }

    case "REDO": {
      if (state.redoStack.length === 0) return state;
      const next = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        undoStack: [...state.undoStack, state.strokes],
        strokes: next,
        redoStack: state.redoStack.slice(0, -1),
      };
    }

    case "CLEAR": {
      if (state.strokes.length === 0) return state;
      let undoStack = [...state.undoStack, [...state.strokes]];
      if (undoStack.length > UNDO_LIMIT) {
        undoStack = undoStack.slice(undoStack.length - UNDO_LIMIT);
      }
      return {
        ...state,
        strokes: [],
        undoStack,
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

// ─── Drawing Utilities ───────────────────────────────────────────────────────

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

function redrawAll(ctx: CanvasRenderingContext2D, strokes: Stroke[], currentStroke: Stroke | null): void {
  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  for (const s of strokes) {
    drawStroke(ctx, s);
  }
  if (currentStroke) {
    drawStroke(ctx, currentStroke);
  }
}

// ─── Toolbar ─────────────────────────────────────────────────────────────────

function Toolbar({
  state,
  dispatch,
}: {
  state: WhiteboardState;
  dispatch: React.Dispatch<Action>;
}) {
  return (
    <div className="toolbar">
      <button
        className={`toolBtn${state.tool === "pen" ? " toolBtnActive" : ""}`}
        onClick={() => dispatch({ type: "SET_TOOL", tool: "pen" })}
      >
        ✏️ Pen
      </button>
      <button
        className={`toolBtn${state.tool === "eraser" ? " toolBtnActive" : ""}`}
        onClick={() => dispatch({ type: "SET_TOOL", tool: "eraser" })}
      >
        🧹 Eraser
      </button>
      <div className="separator" />
      <input
        type="color"
        className="colorPicker"
        value={state.color}
        onChange={(e) => dispatch({ type: "SET_COLOR", color: e.target.value })}
      />
      <div className="separator" />
      <button
        className="toolBtn"
        onClick={() => dispatch({ type: "UNDO" })}
        disabled={state.undoStack.length === 0}
      >
        ↩ Undo
      </button>
      <button
        className="toolBtn"
        onClick={() => dispatch({ type: "REDO" })}
        disabled={state.redoStack.length === 0}
      >
        ↪ Redo
      </button>
      <div className="separator" />
      <button className="toolBtn toolBtnDanger" onClick={() => dispatch({ type: "CLEAR" })}>
        🗑 Clear
      </button>
    </div>
  );
}

// ─── Whiteboard (root) ───────────────────────────────────────────────────────

function Whiteboard() {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    redrawAll(ctx, state.strokes, state.currentStroke);
  }, [state.strokes, state.currentStroke]);

  const getPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      dispatch({ type: "START_STROKE", point: getPoint(e) });
    },
    [getPoint]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!state.isDrawing) return;
      dispatch({ type: "ADD_POINT", point: getPoint(e) });
    },
    [state.isDrawing, getPoint]
  );

  const handleMouseUp = useCallback(() => {
    if (!state.isDrawing) return;
    dispatch({ type: "END_STROKE" });
  }, [state.isDrawing]);

  return (
    <div className="wbContainer">
      <style>{css}</style>
      <Toolbar state={state} dispatch={dispatch} />
      <div className="canvasArea">
        <canvas
          ref={canvasRef}
          className="canvas"
          width={CANVAS_WIDTH}
          height={CANVAS_HEIGHT}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
      </div>
      <div className="statusBar">
        <span>
          Tool: {state.tool} | Color: {state.color} | Strokes: {state.strokes.length}
        </span>
        <span>
          Undo: {state.undoStack.length} | Redo: {state.redoStack.length}
        </span>
      </div>
    </div>
  );
}

export default Whiteboard;
