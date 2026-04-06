import React, { useReducer, useRef, useState, DragEvent } from 'react';

type Item = { id: number; text: string };

const DraggableSortList = () => {
  const [items, setItems] = useState<Item[]>([
    { id: 1, text: 'Item 1' },
    { id: 2, text: 'Item 2' },
    { id: 3, text: 'Item 3' },
    { id: 4, text: 'Item 4' },
    { id: 5, text: 'Item 5' },
  ]);

  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);

  const handleMouseDown = (index: number) => {
    setDraggingIndex(index);
  };

  const handleMouseMove = (index: number, e: MouseEvent) => {
    if (draggingIndex === null || draggingIndex === index) return;

    const newItems = [...items];
    const draggedItem = newItems.splice(draggingIndex, 1)[0];
    newItems.splice(index, 0, draggedItem);
    setItems(newItems);
    setDraggingIndex(index);
  };

  const handleMouseUp = () => {
    setDraggingIndex(null);
  };

  return (
    <ul style={{ listStyle: 'none', padding: 0 }}>
      {items.map((item, index) => (
        <li
          key={item.id}
          onMouseDown={() => handleMouseDown(index)}
          onMouseMove={(e) => handleMouseMove(index, e.nativeEvent)}
          onMouseUp={handleMouseUp}
          style={{
            padding: '10px',
            border: '1px solid #ccc',
            marginBottom: '5px',
            cursor: 'grab',
            backgroundColor: draggingIndex === index ? '#eee' : 'white',
          }}
        >
          {item.text}
        </li>
      ))}
    </ul>
  );
};

export default DraggableSortList;
