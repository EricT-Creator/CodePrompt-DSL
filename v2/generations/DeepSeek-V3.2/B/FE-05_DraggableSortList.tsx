import React, { useState, useRef, useEffect } from 'react';

interface ListItem {
  id: number;
  text: string;
}

const initialItems: ListItem[] = [
  { id: 1, text: 'Item 1' },
  { id: 2, text: 'Item 2' },
  { id: 3, text: 'Item 3' },
  { id: 4, text: 'Item 4' },
  { id: 5, text: 'Item 5' },
];

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<ListItem[]>(initialItems);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragStartY, setDragStartY] = useState<number>(0);
  const [currentY, setCurrentY] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  
  const handleMouseDown = (e: React.MouseEvent, id: number) => {
    setDraggingId(id);
    setDragStartY(e.clientY);
    setCurrentY(e.clientY);
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    e.preventDefault();
  };
  
  const handleTouchStart = (e: React.TouchEvent, id: number) => {
    if (e.touches.length === 1) {
      setDraggingId(id);
      setDragStartY(e.touches[0].clientY);
      setCurrentY(e.touches[0].clientY);
      
      document.addEventListener('touchmove', handleTouchMove);
      document.addEventListener('touchend', handleTouchEnd);
      
      e.preventDefault();
    }
  };
  
  const handleMouseMove = (e: MouseEvent) => {
    if (draggingId === null) return;
    setCurrentY(e.clientY);
    
    const container = containerRef.current;
    if (!container) return;
    
    const itemsArray = Array.from(container.children) as HTMLElement[];
    const draggingIndex = items.findIndex(item => item.id === draggingId);
    
    const dragOffset = e.clientY - dragStartY;
    const itemHeight = 60;
    const targetIndex = Math.round(dragOffset / itemHeight) + draggingIndex;
    
    if (targetIndex >= 0 && targetIndex < items.length && targetIndex !== draggingIndex) {
      const newItems = [...items];
      const [draggedItem] = newItems.splice(draggingIndex, 1);
      newItems.splice(targetIndex, 0, draggedItem);
      setItems(newItems);
      setDragStartY(e.clientY);
    }
  };
  
  const handleTouchMove = (e: TouchEvent) => {
    if (draggingId === null || e.touches.length !== 1) return;
    setCurrentY(e.touches[0].clientY);
    
    const container = containerRef.current;
    if (!container) return;
    
    const itemsArray = Array.from(container.children) as HTMLElement[];
    const draggingIndex = items.findIndex(item => item.id === draggingId);
    
    const dragOffset = e.touches[0].clientY - dragStartY;
    const itemHeight = 60;
    const targetIndex = Math.round(dragOffset / itemHeight) + draggingIndex;
    
    if (targetIndex >= 0 && targetIndex < items.length && targetIndex !== draggingIndex) {
      const newItems = [...items];
      const [draggedItem] = newItems.splice(draggingIndex, 1);
      newItems.splice(targetIndex, 0, draggedItem);
      setItems(newItems);
      setDragStartY(e.touches[0].clientY);
    }
    
    e.preventDefault();
  };
  
  const handleMouseUp = () => {
    setDraggingId(null);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  const handleTouchEnd = () => {
    setDraggingId(null);
    document.removeEventListener('touchmove', handleTouchMove);
    document.removeEventListener('touchend', handleTouchEnd);
  };
  
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, []);
  
  const ghostStyle = draggingId !== null ? {
    transform: `translateY(${currentY - dragStartY}px)`,
    opacity: 0.7,
    zIndex: 1000,
  } : {};
  
  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Draggable Sortable List</h2>
      <div ref={containerRef} style={styles.listContainer}>
        {items.map((item) => {
          const isDragging = item.id === draggingId;
          return (
            <div
              key={item.id}
              ref={(el) => {
                if (el) {
                  itemRefs.current.set(item.id, el);
                } else {
                  itemRefs.current.delete(item.id);
                }
              }}
              style={{
                ...styles.listItem,
                ...(isDragging ? ghostStyle : {}),
                ...(isDragging ? styles.draggingItem : {}),
              }}
              onMouseDown={(e) => handleMouseDown(e, item.id)}
              onTouchStart={(e) => handleTouchStart(e, item.id)}
              data-id={item.id}
            >
              <div style={styles.dragHandle}>⋮⋮</div>
              <div style={styles.itemContent}>{item.text}</div>
              {isDragging && <div style={styles.placeholder} />}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '400px',
    margin: '0 auto',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    marginBottom: '20px',
    color: '#333',
  },
  listContainer: {
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
    padding: '10px',
  },
  listItem: {
    backgroundColor: 'white',
    borderRadius: '6px',
    padding: '15px',
    marginBottom: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    display: 'flex',
    alignItems: 'center',
    cursor: 'move',
    userSelect: 'none',
    position: 'relative',
    transition: 'background-color 0.2s',
  },
  draggingItem: {
    backgroundColor: '#e3f2fd',
  },
  dragHandle: {
    marginRight: '15px',
    color: '#666',
    fontSize: '20px',
    cursor: 'grab',
  },
  itemContent: {
    flex: 1,
    fontSize: '16px',
  },
  placeholder: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(66, 165, 245, 0.1)',
    border: '2px dashed #42a5f5',
    borderRadius: '6px',
  },
};

export default DraggableSortList;