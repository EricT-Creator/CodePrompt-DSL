import React, { useState, useRef } from 'react';

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState(['Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5']);
  const [draggingItem, setDraggingItem] = useState<number | null>(null);
  const [placeholderIndex, setPlaceholderIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLUListElement>(null);

  const handleMouseDown = (index: number) => {
    setDraggingItem(index);
    setPlaceholderIndex(index);
  };

  const handleMouseMove = (e: MouseEvent, index: number) => {
    if (draggingItem === null) return;
    setPlaceholderIndex(index);
  };

  const handleMouseUp = () => {
    if (draggingItem !== null && placeholderIndex !== null) {
      const newItems = [...items];
      const item = newItems.splice(draggingItem, 1)[0];
      newItems.splice(placeholderIndex, 0, item);
      setItems(newItems);
    }
    setDraggingItem(null);
    setPlaceholderIndex(null);
  };

  return (
    <ul ref={containerRef} style={{ listStyle: 'none', padding: 0 }}>
      {items.map((item, index) => (
        <li
          key={item}
          onMouseDown={() => handleMouseDown(index)}
          onMouseMove={(e) => handleMouseMove(e as unknown as MouseEvent, index)}
          onMouseUp={handleMouseUp}
          style={{
            padding: '10px',
            margin: '5px',
            background: draggingItem === index ? '#ddd' : '#eee',
            border: placeholderIndex === index ? '2px dashed blue' : '1px solid #ccc',
            cursor: 'grab',
          }}
        >
          {item}
        </li>
      ))}
    </ul>
  );
};

export default DraggableSortList;
