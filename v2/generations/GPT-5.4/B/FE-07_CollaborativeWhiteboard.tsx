import React, { useEffect, useReducer, useRef } from "react";

type Tool = "pen" | "eraser";

type Point = {
  x: number;
  y: number;
};

type Stroke = {
  tool: Tool;
  color: string;
  size: number;
  points: Point[];
};

type State = {
  tool: Tool;
  color: string;
  brushSize: number;
  strokes: Stroke[];
  redoStack: Stroke[];
};

type Action =
  | { type: "SET_TOOL"; tool: Tool }
  | { type: "SET_COLOR"; color: string }
  | { type: "SET_BRUSH_SIZE"; size: number }
  | { type: "COMMIT_STROKE"; stroke: Stroke }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" };

const COLORS = ["#0f172a", "#2563eb", "#ef4444", "#16a34a", "#a855f7", "#f59e0b"];

const initialState: State = {
  tool: "pen",
  color: COLORS[0],
  brushSize: 5,
  strokes: [],
  redoStack: [],
};

const styles = `
  .whiteboard-page {
    min-height: 100vh;
    padding: 24px 16px;
    box-sizing: border-box;
    background: linear-gradient(180deg, #f8fafc 0%, #e0f2fe 100%);
    font-family: Arial, Helvetica, sans-serif;
    color: #0f172a;
  }

  .whiteboard-shell {
    max-width: 1100px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-radius: 24px;
    box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
    overflow: hidden;
  }

  .whiteboard-header {
    padding: 24px 24px 18px;
    border-bottom: 1px solid #e2e8f0;
  }

  .whiteboard-title {
    margin: 0 0 8px;
    font-size: 30px;
  }

  .whiteboard-subtitle {
    margin: 0;
    font-size: 14px;
    line-height: 1.6;
    color: #475569;
  }

  .whiteboard-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 18px 24px;
    border-bottom: 1px solid #e2e8f0;
    align-items: center;
  }

  .toolbar-group {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
  }

  .toolbar-label {
    font-size: 12px;
    font-weight: 700;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .tool-button,
  .action-button {
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #0f172a;
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: background 120ms ease, border-color 120ms ease, transform 120ms ease;
  }

  .tool-button:hover,
  .action-button:hover {
    background: #eff6ff;
    border-color: #60a5fa;
    transform: translateY(-1px);
  }

  .tool-button.active {
    background: #1d4ed8;
    color: #ffffff;
    border-color: #1d4ed8;
  }

  .color-button {
    width: 28px;
    height: 28px;
    border-radius: 999px;
    border: 2px solid transparent;
    cursor: pointer;
    box-sizing: border-box;
  }

  .color-button.active {
    border-color: #0f172a;
    box-shadow: 0 0 0 2px #ffffff inset;
  }

  .size-input {
    width: 120px;
  }

  .board-panel {
    padding: 24px;
  }

  .board-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;
  }

  .board-stat {
    padding: 8px 12px;
    border-radius: 999px;
    background: #eff6ff;
    color: #1d4ed8;
    font-size: 13px;
    font-weight: 700;
  }

  .canvas-frame {
    border: 1px solid #cbd5e1;
    border-radius: 18px;
    overflow: hidden;
    background: repeating-linear-gradient(
      0deg,
      #ffffff,
      #ffffff 28px,
      #f8fafc 28px,
      #f8fafc 29px
    );
  }

  .drawing-canvas {
    display: block;
    width: 100%;
    height: auto;
    touch-action: none;
    background: transparent;
  }

  .whiteboard-footer {
    padding: 0 24px 24px;
    color: #64748b;
    font-size: 13px;
    line-height: 1.6;
  }

  @media (max-width: 768px) {
    .whiteboard-header,
    .whiteboard-toolbar,
    .board-panel,
    .whiteboard-footer {
      padding-left: 16px;
      padding-right: 16px;
    }

    .whiteboard-title {
      font-size: 24px;
    }
  }
`;

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_TOOL":
      return { ...state, tool: action.tool };
    case "SET_COLOR":
      return { ...state, color: action.color };
    case "SET_BRUSH_SIZE":
      return { ...state, brushSize: action.size };
    case "COMMIT_STROKE":
      return {
        ...state,
        strokes: [...state.strokes, action.stroke],
        redoStack: [],
      };
    case "UNDO": {
      if (state.strokes.length === 0) {
        return state;
      }
      const nextStrokes = state.strokes.slice(0, -1);
      const lastStroke = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: nextStrokes,
        redoStack: [...state.redoStack, lastStroke],
      };
    }
    case "REDO": {
      if (state.redoStack.length === 0) {
        return state;
      }
      const recovered = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, recovered],
        redoStack: state.redoStack.slice(0, -1),
      };
    }
    case "CLEAR":
      return {
        ...state,
        strokes: [],
        redoStack: [],
      };
    default:
      return state;
  }
}

function drawStroke(context: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length === 0) {
    return;
  }

  context.save();
  context.lineJoin = "round";
  context.lineCap = "round";
  context.lineWidth = stroke.size;
  context.strokeStyle = stroke.tool === "eraser" ? "#ffffff" : stroke.color;
  context.beginPath();

  stroke.points.forEach((point, index) => {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  });

  if (stroke.points.length === 1) {
    const point = stroke.points[0];
    context.arc(point.x, point.y, stroke.size / 2, 0, Math.PI * 2);
  }

  context.stroke();
  context.restore();
}

function getCanvasPoint(
  canvas: HTMLCanvasElement,
  event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
): Point {
  const rect = canvas.getBoundingClientRect();
  const touchPoint = "touches" in event ? event.touches[0] ?? event.changedTouches[0] : null;
  const clientX = touchPoint ? touchPoint.clientX : event.clientX;
  const clientY = touchPoint ? touchPoint.clientY : event.clientY;

  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  };
}

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const isDrawingRef = useRef(false);
  const currentStrokeRef = useRef<Stroke | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);

    state.strokes.forEach((stroke) => {
      drawStroke(context, stroke);
    });
  }, [state.strokes]);

  const startDrawing = (
    event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    event.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const point = getCanvasPoint(canvas, event);
    const stroke: Stroke = {
      tool: state.tool,
      color: state.color,
      size: state.brushSize,
      points: [point],
    };

    isDrawingRef.current = true;
    currentStrokeRef.current = stroke;
  };

  const continueDrawing = (
    event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    if (!isDrawingRef.current) {
      return;
    }

    event.preventDefault();
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const currentStroke = currentStrokeRef.current;
    if (!canvas || !context || !currentStroke) {
      return;
    }

    const point = getCanvasPoint(canvas, event);
    currentStroke.points.push(point);

    const lastPoint = currentStroke.points[currentStroke.points.length - 2] ?? point;
    context.save();
    context.lineCap = "round";
    context.lineJoin = "round";
    context.lineWidth = currentStroke.size;
    context.strokeStyle = currentStroke.tool === "eraser" ? "#ffffff" : currentStroke.color;
    context.beginPath();
    context.moveTo(lastPoint.x, lastPoint.y);
    context.lineTo(point.x, point.y);
    context.stroke();
    context.restore();
  };

  const stopDrawing = () => {
    if (!isDrawingRef.current || !currentStrokeRef.current) {
      return;
    }

    isDrawingRef.current = false;
    dispatch({ type: "COMMIT_STROKE", stroke: currentStrokeRef.current });
    currentStrokeRef.current = null;
  };

  return (
    <div className="whiteboard-page">
      <style>{styles}</style>
      <div className="whiteboard-shell">
        <div className="whiteboard-header">
          <h1 className="whiteboard-title">Collaborative Whiteboard</h1>
          <p className="whiteboard-subtitle">
            Draw with a pen, erase with a soft white brush, change colors and brush size, then undo,
            redo, or clear the board. All state is managed with useReducer only.
          </p>
        </div>

        <div className="whiteboard-toolbar">
          <div className="toolbar-group">
            <span className="toolbar-label">Tool</span>
            <button
              type="button"
              className={`tool-button ${state.tool === "pen" ? "active" : ""}`}
              onClick={() => dispatch({ type: "SET_TOOL", tool: "pen" })}
            >
              Pen
            </button>
            <button
              type="button"
              className={`tool-button ${state.tool === "eraser" ? "active" : ""}`}
              onClick={() => dispatch({ type: "SET_TOOL", tool: "eraser" })}
            >
              Eraser
            </button>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Colors</span>
            {COLORS.map((color) => (
              <button
                key={color}
                type="button"
                className={`color-button ${state.color === color ? "active" : ""}`}
                style={{ background: color }}
                onClick={() => dispatch({ type: "SET_COLOR", color })}
                aria-label={`Select ${color}`}
              />
            ))}
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Brush</span>
            <input
              className="size-input"
              type="range"
              min={2}
              max={24}
              step={1}
              value={state.brushSize}
              onChange={(event) =>
                dispatch({ type: "SET_BRUSH_SIZE", size: Number(event.currentTarget.value) })
              }
            />
            <strong>{state.brushSize}px</strong>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">History</span>
            <button type="button" className="action-button" onClick={() => dispatch({ type: "UNDO" })}>
              Undo
            </button>
            <button type="button" className="action-button" onClick={() => dispatch({ type: "REDO" })}>
              Redo
            </button>
            <button type="button" className="action-button" onClick={() => dispatch({ type: "CLEAR" })}>
              Clear
            </button>
          </div>
        </div>

        <div className="board-panel">
          <div className="board-stats">
            <div className="board-stat">Strokes: {state.strokes.length}</div>
            <div className="board-stat">Redo stack: {state.redoStack.length}</div>
            <div className="board-stat">Mode: {state.tool}</div>
          </div>

          <div className="canvas-frame">
            <canvas
              ref={canvasRef}
              className="drawing-canvas"
              width={960}
              height={540}
              onMouseDown={startDrawing}
              onMouseMove={continueDrawing}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawing}
              onTouchMove={continueDrawing}
              onTouchEnd={stopDrawing}
            />
          </div>
        </div>

        <div className="whiteboard-footer">
          Tip: the eraser is implemented as a white brush on a white canvas, so undo and redo still work
          because every stroke remains part of the reducer-managed history.
        </div>
      </div>
    </div>
  );
}
