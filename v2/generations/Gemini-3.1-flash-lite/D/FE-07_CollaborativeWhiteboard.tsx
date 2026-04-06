import React, { useReducer, useRef, useEffect, MouseEvent } from 'react';

type State = {
  paths: { x: number; y: number }[][];
  color: string;
  size: number;
};

type Action =
  | { type: 'START_PATH'; x: number; y: number }
  | { type: 'ADD_POINT'; x: number; y: number }
  | { type: 'END_PATH' }
  | { type: 'SET_COLOR'; color: string }
  | { type: 'SET_SIZE'; size: number }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'START_PATH':
      return { ...state, paths: [...state.paths, [{ x: action.x, y: action.y }]] };
    case 'ADD_POINT':
      const newPaths = [...state.paths];
      newPaths[newPaths.length - 1].push({ x: action.x, y: action.y });
      return { ...state, paths: newPaths };
    case 'CLEAR':
      return { ...state, paths: [] };
    case 'SET_COLOR':
      return { ...state, color: action.color };
    case 'SET_SIZE':
      return { ...state, size: action.size };
    default:
      return state;
  }
};

const CollaborativeWhiteboard = () => {
  const [state, dispatch] = useReducer(reducer, { paths: [], color: 'black', size: 5 });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    state.paths.forEach(path => {
      ctx.beginPath();
      ctx.moveTo(path[0].x, path[0].y);
      path.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.strokeStyle = state.color;
      ctx.lineWidth = state.size;
      ctx.stroke();
    });
  }, [state]);

  const handleMouseDown = (e: MouseEvent) => {
    isDrawing.current = true;
    dispatch({ type: 'START_PATH', x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY });
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDrawing.current) return;
    dispatch({ type: 'ADD_POINT', x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY });
  };

  const handleMouseUp = () => {
    isDrawing.current = false;
  };

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{ border: '1px solid black' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      />
      <div>
        <button onClick={() => dispatch({ type: 'CLEAR' })}>Clear</button>
      </div>
    </div>
  );
};

export default CollaborativeWhiteboard;
