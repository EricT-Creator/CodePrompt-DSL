import React, { useReducer, useRef, MouseEvent, TouchEvent } from 'react';

type Action =
  | { type: 'DRAW'; x: number; y: number; color: string; size: number }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' };

interface State {
  history: { type: 'PATH'; points: { x: number; y: number }[] }[];
  redoStack: any[];
  currentColor: string;
  currentSize: number;
}

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'DRAW':
      // Simplified drawing logic
      return { ...state, history: [...state.history, { type: 'PATH', points: [{ x: action.x, y: action.y }] }] };
    case 'UNDO':
      return { ...state, redoStack: [state.history[state.history.length - 1], ...state.redoStack], history: state.history.slice(0, -1) };
    case 'REDO':
      return { ...state, history: [...state.history, state.redoStack[0]], redoStack: state.redoStack.slice(1) };
    case 'CLEAR':
      return { ...state, history: [], redoStack: [] };
    default:
      return state;
  }
};

const CollaborativeWhiteboard: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, { history: [], redoStack: [], currentColor: '#000', currentSize: 5 });
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = (e: MouseEvent | TouchEvent) => {
    // simplified drawing to canvas context
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // ... logic
  };

  return (
    <div style={{ textAlign: 'center' }}>
      <canvas ref={canvasRef} onMouseDown={draw} style={{ border: '1px solid black', width: '800px', height: '600px' }} />
      <div>
        <button onClick={() => dispatch({ type: 'UNDO' })}>Undo</button>
        <button onClick={() => dispatch({ type: 'REDO' })}>Redo</button>
        <button onClick={() => dispatch({ type: 'CLEAR' })}>Clear</button>
      </div>
    </div>
  );
};

export default CollaborativeWhiteboard;