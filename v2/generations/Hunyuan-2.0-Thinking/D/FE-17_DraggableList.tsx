import React, { useState } from 'react';

interface Item {
  id: number;
  text: string;
}

const DraggableList: React.FC = () => {
  const [items, setItems] = useState<Item[]>([
    { id: 1, text: '项目一' },
    { id: 2, text: '项目二' },
    { id: 3, text: '项目三' },
    { id: 4, text: '项目四' },
    { id: 5, text: '项目五' }
  ]);
  const [draggedId, setDraggedId] = useState<number | null>(null);

  const handleDragStart = (e: React.DragEvent, id: number) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, targetId: number) => {
    e.preventDefault();
    if (draggedId === null || draggedId === targetId) return;

    const draggedIndex = items.findIndex(item => item.id === draggedId);
    const targetIndex = items.findIndex(item => item.id === targetId);
    
    const newItems = [...items];
    const [draggedItem] = newItems.splice(draggedIndex, 1);
    newItems.splice(targetIndex, 0, draggedItem);
    
    setItems(newItems);
    setDraggedId(null);
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-xl font-bold mb-4">可拖拽列表</h2>
      <ul className="space-y-2">
        {items.map(item => (
          <li
            key={item.id}
            draggable
            onDragStart={(e) => handleDragStart(e, item.id)}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, item.id)}
            className={`p-3 border rounded cursor-move transition-opacity ${draggedId === item.id ? 'opacity-50' : 'opacity-100'}`}
          >
            {item.text}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default DraggableList;