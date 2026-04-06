import React, { useReducer, useRef, useEffect } from 'react';

type Point = { x: number; y: number };
type Tool = 'pen' | 'eraser';
type State = {
  paths: { points: Point[]; color: string; size: number; tool: Tool }[];
  currentPath: Point[];
  color: string;
  size: number;
  tool: Tool;
  history: any[]; // Simple stack for undo/redo
};

type Action =
  | { type: 'START'; point: Point }
  | { type: 'MOVE'; point: Point }
  | { type: 'END' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_SIZE'; size: number }
  | { type: 'SET_TOOL'; tool: Tool }
  | { type: 'UNDO' }
  | { type: 'CLEAR' };

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'START':
      return { ...state, currentPath: [action.point] };
    case 'MOVE':
      return { ...state, currentPath: [...state.currentPath, action.point] };
    case 'END':
      const newPath = { points: state.currentPath, color: state.tool === 'pen' ? state.color : '#FFFFFF', size: state.size, tool: state.tool };
      return { ...state, paths: [...state.paths, newPath], currentPath: [] };
    case 'SET_COLOR':
      return { ...state, color: action.color };
    case 'SET_SIZE':
      return { ...state, size: action.size };
    case 'SET_TOOL':
      return { ...state, tool: action.tool };
    case 'CLEAR':
      return { ...state, paths: [] };
    default:
      return state;
  }
};

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, {
    paths: [],
    currentPath: [],
    color: '#000000',
    size: 2,
    tool: 'pen',
    history: [],
  });

  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    state.paths.forEach((path) => {
      ctx.beginPath();
      ctx.strokeStyle = path.color;
      ctx.lineWidth = path.size;
      path.points.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.stroke();
    });
  }, [state.paths]);

  const onMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    dispatch({ type: 'START', point: { x: e.clientX - rect.left, y: e.clientY - rect.top } });
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (state.currentPath.length === 0) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    dispatch({ type: 'MOVE', point: { x: e.clientX - rect.left, y: e.clientY - rect.top } });
  };

  const onMouseUp = () => dispatch({ type: 'END' });

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h3>Whiteboard</h3>
      <div style={{ marginBottom: '10px' }}>
        <button onClick={() => dispatch({ type: 'SET_TOOL', tool: 'pen' })}>Pen</button>
        <button onClick={() => dispatch({ type: 'SET_TOOL', tool: 'eraser' })}>Eraser</button>
        {['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00'].map(c => <button key={c} onClick={() => dispatch({ type: 'SET_COLOR', color: c })} style={{ backgroundColor: c, width: '20px', height: '20px' }}></button>)}
        <input type="range" min="1" max="10" onChange={(e) => dispatch({ type: 'SET_SIZE', size: Number(e.target.value) })} />
        <button onClick={() => dispatch({ type: 'CLEAR' })}>Clear</button>
      </div>
      <canvas
        ref={canvasRef}
        width={600}
        height={400}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        style={{ border: '1px solid #ccc', cursor: 'crosshair' }}
      />
    </div>
  );
};

export default CollaborativeWhiteboard;
