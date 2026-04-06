import React, { useRef, useState, useCallback, useEffect } from 'react';

interface DraggableSortListProps {
  items?: string[];
}

interface DragState {
  draggingIndex: number | null;
  startIndex: number;
  currentIndex: number;
  offsetY: number;
  itemHeight: number;
  placeholderIndex: number;
}

const defaultItems = [
  'Item 1 - Learn TypeScript',
  'Item 2 - Build React App',
  'Item 3 - Master CSS Grid',
  'Item 4 - Study State Management',
  'Item 5 - Deploy to Production',
  'Item 6 - Write Unit Tests',
  'Item 7 - Code Review',
];

const DraggableSortList: React.FC<DraggableSortListProps> = ({ items = defaultItems }) => {
  const [order, setOrder] = useState<number[]>(() => items.map((_, i) => i));
  const [dragState, setDragState] = useState<DragState | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const getItemHeight = useCallback((index: number): number => {
    const el = itemRefs.current.get(index);
    return el ? el.offsetHeight : 50;
  }, []);

  const getItemIndexFromY = useCallback((clientY: number): number => {
    if (!listRef.current) return 0;
    const rect = listRef.current.getBoundingClientRect();
    const y = clientY - rect.top;
    let cumulative = 0;
    for (let i = 0; i < order.length; i++) {
      const h = getItemHeight(i);
      if (cumulative + h > y + 5) return i;
      cumulative += h;
    }
    return order.length - 1;
  }, [order, getItemHeight]);

  const handlePointerDown = useCallback((e: React.MouseEvent | React.TouchEvent, index: number) => {
    e.preventDefault();
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    const el = itemRefs.current.get(index);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const offsetY = clientY - rect.top;

    setDragState({
      draggingIndex: index,
      startIndex: index,
      currentIndex: index,
      offsetY,
      itemHeight: el.offsetHeight,
      placeholderIndex: index,
    });

    const handleMove = (me: MouseEvent | TouchEvent) => {
      const cy = 'touches' in me ? me.touches[0].clientY : me.clientY;
      setDragState((prev) => {
        if (!prev) return null;
        const targetIndex = getItemIndexFromY(cy - prev.offsetY + prev.itemHeight / 2);
        return {
          ...prev,
          currentIndex: cy,
          placeholderIndex: Math.max(0, Math.min(targetIndex, order.length - 1)),
        };
      });
    };

    const handleUp = () => {
      setDragState((prev) => {
        if (prev && prev.placeholderIndex !== prev.startIndex) {
          setOrder((o) => {
            const newOrder = [...o];
            const [moved] = newOrder.splice(prev.startIndex, 1);
            newOrder.splice(prev.placeholderIndex, 0, moved);
            return newOrder;
          });
        }
        return null;
      });
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
      window.removeEventListener('touchmove', handleMove);
      window.removeEventListener('touchend', handleUp);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleUp);
  }, [order, getItemIndexFromY]);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Sortable List</h2>
      <p style={styles.subtitle}>Drag items to reorder</p>
      <div ref={listRef} style={styles.list}>
        {order.map((itemIndex, position) => {
          const isDragging = dragState !== null && dragState.startIndex === position;
          const isPlaceholder = dragState !== null && dragState.placeholderIndex === position && !isDragging;

          return (
            <div
              key={items[itemIndex]}
              ref={(el) => {
                if (el) itemRefs.current.set(position, el);
                else itemRefs.current.delete(position);
              }}
              style={{
                ...styles.item,
                opacity: isDragging ? 0.4 : 1,
                transform: isPlaceholder && dragState ? `translateY(${dragState.startIndex < dragState.placeholderIndex ? -dragState.itemHeight : dragState.itemHeight}px)` : undefined,
                transition: isDragging ? 'none' : 'transform 0.2s ease',
                backgroundColor: isPlaceholder ? '#e3f2fd' : '#ffffff',
                border: isPlaceholder ? '2px dashed #1976d2' : '1px solid #e0e0e0',
                cursor: 'grab',
                userSelect: 'none',
              }}
              onMouseDown={(e) => handlePointerDown(e, position)}
              onTouchStart={(e) => handlePointerDown(e, position)}
            >
              <span style={styles.grip}>☰</span>
              <span style={styles.itemText}>{items[itemIndex]}</span>
            </div>
          );
        })}
        {dragState && (
          <div
            style={{
              ...styles.ghostItem,
              position: 'fixed',
              top: (typeof dragState.currentIndex === 'number' ? dragState.currentIndex : 0) - dragState.offsetY,
              left: listRef.current ? listRef.current.getBoundingClientRect().left : 0,
              width: listRef.current ? listRef.current.offsetWidth : 300,
              height: dragState.itemHeight,
              zIndex: 1000,
              pointerEvents: 'none',
            }}
          >
            <span style={styles.grip}>☰</span>
            <span style={styles.itemText}>{items[order[dragState.startIndex]]}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: 400,
    margin: '40px auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    marginBottom: 4,
    color: '#1a1a1a',
  },
  subtitle: {
    fontSize: 13,
    color: '#888',
    marginBottom: 16,
  },
  list: {
    position: 'relative',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    marginBottom: 4,
    borderRadius: 8,
    fontSize: 14,
    transition: 'transform 0.2s ease, opacity 0.2s ease',
  },
  grip: {
    marginRight: 12,
    fontSize: 16,
    color: '#bbb',
  },
  itemText: {
    flex: 1,
  },
  ghostItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    borderRadius: 8,
    fontSize: 14,
    backgroundColor: '#bbdefb',
    border: '2px solid #1976d2',
    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
  },
};

export default DraggableSortList;
