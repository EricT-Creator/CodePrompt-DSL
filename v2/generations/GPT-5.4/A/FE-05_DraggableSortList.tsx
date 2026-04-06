import React, { useEffect, useMemo, useRef, useState } from "react";

type Item = {
  id: number;
  title: string;
  detail: string;
};

type DragState = {
  sourceIndex: number;
  targetIndex: number;
  pointerY: number;
  offsetY: number;
  itemWidth: number;
  itemHeight: number;
  containerLeft: number;
};

const INITIAL_ITEMS: Item[] = [
  { id: 1, title: "Write spec", detail: "Draft the sorting interaction requirements." },
  { id: 2, title: "Collect feedback", detail: "Review the prototype with the design team." },
  { id: 3, title: "Implement UI", detail: "Build the draggable list interactions." },
  { id: 4, title: "Test mobile", detail: "Verify touch gestures on small screens." },
  { id: 5, title: "Ship release", detail: "Prepare the changelog and publish." },
  { id: 6, title: "Monitor usage", detail: "Watch for regressions after rollout." },
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function getClientY(event: MouseEvent | TouchEvent | React.MouseEvent | React.TouchEvent): number {
  if ("touches" in event && event.touches.length > 0) {
    return event.touches[0].clientY;
  }

  if ("changedTouches" in event && event.changedTouches.length > 0) {
    return event.changedTouches[0].clientY;
  }

  return (event as MouseEvent).clientY;
}

export default function DraggableSortList(): JSX.Element {
  const [items, setItems] = useState<Item[]>(INITIAL_ITEMS);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const draggedItem = dragState ? items[dragState.sourceIndex] : null;

  const projectedItems = useMemo(() => {
    if (!dragState) {
      return items.map((item) => ({ item, isPlaceholder: false }));
    }

    const reordered = items.slice();
    const [moving] = reordered.splice(dragState.sourceIndex, 1);
    reordered.splice(dragState.targetIndex, 0, moving);

    return reordered.map((item, index) => ({
      item,
      isPlaceholder: item.id === moving.id && index === dragState.targetIndex,
    }));
  }, [dragState, items]);

  useEffect(() => {
    if (!dragState) {
      return undefined;
    }

    const updateTarget = (clientY: number) => {
      const container = containerRef.current;
      if (!container) {
        return;
      }

      const rect = container.getBoundingClientRect();
      const relativeY = clientY - rect.top - dragState.offsetY + dragState.itemHeight / 2;
      const nextIndex = clamp(Math.floor(relativeY / dragState.itemHeight), 0, items.length - 1);

      setDragState((current) =>
        current
          ? {
              ...current,
              pointerY: clientY,
              targetIndex: nextIndex,
            }
          : current,
      );
    };

    const handleMouseMove = (event: MouseEvent) => {
      event.preventDefault();
      updateTarget(event.clientY);
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (event.touches.length === 0) {
        return;
      }
      event.preventDefault();
      updateTarget(event.touches[0].clientY);
    };

    const finishDrag = () => {
      setItems((currentItems) => {
        if (!dragState || dragState.sourceIndex === dragState.targetIndex) {
          return currentItems;
        }

        const reordered = currentItems.slice();
        const [moving] = reordered.splice(dragState.sourceIndex, 1);
        reordered.splice(dragState.targetIndex, 0, moving);
        return reordered;
      });
      setDragState(null);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", finishDrag);
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", finishDrag);
    window.addEventListener("touchcancel", finishDrag);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", finishDrag);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", finishDrag);
      window.removeEventListener("touchcancel", finishDrag);
    };
  }, [dragState, items.length]);

  const startDrag = (
    index: number,
    event: React.MouseEvent<HTMLButtonElement> | React.TouchEvent<HTMLButtonElement>,
  ) => {
    const target = event.currentTarget.closest("li");
    const container = containerRef.current;

    if (!target || !container) {
      return;
    }

    if ("button" in event && event.button !== 0) {
      return;
    }

    const rect = target.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    const clientY = getClientY(event);

    if ("preventDefault" in event) {
      event.preventDefault();
    }

    setDragState({
      sourceIndex: index,
      targetIndex: index,
      pointerY: clientY,
      offsetY: clientY - rect.top,
      itemWidth: rect.width,
      itemHeight: rect.height,
      containerLeft: containerRect.left,
    });
  };

  return (
    <div className="drag-sort-root">
      <style>{`
        .drag-sort-root {
          min-height: 100%;
          background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
          padding: 24px;
          font-family: Arial, Helvetica, sans-serif;
          color: #0f172a;
        }
        .drag-sort-panel {
          max-width: 760px;
          margin: 0 auto;
          background: #ffffff;
          border: 1px solid #dbeafe;
          border-radius: 20px;
          box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
          padding: 24px;
        }
        .drag-sort-title {
          margin: 0 0 8px;
          font-size: 28px;
          font-weight: 700;
        }
        .drag-sort-subtitle {
          margin: 0 0 20px;
          line-height: 1.6;
          color: #475569;
        }
        .drag-sort-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: grid;
          gap: 12px;
        }
        .drag-sort-item,
        .drag-sort-placeholder {
          border-radius: 16px;
          border: 1px solid #cbd5e1;
          background: #ffffff;
          min-height: 84px;
          display: grid;
          grid-template-columns: auto 1fr auto;
          gap: 16px;
          align-items: center;
          padding: 16px 18px;
          box-sizing: border-box;
          transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }
        .drag-sort-item:hover {
          transform: translateY(-1px);
          box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12);
          border-color: #93c5fd;
        }
        .drag-sort-placeholder {
          border: 2px dashed #60a5fa;
          background: rgba(191, 219, 254, 0.35);
        }
        .drag-sort-order {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: #dbeafe;
          color: #1d4ed8;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          flex-shrink: 0;
        }
        .drag-sort-copy {
          min-width: 0;
        }
        .drag-sort-copy h3 {
          margin: 0 0 6px;
          font-size: 18px;
        }
        .drag-sort-copy p {
          margin: 0;
          color: #475569;
          line-height: 1.5;
        }
        .drag-sort-handle {
          border: none;
          width: 44px;
          height: 44px;
          border-radius: 12px;
          background: #eff6ff;
          color: #1d4ed8;
          cursor: grab;
          font-size: 22px;
          font-weight: 700;
        }
        .drag-sort-handle:active {
          cursor: grabbing;
        }
        .drag-sort-ghost {
          position: fixed;
          z-index: 50;
          pointer-events: none;
          opacity: 0.96;
          box-shadow: 0 22px 40px rgba(37, 99, 235, 0.22);
          transform: scale(1.01);
        }
        .drag-sort-footnote {
          margin-top: 18px;
          color: #64748b;
          font-size: 14px;
        }
        @media (max-width: 640px) {
          .drag-sort-root {
            padding: 16px;
          }
          .drag-sort-item,
          .drag-sort-placeholder {
            grid-template-columns: 1fr auto;
          }
          .drag-sort-order {
            display: none;
          }
        }
      `}</style>

      <div className="drag-sort-panel">
        <h1 className="drag-sort-title">Sortable Release Checklist</h1>
        <p className="drag-sort-subtitle">
          Drag any card with mouse or touch to reorder the list. A placeholder marks the drop
          position while the dragged card follows your pointer.
        </p>

        <div ref={containerRef}>
          <ul className="drag-sort-list">
            {projectedItems.map(({ item, isPlaceholder }, index) => {
              if (isPlaceholder && dragState && draggedItem) {
                return (
                  <li key={`placeholder-${item.id}`} className="drag-sort-placeholder" aria-hidden="true">
                    <div className="drag-sort-order">{dragState.targetIndex + 1}</div>
                    <div className="drag-sort-copy">
                      <h3>Drop here</h3>
                      <p>{draggedItem.title}</p>
                    </div>
                    <div />
                  </li>
                );
              }

              return (
                <li key={item.id} className="drag-sort-item">
                  <div className="drag-sort-order">{index + 1}</div>
                  <div className="drag-sort-copy">
                    <h3>{item.title}</h3>
                    <p>{item.detail}</p>
                  </div>
                  <button
                    type="button"
                    className="drag-sort-handle"
                    aria-label={`Drag ${item.title}`}
                    onMouseDown={(event) => startDrag(items.findIndex((entry) => entry.id === item.id), event)}
                    onTouchStart={(event) => startDrag(items.findIndex((entry) => entry.id === item.id), event)}
                  >
                    ≡
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="drag-sort-footnote">
          Current order updates on release, using only mouse and touch events.
        </div>
      </div>

      {dragState && draggedItem ? (
        <div
          className="drag-sort-item drag-sort-ghost"
          style={{
            top: dragState.pointerY - dragState.offsetY,
            left: dragState.containerLeft,
            width: dragState.itemWidth,
          }}
        >
          <div className="drag-sort-order">{dragState.sourceIndex + 1}</div>
          <div className="drag-sort-copy">
            <h3>{draggedItem.title}</h3>
            <p>{draggedItem.detail}</p>
          </div>
          <div />
        </div>
      ) : null}
    </div>
  );
}
