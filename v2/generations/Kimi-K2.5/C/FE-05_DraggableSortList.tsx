import React, { useState, useRef, useCallback } from 'react';

interface Item {
  id: string;
  text: string;
}

const initialItems: Item[] = [
  { id: '1', text: 'Item 1 - First task' },
  { id: '2', text: 'Item 2 - Second task' },
  { id: '3', text: 'Item 3 - Third task' },
  { id: '4', text: 'Item 4 - Fourth task' },
  { id: '5', text: 'Item 5 - Fifth task' },
  { id: '6', text: 'Item 6 - Sixth task' },
];

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [dragY, setDragY] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const dragStartY = useRef<number>(0);
  const dragItemIndex = useRef<number>(-1);
  const isDragging = useRef<boolean>(false);

  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent, id: string) => {
    e.preventDefault();
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    dragStartY.current = clientY;
    dragItemIndex.current = items.findIndex(item => item.id === id);
    isDragging.current = true;
    setDraggingId(id);
    setDragY(clientY);
  }, [items]);

  const handleMove = useCallback((e: MouseEvent | TouchEvent) => {
    if (!isDragging.current || draggingId === null) return;
    
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    setDragY(clientY);

    const container = containerRef.current;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const relativeY = clientY - containerRect.top;

    let newDragOverId: string | null = null;
    itemRefs.current.forEach((el, itemId) => {
      if (itemId === draggingId) return;
      const rect = el.getBoundingClientRect();
      const itemCenterY = rect.top + rect.height / 2 - containerRect.top;
      if (relativeY < itemCenterY) {
        if (newDragOverId === null) {
          newDragOverId = itemId;
        }
      }
    });

    if (newDragOverId === null && items.length > 0) {
      newDragOverId = items[items.length - 1].id;
    }

    setDragOverId(newDragOverId);
  }, [draggingId, items]);

  const handleEnd = useCallback(() => {
    if (!isDragging.current || draggingId === null) return;

    if (dragOverId !== null && dragOverId !== draggingId) {
      const fromIndex = items.findIndex(item => item.id === draggingId);
      const toIndex = items.findIndex(item => item.id === dragOverId);
      
      const newItems = [...items];
      const [movedItem] = newItems.splice(fromIndex, 1);
      const insertIndex = fromIndex < toIndex ? toIndex : toIndex;
      newItems.splice(insertIndex, 0, movedItem);
      
      setItems(newItems);
    }

    isDragging.current = false;
    setDraggingId(null);
    setDragOverId(null);
    dragItemIndex.current = -1;
  }, [draggingId, dragOverId, items]);

  React.useEffect(() => {
    if (draggingId !== null) {
      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleEnd);
      window.addEventListener('touchmove', handleMove, { passive: false });
      window.addEventListener('touchend', handleEnd);
      
      return () => {
        window.removeEventListener('mousemove', handleMove);
        window.removeEventListener('mouseup', handleEnd);
        window.removeEventListener('touchmove', handleMove);
        window.removeEventListener('touchend', handleEnd);
      };
    }
  }, [draggingId, handleMove, handleEnd]);

  const getItemStyle = (id: string): React.CSSProperties => {
    const baseStyle: React.CSSProperties = {
      padding: '16px 20px',
      marginBottom: '8px',
      backgroundColor: '#ffffff',
      border: '1px solid #e0e0e0',
      borderRadius: '8px',
      cursor: 'grab',
      userSelect: 'none',
      transition: 'transform 0.15s, box-shadow 0.15s, border-color 0.15s',
      position: 'relative',
    };

    if (draggingId === id) {
      return {
        ...baseStyle,
        opacity: 0.5,
        cursor: 'grabbing',
        backgroundColor: '#f5f5f5',
      };
    }

    if (dragOverId === id && draggingId !== null) {
      return {
        ...baseStyle,
        borderColor: '#4a90d9',
        borderWidth: '2px',
        boxShadow: '0 2px 8px rgba(74, 144, 217, 0.3)',
      };
    }

    return baseStyle;
  };

  return (
    <div
      ref={containerRef}
      style={{
        maxWidth: '400px',
        margin: '40px auto',
        padding: '20px',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <h2 style={{ marginBottom: '20px', color: '#333' }}>Draggable Sort List</h2>
      <div>
        {items.map((item) => (
          <div
            key={item.id}
            ref={(el) => {
              if (el) itemRefs.current.set(item.id, el);
            }}
            style={getItemStyle(item.id)}
            onMouseDown={(e) => handleStart(e, item.id)}
            onTouchStart={(e) => handleStart(e, item.id)}
          >
            <span style={{ marginRight: '12px', color: '#999' }}>☰</span>
            {item.text}
          </div>
        ))}
      </div>
      <p style={{ marginTop: '20px', color: '#666', fontSize: '14px' }}>
        Drag items to reorder using mouse or touch
      </p>
    </div>
  );
}
