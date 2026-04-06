import React, { useState, useRef, useCallback } from 'react';

interface Item {
  id: string;
  text: string;
}

const initialItems: Item[] = [
  { id: '1', text: '项目一' },
  { id: '2', text: '项目二' },
  { id: '3', text: '项目三' },
  { id: '4', text: '项目四' },
  { id: '5', text: '项目五' },
  { id: '6', text: '项目六' },
  { id: '7', text: '项目七' },
];

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const dragItemRef = useRef<Item | null>(null);
  const dragIndexRef = useRef<number>(-1);
  const listRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const handleMouseDown = useCallback((e: React.MouseEvent, item: Item, index: number) => {
    e.preventDefault();
    dragItemRef.current = item;
    dragIndexRef.current = index;
    setDraggingId(item.id);
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent, item: Item, index: number) => {
    dragItemRef.current = item;
    dragIndexRef.current = index;
    setDraggingId(item.id);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!draggingId || !listRef.current) return;
    
    const rect = listRef.current.getBoundingClientRect();
    const y = e.clientY - rect.top;
    
    let newDragOverId: string | null = null;
    items.forEach((item) => {
      const el = itemRefs.current.get(item.id);
      if (el) {
        const itemRect = el.getBoundingClientRect();
        const itemY = itemRect.top - rect.top + itemRect.height / 2;
        if (y < itemY && item.id !== draggingId) {
          if (!newDragOverId) newDragOverId = item.id;
        }
      }
    });
    
    if (!newDragOverId && items.length > 0) {
      const lastItem = items[items.length - 1];
      if (lastItem.id !== draggingId) {
        newDragOverId = lastItem.id;
      }
    }
    
    setDragOverId(newDragOverId);
  }, [draggingId, items]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!draggingId || !listRef.current) return;
    
    const touch = e.touches[0];
    const rect = listRef.current.getBoundingClientRect();
    const y = touch.clientY - rect.top;
    
    let newDragOverId: string | null = null;
    items.forEach((item) => {
      const el = itemRefs.current.get(item.id);
      if (el) {
        const itemRect = el.getBoundingClientRect();
        const itemY = itemRect.top - rect.top + itemRect.height / 2;
        if (y < itemY && item.id !== draggingId) {
          if (!newDragOverId) newDragOverId = item.id;
        }
      }
    });
    
    if (!newDragOverId && items.length > 0) {
      const lastItem = items[items.length - 1];
      if (lastItem.id !== draggingId) {
        newDragOverId = lastItem.id;
      }
    }
    
    setDragOverId(newDragOverId);
  }, [draggingId, items]);

  const handleMouseUp = useCallback(() => {
    if (!draggingId || dragIndexRef.current === -1) {
      setDraggingId(null);
      setDragOverId(null);
      return;
    }

    const dragItem = dragItemRef.current;
    if (!dragItem) {
      setDraggingId(null);
      setDragOverId(null);
      return;
    }

    const newItems = [...items];
    const dragIndex = dragIndexRef.current;
    newItems.splice(dragIndex, 1);

    let dropIndex = newItems.length;
    if (dragOverId) {
      const index = newItems.findIndex(item => item.id === dragOverId);
      if (index !== -1) {
        dropIndex = index;
      }
    }

    newItems.splice(dropIndex, 0, dragItem);
    setItems(newItems);
    setDraggingId(null);
    setDragOverId(null);
    dragItemRef.current = null;
    dragIndexRef.current = -1;
  }, [draggingId, dragOverId, items]);

  const handleTouchEnd = useCallback(() => {
    handleMouseUp();
  }, [handleMouseUp]);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h2>可拖拽排序列表</h2>
      <div
        ref={listRef}
        style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '400px' }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {items.map((item, index) => (
          <div
            key={item.id}
            ref={(el) => {
              if (el) itemRefs.current.set(item.id, el);
            }}
            onMouseDown={(e) => handleMouseDown(e, item, index)}
            onTouchStart={(e) => handleTouchStart(e, item, index)}
            style={{
              padding: '16px 20px',
              backgroundColor: draggingId === item.id ? '#e3f2fd' : '#fff',
              border: `2px solid ${draggingId === item.id ? '#2196f3' : dragOverId === item.id ? '#4caf50' : '#ddd'}`,
              borderRadius: '8px',
              cursor: draggingId === item.id ? 'grabbing' : 'grab',
              boxShadow: draggingId === item.id ? '0 4px 12px rgba(0,0,0,0.15)' : '0 2px 4px rgba(0,0,0,0.1)',
              transform: draggingId === item.id ? 'scale(1.02)' : 'scale(1)',
              transition: draggingId ? 'none' : 'all 0.2s ease',
              userSelect: 'none',
            }}
          >
            {item.text}
          </div>
        ))}
      </div>
    </div>
  );
}
