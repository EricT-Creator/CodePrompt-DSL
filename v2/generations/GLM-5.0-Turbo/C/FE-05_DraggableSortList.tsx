import React, { useState, useRef, useCallback, useEffect } from 'react';

interface Item {
  id: string;
  text: string;
}

const INITIAL_ITEMS: Item[] = [
  { id: '1', text: 'Learn TypeScript' },
  { id: '2', text: 'Build a React App' },
  { id: '3', text: 'Master CSS Grid' },
  { id: '4', text: 'Write Unit Tests' },
  { id: '5', text: 'Deploy to Production' },
  { id: '6', text: 'Code Review PRs' },
  { id: '7', text: 'Update Documentation' },
];

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(INITIAL_ITEMS);
  const [dragState, setDragState] = useState<{
    draggingId: string | null;
    startIndex: number;
    currentIndex: number;
    offsetY: number;
    cloneRect: DOMRect | null;
    placeholderIndex: number;
  }>({
    draggingId: null,
    startIndex: -1,
    currentIndex: -1,
    offsetY: 0,
    cloneRect: null,
    placeholderIndex: -1,
  });

  const containerRef = useRef<HTMLUListElement>(null);
  const itemRefs = useRef<Map<string, HTMLLIElement>>(new Map());

  const getDragOverIndex = useCallback(
    (clientY: number): number => {
      if (!containerRef.current) return -1;
      const children = Array.from(containerRef.current.children);
      for (let i = 0; i < children.length; i++) {
        const rect = children[i].getBoundingClientRect();
        const mid = rect.top + rect.height / 2;
        if (clientY < mid) return i;
      }
      return children.length - 1;
    },
    []
  );

  const startDrag = useCallback(
    (id: string, startY: number) => {
      const el = itemRefs.current.get(id);
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const startIdx = items.findIndex((item) => item.id === id);
      setDragState({
        draggingId: id,
        startIndex: startIdx,
        currentIndex: startIdx,
        offsetY: startY - rect.top,
        cloneRect: rect,
        placeholderIndex: startIdx,
      });
    },
    [items]
  );

  const moveDrag = useCallback(
    (clientY: number) => {
      if (!dragState.draggingId) return;
      const overIndex = getDragOverIndex(clientY);
      if (overIndex !== dragState.placeholderIndex) {
        setItems((prev) => {
          const newItems = [...prev];
          const dragIdx = newItems.findIndex((i) => i.id === dragState.draggingId);
          const [removed] = newItems.splice(dragIdx, 1);
          const insertAt = overIndex > dragIdx ? overIndex - 1 : overIndex;
          newItems.splice(insertAt < 0 ? 0 : insertAt, 0, removed);
          return newItems;
        });
        setDragState((prev) => ({ ...prev, placeholderIndex: overIndex }));
      }
    },
    [dragState.draggingId, dragState.placeholderIndex, getDragOverIndex]
  );

  const endDrag = useCallback(() => {
    setDragState({
      draggingId: null,
      startIndex: -1,
      currentIndex: -1,
      offsetY: 0,
      cloneRect: null,
      placeholderIndex: -1,
    });
  }, []);

  useEffect(() => {
    if (!dragState.draggingId) return;

    const handleMouseMove = (e: MouseEvent) => {
      e.preventDefault();
      moveDrag(e.clientY);
    };
    const handleTouchMove = (e: TouchEvent) => {
      e.preventDefault();
      moveDrag(e.touches[0].clientY);
    };
    const handleMouseUp = () => endDrag();
    const handleTouchEnd = () => endDrag();

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [dragState.draggingId, moveDrag, endDrag]);

  const handleMouseDown = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    startDrag(id, e.clientY);
  };

  const handleTouchStart = (id: string, e: React.TouchEvent) => {
    startDrag(id, e.touches[0].clientY);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Draggable Sort List</h2>
      <p style={styles.subheading}>Drag items to reorder (mouse or touch)</p>
      <ul ref={containerRef} style={styles.list}>
        {items.map((item, index) => {
          const isDragging = item.id === dragState.draggingId;
          return (
            <li
              key={item.id}
              ref={(el) => {
                if (el) itemRefs.current.set(item.id, el);
              }}
              style={{
                ...styles.item,
                ...(isDragging ? styles.dragging : {}),
                ...(isDragging ? { opacity: 0.3 } : {}),
              }}
              onMouseDown={(e) => handleMouseDown(item.id, e)}
              onTouchStart={(e) => handleTouchStart(item.id, e)}
            >
              <span style={styles.grip}>⠿</span>
              <span style={styles.index}>{index + 1}</span>
              <span style={styles.text}>{item.text}</span>
            </li>
          );
        })}
      </ul>
      {dragState.draggingId && dragState.cloneRect && (() => {
        const el = itemRefs.current.get(dragState.draggingId!);
        if (!el) return null;
        const rect = el.getBoundingClientRect();
        return (
          <div
            style={{
              position: 'fixed',
              top: rect.top,
              left: rect.left,
              width: rect.width,
              height: rect.height,
              background: '#3b82f6',
              color: '#fff',
              padding: '12px 16px',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
              zIndex: 10000,
              pointerEvents: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '15px',
              fontWeight: 500,
              opacity: 0.92,
            }}
          >
            <span>⠿</span>
            <span>{items.find((i) => i.id === dragState.draggingId)?.text}</span>
          </div>
        );
      })()}
      <style>{`
        .drag-list-item:hover {
          background: #f1f5f9 !important;
        }
        .drag-list-item:active {
          cursor: grabbing;
        }
      `}</style>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '520px',
    margin: '40px auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '0 20px',
  },
  heading: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#1e293b',
    marginBottom: '4px',
  },
  subheading: {
    fontSize: '14px',
    color: '#64748b',
    marginBottom: '24px',
  },
  list: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
    borderRadius: '12px',
    overflow: 'hidden',
    border: '1px solid #e2e8f0',
    background: '#fff',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '14px 16px',
    borderBottom: '1px solid #f1f5f9',
    cursor: 'grab',
    userSelect: 'none' as const,
    transition: 'background 0.15s',
    fontSize: '15px',
    color: '#334155',
    background: '#fff',
  },
  dragging: {
    background: '#eff6ff',
    borderLeft: '3px solid #3b82f6',
  },
  grip: {
    fontSize: '18px',
    color: '#94a3b8',
    flexShrink: 0,
  },
  index: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    background: '#e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 600,
    color: '#64748b',
    flexShrink: 0,
  },
  text: {
    flex: 1,
    fontWeight: 500,
  },
};
