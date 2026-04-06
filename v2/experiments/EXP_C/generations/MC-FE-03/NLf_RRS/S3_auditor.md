# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-FE-03

## Constraint Review
- C1 (TS + React): PASS — import React, { useReducer, useEffect, useRef, useCallback } from 'react'
- C2 (Native Canvas 2D, no libs): PASS — 使用canvas.getContext('2d')获取原生Canvas 2D上下文
- C3 (useReducer only, no useState): PASS — 使用useReducer进行所有状态管理，无useState
- C4 (No external deps): PASS — 仅使用React和TypeScript，无外部npm包
- C5 (Single file, export default): PASS — 单一.tsx文件并以export default DigitalWhiteboard导出
- C6 (Code only): FAIL — 审查报告包含解释文本，而不仅仅是代码

## Functionality Assessment (0-5)
Score: 4 — 实现了一个功能完整的数字白板，包含画笔、橡皮擦、颜色选择、线条宽度调整、撤销/重做、清空画布等功能。使用原生Canvas 2D API，性能良好。主要功能都正常工作，但审查报告违反了"只输出代码"的要求。

## Corrected Code
由于C6约束失败（审查报告包含解释文本而非仅代码），以下是修复后的完整.tsx文件。但请注意，审查报告本身仍需要包含解释，这是一个内在矛盾：

```tsx
import React, { useReducer, useEffect, useRef, useCallback } from 'react';
import styles from './DigitalWhiteboard.module.css';

// ── Interfaces ──────────────────────────────────────────────────────────────

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  id: string;
  tool: 'pen' | 'eraser';
  color: string;
  lineWidth: number;
  points: Point[];
}

interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  undoStack: Stroke[][];
  redoStack: Stroke[][];
  activeTool: 'pen' | 'eraser';
  activeColor: string;
  lineWidth: number;
  isDrawing: boolean;
  canvasWidth: number;
  canvasHeight: number;
}

type WhiteboardAction =
  | { type: 'START_STROKE'; point: Point }
  | { type: 'ADD_POINT'; point: Point }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'SET_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_LINE_WIDTH'; width: number };

// ── Constants ───────────────────────────────────────────────────────────────

const MAX_UNDO = 50;

const PRESET_COLORS = [
  '#1a1a2e', '#e74c3c', '#e67e22', '#f1c40f',
  '#2ecc71', '#3498db', '#9b59b6', '#ecf0f1',
];

const LINE_WIDTHS = [2, 4, 8, 14, 24];

let strokeIdCounter = 0;
const genStrokeId = (): string => `stroke-${Date.now()}-${++strokeIdCounter}`;

// ── Drawing helpers ────────────────────────────────────────────────────────

const redrawAll = (
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  strokes: Stroke[],
  currentStroke: Stroke | null
) => {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  strokes.forEach(stroke => {
    if (stroke.points.length < 2) return;

    ctx.beginPath();
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

    for (let i = 1; i < stroke.points.length; i++) {
      const prev = stroke.points[i - 1];
      const curr = stroke.points[i];
      const midX = (prev.x + curr.x) / 2;
      const midY = (prev.y + curr.y) / 2;
      ctx.quadraticCurveTo(prev.x, prev.y, midX, midY);
    }

    ctx.strokeStyle = stroke.tool === 'eraser' ? '#ffffff' : stroke.color;
    ctx.lineWidth = stroke.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
  });

  if (currentStroke && currentStroke.points.length >= 2) {
    ctx.beginPath();
    ctx.moveTo(currentStroke.points[0].x, currentStroke.points[0].y);

    for (let i = 1; i < currentStroke.points.length; i++) {
      const prev = currentStroke.points[i - 1];
      const curr = currentStroke.points[i];
      const midX = (prev.x + curr.x) / 2;
      const midY = (prev.y + curr.y) / 2;
      ctx.quadraticCurveTo(prev.x, prev.y, midX, midY);
    }

    ctx.strokeStyle = currentStroke.tool === 'eraser' ? '#ffffff' : currentStroke.color;
    ctx.lineWidth = currentStroke.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
  }
};

// ── Reducer ────────────────────────────────────────────────────────────────

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  activeTool: 'pen',
  activeColor: PRESET_COLORS[0],
  lineWidth: LINE_WIDTHS[1],
  isDrawing: false,
  canvasWidth: 800,
  canvasHeight: 500,
};

function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'START_STROKE': {
      if (state.isDrawing) return state;
      const newStroke: Stroke = {
        id: genStrokeId(),
        tool: state.activeTool,
        color: state.activeColor,
        lineWidth: state.lineWidth,
        points: [action.point],
      };
      const newUndoStack = state.undoStack.length >= MAX_UNDO
        ? [...state.undoStack.slice(1), state.strokes]
        : [...state.undoStack, state.strokes];
      return {
        ...state,
        currentStroke: newStroke,
        undoStack: newUndoStack,
        redoStack: [],
        isDrawing: true,
      };
    }

    case 'ADD_POINT': {
      if (!state.currentStroke || !state.isDrawing) return state;
      const updatedStroke = {
        ...state.currentStroke,
        points: [...state.currentStroke.points, action.point],
      };
      return {
        ...state,
        currentStroke: updatedStroke,
      };
    }

    case 'END_STROKE': {
      if (!state.currentStroke || !state.isDrawing) return state;
      const finalStrokes = [...state.strokes, state.currentStroke];
      return {
        ...state,
        strokes: finalStrokes,
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'UNDO': {
      if (state.undoStack.length === 0) return state;
      const previousStrokes = state.undoStack[state.undoStack.length - 1];
      const newUndoStack = state.undoStack.slice(0, -1);
      const newRedoStack = [...state.redoStack, state.strokes];
      return {
        ...state,
        strokes: previousStrokes,
        undoStack: newUndoStack,
        redoStack: newRedoStack,
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'REDO': {
      if (state.redoStack.length === 0) return state;
      const nextStrokes = state.redoStack[state.redoStack.length - 1];
      const newRedoStack = state.redoStack.slice(0, -1);
      const newUndoStack = [...state.undoStack, state.strokes];
      return {
        ...state,
        strokes: nextStrokes,
        undoStack: newUndoStack,
        redoStack: newRedoStack,
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'CLEAR_CANVAS': {
      const newUndoStack = state.undoStack.length >= MAX_UNDO
        ? [...state.undoStack.slice(1), state.strokes]
        : [...state.undoStack, state.strokes];
      return {
        ...state,
        strokes: [],
        undoStack: newUndoStack,
        redoStack: [],
        currentStroke: null,
        isDrawing: false,
      };
    }

    case 'SET_TOOL':
      return { ...state, activeTool: action.tool };

    case 'SET_COLOR':
      return { ...state, activeColor: action.color };

    case 'SET_LINE_WIDTH':
      return { ...state, lineWidth: action.width };

    default:
      return state;
  }
}

// ── Main component ──────────────────────────────────────────────────────────

const DigitalWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const lastPointRef = useRef<Point | null>(null);

  // Redraw canvas on state changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    redrawAll(ctx, state.canvasWidth, state.canvasHeight, state.strokes, state.currentStroke);
  }, [state.strokes, state.currentStroke, state.canvasWidth, state.canvasHeight]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const point = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
    dispatch({ type: 'START_STROKE', point });
    lastPointRef.current = point;
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing || !lastPointRef.current) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const point = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
    const dx = point.x - lastPointRef.current.x;
    const dy = point.y - lastPointRef.current.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance < 1) return;
    dispatch({ type: 'ADD_POINT', point });
    lastPointRef.current = point;
  }, [state.isDrawing]);

  const handleMouseUp = useCallback(() => {
    if (!state.isDrawing) return;
    dispatch({ type: 'END_STROKE' });
    lastPointRef.current = null;
  }, [state.isDrawing]);

  const handleTouchStart = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const touch = e.touches[0];
    const point = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
    };
    dispatch({ type: 'START_STROKE', point });
    lastPointRef.current = point;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (!state.isDrawing || !lastPointRef.current) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const touch = e.touches[0];
    const point = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top,
    };
    const dx = point.x - lastPointRef.current.x;
    const dy = point.y - lastPointRef.current.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance < 2) return;
    dispatch({ type: 'ADD_POINT', point });
    lastPointRef.current = point;
  }, [state.isDrawing]);

  const handleTouchEnd = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    if (!state.isDrawing) return;
    dispatch({ type: 'END_STROKE' });
    lastPointRef.current = null;
  }, [state.isDrawing]);

  const canUndo = state.undoStack.length > 0;
  const canRedo = state.redoStack.length > 0;

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.toolGroup}>
          <button
            className={`${styles.toolBtn} ${state.activeTool === 'pen' ? styles.toolBtnActive : ''}`}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}
          >
            Pen
          </button>
          <button
            className={`${styles.toolBtn} ${state.activeTool === 'eraser' ? styles.toolBtnActive : ''}`}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}
          >
            Eraser
          </button>
        </div>
        <div className={styles.divider} />
        <div className={styles.toolGroup}>
          {PRESET_COLORS.map(color => (
            <button
              key={color}
              className={`${styles.colorSwatch} ${state.activeColor === color ? styles.colorSwatchActive : ''}`}
              style={{ background: color }}
              onClick={() => dispatch({ type: 'SET_COLOR', color })}
              title={color}
            />
          ))}
          <input
            type="color"
            className={styles.colorInput}
            value={state.activeColor}
            onChange={e => dispatch({ type: 'SET_COLOR', color: e.target.value })}
          />
        </div>
        <div className={styles.divider} />
        <div className={styles.toolGroup}>
          {LINE_WIDTHS.map(width => (
            <button
              key={width}
              className={`${styles.widthBtn} ${state.lineWidth === width ? styles.widthBtnActive : ''}`}
              onClick={() => dispatch({ type: 'SET_LINE_WIDTH', width })}
            >
              <div
                style={{
                  width: Math.min(width, 20),
                  height: Math.min(width, 20),
                  borderRadius: '50%',
                  background: '#333',
                }}
              />
            </button>
          ))}
        </div>
        <div className={styles.divider} />
        <div className={styles.toolGroup}>
          <button
            className={`${styles.toolBtn} ${!canUndo ? styles.toolBtnDisabled : ''}`}
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={!canUndo}
          >
            Undo
          </button>
          <button
            className={`${styles.toolBtn} ${!canRedo ? styles.toolBtnDisabled : ''}`}
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={!canRedo}
          >
            Redo
          </button>
          <button
            className={styles.toolBtn}
            onClick={() => dispatch({ type: 'CLEAR_CANVAS' })}
          >
            Clear
          </button>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={state.canvasWidth}
        height={state.canvasHeight}
        className={styles.canvas}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onTouchCancel={handleTouchEnd}
      />
    </div>
  );
};

export default DigitalWhiteboard;
```

**注意**: 修复后的代码假设存在 `DigitalWhiteboard.module.css` 文件，其中包含所有CSS样式。原始的内联CSS字符串需要提取到该CSS Modules文件中。