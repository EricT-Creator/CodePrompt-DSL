import React, { useState, useRef, useCallback } from 'react';

interface DragState {
  isDragging: boolean;
  dragIndex: number;
  overIndex: number;
  startY: number;
  currentY: number;
}

const initialItems = [
  'Build the landing page',
  'Write unit tests',
  'Deploy to staging',
  'Review pull requests',
  'Update documentation',
  'Fix login bug',
  'Optimize database queries',
];

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<string[]>(initialItems);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    dragIndex: -1,
    overIndex: -1,
    startY: 0,
    currentY: 0,
  });
  const listRef = useRef<HTMLUListElement>(null);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);

  const getClientY = (e: React.MouseEvent | React.TouchEvent | MouseEvent | TouchEvent): number => {
    if ('touches' in e) {
      return e.touches.length > 0 ? e.touches[0].clientY : (e as TouchEvent).changedTouches[0].clientY;
    }
    return (e as MouseEvent).clientY;
  };

  const getOverIndex = useCallback((clientY: number): number => {
    for (let i = 0; i < itemRefs.current.length; i++) {
      const el = itemRefs.current[i];
      if (el) {
        const rect = el.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        if (clientY < midY) return i;
      }
    }
    return items.length - 1;
  }, [items.length]);

  const handleDragStart = useCallback((index: number, e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    const clientY = getClientY(e);
    setDragState({
      isDragging: true,
      dragIndex: index,
      overIndex: index,
      startY: clientY,
      currentY: clientY,
    });

    const handleMove = (ev: MouseEvent | TouchEvent) => {
      ev.preventDefault();
      const cy = getClientY(ev);
      const oi = getOverIndex(cy);
      setDragState(prev => ({
        ...prev,
        currentY: cy,
        overIndex: oi,
      }));
    };

    const handleEnd = () => {
      setDragState(prev => {
        if (prev.dragIndex !== prev.overIndex) {
          setItems(currentItems => {
            const newItems = [...currentItems];
            const [removed] = newItems.splice(prev.dragIndex, 1);
            newItems.splice(prev.overIndex, 0, removed);
            return newItems;
          });
        }
        return {
          isDragging: false,
          dragIndex: -1,
          overIndex: -1,
          startY: 0,
          currentY: 0,
        };
      });
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleEnd);
      document.removeEventListener('touchmove', handleMove);
      document.removeEventListener('touchend', handleEnd);
    };

    document.addEventListener('mousemove', handleMove, { passive: false });
    document.addEventListener('mouseup', handleEnd);
    document.addEventListener('touchmove', handleMove, { passive: false });
    document.addEventListener('touchend', handleEnd);
  }, [getOverIndex]);

  const getItemStyle = (index: number): React.CSSProperties => {
    if (!dragState.isDragging) return {};

    if (index === dragState.dragIndex) {
      return {
        opacity: 0.4,
        transform: 'scale(0.98)',
        background: '#e2e8f0',
      };
    }

    if (dragState.dragIndex < dragState.overIndex) {
      if (index > dragState.dragIndex && index <= dragState.overIndex) {
        return { transform: 'translateY(-48px)', transition: 'transform 200ms ease' };
      }
    } else if (dragState.dragIndex > dragState.overIndex) {
      if (index >= dragState.overIndex && index < dragState.dragIndex) {
        return { transform: 'translateY(48px)', transition: 'transform 200ms ease' };
      }
    }

    return {};
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Draggable Sort List</h2>
      <ul ref={listRef} style={styles.list}>
        {items.map((item, index) => (
          <li
            key={item}
            ref={el => { itemRefs.current[index] = el; }}
            style={{
              ...styles.item,
              ...getItemStyle(index),
              cursor: dragState.isDragging ? 'grabbing' : 'grab',
            }}
            onMouseDown={e => handleDragStart(index, e)}
            onTouchStart={e => handleDragStart(index, e)}
          >
            <span style={styles.handle}>⠿</span>
            <span style={styles.text}>{item}</span>
            <span style={styles.index}>#{index + 1}</span>
          </li>
        ))}
      </ul>
      {dragState.isDragging && (
        <div style={styles.indicator}>
          Moving item {dragState.dragIndex + 1} → position {dragState.overIndex + 1}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '480px',
    margin: '40px auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    color: '#1a202c',
    marginBottom: '24px',
    fontSize: '24px',
    fontWeight: 600,
  },
  list: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    marginBottom: '4px',
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    userSelect: 'none',
    height: '44px',
    boxSizing: 'border-box',
  },
  handle: {
    marginRight: '12px',
    color: '#a0aec0',
    fontSize: '16px',
    letterSpacing: '2px',
  },
  text: {
    flex: 1,
    color: '#2d3748',
    fontSize: '14px',
  },
  index: {
    color: '#a0aec0',
    fontSize: '12px',
    fontWeight: 500,
  },
  indicator: {
    textAlign: 'center',
    marginTop: '16px',
    color: '#718096',
    fontSize: '13px',
    fontStyle: 'italic',
  },
};

export default DraggableSortList;
