import React, { useRef, useState, useCallback } from 'react';

interface Item {
  id: string;
  text: string;
}

const initialItems: Item[] = [
  { id: '1', text: 'Item 1' },
  { id: '2', text: 'Item 2' },
  { id: '3', text: 'Item 3' },
  { id: '4', text: 'Item 4' },
  { id: '5', text: 'Item 5' },
];

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [placeholderIndex, setPlaceholderIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragItemRef = useRef<Item | null>(null);
  const dragIndexRef = useRef<number>(-1);
  const startYRef = useRef<number>(0);
  const currentYRef = useRef<number>(0);
  const ghostRef = useRef<HTMLDivElement | null>(null);

  const getItemHeight = useCallback(() => {
    const item = containerRef.current?.querySelector('.sort-item');
    return item ? (item as HTMLElement).offsetHeight : 50;
  }, []);

  const calculateIndex = useCallback((clientY: number) => {
    if (!containerRef.current) return 0;
    const rect = containerRef.current.getBoundingClientRect();
    const itemHeight = getItemHeight();
    const relativeY = clientY - rect.top;
    return Math.max(0, Math.min(items.length - 1, Math.floor(relativeY / itemHeight)));
  }, [items.length, getItemHeight]);

  const createGhost = useCallback((item: Item, clientY: number, clientX: number) => {
    const ghost = document.createElement('div');
    ghost.textContent = item.text;
    ghost.style.cssText = `
      position: fixed;
      pointer-events: none;
      z-index: 1000;
      background: #e3f2fd;
      border: 2px solid #2196f3;
      border-radius: 4px;
      padding: 12px 16px;
      font-size: 16px;
      opacity: 0.9;
      box-shadow: 0 4px 8px rgba(0,0,0,0.2);
      left: ${clientX}px;
      top: ${clientY}px;
      transform: translate(-50%, -50%);
      width: 200px;
    `;
    document.body.appendChild(ghost);
    return ghost;
  }, []);

  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent, item: Item, index: number) => {
    e.preventDefault();
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    
    dragItemRef.current = item;
    dragIndexRef.current = index;
    startYRef.current = clientY;
    currentYRef.current = clientY;
    setDraggingId(item.id);
    setPlaceholderIndex(index);
    
    ghostRef.current = createGhost(item, clientY, clientX);
  }, [createGhost]);

  const handleMove = useCallback((clientY: number, clientX: number) => {
    currentYRef.current = clientY;
    
    if (ghostRef.current) {
      ghostRef.current.style.left = `${clientX}px`;
      ghostRef.current.style.top = `${clientY}px`;
    }
    
    const newIndex = calculateIndex(clientY);
    if (newIndex !== placeholderIndex) {
      setPlaceholderIndex(newIndex);
    }
  }, [calculateIndex, placeholderIndex]);

  const handleEnd = useCallback(() => {
    if (dragItemRef.current && placeholderIndex !== null && placeholderIndex !== dragIndexRef.current) {
      const newItems = [...items];
      const [removed] = newItems.splice(dragIndexRef.current, 1);
      newItems.splice(placeholderIndex, 0, removed);
      setItems(newItems);
    }
    
    if (ghostRef.current) {
      document.body.removeChild(ghostRef.current);
      ghostRef.current = null;
    }
    
    dragItemRef.current = null;
    dragIndexRef.current = -1;
    setDraggingId(null);
    setPlaceholderIndex(null);
  }, [items, placeholderIndex]);

  React.useEffect(() => {
    const onMouseMove = (e: MouseEvent) => handleMove(e.clientY, e.clientX);
    const onTouchMove = (e: TouchEvent) => handleMove(e.touches[0].clientY, e.touches[0].clientX);
    const onMouseUp = () => handleEnd();
    const onTouchEnd = () => handleEnd();

    if (draggingId) {
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      document.addEventListener('touchmove', onTouchMove, { passive: false });
      document.addEventListener('touchend', onTouchEnd);
    }

    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.removeEventListener('touchmove', onTouchMove);
      document.removeEventListener('touchend', onTouchEnd);
    };
  }, [draggingId, handleMove, handleEnd]);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h2>Draggable Sort List</h2>
      <div
        ref={containerRef}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          maxWidth: '300px',
        }}
      >
        {items.map((item, index) => {
          const isDragging = draggingId === item.id;
          const isPlaceholder = placeholderIndex === index && draggingId !== null;
          
          return (
            <React.Fragment key={item.id}>
              {isPlaceholder && (
                <div
                  style={{
                    height: '44px',
                    background: '#e0e0e0',
                    border: '2px dashed #999',
                    borderRadius: '4px',
                  }}
                />
              )}
              <div
                className="sort-item"
                onMouseDown={(e) => handleStart(e, item, index)}
                onTouchStart={(e) => handleStart(e, item, index)}
                style={{
                  padding: '12px 16px',
                  background: isDragging ? '#f5f5f5' : '#fff',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'grab',
                  opacity: isDragging ? 0.3 : 1,
                  userSelect: 'none',
                  touchAction: 'none',
                }}
              >
                {item.text}
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
