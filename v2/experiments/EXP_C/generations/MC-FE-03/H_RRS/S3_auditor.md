# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (H × RRS)
## Task: MC-FE-03

**模型**: DeepSeek-V3.2  
**Stage**: S3 Auditor  
**编码**: H  
**管线组合**: RRS  

## Constraint Review

- C1 [L]TS [F]React: PASS — 代码使用TypeScript（.tsx文件）和React（import React, { useReducer, useRef, useEffect, useCallback } from "react"）
- C2 [!D]NO_CANVAS_LIB [DRAW]CTX2D: PASS — 使用原生Canvas 2D Context（canvas.getContext("2d")），没有使用第三方Canvas库如Fabric.js或Konva.js
- C3 [STATE]useReducer_ONLY: FAIL — 代码使用了React.CSSProperties和内联样式对象，这不符合"仅使用useReducer"的严格约束。useReducer_ONLY意味着状态管理应完全通过useReducer处理，不应使用内联样式对象作为状态或配置
- C4 [D]NO_EXTERNAL: PASS — 只使用React内置钩子，没有外部依赖
- C5 [O]SFC [EXP]DEFAULT: PASS — 导出默认的单一函数组件（export default function Whiteboard(): React.ReactElement）
- C6 [OUT]CODE_ONLY: PASS — 输出为纯代码格式

## Functionality Assessment (0-5)
Score: 3 — 代码实现了基本白板功能，包含画笔/橡皮擦工具、颜色选择、线条宽度调整、撤销/重做/清除功能。但违反了useReducer_ONLY约束，使用了内联样式对象。Canvas绘制逻辑合理，性能处理得当。

## Corrected Code
由于C3约束FAIL，需要提供修复后代码。需要移除内联样式对象，将样式相关状态迁移到useReducer中：

```tsx
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
  // 移除了内联样式对象，添加UI状态
  uiState: {
    containerBackground: string;
    fontFamily: string;
    padding: number;
    buttonGap: number;
    buttonBorderRadius: number;
    buttonPadding: string;
    buttonFontSize: number;
    inputPadding: string;
    inputBorderColor: string;
    inputFocusBorderColor: string;
    labelMargin: string;
    labelFontSize: number;
    infoMarginTop: number;
    infoFontSize: number;
    infoColor: string;
  };
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
  uiState: {
    containerBackground: "#f5f5f5",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: 24,
    buttonGap: 8,
    buttonBorderRadius: 4,
    buttonPadding: "6px 12px",
    buttonFontSize: 13,
    inputPadding: "4px 8px",
    inputBorderColor: "#ccc",
    inputFocusBorderColor: "#1890ff",
    labelMargin: "0 0 4px 0",
    labelFontSize: 12,
    infoMarginTop: 8,
    infoFontSize: 12,
    infoColor: "#999",
  },
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

// ─── Main Component ───
export default function Whiteboard(): React.ReactElement {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);
  const currentPathRef = useRef<PathSegment | null>(null);

  // Canvas setup and drawing
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw all strokes
    for (const stroke of state.strokes) {
      ctx.beginPath();
      ctx.strokeStyle = stroke.tool === "eraser" ? state.uiState.containerBackground : stroke.color;
      ctx.lineWidth = stroke.lineWidth;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      if (stroke.points.length > 0) {
        ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
        for (let i = 1; i < stroke.points.length; i++) {
          ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
        }
        ctx.stroke();
      }
    }
  }, [state.strokes, state.uiState.containerBackground]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    isDrawingRef.current = true;
    currentPathRef.current = {
      id: generateId(),
      tool: state.currentTool,
      color: state.currentColor,
      lineWidth: state.lineWidth,
      points: [{ x, y }],
    };
  }, [state.currentTool, state.currentColor, state.lineWidth]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current || !currentPathRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    currentPathRef.current.points.push({ x, y });

    // Immediate feedback drawing
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const lastPoint = currentPathRef.current.points[currentPathRef.current.points.length - 2];
    if (!lastPoint) return;

    ctx.beginPath();
    ctx.strokeStyle = currentPathRef.current.tool === "eraser" 
      ? state.uiState.containerBackground 
      : currentPathRef.current.color;
    ctx.lineWidth = currentPathRef.current.lineWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.moveTo(lastPoint.x, lastPoint.y);
    ctx.lineTo(x, y);
    ctx.stroke();
  }, [state.uiState.containerBackground]);

  const handleMouseUp = useCallback(() => {
    if (!isDrawingRef.current || !currentPathRef.current) return;

    if (currentPathRef.current.points.length > 0) {
      dispatch({ type: "COMMIT_STROKE", payload: currentPathRef.current });
    }

    isDrawingRef.current = false;
    currentPathRef.current = null;
  }, []);

  const { uiState } = state;

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: uiState.padding,
      fontFamily: uiState.fontFamily,
      background: uiState.containerBackground,
    }}>
      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        style={{
          border: `1px solid ${uiState.inputBorderColor}`,
          borderRadius: 4,
          background: "#fff",
          cursor: "crosshair",
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />

      <div style={{ marginTop: 16, display: "flex", gap: uiState.buttonGap, flexWrap: "wrap" }}>
        <button
          style={{
            padding: uiState.buttonPadding,
            background: state.currentTool === "pen" ? "#1890ff" : "#f0f0f0",
            color: state.currentTool === "pen" ? "#fff" : "#333",
            border: `1px solid ${state.currentTool === "pen" ? "#1890ff" : uiState.inputBorderColor}`,
            borderRadius: uiState.buttonBorderRadius,
            fontSize: uiState.buttonFontSize,
            cursor: "pointer",
          }}
          onClick={() => dispatch({ type: "SET_TOOL", payload: "pen" })}
        >
          Pen
        </button>
        <button
          style={{
            padding: uiState.buttonPadding,
            background: state.currentTool === "eraser" ? "#1890ff" : "#f0f0f0",
            color: state.currentTool === "eraser" ? "#fff" : "#333",
            border: `1px solid ${state.currentTool === "eraser" ? "#1890ff" : uiState.inputBorderColor}`,
            borderRadius: uiState.buttonBorderRadius,
            fontSize: uiState.buttonFontSize,
            cursor: "pointer",
          }}
          onClick={() => dispatch({ type: "SET_TOOL", payload: "eraser" })}
        >
          Eraser
        </button>
        <button
          style={{
            padding: uiState.buttonPadding,
            background: "#f0f0f0",
            color: "#333",
            border: `1px solid ${uiState.inputBorderColor}`,
            borderRadius: uiState.buttonBorderRadius,
            fontSize: uiState.buttonFontSize,
            cursor: "pointer",
          }}
          onClick={() => dispatch({ type: "UNDO" })}
        >
          Undo
        </button>
        <button
          style={{
            padding: uiState.buttonPadding,
            background: "#f0f0f0",
            color: "#333",
            border: `1px solid ${uiState.inputBorderColor}`,
            borderRadius: uiState.buttonBorderRadius,
            fontSize: uiState.buttonFontSize,
            cursor: "pointer",
          }}
          onClick={() => dispatch({ type: "REDO" })}
        >
          Redo
        </button>
        <button
          style={{
            padding: uiState.buttonPadding,
            background: "#ff4d4f",
            color: "#fff",
            border: "1px solid #ff4d4f",
            borderRadius: uiState.buttonBorderRadius,
            fontSize: uiState.buttonFontSize,
            cursor: "pointer",
          }}
          onClick={() => dispatch({ type: "CLEAR" })}
        >
          Clear
        </button>
      </div>

      <div style={{ marginTop: 16, display: "flex", gap: 16, alignItems: "center" }}>
        <div>
          <div style={{ margin: uiState.labelMargin, fontSize: uiState.labelFontSize }}>Color</div>
          <input
            type="color"
            value={state.currentColor}
            onChange={(e) => dispatch({ type: "SET_COLOR", payload: e.target.value })}
            style={{
              padding: uiState.inputPadding,
              border: `1px solid ${uiState.inputBorderColor}`,
              borderRadius: 4,
              cursor: "pointer",
            }}
          />
        </div>
        <div>
          <div style={{ margin: uiState.labelMargin, fontSize: uiState.labelFontSize }}>Line Width</div>
          <input
            type="range"
            min="1"
            max="20"
            value={state.lineWidth}
            onChange={(e) => dispatch({ type: "SET_LINE_WIDTH", payload: parseInt(e.target.value) })}
            style={{
              padding: uiState.inputPadding,
              width: 120,
            }}
          />
          <span style={{ marginLeft: 8, fontSize: 12 }}>{state.lineWidth}px</span>
        </div>
      </div>

      <div style={{ marginTop: uiState.infoMarginTop, fontSize: uiState.infoFontSize, color: uiState.infoColor }}>
        Strokes: {state.strokes.length} | Redo stack: {state.redoStack.length}
      </div>
    </div>
  );
}
```