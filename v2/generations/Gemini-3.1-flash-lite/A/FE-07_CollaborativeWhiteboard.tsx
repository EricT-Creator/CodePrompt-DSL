import React, { useReducer, useRef, useEffect } from 'react';

type State = {
  drawing: boolean;
  color: string;
  size: number;
  tool: 'pen' | 'eraser';
  history: string[];
};

type Action =
  | { type: 'DRAWING_START' }
  | { type: 'DRAWING_STOP' }
  | { type: 'SET_COLOR', color: string }
  | { type: 'SET_SIZE', size: number }
  | { type: 'SET_TOOL', tool: 'pen' | 'eraser' }
  | { type: 'UNDO' }
  | { type: 'CLEAR' };

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'DRAWING_START': return { ...state, drawing: true };
    case 'DRAWING_STOP': return { ...state, drawing: false };
    case 'SET_COLOR': return { ...state, color: action.color };
    case 'SET_SIZE': return { ...state, size: action.size };
    case 'SET_TOOL': return { ...state, tool: action.tool };
    case 'UNDO': return { ...state, history: state.history.slice(0, -1) };
    case 'CLEAR': return { ...state, history: [] };
    default: return state;
  }
};

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, {
    drawing: false,
    color: '#000000',
    size: 5,
    tool: 'pen',
    history: [],
  });
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    dispatch({ type: 'DRAWING_START' });
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    ctx.beginPath();
    ctx.moveTo(e.nativeEvent.offsetX, e.nativeEvent.offsetY);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!state.drawing) return;
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    ctx.strokeStyle = state.tool === 'pen' ? state.color : '#ffffff';
    ctx.lineWidth = state.size;
    ctx.lineTo(e.nativeEvent.offsetX, e.nativeEvent.offsetY);
    ctx.stroke();
  };

  return (
    <div>
      <div style={{ marginBottom: '10px' }}>
        <button onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}>Pen</button>
        <button onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}>Eraser</button>
        <input type="color" onChange={(e) => dispatch({ type: 'SET_COLOR', color: e.target.value })} />
        <input type="range" min="1" max="20" onChange={(e) => dispatch({ type: 'SET_SIZE', size: parseInt(e.target.value) })} />
        <button onClick={() => dispatch({ type: 'UNDO' })}>Undo</button>
        <button onClick={() => dispatch({ type: 'CLEAR' })}>Clear</button>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{ border: '1px solid black' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={() => dispatch({ type: 'DRAWING_STOP' })}
      />
    </div>
  );
};

export default CollaborativeWhiteboard;
