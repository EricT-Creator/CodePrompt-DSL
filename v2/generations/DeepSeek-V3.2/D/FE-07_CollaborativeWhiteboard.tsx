import React, { useReducer, useRef, useEffect, useCallback } from 'react';

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  color: string;
  width: number;
  type: 'draw' | 'erase';
  timestamp: number;
}

interface WhiteboardState {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  undoStack: Stroke[][];
  redoStack: Stroke[][];
  selectedColor: string;
  selectedWidth: number;
  isDrawing: boolean;
  tool: 'brush' | 'eraser';
}

type WhiteboardAction =
  | { type: 'START_DRAWING'; payload: { x: number; y: number; color?: string; width?: number; tool?: 'brush' | 'eraser' } }
  | { type: 'CONTINUE_DRAWING'; payload: Point }
  | { type: 'STOP_DRAWING' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_WIDTH'; payload: number }
  | { type: 'SET_TOOL'; payload: 'brush' | 'eraser' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'UNDO' }
  | { type: 'REDO' };

const initialState: WhiteboardState = {
  strokes: [],
  currentStroke: null,
  undoStack: [],
  redoStack: [],
  selectedColor: '#000000',
  selectedWidth: 3,
  isDrawing: false,
  tool: 'brush'
};

const whiteboardReducer = (state: WhiteboardState, action: WhiteboardAction): WhiteboardState => {
  switch (action.type) {
    case 'START_DRAWING': {
      const { x, y } = action.payload;
      const color = action.payload.color || state.selectedColor;
      const width = action.payload.width || state.selectedWidth;
      const tool = action.payload.tool || state.tool;
      
      const newStroke: Stroke = {
        points: [{ x, y }],
        color: tool === 'eraser' ? '#FFFFFF' : color,
        width: tool === 'eraser' ? state.selectedWidth * 3 : width,
        type: tool === 'eraser' ? 'erase' : 'draw',
        timestamp: Date.now()
      };
      
      return {
        ...state,
        currentStroke: newStroke,
        isDrawing: true,
        tool
      };
    }
    
    case 'CONTINUE_DRAWING': {
      if (!state.currentStroke) return state;
      
      const newPoint = action.payload;
      const updatedStroke = {
        ...state.currentStroke,
        points: [...state.currentStroke.points, newPoint]
      };
      
      return {
        ...state,
        currentStroke: updatedStroke
      };
    }
    
    case 'STOP_DRAWING': {
      if (!state.currentStroke) return state;
      
      const newStrokes = [...state.strokes, state.currentStroke];
      const newUndoStack = [...state.undoStack, state.strokes];
      
      return {
        ...state,
        strokes: newStrokes,
        currentStroke: null,
        undoStack: newUndoStack,
        redoStack: [],
        isDrawing: false
      };
    }
    
    case 'SET_COLOR':
      return {
        ...state,
        selectedColor: action.payload
      };
    
    case 'SET_WIDTH':
      return {
        ...state,
        selectedWidth: action.payload
      };
    
    case 'SET_TOOL':
      return {
        ...state,
        tool: action.payload,
        selectedColor: action.payload === 'eraser' ? '#000000' : state.selectedColor
      };
    
    case 'CLEAR_CANVAS': {
      if (state.strokes.length === 0) return state;
      
      return {
        ...initialState,
        selectedColor: state.selectedColor,
        selectedWidth: state.selectedWidth,
        tool: state.tool,
        undoStack: [...state.undoStack, state.strokes],
        redoStack: []
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
        redoStack: newRedoStack
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
        redoStack: newRedoStack
      };
    }
    
    default:
      return state;
  }
};

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(whiteboardReducer, initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const colors = [
    '#000000', '#FF3B30', '#FF9500', '#FFCC00',
    '#4CD964', '#5AC8FA', '#007AFF', '#5856D6',
    '#FF2D55', '#8E8E93', '#C7C7CC', '#EFEFF4'
  ];
  
  const brushWidths = [1, 3, 5, 8, 12, 20];
  
  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke) => {
    if (stroke.points.length < 2) return;
    
    ctx.strokeStyle = stroke.color;
    ctx.lineWidth = stroke.width;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    if (stroke.type === 'erase') {
      ctx.globalCompositeOperation = 'destination-out';
    } else {
      ctx.globalCompositeOperation = 'source-over';
    }
    
    ctx.beginPath();
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    
    for (let i = 1; i < stroke.points.length; i++) {
      const point = stroke.points[i];
      ctx.lineTo(point.x, point.y);
    }
    
    ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }, []);
  
  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    state.strokes.forEach(stroke => {
      drawStroke(ctx, stroke);
    });
    
    if (state.currentStroke) {
      drawStroke(ctx, state.currentStroke);
    }
  }, [state.strokes, state.currentStroke, drawStroke]);
  
  const getCanvasCoordinates = useCallback((clientX: number, clientY: number): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY
    };
  }, []);
  
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const point = getCanvasCoordinates(e.clientX, e.clientY);
    if (!point) return;
    
    dispatch({
      type: 'START_DRAWING',
      payload: {
        x: point.x,
        y: point.y,
        color: state.selectedColor,
        width: state.selectedWidth,
        tool: state.tool
      }
    });
  }, [getCanvasCoordinates, state.selectedColor, state.selectedWidth, state.tool]);
  
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!state.isDrawing) return;
    
    const point = getCanvasCoordinates(e.clientX, e.clientY);
    if (!point) return;
    
    dispatch({ type: 'CONTINUE_DRAWING', payload: point });
  }, [state.isDrawing, getCanvasCoordinates]);
  
  const handleMouseUp = useCallback(() => {
    if (!state.isDrawing) return;
    
    dispatch({ type: 'STOP_DRAWING' });
  }, [state.isDrawing]);
  
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    const touch = e.touches[0];
    const point = getCanvasCoordinates(touch.clientX, touch.clientY);
    if (!point) return;
    
    dispatch({
      type: 'START_DRAWING',
      payload: {
        x: point.x,
        y: point.y,
        color: state.selectedColor,
        width: state.selectedWidth,
        tool: state.tool
      }
    });
  }, [getCanvasCoordinates, state.selectedColor, state.selectedWidth, state.tool]);
  
  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    if (!state.isDrawing) return;
    
    const touch = e.touches[0];
    const point = getCanvasCoordinates(touch.clientX, touch.clientY);
    if (!point) return;
    
    dispatch({ type: 'CONTINUE_DRAWING', payload: point });
  }, [state.isDrawing, getCanvasCoordinates]);
  
  const handleTouchEnd = useCallback(() => {
    if (!state.isDrawing) return;
    
    dispatch({ type: 'STOP_DRAWING' });
  }, [state.isDrawing]);
  
  useEffect(() => {
    redrawCanvas();
  }, [redrawCanvas]);
  
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height - 60;
      redrawCanvas();
    };
    
    handleResize();
    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [redrawCanvas]);
  
  const handleClearCanvas = () => {
    if (window.confirm('确定要清除所有内容吗？')) {
      dispatch({ type: 'CLEAR_CANVAS' });
    }
  };
  
  const canUndo = state.undoStack.length > 0;
  const canRedo = state.redoStack.length > 0;
  
  return (
    <div style={styles.container} ref={containerRef}>
      <h2 style={styles.title}>协作白板</h2>
      
      <div style={styles.toolbar}>
        <div style={styles.toolGroup}>
          <button
            style={{
              ...styles.toolButton,
              ...(state.tool === 'brush' ? styles.activeToolButton : {})
            }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'brush' })}
            title="画笔"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
          </button>
          
          <button
            style={{
              ...styles.toolButton,
              ...(state.tool === 'eraser' ? styles.activeToolButton : {})
            }}
            onClick={() => dispatch({ type: 'SET_TOOL', payload: 'eraser' })}
            title="橡皮擦"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16.24 3.56L21.19 8.5c.78.78.78 2.05 0 2.83L12 20.5c-1.29 1.29-3.05 2.01-4.9 2.01H3v-4.1c0-1.85.72-3.61 2.01-4.9l9.19-9.19c.78-.78 2.05-.78 2.83 0zM5.92 19.5c-.59.59-1.54.59-2.12 0-.59-.59-.59-1.54 0-2.12.59-.59 1.54-.59 2.12 0 .59.59.59 1.54 0 2.12z"/>
            </svg>
          </button>
        </div>
        
        <div style={styles.colorPicker}>
          {colors.map(color => (
            <button
              key={color}
              style={{
                ...styles.colorButton,
                backgroundColor: color,
                border: color === state.selectedColor ? '3px solid #333' : '1px solid #ccc',
                transform: color === state.selectedColor ? 'scale(1.1)' : 'scale(1)'
              }}
              onClick={() => dispatch({ type: 'SET_COLOR', payload: color })}
              title={color}
            />
          ))}
        </div>
        
        <div style={styles.widthPicker}>
          {brushWidths.map(width => (
            <button
              key={width}
              style={{
                ...styles.widthButton,
                width: width * 2,
                height: width * 2,
                border: width === state.selectedWidth ? '2px solid #007AFF' : '1px solid #ccc'
              }}
              onClick={() => dispatch({ type: 'SET_WIDTH', payload: width })}
              title={`笔刷大小: ${width}px`}
            />
          ))}
        </div>
        
        <div style={styles.actionButtons}>
          <button
            style={{
              ...styles.actionButton,
              ...(!canUndo ? styles.disabledButton : {})
            }}
            onClick={() => canUndo && dispatch({ type: 'UNDO' })}
            disabled={!canUndo}
            title="撤销"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/>
            </svg>
          </button>
          
          <button
            style={{
              ...styles.actionButton,
              ...(!canRedo ? styles.disabledButton : {})
            }}
            onClick={() => canRedo && dispatch({ type: 'REDO' })}
            disabled={!canRedo}
            title="重做"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.4 10.6C16.55 9 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.06-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/>
            </svg>
          </button>
          
          <button
            style={styles.clearButton}
            onClick={handleClearCanvas}
            title="清除画布"
          >
            清除
          </button>
        </div>
      </div>
      
      <div style={styles.canvasContainer}>
        <canvas
          ref={canvasRef}
          style={styles.canvas}
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
      
      <div style={styles.statusBar}>
        <div style={styles.statusItem}>
          <span style={styles.statusLabel}>工具:</span>
          <span style={styles.statusValue}>
            {state.tool === 'brush' ? '画笔' : '橡皮擦'}
          </span>
        </div>
        
        <div style={styles.statusItem}>
          <span style={styles.statusLabel}>颜色:</span>
          <div style={{
            ...styles.colorIndicator,
            backgroundColor: state.selectedColor
          }} />
          <span style={styles.statusValue}>{state.selectedColor}</span>
        </div>
        
        <div style={styles.statusItem}>
          <span style={styles.statusLabel}>大小:</span>
          <span style={styles.statusValue}>{state.selectedWidth}px</span>
        </div>
        
        <div style={styles.statusItem}>
          <span style={styles.statusLabel}>笔画数:</span>
          <span style={styles.statusValue}>{state.strokes.length}</span>
        </div>
        
        <div style={styles.statusItem}>
          <span style={styles.statusLabel}>可撤销:</span>
          <span style={styles.statusValue}>{state.undoStack.length}</span>
        </div>
        
        <div style={styles.statusItem}>
          <span style={styles.statusLabel}>可重做:</span>
          <span style={styles.statusValue}>{state.redoStack.length}</span>
        </div>
      </div>
      
      <div style={styles.instructions}>
        <p>使用说明：</p>
        <ul style={styles.instructionList}>
          <li>鼠标或手指在画布上拖动进行绘制</li>
          <li>点击上方颜色选择器切换画笔颜色（至少5色）</li>
          <li>选择笔刷大小（1-20px）</li>
          <li>使用橡皮擦擦除内容</li>
          <li>撤销/重做支持多步操作</li>
          <li>所有状态使用useReducer管理</li>
        </ul>
      </div>
    </div>
  );
};

const styles = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '1000px',
    margin: '0 auto',
    padding: '20px',
    backgroundColor: '#f5f5f5',
    borderRadius: '10px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
    height: 'calc(100vh - 60px)',
    display: 'flex',
    flexDirection: 'column' as const
  } as React.CSSProperties,
  
  title: {
    textAlign: 'center' as const,
    color: '#333',
    marginBottom: '20px',
    fontSize: '28px',
    fontWeight: 'bold' as const
  } as React.CSSProperties,
  
  toolbar: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '15px',
    padding: '15px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    marginBottom: '20px',
    alignItems: 'center'
  } as React.CSSProperties,
  
  toolGroup: {
    display: 'flex',
    gap: '8px'
  } as React.CSSProperties,
  
  toolButton: {
    padding: '10px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    backgroundColor: 'white',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease'
  } as React.CSSProperties,
  
  activeToolButton: {
    backgroundColor: '#007AFF',
    color: 'white',
    borderColor: '#007AFF'
  } as React.CSSProperties,
  
  colorPicker: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
    flex: 1,
    justifyContent: 'center'
  } as React.CSSProperties,
  
  colorButton: {
    width: '30px',
    height: '30px',
    borderRadius: '50%',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    border: 'none'
  } as React.CSSProperties,
  
  widthPicker: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center'
  } as React.CSSProperties,
  
  widthButton: {
    borderRadius: '50%',
    cursor: 'pointer',
    backgroundColor: '#333',
    transition: 'all 0.2s ease',
    border: 'none'
  } as React.CSSProperties,
  
  actionButtons: {
    display: 'flex',
    gap: '10px'
  } as React.CSSProperties,
  
  actionButton: {
    padding: '10px 15px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    backgroundColor: 'white',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease',
    color: '#333'
  } as React.CSSProperties,
  
  disabledButton: {
    opacity: 0.5,
    cursor: 'not-allowed'
  } as React.CSSProperties,
  
  clearButton: {
    padding: '10px 20px',
    border: '1px solid #FF3B30',
    borderRadius: '6px',
    backgroundColor: '#FF3B30',
    color: 'white',
    cursor: 'pointer',
    fontWeight: 'bold' as const,
    transition: 'all 0.2s ease'
  } as React.CSSProperties,
  
  canvasContainer: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    marginBottom: '20px'
  } as React.CSSProperties,
  
  canvas: {
    width: '100%',
    height: '100%',
    display: 'block',
    cursor: 'crosshair'
  } as React.CSSProperties,
  
  statusBar: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '20px',
    padding: '15px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    marginBottom: '20px',
    justifyContent: 'space-between'
  } as React.CSSProperties,
  
  statusItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  } as React.CSSProperties,
  
  statusLabel: {
    color: '#666',
    fontWeight: 'bold' as const,
    fontSize: '14px'
  } as React.CSSProperties,
  
  statusValue: {
    color: '#333',
    fontWeight: '500' as const,
    fontSize: '14px'
  } as React.CSSProperties,
  
  colorIndicator: {
    width: '20px',
    height: '20px',
    borderRadius: '4px',
    border: '1px solid #ddd'
  } as React.CSSProperties,
  
  instructions: {
    padding: '15px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  } as React.CSSProperties,
  
  instructionList: {
    margin: '10px 0 0 0',
    paddingLeft: '20px',
    color: '#666',
    fontSize: '14px',
    lineHeight: '1.6'
  } as React.CSSProperties
};

export default CollaborativeWhiteboard;