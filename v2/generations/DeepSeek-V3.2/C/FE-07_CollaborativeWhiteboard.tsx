import React, { useRef, useEffect, useReducer, MouseEvent } from 'react';

type Point = [number, number];
type Stroke = {
  points: Point[];
  color: string;
  width: number;
  type: 'pen' | 'eraser';
};

type Action =
  | { type: 'START_STROKE'; x: number; y: number; color: string; width: number; tool: 'pen' | 'eraser' }
  | { type: 'CONTINUE_STROKE'; x: number; y: number }
  | { type: 'END_STROKE' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }
  | { type: 'CHANGE_TOOL'; tool: 'pen' | 'eraser' }
  | { type: 'CHANGE_COLOR'; color: string }
  | { type: 'CHANGE_WIDTH'; width: number };

interface State {
  strokes: Stroke[];
  history: Stroke[][];
  historyIndex: number;
  currentStroke: Stroke | null;
  isDrawing: boolean;
  tool: 'pen' | 'eraser';
  color: string;
  width: number;
}

const initialState: State = {
  strokes: [],
  history: [[]],
  historyIndex: 0,
  currentStroke: null,
  isDrawing: false,
  tool: 'pen',
  color: '#000000',
  width: 3,
};

const colors = [
  '#000000', '#ff0000', '#00ff00', '#0000ff', 
  '#ffff00', '#ff00ff', '#00ffff', '#ff9900',
  '#9900ff', '#009900', '#990000', '#000099'
];

const widths = [1, 2, 3, 5, 8, 12];

function whiteboardReducer(state: State, action: Action): State {
  switch (action.type) {
    case 'START_STROKE': {
      const newStroke: Stroke = {
        points: [[action.x, action.y]],
        color: action.color,
        width: action.width,
        type: action.tool,
      };
      
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push([...state.strokes, newStroke]);
      
      return {
        ...state,
        currentStroke: newStroke,
        isDrawing: true,
        strokes: [...state.strokes, newStroke],
        history: newHistory,
        historyIndex: state.historyIndex + 1,
      };
    }
    
    case 'CONTINUE_STROKE': {
      if (!state.currentStroke) return state;
      
      const updatedStroke = {
        ...state.currentStroke,
        points: [...state.currentStroke.points, [action.x, action.y]],
      };
      
      const updatedStrokes = [
        ...state.strokes.slice(0, -1),
        updatedStroke,
      ];
      
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory[state.historyIndex] = updatedStrokes;
      
      return {
        ...state,
        currentStroke: updatedStroke,
        strokes: updatedStrokes,
        history: newHistory,
      };
    }
    
    case 'END_STROKE': {
      return {
        ...state,
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'UNDO': {
      if (state.historyIndex <= 0) return state;
      
      return {
        ...state,
        historyIndex: state.historyIndex - 1,
        strokes: state.history[state.historyIndex - 1],
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'REDO': {
      if (state.historyIndex >= state.history.length - 1) return state;
      
      return {
        ...state,
        historyIndex: state.historyIndex + 1,
        strokes: state.history[state.historyIndex + 1],
        currentStroke: null,
        isDrawing: false,
      };
    }
    
    case 'CLEAR': {
      return {
        ...initialState,
        history: [[]],
        tool: state.tool,
        color: state.color,
        width: state.width,
      };
    }
    
    case 'CHANGE_TOOL': {
      return {
        ...state,
        tool: action.tool,
      };
    }
    
    case 'CHANGE_COLOR': {
      return {
        ...state,
        color: action.color,
      };
    }
    
    case 'CHANGE_WIDTH': {
      return {
        ...state,
        width: action.width,
      };
    }
    
    default:
      return state;
  }
}

const CollaborativeWhiteboard: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  
  const getCanvasCoordinates = (e: MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };
  
  const handleMouseDown = (e: MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = getCanvasCoordinates(e);
    dispatch({
      type: 'START_STROKE',
      x,
      y,
      color: state.color,
      width: state.width,
      tool: state.tool,
    });
  };
  
  const handleMouseMove = (e: MouseEvent<HTMLCanvasElement>) => {
    if (!state.isDrawing) return;
    
    const { x, y } = getCanvasCoordinates(e);
    dispatch({ type: 'CONTINUE_STROKE', x, y });
  };
  
  const handleMouseUp = () => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  };
  
  const handleMouseLeave = () => {
    if (state.isDrawing) {
      dispatch({ type: 'END_STROKE' });
    }
  };
  
  const drawStroke = (ctx: CanvasRenderingContext2D, stroke: Stroke) => {
    if (stroke.points.length < 2) return;
    
    ctx.beginPath();
    ctx.moveTo(stroke.points[0][0], stroke.points[0][1]);
    
    for (let i = 1; i < stroke.points.length; i++) {
      ctx.lineTo(stroke.points[i][0], stroke.points[i][1]);
    }
    
    if (stroke.type === 'pen') {
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.stroke();
    } else {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = stroke.width * 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.stroke();
    }
  };
  
  const drawGrid = (ctx: CanvasRenderingContext2D) => {
    const gridSize = 20;
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 0.5;
    
    for (let x = 0; x < ctx.canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, ctx.canvas.height);
      ctx.stroke();
    }
    
    for (let y = 0; y < ctx.canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(ctx.canvas.width, y);
      ctx.stroke();
    }
  };
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    drawGrid(ctx);
    
    state.strokes.forEach(stroke => {
      drawStroke(ctx, stroke);
    });
    
    if (state.currentStroke && state.currentStroke.points.length >= 2) {
      drawStroke(ctx, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke]);
  
  const canUndo = state.historyIndex > 0;
  const canRedo = state.historyIndex < state.history.length - 1;
  
  return (
    <div className="whiteboard-container">
      <h2>协作白板</h2>
      
      <div className="whiteboard-controls">
        <div className="tool-selector">
          <button
            className={`tool-button ${state.tool === 'pen' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'CHANGE_TOOL', tool: 'pen' })}
          >
            <span className="tool-icon">✎</span>
            <span>画笔</span>
          </button>
          <button
            className={`tool-button ${state.tool === 'eraser' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'CHANGE_TOOL', tool: 'eraser' })}
          >
            <span className="tool-icon">◻</span>
            <span>橡皮</span>
          </button>
        </div>
        
        <div className="color-picker">
          <div className="color-label">颜色:</div>
          <div className="color-grid">
            {colors.map(color => (
              <button
                key={color}
                className={`color-button ${state.color === color ? 'selected' : ''}`}
                style={{ backgroundColor: color }}
                onClick={() => dispatch({ type: 'CHANGE_COLOR', color })}
                title={color}
              />
            ))}
          </div>
        </div>
        
        <div className="width-picker">
          <div className="width-label">粗细:</div>
          <div className="width-grid">
            {widths.map(width => (
              <button
                key={width}
                className={`width-button ${state.width === width ? 'selected' : ''}`}
                onClick={() => dispatch({ type: 'CHANGE_WIDTH', width })}
              >
                <div 
                  className="width-preview" 
                  style={{ 
                    width: width * 4, 
                    height: width * 4,
                    backgroundColor: state.color,
                  }}
                />
                <span className="width-text">{width}px</span>
              </button>
            ))}
          </div>
        </div>
        
        <div className="action-buttons">
          <button
            className="action-button undo"
            onClick={() => dispatch({ type: 'UNDO' })}
            disabled={!canUndo}
          >
            ↶ 撤销
          </button>
          <button
            className="action-button redo"
            onClick={() => dispatch({ type: 'REDO' })}
            disabled={!canRedo}
          >
            ↷ 重做
          </button>
          <button
            className="action-button clear"
            onClick={() => dispatch({ type: 'CLEAR' })}
          >
            ✕ 清空
          </button>
        </div>
        
        <div className="status-info">
          <div className="status-item">
            当前工具: <span className="status-value">{state.tool === 'pen' ? '画笔' : '橡皮'}</span>
          </div>
          <div className="status-item">
            当前颜色: <span className="status-value" style={{ color: state.color }}>{state.color}</span>
          </div>
          <div className="status-item">
            笔画数: <span className="status-value">{state.strokes.length}</span>
          </div>
          <div className="status-item">
            历史记录: <span className="status-value">{state.historyIndex}/{state.history.length - 1}</span>
          </div>
        </div>
      </div>
      
      <div className="canvas-wrapper">
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          className="whiteboard-canvas"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        />
        <div className="canvas-hint">
          点击并拖动鼠标进行绘制。使用撤销/重做管理历史记录。
        </div>
      </div>

      <style>{`
        .whiteboard-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 900px;
          margin: 0 auto;
          padding: 20px;
        }
        
        h2 {
          color: #333;
          margin-bottom: 20px;
          text-align: center;
        }
        
        .whiteboard-controls {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 20px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        
        .tool-selector {
          display: flex;
          gap: 10px;
          margin-bottom: 10px;
        }
        
        .tool-button {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 10px 16px;
          border: 2px solid #e0e0e0;
          border-radius: 6px;
          background: white;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 14px;
          min-width: 80px;
        }
        
        .tool-button:hover {
          border-color: #1976d2;
          background: #e3f2fd;
        }
        
        .tool-button.active {
          border-color: #1976d2;
          background: #bbdefb;
          font-weight: 600;
        }
        
        .tool-icon {
          font-size: 20px;
          margin-bottom: 5px;
        }
        
        .color-picker, .width-picker {
          margin-bottom: 15px;
        }
        
        .color-label, .width-label {
          font-weight: 600;
          color: #555;
          margin-bottom: 8px;
          font-size: 14px;
        }
        
        .color-grid {
          display: grid;
          grid-template-columns: repeat(6, 1fr);
          gap: 6px;
        }
        
        .color-button {
          width: 28px;
          height: 28px;
          border: 2px solid transparent;
          border-radius: 50%;
          cursor: pointer;
          transition: transform 0.2s, border-color 0.2s;
          padding: 0;
        }
        
        .color-button:hover {
          transform: scale(1.1);
        }
        
        .color-button.selected {
          border-color: #333;
          transform: scale(1.2);
        }
        
        .width-grid {
          display: flex;
          gap: 10px;
          align-items: center;
          flex-wrap: wrap;
        }
        
        .width-button {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 6px 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          transition: all 0.2s;
          min-width: 60px;
        }
        
        .width-button:hover {
          border-color: #1976d2;
          background: #f5f5f5;
        }
        
        .width-button.selected {
          border-color: #1976d2;
          background: #e3f2fd;
          font-weight: 500;
        }
        
        .width-preview {
          border-radius: 50%;
          margin-bottom: 4px;
        }
        
        .width-text {
          font-size: 11px;
          color: #666;
        }
        
        .action-buttons {
          display: flex;
          gap: 10px;
          margin-bottom: 15px;
        }
        
        .action-button {
          padding: 10px 16px;
          border: none;
          border-radius: 4px;
          background: #1976d2;
          color: white;
          cursor: pointer;
          font-size: 14px;
          transition: background-color 0.2s;
          flex: 1;
        }
        
        .action-button:hover:not(:disabled) {
          background: #1565c0;
        }
        
        .action-button:disabled {
          background: #bdbdbd;
          cursor: not-allowed;
          opacity: 0.6;
        }
        
        .action-button.undo {
          background: #ff9800;
        }
        
        .action-button.undo:hover:not(:disabled) {
          background: #f57c00;
        }
        
        .action-button.redo {
          background: #4caf50;
        }
        
        .action-button.redo:hover:not(:disabled) {
          background: #388e3c;
        }
        
        .action-button.clear {
          background: #f44336;
        }
        
        .action-button.clear:hover:not(:disabled) {
          background: #d32f2f;
        }
        
        .status-info {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          background: white;
          padding: 12px;
          border-radius: 6px;
          border: 1px solid #e0e0e0;
        }
        
        .status-item {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          color: #666;
        }
        
        .status-value {
          font-weight: 500;
          color: #333;
        }
        
        .canvas-wrapper {
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          overflow: hidden;
          background: white;
          padding: 10px;
        }
        
        .whiteboard-canvas {
          display: block;
          width: 100%;
          height: 500px;
          background: white;
          border: 1px solid #ccc;
          cursor: crosshair;
        }
        
        .canvas-hint {
          text-align: center;
          color: #666;
          font-size: 12px;
          margin-top: 10px;
          font-style: italic;
        }
        
        @media (max-width: 768px) {
          .whiteboard-controls {
            grid-template-columns: 1fr;
          }
          
          .whiteboard-canvas {
            height: 400px;
          }
        }
      `}</style>
    </div>
  );
};

export default CollaborativeWhiteboard;