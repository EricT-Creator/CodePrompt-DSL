import React, { useState, useRef, useCallback, useEffect } from "react";

interface DragState {
  isDragging: boolean;
  dragIndex: number;
  overIndex: number;
  startY: number;
  currentY: number;
}

const initialItems = [
  { id: 1, text: "Learn TypeScript" },
  { id: 2, text: "Build React Components" },
  { id: 3, text: "Master CSS Grid" },
  { id: 4, text: "Study Algorithms" },
  { id: 5, text: "Practice System Design" },
  { id: 6, text: "Write Unit Tests" },
  { id: 7, text: "Deploy to Production" },
];

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: 400,
    margin: "40px auto",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    marginBottom: 16,
    textAlign: "center" as const,
    color: "#1a1a2e",
  },
  list: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    position: "relative" as const,
  },
  item: {
    padding: "12px 16px",
    marginBottom: 4,
    backgroundColor: "#ffffff",
    border: "1px solid #e0e0e0",
    borderRadius: 6,
    cursor: "grab",
    userSelect: "none" as const,
    display: "flex",
    alignItems: "center",
    gap: 10,
    transition: "background-color 0.15s, box-shadow 0.15s",
  },
  itemDragging: {
    opacity: 0.9,
    backgroundColor: "#e8f0fe",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    zIndex: 10,
    cursor: "grabbing",
  },
  itemOver: {
    borderTop: "2px solid #4285f4",
  },
  handle: {
    color: "#999",
    fontSize: 18,
    lineHeight: 1,
    flexShrink: 0,
  },
  placeholder: {
    padding: "12px 16px",
    marginBottom: 4,
    backgroundColor: "#f0f4ff",
    border: "2px dashed #4285f4",
    borderRadius: 6,
    height: 44,
    boxSizing: "border-box" as const,
  },
};

export default function DraggableSortList() {
  const [items, setItems] = useState(initialItems);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    dragIndex: -1,
    overIndex: -1,
    startY: 0,
    currentY: 0,
  });

  const listRef = useRef<HTMLUListElement>(null);
  const itemRefs = useRef<Map<number, HTMLLIElement>>(new Map());
  const dragStateRef = useRef(dragState);
  dragStateRef.current = dragState;

  const getClientY = (e: MouseEvent | TouchEvent): number => {
    if ("touches" in e) {
      return e.touches[0]?.clientY ?? e.changedTouches[0]?.clientY ?? 0;
    }
    return e.clientY;
  };

  const getOverIndex = useCallback(
    (clientY: number): number => {
      const entries = Array.from(itemRefs.current.entries());
      for (let i = 0; i < items.length; i++) {
        const el = itemRefs.current.get(i);
        if (el) {
          const rect = el.getBoundingClientRect();
          const midY = rect.top + rect.height / 2;
          if (clientY < midY) {
            return i;
          }
        }
      }
      return items.length - 1;
    },
    [items.length]
  );

  const handlePointerDown = useCallback(
    (index: number, e: React.MouseEvent | React.TouchEvent) => {
      e.preventDefault();
      const clientY =
        "touches" in e.nativeEvent
          ? e.nativeEvent.touches[0].clientY
          : (e.nativeEvent as MouseEvent).clientY;

      setDragState({
        isDragging: true,
        dragIndex: index,
        overIndex: index,
        startY: clientY,
        currentY: clientY,
      });
    },
    []
  );

  useEffect(() => {
    if (!dragState.isDragging) return;

    const handleMove = (e: MouseEvent | TouchEvent) => {
      e.preventDefault();
      const clientY = getClientY(e);
      const overIdx = getOverIndex(clientY);
      setDragState((prev) => ({
        ...prev,
        currentY: clientY,
        overIndex: overIdx,
      }));
    };

    const handleEnd = (e: MouseEvent | TouchEvent) => {
      const state = dragStateRef.current;
      if (state.isDragging && state.dragIndex !== state.overIndex) {
        setItems((prev) => {
          const next = [...prev];
          const [removed] = next.splice(state.dragIndex, 1);
          next.splice(state.overIndex, 0, removed);
          return next;
        });
      }
      setDragState({
        isDragging: false,
        dragIndex: -1,
        overIndex: -1,
        startY: 0,
        currentY: 0,
      });
    };

    window.addEventListener("mousemove", handleMove, { passive: false });
    window.addEventListener("mouseup", handleEnd);
    window.addEventListener("touchmove", handleMove, { passive: false });
    window.addEventListener("touchend", handleEnd);

    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleEnd);
      window.removeEventListener("touchmove", handleMove);
      window.removeEventListener("touchend", handleEnd);
    };
  }, [dragState.isDragging, getOverIndex]);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Draggable Sort List</h2>
      <ul ref={listRef} style={styles.list}>
        {items.map((item, index) => {
          const isDraggedItem = dragState.isDragging && dragState.dragIndex === index;
          const isOverItem = dragState.isDragging && dragState.overIndex === index && dragState.dragIndex !== index;

          return (
            <React.Fragment key={item.id}>
              {isOverItem && dragState.dragIndex > index && (
                <li style={styles.placeholder} aria-hidden />
              )}
              <li
                ref={(el) => {
                  if (el) itemRefs.current.set(index, el);
                }}
                style={{
                  ...styles.item,
                  ...(isDraggedItem ? styles.itemDragging : {}),
                }}
                onMouseDown={(e) => handlePointerDown(index, e)}
                onTouchStart={(e) => handlePointerDown(index, e)}
              >
                <span style={styles.handle}>⠿</span>
                <span>{item.text}</span>
              </li>
              {isOverItem && dragState.dragIndex < index && (
                <li style={styles.placeholder} aria-hidden />
              )}
            </React.Fragment>
          );
        })}
      </ul>
    </div>
  );
}
