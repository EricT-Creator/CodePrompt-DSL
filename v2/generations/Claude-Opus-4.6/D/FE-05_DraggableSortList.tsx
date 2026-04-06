import React, { useState, useRef, useCallback, useEffect } from "react";

interface DragState {
  dragging: boolean;
  dragIndex: number;
  overIndex: number;
  startY: number;
  currentY: number;
}

const initialItems = [
  "🍎 Apple",
  "🍌 Banana",
  "🍒 Cherry",
  "🍇 Grapes",
  "🍋 Lemon",
  "🥝 Kiwi",
  "🍑 Peach",
];

const DraggableSortList: React.FC = () => {
  const [items, setItems] = useState<string[]>(initialItems);
  const [dragState, setDragState] = useState<DragState>({
    dragging: false,
    dragIndex: -1,
    overIndex: -1,
    startY: 0,
    currentY: 0,
  });

  const listRef = useRef<HTMLUListElement>(null);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);

  const getIndexFromY = useCallback(
    (clientY: number): number => {
      for (let i = 0; i < itemRefs.current.length; i++) {
        const el = itemRefs.current[i];
        if (el) {
          const rect = el.getBoundingClientRect();
          const midY = rect.top + rect.height / 2;
          if (clientY < midY) return i;
        }
      }
      return items.length - 1;
    },
    [items.length]
  );

  const handlePointerDown = useCallback(
    (index: number, clientY: number) => {
      setDragState({
        dragging: true,
        dragIndex: index,
        overIndex: index,
        startY: clientY,
        currentY: clientY,
      });
    },
    []
  );

  const handlePointerMove = useCallback(
    (clientY: number) => {
      if (!dragState.dragging) return;
      const overIdx = getIndexFromY(clientY);
      setDragState((prev) => ({
        ...prev,
        currentY: clientY,
        overIndex: overIdx,
      }));
    },
    [dragState.dragging, getIndexFromY]
  );

  const handlePointerUp = useCallback(() => {
    if (!dragState.dragging) return;
    const { dragIndex, overIndex } = dragState;
    if (dragIndex !== overIndex) {
      setItems((prev) => {
        const next = [...prev];
        const [removed] = next.splice(dragIndex, 1);
        next.splice(overIndex, 0, removed);
        return next;
      });
    }
    setDragState({
      dragging: false,
      dragIndex: -1,
      overIndex: -1,
      startY: 0,
      currentY: 0,
    });
  }, [dragState]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      e.preventDefault();
      handlePointerMove(e.clientY);
    };
    const onMouseUp = () => handlePointerUp();
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        handlePointerMove(e.touches[0].clientY);
      }
    };
    const onTouchEnd = () => handlePointerUp();

    if (dragState.dragging) {
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
      window.addEventListener("touchmove", onTouchMove, { passive: false });
      window.addEventListener("touchend", onTouchEnd);
    }

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [dragState.dragging, handlePointerMove, handlePointerUp]);

  const offsetY = dragState.currentY - dragState.startY;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Draggable Sort List</h2>
      <ul ref={listRef} style={styles.list}>
        {items.map((item, index) => {
          const isDragging = dragState.dragging && dragState.dragIndex === index;
          const isOver = dragState.dragging && dragState.overIndex === index && dragState.dragIndex !== index;

          let itemStyle: React.CSSProperties = {
            ...styles.item,
            ...(isDragging
              ? {
                  transform: `translateY(${offsetY}px)`,
                  zIndex: 10,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
                  opacity: 0.9,
                  transition: "box-shadow 0.2s",
                }
              : {}),
            ...(isOver
              ? {
                  borderTop: "3px solid #4a90d9",
                  paddingTop: "13px",
                }
              : {}),
          };

          return (
            <li
              key={`${item}-${index}`}
              ref={(el) => {
                itemRefs.current[index] = el;
              }}
              style={itemStyle}
              onMouseDown={(e) => {
                e.preventDefault();
                handlePointerDown(index, e.clientY);
              }}
              onTouchStart={(e) => {
                if (e.touches.length === 1) {
                  handlePointerDown(index, e.touches[0].clientY);
                }
              }}
            >
              <span style={styles.handle}>☰</span>
              <span style={styles.text}>{item}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "400px",
    margin: "40px auto",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  title: {
    textAlign: "center",
    color: "#333",
    marginBottom: "20px",
  },
  list: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    userSelect: "none",
  },
  item: {
    display: "flex",
    alignItems: "center",
    padding: "16px",
    marginBottom: "8px",
    backgroundColor: "#fff",
    borderRadius: "8px",
    border: "1px solid #e0e0e0",
    cursor: "grab",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
    position: "relative",
  },
  handle: {
    marginRight: "12px",
    fontSize: "18px",
    color: "#999",
  },
  text: {
    fontSize: "16px",
    color: "#333",
  },
};

export default DraggableSortList;
