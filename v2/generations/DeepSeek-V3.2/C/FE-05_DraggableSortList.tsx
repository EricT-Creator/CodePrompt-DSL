import React, { useState, useRef, useEffect, TouchEvent, MouseEvent } from 'react';

interface Item {
  id: number;
  text: string;
}

const initialItems: Item[] = [
  { id: 1, text: '任务 1: 完成项目设计' },
  { id: 2, text: '任务 2: 编写组件文档' },
  { id: 3, text: '任务 3: 代码审查' },
  { id: 4, text: '任务 4: 测试验证' },
  { id: 5, text: '任务 5: 部署上线' },
];

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragStartY, setDragStartY] = useState<number>(0);
  const [currentDragY, setCurrentDragY] = useState<number>(0);
  const [dragOffset, setDragOffset] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const getItemHeight = () => {
    if (!containerRef.current) return 60;
    const firstItem = containerRef.current.querySelector('.draggable-item');
    return firstItem ? firstItem.clientHeight : 60;
  };

  const handleMouseDown = (e: MouseEvent<HTMLDivElement>, id: number) => {
    e.preventDefault();
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setDraggingId(id);
    setDragStartY(e.clientY);
    setCurrentDragY(e.clientY);
    setDragOffset(e.clientY - rect.top);
  };

  const handleTouchStart = (e: TouchEvent<HTMLDivElement>, id: number) => {
    const touch = e.touches[0];
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setDraggingId(id);
    setDragStartY(touch.clientY);
    setCurrentDragY(touch.clientY);
    setDragOffset(touch.clientY - rect.top);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (draggingId === null) return;
    setCurrentDragY(e.clientY);
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (draggingId === null) return;
    const touch = e.touches[0];
    setCurrentDragY(touch.clientY);
  };

  const handleMouseUp = () => {
    if (draggingId === null) return;
    finalizeDrag();
  };

  const handleTouchEnd = () => {
    if (draggingId === null) return;
    finalizeDrag();
  };

  const finalizeDrag = () => {
    if (draggingId === null || dragStartY === currentDragY) {
      setDraggingId(null);
      return;
    }

    const itemHeight = getItemHeight();
    const deltaY = currentDragY - dragStartY;
    const moveSteps = Math.round(deltaY / itemHeight);

    if (moveSteps !== 0) {
      const oldIndex = items.findIndex(item => item.id === draggingId);
      const newIndex = Math.max(0, Math.min(items.length - 1, oldIndex + moveSteps));
      
      if (oldIndex !== newIndex) {
        const newItems = [...items];
        const [movedItem] = newItems.splice(oldIndex, 1);
        newItems.splice(newIndex, 0, movedItem);
        setItems(newItems);
      }
    }

    setDraggingId(null);
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      if (draggingId !== null) {
        finalizeDrag();
      }
    };

    const handleGlobalTouchEnd = () => {
      if (draggingId !== null) {
        finalizeDrag();
      }
    };

    document.addEventListener('mouseup', handleGlobalMouseUp);
    document.addEventListener('touchend', handleGlobalTouchEnd);

    return () => {
      document.removeEventListener('mouseup', handleGlobalMouseUp);
      document.removeEventListener('touchend', handleGlobalTouchEnd);
    };
  }, [draggingId, items]);

  const getDraggingStyle = (id: number) => {
    if (id !== draggingId) return {};
    
    const itemHeight = getItemHeight();
    const deltaY = currentDragY - dragStartY;
    const snappedDelta = Math.round(deltaY / itemHeight) * itemHeight;
    
    return {
      transform: `translateY(${snappedDelta}px)`,
      zIndex: 1000,
      opacity: 0.8,
      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
    };
  };

  return (
    <div 
      className="draggable-list-container" 
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
      onMouseUp={handleMouseUp}
      onTouchEnd={handleTouchEnd}
      style={{
        userSelect: 'none',
        touchAction: 'none',
      }}
    >
      <h2>可拖拽排序列表</h2>
      <p>使用鼠标或触摸拖拽项目进行重新排序</p>
      
      <div className="draggable-list">
        {items.map((item) => (
          <div
            key={item.id}
            className={`draggable-item ${item.id === draggingId ? 'dragging' : ''}`}
            style={getDraggingStyle(item.id)}
            onMouseDown={(e) => handleMouseDown(e, item.id)}
            onTouchStart={(e) => handleTouchStart(e, item.id)}
          >
            <div className="drag-handle">⋮⋮</div>
            <div className="item-content">
              <span className="item-id">{item.id}.</span>
              <span className="item-text">{item.text}</span>
            </div>
            <div className="item-indicator">
              {item.id === draggingId ? '正在拖动...' : '可拖动'}
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .draggable-list-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }
        
        h2 {
          color: #333;
          margin-bottom: 10px;
        }
        
        p {
          color: #666;
          margin-bottom: 20px;
        }
        
        .draggable-list {
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          overflow: hidden;
          background: #fff;
        }
        
        .draggable-item {
          display: flex;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid #f0f0f0;
          background: #fff;
          cursor: grab;
          transition: background-color 0.2s, transform 0.2s;
          position: relative;
        }
        
        .draggable-item:last-child {
          border-bottom: none;
        }
        
        .draggable-item:hover {
          background-color: #f8f9fa;
        }
        
        .draggable-item.dragging {
          cursor: grabbing;
          background-color: #e3f2fd;
        }
        
        .drag-handle {
          color: #757575;
          font-size: 18px;
          margin-right: 12px;
          user-select: none;
          cursor: inherit;
        }
        
        .item-content {
          flex: 1;
          display: flex;
          align-items: center;
        }
        
        .item-id {
          font-weight: bold;
          color: #1976d2;
          margin-right: 8px;
          min-width: 20px;
        }
        
        .item-text {
          color: #333;
          font-size: 15px;
        }
        
        .item-indicator {
          font-size: 12px;
          color: #888;
          padding: 4px 8px;
          background: #f5f5f5;
          border-radius: 12px;
          transition: all 0.2s;
        }
        
        .draggable-item.dragging .item-indicator {
          background: #bbdefb;
          color: #1565c0;
        }
      `}</style>
    </div>
  );
};

export default DraggableSortList;