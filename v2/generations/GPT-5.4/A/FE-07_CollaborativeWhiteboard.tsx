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
  currentStroke: Stroke | null;
};

type Action =
  | { type: "setTool"; tool: Tool }
  | { type: "setColor"; color: string }
  | { type: "setBrushSize"; size: number }
  | { type: "startStroke"; point: Point }
  | { type: "appendPoint"; point: Point }
  | { type: "endStroke" }
  | { type: "undo" }
  | { type: "redo" }
  | { type: "clear" };

const COLORS = ["#111827", "#ef4444", "#3b82f6", "#10b981", "#f59e0b"];

const initialState: State = {
  tool: "pen",
  color: COLORS[0],
  brushSize: 5,
  strokes: [],
  redoStack: [],
  currentStroke: null,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "setTool":
      return { ...state, tool: action.tool };
    case "setColor":
      return { ...state, color: action.color };
    case "setBrushSize":
      return { ...state, brushSize: action.size };
    case "startStroke":
      return {
        ...state,
        redoStack: [],
        currentStroke: {
          tool: state.tool,
          color: state.color,
          size: state.brushSize,
          points: [action.point],
        },
      };
    case "appendPoint":
      if (!state.currentStroke) {
        return state;
      }
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points: [...state.currentStroke.points, action.point],
        },
      };
    case "endStroke":
      if (!state.currentStroke) {
        return state;
      }
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
      };
    case "undo": {
      if (state.currentStroke || state.strokes.length === 0) {
        return state;
      }
      const removed = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        redoStack: [...state.redoStack, removed],
      };
    }
    case "redo": {
      if (state.currentStroke || state.redoStack.length === 0) {
        return state;
      }
      const restored = state.redoStack[state.redoStack.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, restored],
        redoStack: state.redoStack.slice(0, -1),
      };
    }
    case "clear":
      return {
        ...state,
        strokes: [],
        redoStack: [],
        currentStroke: null,
      };
    default:
      return state;
  }
}

function drawStroke(context: CanvasRenderingContext2D, stroke: Stroke): void {
  if (stroke.points.length === 0) {
    return;
  }

  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";
  context.lineWidth = stroke.size;
  context.globalCompositeOperation = stroke.tool === "eraser" ? "destination-out" : "source-over";
  context.strokeStyle = stroke.color;
  context.beginPath();
  context.moveTo(stroke.points[0].x, stroke.points[0].y);

  for (let index = 1; index < stroke.points.length; index += 1) {
    const point = stroke.points[index];
    context.lineTo(point.x, point.y);
  }

  if (stroke.points.length === 1) {
    context.lineTo(stroke.points[0].x + 0.01, stroke.points[0].y + 0.01);
  }

  context.stroke();
  context.restore();
}

function getCanvasPoint(
  canvas: HTMLCanvasElement,
  event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
): Point {
  const rect = canvas.getBoundingClientRect();
  const source = "touches" in event ? event.touches[0] : event;
  return {
    x: source.clientX - rect.left,
    y: source.clientY - rect.top,
  };
}

export default function CollaborativeWhiteboard(): JSX.Element {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawingRef = useRef(false);

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

    state.strokes.forEach((stroke) => drawStroke(context, stroke));
    if (state.currentStroke) {
      drawStroke(context, state.currentStroke);
    }
  }, [state.currentStroke, state.strokes]);

  useEffect(() => {
    if (!state.currentStroke) {
      drawingRef.current = false;
      return undefined;
    }

    const stopDrawing = () => {
      drawingRef.current = false;
      dispatch({ type: "endStroke" });
    };

    window.addEventListener("mouseup", stopDrawing);
    window.addEventListener("touchend", stopDrawing);
    window.addEventListener("touchcancel", stopDrawing);

    return () => {
      window.removeEventListener("mouseup", stopDrawing);
      window.removeEventListener("touchend", stopDrawing);
      window.removeEventListener("touchcancel", stopDrawing);
    };
  }, [state.currentStroke]);

  const beginDrawing = (
    event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    if ("button" in event && event.button !== 0) {
      return;
    }

    if ("preventDefault" in event) {
      event.preventDefault();
    }

    drawingRef.current = true;
    dispatch({ type: "startStroke", point: getCanvasPoint(canvas, event) });
  };

  const continueDrawing = (
    event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
  ) => {
    if (!drawingRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    if ("preventDefault" in event) {
      event.preventDefault();
    }

    dispatch({ type: "appendPoint", point: getCanvasPoint(canvas, event) });
  };

  const finishDrawing = () => {
    if (!drawingRef.current) {
      return;
    }
    drawingRef.current = false;
    dispatch({ type: "endStroke" });
  };

  return (
    <div className="whiteboard-root">
      <style>{`
        .whiteboard-root {
          min-height: 100%;
          background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
          padding: 24px;
          box-sizing: border-box;
          font-family: Arial, Helvetica, sans-serif;
          color: #0f172a;
        }
        .whiteboard-shell {
          max-width: 1080px;
          margin: 0 auto;
          background: #ffffff;
          border-radius: 20px;
          border: 1px solid #dbeafe;
          box-shadow: 0 24px 50px rgba(15, 23, 42, 0.08);
          overflow: hidden;
        }
        .whiteboard-header {
          padding: 24px 24px 0;
        }
        .whiteboard-header h1 {
          margin: 0 0 8px;
          font-size: 28px;
        }
        .whiteboard-header p {
          margin: 0 0 18px;
          color: #475569;
          line-height: 1.6;
        }
        .toolbar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 14px;
          padding: 0 24px 20px;
          border-bottom: 1px solid #e2e8f0;
        }
        .tool-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .tool-label {
          font-size: 14px;
          color: #475569;
          font-weight: 700;
        }
        .tool-button,
        .action-button,
        .color-button {
          border: 1px solid #cbd5e1;
          background: #ffffff;
          border-radius: 12px;
          padding: 10px 14px;
          cursor: pointer;
          transition: all 0.15s ease;
          font-size: 14px;
        }
        .tool-button.active,
        .action-button:hover {
          background: #dbeafe;
          border-color: #60a5fa;
          color: #1d4ed8;
        }
        .color-button {
          width: 34px;
          height: 34px;
          padding: 0;
          border-radius: 50%;
        }
        .color-button.active {
          transform: scale(1.08);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
          border-color: #1d4ed8;
        }
        .size-input {
          width: 160px;
        }
        .canvas-wrap {
          padding: 24px;
        }
        .canvas {
          width: 100%;
          max-width: 100%;
          background: #ffffff;
          border-radius: 18px;
          border: 1px solid #cbd5e1;
          touch-action: none;
          display: block;
        }
        .status-row {
          padding: 0 24px 24px;
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          color: #475569;
          font-size: 14px;
        }
        @media (max-width: 720px) {
          .whiteboard-root {
            padding: 16px;
          }
          .toolbar {
            flex-direction: column;
            align-items: stretch;
          }
          .tool-group {
            flex-wrap: wrap;
          }
        }
      `}</style>

      <div className="whiteboard-shell">
        <div className="whiteboard-header">
          <h1>Collaborative Whiteboard</h1>
          <p>
            Sketch ideas with a pen or erase details, then use undo, redo, and clear controls to
            manage the board state.
          </p>
        </div>

        <div className="toolbar">
          <div className="tool-group">
            <span className="tool-label">Tool</span>
            <button
              type="button"
              className={`tool-button ${state.tool === "pen" ? "active" : ""}`.trim()}
              onClick={() => dispatch({ type: "setTool", tool: "pen" })}
            >
              Pen
            </button>
            <button
              type="button"
              className={`tool-button ${state.tool === "eraser" ? "active" : ""}`.trim()}
              onClick={() => dispatch({ type: "setTool", tool: "eraser" })}
            >
              Eraser
            </button>
          </div>

          <div className="tool-group">
            <span className="tool-label">Colors</span>
            {COLORS.map((color) => (
              <button
                key={color}
                type="button"
                className={`color-button ${state.color === color ? "active" : ""}`.trim()}
                aria-label={`Choose ${color}`}
                onClick={() => dispatch({ type: "setColor", color })}
                style={{ background: color }}
              />
            ))}
          </div>

          <div className="tool-group">
            <span className="tool-label">Brush</span>
            <input
              className="size-input"
              type="range"
              min="2"
              max="24"
              value={state.brushSize}
              onChange={(event) => dispatch({ type: "setBrushSize", size: Number(event.target.value) })}
            />
            <span>{state.brushSize}px</span>
          </div>

          <div className="tool-group">
            <button type="button" className="action-button" onClick={() => dispatch({ type: "undo" })}>
              Undo
            </button>
            <button type="button" className="action-button" onClick={() => dispatch({ type: "redo" })}>
              Redo
            </button>
            <button type="button" className="action-button" onClick={() => dispatch({ type: "clear" })}>
              Clear Canvas
            </button>
          </div>
        </div>

        <div className="canvas-wrap">
          <canvas
            ref={canvasRef}
            className="canvas"
            width={1032}
            height={580}
            onMouseDown={beginDrawing}
            onMouseMove={continueDrawing}
            onMouseUp={finishDrawing}
            onMouseLeave={finishDrawing}
            onTouchStart={beginDrawing}
            onTouchMove={continueDrawing}
            onTouchEnd={finishDrawing}
          />
        </div>

        <div className="status-row">
          <span>Active tool: {state.tool}</span>
          <span>Saved strokes: {state.strokes.length}</span>
          <span>Redo stack: {state.redoStack.length}</span>
        </div>
      </div>
    </div>
  );
}
