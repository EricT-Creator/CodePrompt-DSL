import React, { useState, useRef, useEffect } from 'react';

interface DraggableItem {
  id: number;
  text: string;
}

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<DraggableItem[]>([
    { id: 1, text: '项目一：任务规划' },
    { id: 2, text: '项目二：代码审查' },
    { id: 3, text: '项目三：文档编写' },
    { id: 4, text: '项目四：测试执行' },
    { id: 5, text: '项目五：部署上线' },
    { id: 6, text: '项目六：性能优化' }
  ]);
  
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);
  const dragStartPos = useRef({ x: 0, y: 0 });
  const dragOffset = useRef({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const handleMouseDown = (e: React.MouseEvent, id: number) => {
    e.preventDefault();
    setDraggingId(id);
    dragStartPos.current = { x: e.clientX, y: e.clientY };
    dragOffset.current = { x: 0, y: 0 };
    
    const itemElement = itemRefs.current.get(id);
    if (itemElement) {
      itemElement.style.zIndex = '1000';
      itemElement.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
    }
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (draggingId === null) return;
    
    dragOffset.current = {
      x: e.clientX - dragStartPos.current.x,
      y: e.clientY - dragStartPos.current.y
    };
    
    const draggingElement = itemRefs.current.get(draggingId);
    if (draggingElement) {
      draggingElement.style.transform = `translate(${dragOffset.current.x}px, ${dragOffset.current.y}px)`;
    }
    
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (!containerRect) return;
    
    const mouseY = e.clientY;
    let newDragOverId: number | null = null;
    
    itemRefs.current.forEach((element, id) => {
      if (id === draggingId) return;
      
      const rect = element.getBoundingClientRect();
      const elementCenterY = rect.top + rect.height / 2;
      
      if (mouseY >= rect.top && mouseY <= rect.bottom) {
        newDragOverId = id;
      }
      
      if (id === dragOverId && id !== newDragOverId) {
        element.style.backgroundColor = '';
        element.style.borderColor = '#ddd';
      }
    });
    
    if (newDragOverId && newDragOverId !== dragOverId) {
      const dragOverElement = itemRefs.current.get(newDragOverId);
      if (dragOverElement) {
        dragOverElement.style.backgroundColor = '#f0f8ff';
        dragOverElement.style.borderColor = '#007bff';
      }
      setDragOverId(newDragOverId);
    }
  };

  const handleMouseUp = () => {
    if (draggingId === null) return;
    
    const draggingElement = itemRefs.current.get(draggingId);
    if (draggingElement) {
      draggingElement.style.transform = '';
      draggingElement.style.zIndex = '';
      draggingElement.style.boxShadow = '';
      draggingElement.style.transition = 'transform 0.2s ease';
      setTimeout(() => {
        if (draggingElement) {
          draggingElement.style.transition = '';
        }
      }, 200);
    }
    
    if (dragOverId !== null && draggingId !== dragOverId) {
      const dragOverElement = itemRefs.current.get(dragOverId);
      if (dragOverElement) {
        dragOverElement.style.backgroundColor = '';
        dragOverElement.style.borderColor = '#ddd';
      }
      
      const draggingIndex = items.findIndex(item => item.id === draggingId);
      const dragOverIndex = items.findIndex(item => item.id === dragOverId);
      
      if (draggingIndex !== -1 && dragOverIndex !== -1) {
        const newItems = [...items];
        const [draggedItem] = newItems.splice(draggingIndex, 1);
        newItems.splice(dragOverIndex, 0, draggedItem);
        setItems(newItems);
      }
    }
    
    setDraggingId(null);
    setDragOverId(null);
  };

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [draggingId, dragOverId, items]);

  return (
    <div style={styles.container} ref={containerRef}>
      <h2 style={styles.title}>可拖拽排序列表</h2>
      <p style={styles.instructions}>鼠标按住任意项目拖动进行排序</p>
      
      <div style={styles.listContainer}>
        {items.map(item => (
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
              ...styles.item,
              ...(item.id === draggingId ? styles.draggingItem : {}),
              ...(item.id === dragOverId ? styles.dragOverItem : {})
            }}
            onMouseDown={(e) => handleMouseDown(e, item.id)}
          >
            <div style={styles.handle}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="6" cy="8" r="1.5"/>
                <circle cx="12" cy="8" r="1.5"/>
                <circle cx="18" cy="8" r="1.5"/>
                <circle cx="6" cy="12" r="1.5"/>
                <circle cx="12" cy="12" r="1.5"/>
                <circle cx="18" cy="12" r="1.5"/>
                <circle cx="6" cy="16" r="1.5"/>
                <circle cx="12" cy="16" r="1.5"/>
                <circle cx="18" cy="16" r="1.5"/>
              </svg>
            </div>
            <span style={styles.itemText}>{item.text}</span>
            <div style={styles.orderIndicator}>#{items.findIndex(i => i.id === item.id) + 1}</div>
          </div>
        ))}
      </div>
      
      <div style={styles.footer}>
        <div style={styles.legend}>
          <div style={styles.legendItem}>
            <div style={{...styles.legendColor, backgroundColor: '#4CAF50'}}></div>
            <span>当前拖拽项</span>
          </div>
          <div style={styles.legendItem}>
            <div style={{...styles.legendColor, backgroundColor: '#2196F3'}}></div>
            <span>放置位置</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '600px',
    margin: '0 auto',
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
  } as React.CSSProperties,
  
  title: {
    textAlign: 'center' as const,
    color: '#333',
    marginBottom: '10px'
  } as React.CSSProperties,
  
  instructions: {
    textAlign: 'center' as const,
    color: '#666',
    marginBottom: '20px',
    fontSize: '14px'
  } as React.CSSProperties,
  
  listContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px'
  } as React.CSSProperties,
  
  item: {
    display: 'flex',
    alignItems: 'center',
    padding: '15px',
    backgroundColor: 'white',
    border: '2px solid #ddd',
    borderRadius: '6px',
    cursor: 'grab',
    userSelect: 'none' as const,
    transition: 'all 0.2s ease',
    position: 'relative' as const
  } as React.CSSProperties,
  
  draggingItem: {
    backgroundColor: '#4CAF50',
    color: 'white',
    cursor: 'grabbing'
  } as React.CSSProperties,
  
  dragOverItem: {
    borderColor: '#2196F3',
    borderStyle: 'dashed'
  } as React.CSSProperties,
  
  handle: {
    marginRight: '12px',
    color: '#999',
    display: 'flex',
    alignItems: 'center'
  } as React.CSSProperties,
  
  itemText: {
    flex: 1,
    fontSize: '16px'
  } as React.CSSProperties,
  
  orderIndicator: {
    backgroundColor: '#f0f0f0',
    color: '#666',
    padding: '4px 10px',
    borderRadius: '12px',
    fontSize: '14px',
    fontWeight: 'bold' as const
  } as React.CSSProperties,
  
  footer: {
    marginTop: '20px',
    paddingTop: '15px',
    borderTop: '1px solid #eee'
  } as React.CSSProperties,
  
  legend: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    flexWrap: 'wrap' as const
  } as React.CSSProperties,
  
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: '#666'
  } as React.CSSProperties,
  
  legendColor: {
    width: '16px',
    height: '16px',
    borderRadius: '4px'
  } as React.CSSProperties
};

export default DraggableSortList;