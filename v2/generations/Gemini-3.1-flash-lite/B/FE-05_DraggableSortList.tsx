import React, { useReducer, useRef, useState, useEffect } from 'react';

type State = {
  items: string[];
  draggingIndex: number | null;
  dragOverIndex: number | null;
};

type Action =
  | { type: 'START_DRAG'; index: number }
  | { type: 'DRAG_OVER'; index: number }
  | { type: 'END_DRAG' };

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'START_DRAG':
      return { ...state, draggingIndex: action.index };
    case 'DRAG_OVER':
      if (state.draggingIndex === null || state.draggingIndex === action.index) return state;
      const newItems = [...state.items];
      const draggedItem = newItems[state.draggingIndex];
      newItems.splice(state.draggingIndex, 1);
      newItems.splice(action.index, 0, draggedItem);
      return { ...state, items: newItems, draggingIndex: action.index, dragOverIndex: action.index };
    case 'END_DRAG':
      return { ...state, draggingIndex: null, dragOverIndex: null };
    default:
      return state;
  }
};

const DraggableSortList: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, {
    items: ['Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5'],
    draggingIndex: null,
    dragOverIndex: null,
  });

  const onMouseDown = (index: number) => {
    dispatch({ type: 'START_DRAG', index });
  };

  const onMouseMove = (index: number) => {
    if (state.draggingIndex !== null) {
      dispatch({ type: 'DRAG_OVER', index });
    }
  };

  const onMouseUp = () => {
    dispatch({ type: 'END_DRAG' });
  };

  useEffect(() => {
    window.addEventListener('mouseup', onMouseUp);
    return () => window.removeEventListener('mouseup', onMouseUp);
  }, []);

  return (
    <div style={{ width: '300px', margin: '20px', fontFamily: 'sans-serif' }}>
      <h3>Sortable List</h3>
      <div style={{ border: '1px solid #ccc', borderRadius: '4px' }}>
        {state.items.map((item, index) => (
          <div
            key={item}
            onMouseDown={() => onMouseDown(index)}
            onMouseMove={() => onMouseMove(index)}
            style={{
              padding: '10px',
              borderBottom: index !== state.items.length - 1 ? '1px solid #eee' : 'none',
              cursor: 'grab',
              backgroundColor: state.draggingIndex === index ? '#f0f0f0' : 'white',
              opacity: state.draggingIndex === index ? 0.5 : 1,
              userSelect: 'none',
            }}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DraggableSortList;
