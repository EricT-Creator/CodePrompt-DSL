import React, { useState, useRef, useCallback, useEffect } from 'react';

interface Item {
  id: number;
  text: string;
}

const initialItems: Item[] = [
  { id: 1, text: 'Learn React' },
  { id: 2, text: 'Build components' },
  { id: 3, text: 'Write tests' },
  { id: 4, text: 'Deploy app' },
  { id: 5, text: 'Monitor performance' },
  { id: 6, text: 'Gather feedback' },
];

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);
  const [ghostStyle, setGhostStyle] = useState<React.CSSProperties>({});
  const [placeholderIndex, setPlaceholderIndex] = useState<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const startY = useRef(0);
  const offsetY = useRef(0);
  const currentY = useRef(0);

  const getMousePos = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if ('touches' in e) {
      return e.touches[0].clientY;
    }
    return e.clientY;
  }, []);

  const getClientY = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if ('touches' in e) {
      return e.touches[0].clientY;
    }
    return e.clientY;
  }, []);

  const getItemMidpoints = useCallback(() => {
    const midpoints: { index: number; y: number }[] = [];
    items.forEach((_, i) => {
      const el = itemRefs.current.get(items[i].id);
      if (el) {
        const rect = el.getBoundingClientRect();
        midpoints.push({ index: i, y: rect.top + rect.height / 2 });
      }
    });
    return midpoints;
  }, [items]);

  const handleStart = useCallback((e: React.MouseEvent | React.TouchEvent, index: number) => {
    e.preventDefault();
    const clientY = getClientY(e);
    startY.current = clientY;

    const el = itemRefs.current.get(items[index].id);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    offsetY.current = clientY - rect.top;

    setDragIndex(index);
    setPlaceholderIndex(index);
    setGhostStyle({
      position: 'fixed',
      top: rect.top,
      left: rect.left,
      width: rect.width,
      height: rect.height,
      opacity: 0.8,
      zIndex: 1000,
      pointerEvents: 'none',
      transform: 'scale(1.02)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    });
    currentY.current = rect.top;
  }, [items, getClientY]);

  const handleMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (dragIndex === null) return;
    e.preventDefault();
    const clientY = getClientY(e);
    const newTop = clientY - offsetY.current;
    currentY.current = newTop;

    setGhostStyle(prev => ({
      ...prev,
      top: newTop,
    }));

    const midpoints = getItemMidpoints();
    let newPlaceholderIndex = dragIndex;

    if (clientY < midpoints[0].y) {
      newPlaceholderIndex = 0;
    } else if (clientY > midpoints[midpoints.length - 1].y) {
      newPlaceholderIndex = items.length - 1;
    } else {
      for (let i = 0; i < midpoints.length - 1; i++) {
        if (clientY >= midpoints[i].y && clientY < midpoints[i + 1].y) {
          newPlaceholderIndex = midpoints[i + 1].index;
          break;
        }
      }
    }

    setPlaceholderIndex(newPlaceholderIndex);
    setOverIndex(newPlaceholderIndex);
  }, [dragIndex, items, getClientY, getItemMidpoints]);

  const handleEnd = useCallback(() => {
    if (dragIndex === null || placeholderIndex === null) return;

    const newItems = [...items];
    const [removed] = newItems.splice(dragIndex, 1);
    newItems.splice(placeholderIndex, 0, removed);
    setItems(newItems);

    setDragIndex(null);
    setOverIndex(null);
    setPlaceholderIndex(null);
    setGhostStyle({});
  }, [dragIndex, placeholderIndex, items]);

  useEffect(() => {
    const handleGlobalMove = (e: MouseEvent | TouchEvent) => {
      if (dragIndex === null) return;
      const clientY = 'touches' in e ? (e as TouchEvent).touches[0]?.clientY ?? 0 : (e as MouseEvent).clientY;
      const newTop = clientY - offsetY.current;
      currentY.current = newTop;
      setGhostStyle(prev => ({ ...prev, top: newTop }));

      const midpoints = getItemMidpoints();
      let newPlaceholderIndex = dragIndex;
      if (midpoints.length === 0) return;
      if (clientY < midpoints[0].y) {
        newPlaceholderIndex = 0;
      } else if (clientY > midpoints[midpoints.length - 1].y) {
        newPlaceholderIndex = items.length - 1;
      } else {
        for (let i = 0; i < midpoints.length - 1; i++) {
          if (clientY >= midpoints[i].y && clientY < midpoints[i + 1].y) {
            newPlaceholderIndex = midpoints[i + 1].index;
            break;
          }
        }
      }
      setPlaceholderIndex(newPlaceholderIndex);
      setOverIndex(newPlaceholderIndex);
    };

    const handleGlobalEnd = () => {
      if (dragIndex === null) return;
      handleEnd();
    };

    if (dragIndex !== null) {
      window.addEventListener('mousemove', handleGlobalMove);
      window.addEventListener('mouseup', handleGlobalEnd);
      window.addEventListener('touchmove', handleGlobalMove as EventListener, { passive: false });
      window.addEventListener('touchend', handleGlobalEnd);
    }
    return () => {
      window.removeEventListener('mousemove', handleGlobalMove);
      window.removeEventListener('mouseup', handleGlobalEnd);
      window.removeEventListener('touchmove', handleGlobalMove as EventListener);
      window.removeEventListener('touchend', handleGlobalEnd);
    };
  }, [dragIndex, handleEnd, items, getItemMidpoints]);

  return (
    <div style={{ padding: 24 }}>
      <style>{`
        .sort-list {
          max-width: 400px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .sort-list h2 {
          text-align: center;
          color: #333;
          margin-bottom: 16px;
        }
        .sort-list-item {
          display: flex;
          align-items: center;
          padding: 12px 16px;
          margin-bottom: 4px;
          background: #fff;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          cursor: grab;
          user-select: none;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
          box-sizing: border-box;
        }
        .sort-list-item:hover {
          border-color: #4a90d9;
          box-shadow: 0 2px 8px rgba(74,144,217,0.15);
        }
        .sort-list-item.dragging {
          opacity: 0;
        }
        .sort-list-item .grip {
          margin-right: 12px;
          color: #999;
          font-size: 16px;
          flex-shrink: 0;
        }
        .sort-list-item .item-text {
          flex: 1;
          color: #333;
          font-size: 14px;
        }
        .sort-list-item .item-number {
          color: #aaa;
          font-size: 12px;
          margin-left: 8px;
          flex-shrink: 0;
        }
        .placeholder-slot {
          height: 48px;
          margin-bottom: 4px;
          border: 2px dashed #4a90d9;
          border-radius: 8px;
          background: rgba(74,144,217,0.05);
          transition: height 0.15s ease;
        }
        .ghost-element {
          background: #4a90d9;
          color: #fff;
          border-radius: 8px;
          display: flex;
          align-items: center;
          padding: 12px 16px;
          box-sizing: border-box;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 14px;
        }
        .ghost-element .grip {
          margin-right: 12px;
          font-size: 16px;
          flex-shrink: 0;
        }
      `}</style>
      <div className="sort-list">
        <h2>📝 Task List</h2>
        <div ref={listRef}>
          {items.map((item, index) => {
            const isDragging = dragIndex === index;
            const isPlaceholder = placeholderIndex === index && dragIndex !== index;

            return (
              <React.Fragment key={item.id}>
                {isPlaceholder && dragIndex !== null && (
                  <div className="placeholder-slot" />
                )}
                <div
                  ref={(el) => {
                    if (el) itemRefs.current.set(item.id, el);
                    else itemRefs.current.delete(item.id);
                  }}
                  className={`sort-list-item${isDragging ? ' dragging' : ''}`}
                  onMouseDown={(e) => handleStart(e, index)}
                  onTouchStart={(e) => handleStart(e, index)}
                >
                  <span className="grip">⠿</span>
                  <span className="item-text">{item.text}</span>
                  <span className="item-number">#{index + 1}</span>
                </div>
              </React.Fragment>
            );
          })}
          {placeholderIndex === items.length && dragIndex !== null && (
            <div className="placeholder-slot" />
          )}
        </div>
        {Object.keys(ghostStyle).length > 0 && dragIndex !== null && (
          <div className="ghost-element" style={ghostStyle}>
            <span className="grip">⠿</span>
            <span>{items[dragIndex].text}</span>
          </div>
        )}
      </div>
    </div>
  );
}
