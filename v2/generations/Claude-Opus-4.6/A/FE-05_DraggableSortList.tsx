import React, { useRef, useState, useCallback, useEffect } from 'react';

interface DragState {
  isDragging: boolean;
  dragIndex: number;
  overIndex: number;
  startY: number;
  currentY: number;
}

const initialItems = [
  { id: 1, text: 'Learn React' },
  { id: 2, text: 'Build a project' },
  { id: 3, text: 'Write tests' },
  { id: 4, text: 'Deploy to production' },
  { id: 5, text: 'Monitor and iterate' },
  { id: 6, text: 'Document everything' },
  { id: 7, text: 'Review pull requests' },
];

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState(initialItems);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    dragIndex: -1,
    overIndex: -1,
    startY: 0,
    currentY: 0,
  });

  const listRef = useRef<HTMLUListElement>(null);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);
  const dragStateRef = useRef(dragState);

  useEffect(() => {
    dragStateRef.current = dragState;
  }, [dragState]);

  const getClientY = (e: MouseEvent | TouchEvent): number => {
    if ('touches' in e) {
      return e.touches[0]?.clientY ?? e.changedTouches[0]?.clientY ?? 0;
    }
    return e.clientY;
  };

  const findOverIndex = useCallback((clientY: number): number => {
    for (let i = 0; i < itemRefs.current.length; i++) {
      const el = itemRefs.current[i];
      if (el) {
        const rect = el.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        if (clientY < midY) {
          return i;
        }
      }
    }
    return itemRefs.current.length - 1;
  }, []);

  const handleMove = useCallback((e: MouseEvent | TouchEvent) => {
    e.preventDefault();
    const clientY = getClientY(e);
    const overIdx = findOverIndex(clientY);
    setDragState(prev => ({
      ...prev,
      currentY: clientY,
      overIndex: overIdx,
    }));
  }, [findOverIndex]);

  const handleEnd = useCallback(() => {
    const state = dragStateRef.current;
    if (state.isDragging && state.dragIndex !== -1) {
      setItems(prev => {
        const newItems = [...prev];
        const [dragged] = newItems.splice(state.dragIndex, 1);
        const targetIndex = state.overIndex >= 0 ? state.overIndex : state.dragIndex;
        newItems.splice(targetIndex, 0, dragged);
        return newItems;
      });
    }
    setDragState({
      isDragging: false,
      dragIndex: -1,
      overIndex: -1,
      startY: 0,
      currentY: 0,
    });
    document.removeEventListener('mousemove', handleMove);
    document.removeEventListener('mouseup', handleEnd);
    document.removeEventListener('touchmove', handleMove);
    document.removeEventListener('touchend', handleEnd);
  }, [handleMove]);

  const handleStart = useCallback((index: number, e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    const clientY = 'touches' in e.nativeEvent
      ? e.nativeEvent.touches[0]?.clientY ?? 0
      : (e.nativeEvent as MouseEvent).clientY;

    setDragState({
      isDragging: true,
      dragIndex: index,
      overIndex: index,
      startY: clientY,
      currentY: clientY,
    });

    document.addEventListener('mousemove', handleMove, { passive: false });
    document.addEventListener('mouseup', handleEnd);
    document.addEventListener('touchmove', handleMove, { passive: false });
    document.addEventListener('touchend', handleEnd);
  }, [handleMove, handleEnd]);

  const getDragOffset = (): number => {
    return dragState.currentY - dragState.startY;
  };

  return (
    <div style={containerStyle}>
      <h2 style={titleStyle}>Draggable Sort List</h2>
      <ul ref={listRef} style={listStyle}>
        {items.map((item, index) => {
          const isDragging = dragState.isDragging && dragState.dragIndex === index;
          const isOver = dragState.isDragging && dragState.overIndex === index && dragState.dragIndex !== index;

          let itemStyle: React.CSSProperties = {
            ...baseItemStyle,
          };

          if (isDragging) {
            itemStyle = {
              ...itemStyle,
              transform: `translateY(${getDragOffset()}px)`,
              zIndex: 1000,
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              opacity: 0.9,
              background: '#e3f2fd',
              transition: 'box-shadow 0.2s',
            };
          } else if (isOver) {
            const fromAbove = dragState.dragIndex < dragState.overIndex;
            itemStyle = {
              ...itemStyle,
              borderTop: fromAbove ? 'none' : '3px solid #1976d2',
              borderBottom: fromAbove ? '3px solid #1976d2' : 'none',
              transition: 'border 0.15s',
            };
          }

          return (
            <li
              key={item.id}
              ref={(el) => { itemRefs.current[index] = el; }}
              style={itemStyle}
              onMouseDown={(e) => handleStart(index, e)}
              onTouchStart={(e) => handleStart(index, e)}
            >
              <span style={gripStyle}>⠿</span>
              <span style={textStyle}>{item.text}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

const containerStyle: React.CSSProperties = {
  maxWidth: '400px',
  margin: '40px auto',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const titleStyle: React.CSSProperties = {
  textAlign: 'center',
  color: '#333',
  marginBottom: '20px',
};

const listStyle: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
};

const baseItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '14px 16px',
  marginBottom: '8px',
  background: '#ffffff',
  border: '1px solid #e0e0e0',
  borderRadius: '8px',
  cursor: 'grab',
  userSelect: 'none',
  position: 'relative',
};

const gripStyle: React.CSSProperties = {
  marginRight: '12px',
  color: '#999',
  fontSize: '18px',
};

const textStyle: React.CSSProperties = {
  fontSize: '15px',
  color: '#333',
};

export default DraggableSortList;
