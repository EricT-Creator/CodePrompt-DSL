import React, { useState, useRef, TouchEvent, MouseEvent } from 'react';

const DraggableSortList = () => {
  const [items, setItems] = useState<string[]>(['Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5']);
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const handleStart = (index: number) => {
    setDraggingIndex(index);
  };

  const handleMove = (index: number) => {
    if (draggingIndex === null || draggingIndex === index) return;

    const newItems = [...items];
    const draggedItem = newItems.splice(draggingIndex, 1)[0];
    newItems.splice(index, 0, draggedItem);
    setItems(newItems);
    setDraggingIndex(index);
  };

  const handleEnd = () => {
    setDraggingIndex(null);
  };

  return (
    <div ref={listRef} style={{ width: '300px', margin: '20px auto', userSelect: 'none' }}>
      {items.map((item, index) => (
        <div
          key={item}
          onMouseDown={() => handleStart(index)}
          onMouseEnter={() => handleMove(index)}
          onMouseUp={handleEnd}
          onTouchStart={() => handleStart(index)}
          onTouchMove={(e: TouchEvent) => {
            const touch = e.touches[0];
            const elements = document.elementsFromPoint(touch.clientX, touch.clientY);
            const target = elements.find(el => el.getAttribute('data-index') !== null);
            if (target) {
              const targetIndex = parseInt(target.getAttribute('data-index')!);
              handleMove(targetIndex);
            }
          }}
          onTouchEnd={handleEnd}
          data-index={index}
          style={{
            padding: '10px',
            margin: '5px 0',
            backgroundColor: draggingIndex === index ? '#ddd' : '#f9f9f9',
            border: '1px solid #ccc',
            cursor: 'grab',
            transition: 'background-color 0.2s'
          }}
        >
          {item}
        </div>
      ))}
    </div>
  );
};

export default DraggableSortList;