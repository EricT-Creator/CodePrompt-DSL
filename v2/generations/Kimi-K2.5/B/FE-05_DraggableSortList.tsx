import React, { useRef, useState, useCallback } from 'react';

interface Item {
  id: string;
  text: string;
}

const initialItems: Item[] = [
  { id: '1', text: 'Item 1 - Apple' },
  { id: '2', text: 'Item 2 - Banana' },
  { id: '3', text: 'Item 3 - Cherry' },
  { id: '4', text: 'Item 4 - Date' },
  { id: '5', text: 'Item 5 - Elderberry' },
];

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [ghostPosition, setGhostPosition] = useState<{ x: number; y: number } | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const dragItemRef = useRef<Item | null>(null);
  const dragStartPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const getPointerPos = (e: React.MouseEvent | React.TouchEvent) => {
    if ('touches' in e) {
      return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
    return { x: e.clientX, y: e.clientY };
  };

  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent, item: Item) => {
    e.preventDefault();
    const pos = getPointerPos(e);
    dragStartPosRef.current = pos;
    dragItemRef.current = item;
    setDraggingId(item.id);
    setGhostPosition(pos);
  }, []);

  const handleMove = useCallback((e: MouseEvent | TouchEvent) => {
    if (!draggingId || !dragItemRef.current) return;
    
    const pos = 'touches' in e 
      ? { x: e.touches[0].clientX, y: e.touches[0].clientY }
      : { x: e.clientX, y: e.clientY };
    
    setGhostPosition(pos);

    // Find item under cursor
    let overId: string | null = null;
    itemRefs.current.forEach((el, id) => {
      if (id === draggingId) return;
      const rect = el.getBoundingClientRect();
      if (pos.y >= rect.top && pos.y <= rect.bottom) {
        overId = id;
      }
    });
    setDragOverId(overId);
  }, [draggingId]);

  const handleEnd = useCallback(() => {
    if (draggingId && dragOverId && draggingId !== dragOverId) {
      setItems(prev => {
        const dragIndex = prev.findIndex(i => i.id === draggingId);
        const overIndex = prev.findIndex(i => i.id === dragOverId);
        const newItems = [...prev];
        const [removed] = newItems.splice(dragIndex, 1);
        newItems.splice(overIndex, 0, removed);
        return newItems;
      });
    }
    setDraggingId(null);
    setDragOverId(null);
    setGhostPosition(null);
    dragItemRef.current = null;
  }, [draggingId, dragOverId]);

  React.useEffect(() => {
    if (draggingId) {
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

  return (
    <div ref={containerRef} style={{ padding: '20px', maxWidth: '400px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '16px' }}>Draggable Sort List</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {items.map((item) => (
          <div
            key={item.id}
            ref={el => {
              if (el) itemRefs.current.set(item.id, el);
            }}
            onMouseDown={(e) => handleStart(e, item)}
            onTouchStart={(e) => handleStart(e, item)}
            style={{
              padding: '16px 20px',
              backgroundColor: dragOverId === item.id ? '#e3f2fd' : '#f5f5f5',
              border: dragOverId === item.id ? '2px dashed #2196f3' : '2px solid transparent',
              borderRadius: '8px',
              cursor: 'grab',
              userSelect: 'none',
              opacity: draggingId === item.id ? 0.3 : 1,
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
          >
            {item.text}
          </div>
        ))}
      </div>
      
      {ghostPosition && dragItemRef.current && (
        <div
          style={{
            position: 'fixed',
            left: ghostPosition.x - 50,
            top: ghostPosition.y - 20,
            padding: '16px 20px',
            backgroundColor: '#2196f3',
            color: 'white',
            borderRadius: '8px',
            pointerEvents: 'none',
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            transform: 'rotate(3deg)',
            opacity: 0.9,
          }}
        >
          {dragItemRef.current.text}
        </div>
      )}
    </div>
  );
}
