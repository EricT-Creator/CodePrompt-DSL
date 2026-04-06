import React, { useEffect, useMemo, useReducer, useRef } from "react";

type Tool = "brush" | "eraser";

type Point = {
  x: number;
  y: number;
};

type Stroke = {
  id: string;
  tool: Tool;
  color: string;
  size: number;
  points: Point[];
};

type State = {
  tool: Tool;
  color: string;
  size: number;
  strokes: Stroke[];
  redoStack: Stroke[];
  currentStroke: Stroke | null;
};

type Action =
  | { type: "SET_TOOL"; tool: Tool }
  | { type: "SET_COLOR"; color: string }
  | { type: "SET_SIZE"; size: number }
  | { type: "START_STROKE"; point: Point }
  | { type: "APPEND_POINT"; point: Point }
  | { type: "END_STROKE" }
  | { type: "UNDO" }
  | { type: "REDO" }
  | { type: "CLEAR" };

const palette = ["#111827", "#2563eb", "#ef4444", "#16a34a", "#7c3aed", "#f59e0b"];

const initialState: State = {
  tool: "brush",
  color: palette[0],
  size: 6,
  strokes: [],
  redoStack: [],
  currentStroke: null,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_TOOL":
      return { ...state, tool: action.tool };
    case "SET_COLOR":
      return { ...state, color: action.color, tool: "brush" };
    case "SET_SIZE":
      return { ...state, size: action.size };
    case "START_STROKE": {
      const stroke: Stroke = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        tool: state.tool,
        color: state.color,
        size: state.size,
        points: [action.point],
      };
      return { ...state, currentStroke: stroke, redoStack: [] };
    }
    case "APPEND_POINT": {
      if (!state.currentStroke) {
        return state;
      }
      const points = [...state.currentStroke.points, action.point];
      return {
        ...state,
        currentStroke: {
          ...state.currentStroke,
          points,
        },
      };
    }
    case "END_STROKE": {
      if (!state.currentStroke) {
        return state;
      }
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
      };
    }
    case "UNDO": {
      if (state.currentStroke || state.strokes.length === 0) {
        return state;
      }
      const strokes = [...state.strokes];
      const last = strokes.pop();
      if (!last) {
        return state;
      }
      return {
        ...state,
        strokes,
        redoStack: [...state.redoStack, last],
      };
    }
    case "REDO": {
      if (state.currentStroke || state.redoStack.length === 0) {
        return state;
      }
      const redoStack = [...state.redoStack];
      const restored = redoStack.pop();
      if (!restored) {
        return state;
      }
      return {
        ...state,
        strokes: [...state.strokes, restored],
        redoStack,
      };
    }
    case "CLEAR":
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

  if (stroke.tool === "eraser") {
    context.globalCompositeOperation = "destination-out";
    context.strokeStyle = "rgba(0,0,0,1)";
  } else {
    context.globalCompositeOperation = "source-over";
    context.strokeStyle = stroke.color;
  }

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

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const strokesToRender = useMemo(() => {
    return state.currentStroke ? [...state.strokes, state.currentStroke] : state.strokes;
  }, [state.currentStroke, state.strokes]);

  const css = `
    * {
      box-sizing: border-box;
    }

    .wb-page {
      min-height: 100vh;
      padding: 28px 18px;
      background: linear-gradient(180deg, #f4f7fb 0%, #edf1ff 100%);
      font-family: Arial, Helvetica, sans-serif;
      color: #16213a;
    }

    .wb-shell {
      max-width: 1100px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 26px;
      border: 1px solid #d9e1f0;
      box-shadow: 0 24px 64px rgba(20, 40, 90, 0.14);
      overflow: hidden;
    }

    .wb-header {
      padding: 24px 24px 18px;
      border-bottom: 1px solid #e6ebf5;
    }

    .wb-title {
      margin: 0;
      font-size: 30px;
      font-weight: 700;
    }

    .wb-subtitle {
      margin: 10px 0 0;
      color: #596884;
      line-height: 1.6;
    }

    .wb-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
      padding: 18px 24px;
      border-bottom: 1px solid #e6ebf5;
      background: #fafcff;
    }

    .wb-group {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .wb-button {
      appearance: none;
      border: 1px solid #d5deef;
      background: #ffffff;
      color: #33415d;
      border-radius: 14px;
      padding: 10px 14px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.16s ease;
    }

    .wb-button:hover {
      border-color: #7b95ea;
      background: #eff4ff;
    }

    .wb-button--active {
      border-color: #4561df;
      background: #eaf0ff;
      color: #2341c7;
    }

    .wb-color {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      border: 3px solid transparent;
      cursor: pointer;
      transition: transform 0.16s ease, border-color 0.16s ease;
    }

    .wb-color:hover {
      transform: scale(1.05);
    }

    .wb-color--active {
      border-color: #1f2a44;
    }

    .wb-size {
      width: 170px;
    }

    .wb-canvas-wrap {
      padding: 22px;
      background: #f7f9ff;
    }

    .wb-canvas {
      display: block;
      width: 100%;
      height: 560px;
      background:
        linear-gradient(0deg, rgba(17, 24, 39, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(17, 24, 39, 0.04) 1px, transparent 1px),
        #ffffff;
      background-size: 24px 24px;
      border-radius: 20px;
      border: 1px solid #d7dfef;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
      touch-action: none;
      cursor: crosshair;
    }

    .wb-footer {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      padding: 0 24px 22px;
      color: #5b6982;
      flex-wrap: wrap;
    }
  `;

  const getCanvasPoint = (clientX: number, clientY: number): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return null;
    }
    const rect = canvas.getBoundingClientRect();
    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  };

  const startStroke = (clientX: number, clientY: number) => {
    const point = getCanvasPoint(clientX, clientY);
    if (!point) {
      return;
    }
    dispatch({ type: "START_STROKE", point });
  };

  const appendPoint = (clientX: number, clientY: number) => {
    const point = getCanvasPoint(clientX, clientY);
    if (!point) {
      return;
    }
    dispatch({ type: "APPEND_POINT", point });
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width * ratio));
    const height = Math.max(1, Math.floor(rect.height * ratio));

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, rect.width, rect.height);
    strokesToRender.forEach((stroke) => drawStroke(context, stroke));
  }, [strokesToRender]);

  useEffect(() => {
    if (!state.currentStroke) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      appendPoint(event.clientX, event.clientY);
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (event.touches.length === 0) {
        return;
      }
      event.preventDefault();
      appendPoint(event.touches[0].clientX, event.touches[0].clientY);
    };

    const stopDrawing = () => {
      dispatch({ type: "END_STROKE" });
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopDrawing);
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", stopDrawing);
    window.addEventListener("touchcancel", stopDrawing);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopDrawing);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", stopDrawing);
      window.removeEventListener("touchcancel", stopDrawing);
    };
  }, [state.currentStroke]);

  return (
    <div className="wb-page">
      <style>{css}</style>
      <div className="wb-shell">
        <div className="wb-header">
          <h1 className="wb-title">协作白板</h1>
          <p className="wb-subtitle">
            支持画笔、橡皮擦、六色切换、笔刷大小调整、撤销重做与清空画布。所有可变状态均通过 useReducer 统一管理。
          </p>
        </div>

        <div className="wb-toolbar">
          <div className="wb-group">
            <button
              type="button"
              className={[
                "wb-button",
                state.tool === "brush" ? "wb-button--active" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => dispatch({ type: "SET_TOOL", tool: "brush" })}
            >
              画笔
            </button>
            <button
              type="button"
              className={[
                "wb-button",
                state.tool === "eraser" ? "wb-button--active" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => dispatch({ type: "SET_TOOL", tool: "eraser" })}
            >
              橡皮擦
            </button>
          </div>

          <div className="wb-group">
            {palette.map((color) => (
              <button
                key={color}
                type="button"
                className={[
                  "wb-color",
                  state.color === color && state.tool === "brush" ? "wb-color--active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                aria-label={`选择颜色 ${color}`}
                style={{ backgroundColor: color }}
                onClick={() => dispatch({ type: "SET_COLOR", color })}
              />
            ))}
          </div>

          <div className="wb-group">
            <label htmlFor="brush-size">笔刷大小</label>
            <input
              id="brush-size"
              className="wb-size"
              type="range"
              min="2"
              max="24"
              step="1"
              value={state.size}
              onChange={(event) =>
                dispatch({ type: "SET_SIZE", size: Number(event.currentTarget.value) })
              }
            />
            <strong>{state.size}px</strong>
          </div>

          <div className="wb-group">
            <button type="button" className="wb-button" onClick={() => dispatch({ type: "UNDO" })}>
              撤销
            </button>
            <button type="button" className="wb-button" onClick={() => dispatch({ type: "REDO" })}>
              重做
            </button>
            <button type="button" className="wb-button" onClick={() => dispatch({ type: "CLEAR" })}>
              清除画布
            </button>
          </div>
        </div>

        <div className="wb-canvas-wrap">
          <canvas
            ref={canvasRef}
            className="wb-canvas"
            onMouseDown={(event) => startStroke(event.clientX, event.clientY)}
            onTouchStart={(event) => {
              if (event.touches.length > 0) {
                event.preventDefault();
                startStroke(event.touches[0].clientX, event.touches[0].clientY);
              }
            }}
          />
        </div>

        <div className="wb-footer">
          <span>已绘制笔画：{state.strokes.length}</span>
          <span>可重做笔画：{state.redoStack.length}</span>
          <span>当前工具：{state.tool === "brush" ? "画笔" : "橡皮擦"}</span>
        </div>
      </div>
    </div>
  );
}
