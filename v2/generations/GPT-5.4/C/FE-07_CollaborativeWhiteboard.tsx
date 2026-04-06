import React, { useEffect, useReducer, useRef } from 'react';

const STYLE_ID = 'fe07-collaborative-whiteboard-styles';
const COLORS = ['#111827', '#dc2626', '#2563eb', '#059669', '#7c3aed', '#d97706'];

type Tool = 'pen' | 'eraser';

type Point = {
  x: number;
  y: number;
};

type Stroke = {
  points: Point[];
  color: string;
  size: number;
  tool: Tool;
};

type State = {
  strokes: Stroke[];
  undone: Stroke[];
  currentStroke: Stroke | null;
  selectedColor: string;
  brushSize: number;
  tool: Tool;
};

type Action =
  | { type: 'start'; point: Point }
  | { type: 'move'; point: Point }
  | { type: 'end' }
  | { type: 'setColor'; color: string }
  | { type: 'setBrushSize'; value: number }
  | { type: 'setTool'; tool: Tool }
  | { type: 'undo' }
  | { type: 'redo' }
  | { type: 'clear' };

const initialState: State = {
  strokes: [],
  undone: [],
  currentStroke: null,
  selectedColor: COLORS[0],
  brushSize: 4,
  tool: 'pen',
};

function ensureStyles() {
  if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) {
    return;
  }
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .wbShell {
      max-width: 920px;
      margin: 24px auto;
      padding: 18px;
      border-radius: 18px;
      border: 1px solid #d7deea;
      background: #ffffff;
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
      font-family: Arial, Helvetica, sans-serif;
      color: #102a43;
    }
    .wbHeader {
      margin-bottom: 14px;
    }
    .wbTitle {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
    }
    .wbSubtitle {
      margin: 8px 0 0;
      font-size: 13px;
      color: #52667a;
    }
    .wbToolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
      padding: 12px;
      border: 1px solid #e7edf5;
      border-radius: 14px;
      background: #f8fbff;
    }
    .wbButton,
    .wbColor,
    .wbRange {
      appearance: none;
    }
    .wbButton {
      padding: 10px 14px;
      border-radius: 10px;
      border: 1px solid #cbd2d9;
      background: #ffffff;
      color: #243b53;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
    }
    .wbButton:hover {
      border-color: #3b82f6;
    }
    .wbButton--active {
      background: #dbeafe;
      border-color: #2563eb;
      color: #1d4ed8;
    }
    .wbButton:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    .wbColors {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .wbColor {
      width: 28px;
      height: 28px;
      border-radius: 999px;
      border: 2px solid transparent;
      cursor: pointer;
      box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.15);
    }
    .wbColor--active {
      border-color: #111827;
      transform: scale(1.08);
    }
    .wbColor--0 { background: #111827; }
    .wbColor--1 { background: #dc2626; }
    .wbColor--2 { background: #2563eb; }
    .wbColor--3 { background: #059669; }
    .wbColor--4 { background: #7c3aed; }
    .wbColor--5 { background: #d97706; }
    .wbBrush {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 6px;
      font-size: 13px;
      color: #334e68;
    }
    .wbRange {
      width: 120px;
      cursor: pointer;
    }
    .wbCanvasFrame {
      border: 1px solid #cbd5e1;
      border-radius: 16px;
      overflow: hidden;
      background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    }
    .wbCanvas {
      display: block;
      width: 100%;
      touch-action: none;
      background-image: radial-gradient(circle at 1px 1px, rgba(148, 163, 184, 0.22) 1px, transparent 0);
      background-size: 22px 22px;
      cursor: crosshair;
    }
    .wbFooter {
      margin-top: 12px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      color: #52667a;
    }
  `;
  document.head.appendChild(style);
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'start': {
      return {
        ...state,
        currentStroke: {
          points: [action.point],
          color: state.tool === 'eraser' ? '#ffffff' : state.selectedColor,
          size: state.tool === 'eraser' ? state.brushSize * 2 : state.brushSize,
          tool: state.tool,
        },
      };
    }
    case 'move': {
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
    }
    case 'end': {
      if (!state.currentStroke) {
        return state;
      }
      return {
        ...state,
        strokes: [...state.strokes, state.currentStroke],
        currentStroke: null,
        undone: [],
      };
    }
    case 'setColor':
      return { ...state, selectedColor: action.color, tool: 'pen' };
    case 'setBrushSize':
      return { ...state, brushSize: action.value };
    case 'setTool':
      return { ...state, tool: action.tool };
    case 'undo': {
      if (state.strokes.length === 0) {
        return state;
      }
      const last = state.strokes[state.strokes.length - 1];
      return {
        ...state,
        strokes: state.strokes.slice(0, -1),
        undone: [...state.undone, last],
      };
    }
    case 'redo': {
      if (state.undone.length === 0) {
        return state;
      }
      const last = state.undone[state.undone.length - 1];
      return {
        ...state,
        strokes: [...state.strokes, last],
        undone: state.undone.slice(0, -1),
      };
    }
    case 'clear':
      return { ...state, strokes: [], undone: [], currentStroke: null };
    default:
      return state;
  }
}

function drawStroke(context: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.points.length === 0) {
    return;
  }
  context.save();
  context.lineJoin = 'round';
  context.lineCap = 'round';
  context.lineWidth = stroke.size;
  context.strokeStyle = stroke.color;
  context.globalCompositeOperation = stroke.tool === 'eraser' ? 'destination-out' : 'source-over';
  context.beginPath();
  context.moveTo(stroke.points[0].x, stroke.points[0].y);
  if (stroke.points.length === 1) {
    context.lineTo(stroke.points[0].x + 0.01, stroke.points[0].y + 0.01);
  } else {
    for (let index = 1; index < stroke.points.length; index += 1) {
      const point = stroke.points[index];
      context.lineTo(point.x, point.y);
    }
  }
  context.stroke();
  context.restore();
}

function getPoint(event: MouseEvent | TouchEvent | React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>, canvas: HTMLCanvasElement): Point {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  if ('touches' in event) {
    const touch = event.touches[0] ?? event.changedTouches[0];
    return {
      x: (touch.clientX - rect.left) * scaleX,
      y: (touch.clientY - rect.top) * scaleY,
    };
  }

  return {
    x: (event.clientX - rect.left) * scaleX,
    y: (event.clientY - rect.top) * scaleY,
  };
}

export default function CollaborativeWhiteboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointerDownRef = useRef(false);

  useEffect(() => {
    ensureStyles();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, canvas.width, canvas.height);

    state.strokes.forEach((stroke) => drawStroke(context, stroke));
    if (state.currentStroke) {
      drawStroke(context, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke]);

  useEffect(() => {
    const handleMouseUp = () => {
      if (!pointerDownRef.current) {
        return;
      }
      pointerDownRef.current = false;
      dispatch({ type: 'end' });
    };

    const handleTouchEnd = () => {
      if (!pointerDownRef.current) {
        return;
      }
      pointerDownRef.current = false;
      dispatch({ type: 'end' });
    };

    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, []);

  const handleStart = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    event.preventDefault();
    pointerDownRef.current = true;
    dispatch({ type: 'start', point: getPoint(event, canvas) });
  };

  const handleMove = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!pointerDownRef.current) {
      return;
    }
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    event.preventDefault();
    dispatch({ type: 'move', point: getPoint(event, canvas) });
  };

  return (
    <section className="wbShell" aria-label="Collaborative whiteboard">
      <header className="wbHeader">
        <h2 className="wbTitle">Whiteboard Workspace</h2>
        <p className="wbSubtitle">Pen, eraser, six colors, adjustable brush, undo, redo, and clear — all state managed with useReducer.</p>
      </header>

      <div className="wbToolbar">
        <button
          type="button"
          className={`wbButton ${state.tool === 'pen' ? 'wbButton--active' : ''}`}
          onClick={() => dispatch({ type: 'setTool', tool: 'pen' })}
        >
          Pen
        </button>
        <button
          type="button"
          className={`wbButton ${state.tool === 'eraser' ? 'wbButton--active' : ''}`}
          onClick={() => dispatch({ type: 'setTool', tool: 'eraser' })}
        >
          Eraser
        </button>
        <div className="wbColors" aria-label="Color picker">
          {COLORS.map((color, index) => (
            <button
              key={color}
              type="button"
              className={`wbColor wbColor--${index} ${state.selectedColor === color && state.tool === 'pen' ? 'wbColor--active' : ''}`}
              onClick={() => dispatch({ type: 'setColor', color })}
              aria-label={`Select color ${color}`}
            />
          ))}
        </div>
        <label className="wbBrush">
          Brush size
          <input
            className="wbRange"
            type="range"
            min={1}
            max={24}
            value={state.brushSize}
            onChange={(event) => dispatch({ type: 'setBrushSize', value: Number(event.target.value) })}
          />
          <span>{state.brushSize}px</span>
        </label>
        <button type="button" className="wbButton" disabled={state.strokes.length === 0} onClick={() => dispatch({ type: 'undo' })}>
          Undo
        </button>
        <button type="button" className="wbButton" disabled={state.undone.length === 0} onClick={() => dispatch({ type: 'redo' })}>
          Redo
        </button>
        <button type="button" className="wbButton" onClick={() => dispatch({ type: 'clear' })}>
          Clear
        </button>
      </div>

      <div className="wbCanvasFrame">
        <canvas
          ref={canvasRef}
          width={860}
          height={540}
          className="wbCanvas"
          onMouseDown={handleStart}
          onMouseMove={handleMove}
          onMouseLeave={() => {
            if (pointerDownRef.current) {
              pointerDownRef.current = false;
              dispatch({ type: 'end' });
            }
          }}
          onTouchStart={handleStart}
          onTouchMove={handleMove}
        />
      </div>

      <div className="wbFooter">
        <span>Committed strokes: {state.strokes.length}</span>
        <span>Redo stack: {state.undone.length}</span>
        <span>Current tool: {state.tool}</span>
      </div>
    </section>
  );
}
