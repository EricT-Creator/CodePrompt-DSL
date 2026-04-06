import React, { useState, useRef, useEffect, useCallback } from 'react';

interface DraggableItem {
  id: number;
  text: string;
}

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<DraggableItem[]>([
    { id: 1, text: 'Item 1' },
    { id: 2, text: 'Item 2' },
    { id: 3, text: 'Item 3' },
    { id: 4, text: 'Item 4' },
    { id: 5, text: 'Item 5' },
    { id: 6, text: 'Item 6' },
  ]);

  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragStartY, setDragStartY] = useState<number>(0);
  const [currentY, setCurrentY] = useState<number>(0);
  const [ghostOffset, setGhostOffset] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const getItemHeight = () => {
    if (itemRefs.current.size === 0) return 60;
    const firstItem = itemRefs.current.get(items[0].id);
    return firstItem ? firstItem.offsetHeight : 60;
  };

  const handleMouseDown = useCallback((e: React.MouseEvent, id: number) => {
    e.preventDefault();
    setDraggingId(id);
    setDragStartY(e.clientY);
    setCurrentY(e.clientY);
    setGhostOffset(0);
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent, id: number) => {
    e.preventDefault();
    const touch = e.touches[0];
    setDraggingId(id);
    setDragStartY(touch.clientY);
    setCurrentY(touch.clientY);
    setGhostOffset(0);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (draggingId === null) return;
    e.preventDefault();
    setCurrentY(e.clientY);
    
    const deltaY = e.clientY - dragStartY;
    setGhostOffset(deltaY);

    const itemHeight = getItemHeight();
    const targetIndex = Math.round(deltaY / itemHeight);
    
    if (targetIndex !== 0) {
      const oldIndex = items.findIndex(item => item.id === draggingId);
      const newIndex = Math.max(0, Math.min(items.length - 1, oldIndex + targetIndex));
      
      if (newIndex !== oldIndex) {
        const newItems = [...items];
        const [draggedItem] = newItems.splice(oldIndex, 1);
        newItems.splice(newIndex, 0, draggedItem);
        setItems(newItems);
        setDragStartY(e.clientY);
      }
    }
  }, [draggingId, dragStartY, items]);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (draggingId === null) return;
    e.preventDefault();
    const touch = e.touches[0];
    setCurrentY(touch.clientY);
    
    const deltaY = touch.clientY - dragStartY;
    setGhostOffset(deltaY);

    const itemHeight = getItemHeight();
    const targetIndex = Math.round(deltaY / itemHeight);
    
    if (targetIndex !== 0) {
      const oldIndex = items.findIndex(item => item.id === draggingId);
      const newIndex = Math.max(0, Math.min(items.length - 1, oldIndex + targetIndex));
      
      if (newIndex !== oldIndex) {
        const newItems = [...items];
        const [draggedItem] = newItems.splice(oldIndex, 1);
        newItems.splice(newIndex, 0, draggedItem);
        setItems(newItems);
        setDragStartY(touch.clientY);
      }
    }
  }, [draggingId, dragStartY, items]);

  const handleMouseUp = useCallback(() => {
    setDraggingId(null);
    setGhostOffset(0);
  }, []);

  const handleTouchEnd = useCallback(() => {
    setDraggingId(null);
    setGhostOffset(0);
  }, []);

  useEffect(() => {
    if (draggingId !== null) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.addEventListener('touchmove', handleTouchMove, { passive: false });
      document.addEventListener('touchend', handleTouchEnd);
      document.addEventListener('touchcancel', handleTouchEnd);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleTouchEnd);
        document.removeEventListener('touchcancel', handleTouchEnd);
      };
    }
  }, [draggingId, handleMouseMove, handleMouseUp, handleTouchMove, handleTouchEnd]);

  const draggingItem = draggingId !== null ? items.find(item => item.id === draggingId) : null;

  return (
    <div 
      ref={containerRef}
      style={{
        maxWidth: '400px',
        margin: '20px auto',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <h2 style={{ textAlign: 'center', marginBottom: '20px', color: '#333' }}>
        Drag & Drop Sortable List
      </h2>
      
      <div
        style={{
          position: 'relative',
          border: '1px solid #ddd',
          borderRadius: '8px',
          overflow: 'hidden',
          backgroundColor: '#f9f9f9',
        }}
      >
        {items.map((item, index) => (
          <div
            key={item.id}
            ref={el => {
              if (el) {
                itemRefs.current.set(item.id, el);
              } else {
                itemRefs.current.delete(item.id);
              }
            }}
            style={{
              padding: '16px',
              borderBottom: index < items.length - 1 ? '1px solid #eee' : 'none',
              backgroundColor: draggingId === item.id ? '#e3f2fd' : '#fff',
              cursor: draggingId === item.id ? 'grabbing' : 'grab',
              userSelect: 'none',
              position: 'relative',
              transition: draggingId !== item.id ? 'all 0.2s ease' : 'none',
              zIndex: draggingId === item.id ? 100 : 1,
              transform: draggingId === item.id ? `translateY(${ghostOffset}px)` : 'none',
              boxShadow: draggingId === item.id ? '0 4px 12px rgba(0, 0, 0, 0.15)' : 'none',
            }}
            onMouseDown={(e) => handleMouseDown(e, item.id)}
            onTouchStart={(e) => handleTouchStart(e, item.id)}
          >
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: '#2196f3',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '12px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                }}
              >
                {index + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', color: '#333' }}>{item.text}</div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  Drag me to reorder
                </div>
              </div>
              <div
                style={{
                  color: '#999',
                  fontSize: '20px',
                  userSelect: 'none',
                }}
              >
                ⋮⋮
              </div>
            </div>
          </div>
        ))}
        
        {draggingItem && draggingId !== null && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              padding: '16px',
              backgroundColor: 'rgba(227, 242, 253, 0.9)',
              border: '2px dashed #2196f3',
              borderRadius: '8px',
              pointerEvents: 'none',
              zIndex: 50,
              opacity: 0.7,
              transform: `translateY(${currentY - dragStartY}px)`,
              transition: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: '#2196f3',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '12px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                }}
              >
                {items.findIndex(item => item.id === draggingId) + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', color: '#333' }}>{draggingItem.text}</div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  Moving...
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div style={{ marginTop: '20px', textAlign: 'center', color: '#666', fontSize: '14px' }}>
        <p>Drag items up or down to reorder the list</p>
        <p style={{ marginTop: '8px', fontSize: '12px' }}>
          Uses mouse/touch events only (no HTML5 Drag and Drop API)
        </p>
      </div>
    </div>
  );
};

export default DraggableSortList;