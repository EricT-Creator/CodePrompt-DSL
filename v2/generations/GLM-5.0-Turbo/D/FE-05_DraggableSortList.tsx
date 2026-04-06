import React, { useState, useRef, useCallback, useEffect } from 'react';

interface DragItem {
  id: string;
  label: string;
}

const initialItems: DragItem[] = [
  { id: 'item-1', label: '项目 Alpha' },
  { id: 'item-2', label: '项目 Beta' },
  { id: 'item-3', label: '项目 Gamma' },
  { id: 'item-4', label: '项目 Delta' },
  { id: 'item-5', label: '项目 Epsilon' },
  { id: 'item-6', label: '项目 Zeta' },
];

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<DragItem[]>(initialItems);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [dragOffsetY, setDragOffsetY] = useState<number>(0);
  const [dragStartY, setDragStartY] = useState<number>(0);
  const [placeholderStyle, setPlaceholderStyle] = useState<React.CSSProperties>({});
  const listRef = useRef<HTMLUListElement>(null);
  const dragCloneRef = useRef<HTMLDivElement | null>(null);

  const getItemHeight = useCallback((index: number): number => {
    if (!listRef.current) return 0;
    const li = listRef.current.children[index] as HTMLElement;
    return li ? li.getBoundingClientRect().height : 0;
  }, []);

  const getBoundingRect = useCallback((index: number): DOMRect | null => {
    if (!listRef.current) return null;
    const li = listRef.current.children[index] as HTMLElement;
    return li ? li.getBoundingClientRect() : null;
  }, []);

  const handlePointerDown = useCallback((e: React.PointerEvent, index: number) => {
    e.preventDefault();
    const rect = getBoundingRect(index);
    if (!rect) return;
    setDragIndex(index);
    setDragStartY(rect.top);
    setDragOffsetY(e.clientY - rect.top);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    if (dragCloneRef.current) {
      dragCloneRef.current.remove();
      dragCloneRef.current = null;
    }

    const clone = document.createElement('div');
    clone.className = 'drag-clone';
    clone.textContent = items[index].label;
    clone.style.position = 'fixed';
    clone.style.width = `${rect.width}px`;
    clone.style.height = `${rect.height}px`;
    clone.style.left = `${rect.left}px`;
    clone.style.top = `${rect.top}px`;
    clone.style.zIndex = '9999';
    clone.style.opacity = '0.85';
    clone.style.pointerEvents = 'none';
    clone.style.background = '#4a90d9';
    clone.style.color = '#fff';
    clone.style.padding = '12px 16px';
    clone.style.borderRadius = '8px';
    clone.style.boxShadow = '0 8px 24px rgba(0,0,0,0.25)';
    clone.style.fontSize = '15px';
    clone.style.fontWeight = '500';
    clone.style.transform = 'scale(1.03)';
    clone.style.transition = 'transform 0.15s ease';
    document.body.appendChild(clone);
    dragCloneRef.current = clone;

    setPlaceholderStyle({
      height: `${rect.height}px`,
      background: 'rgba(74, 144, 217, 0.12)',
      border: '2px dashed #4a90d9',
      borderRadius: '8px',
      transition: 'height 0.2s ease',
    });
  }, [items, getBoundingRect]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (dragIndex === null) return;

    if (dragCloneRef.current) {
      dragCloneRef.current.style.top = `${e.clientY - dragOffsetY}px`;
    }

    if (!listRef.current) return;

    let newIndex = dragIndex;
    const children = Array.from(listRef.current.children) as HTMLElement[];
    for (let i = 0; i < children.length; i++) {
      const rect = children[i].getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      if (e.clientY < mid) {
        newIndex = i;
        break;
      }
      if (i === children.length - 1) {
        newIndex = children.length;
      }
    }

    setDragOverIndex(newIndex);
  }, [dragIndex, dragOffsetY]);

  const handlePointerUp = useCallback(() => {
    if (dragIndex === null) return;

    if (dragCloneRef.current) {
      dragCloneRef.current.remove();
      dragCloneRef.current = null;
    }

    if (dragOverIndex !== null && dragOverIndex !== dragIndex) {
      const updated = [...items];
      const [moved] = updated.splice(dragIndex, 1);
      const insertAt = dragOverIndex > dragIndex ? dragOverIndex - 1 : dragOverIndex;
      updated.splice(dragOverIndex > dragIndex ? dragOverIndex - 1 : dragOverIndex, 0, moved);
      setItems(updated);
    }

    setDragIndex(null);
    setDragOverIndex(null);
    setPlaceholderStyle({});
  }, [dragIndex, dragOverIndex, items]);

  useEffect(() => {
    const handleGlobalPointerUp = () => {
      if (dragCloneRef.current) {
        dragCloneRef.current.remove();
        dragCloneRef.current = null;
      }
      setDragIndex(null);
      setDragOverIndex(null);
      setPlaceholderStyle({});
    };
    window.addEventListener('pointerup', handleGlobalPointerUp);
    return () => window.removeEventListener('pointerup', handleGlobalPointerUp);
  }, []);

  const renderItems = () => {
    let placeholderInserted = false;
    const elements: React.ReactNode[] = [];

    for (let i = 0; i < items.length; i++) {
      const isDragging = i === dragIndex;
      const showPlaceholder = dragOverIndex !== null && dragOverIndex !== dragIndex && !placeholderInserted && ((dragOverIndex < i && dragOverIndex <= dragIndex) || (dragOverIndex > i && dragOverIndex > dragIndex)) === false;

      if (dragOverIndex !== null && dragOverIndex !== dragIndex && !placeholderInserted) {
        if (dragOverIndex === i) {
          elements.push(
            <li key="placeholder" style={placeholderStyle} className="drag-placeholder" />
          );
          placeholderInserted = true;
        }
      }

      elements.push(
        <li
          key={items[i].id}
          className={`sort-item ${isDragging ? 'dragging' : ''} ${dragOverIndex === i ? 'drag-over' : ''}`}
          onPointerDown={(e) => handlePointerDown(e, i)}
          style={{
            padding: '12px 16px',
            background: isDragging ? 'rgba(74, 144, 217, 0.15)' : dragOverIndex === i ? 'rgba(74, 144, 217, 0.08)' : '#fff',
            borderRadius: '8px',
            cursor: isDragging ? 'grabbing' : 'grab',
            userSelect: 'none',
            touchAction: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            transition: 'background 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease',
            boxShadow: isDragging ? '0 4px 12px rgba(0,0,0,0.1)' : dragOverIndex === i ? '0 2px 8px rgba(74, 144, 217, 0.2)' : '0 1px 3px rgba(0,0,0,0.08)',
            transform: isDragging ? 'scale(0.98)' : dragOverIndex === i ? 'translateY(-1px)' : 'none',
            border: dragOverIndex === i ? '1px solid #4a90d9' : '1px solid #e8eaed',
          }}
        >
          <span style={{ fontSize: '15px', color: isDragging ? '#4a90d9' : '#333' }}>
            ⣿ {items[i].label}
          </span>
          <span style={{ color: '#aaa', fontSize: '13px' }}>
            #{i + 1}
          </span>
        </li>
      );
    }

    if (dragOverIndex !== null && dragOverIndex !== dragIndex && !placeholderInserted && dragOverIndex === items.length) {
      elements.push(
        <li key="placeholder" style={placeholderStyle} className="drag-placeholder" />
      );
    }

    return elements;
  };

  return (
    <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', maxWidth: '480px', margin: '40px auto', padding: '0 16px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', color: '#1a1a1a' }}>
        可拖拽排序列表
      </h2>
      <p style={{ fontSize: '13px', color: '#888', marginBottom: '20px' }}>
        拖动列表项以调整顺序
      </p>
      <ul
        ref={listRef}
        style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}
      >
        {renderItems()}
      </ul>
    </div>
  );
};

export default DraggableSortList;
