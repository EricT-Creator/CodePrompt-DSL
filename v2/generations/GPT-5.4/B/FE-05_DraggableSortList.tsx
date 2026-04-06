import React, { useEffect, useMemo, useRef, useState } from "react";

type Item = {
  id: string;
  title: string;
  detail: string;
};

type DragState = {
  draggedIndex: number;
  placeholderIndex: number;
  ghostX: number;
  ghostY: number;
  pointerOffsetX: number;
  pointerOffsetY: number;
  itemWidth: number;
  itemHeight: number;
};

const initialItems: Item[] = [
  { id: "1", title: "整理研究笔记", detail: "归档本周实验观察与异常案例" },
  { id: "2", title: "补跑缺失任务", detail: "完成中断导致的剩余生成任务" },
  { id: "3", title: "检查约束遵循", detail: "确认无第三方库与输出格式正确" },
  { id: "4", title: "复核代码完整性", detail: "确保每个文件可独立运行或编译" },
  { id: "5", title: "记录交叉审查", detail: "准备后续审查所需的产物目录" },
  { id: "6", title: "更新实验结论", detail: "把新观察纳入下一轮分析" },
];

const styles = `
  .drag-sort-page {
    min-height: 100vh;
    background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
    padding: 32px 16px;
    box-sizing: border-box;
    font-family: Arial, Helvetica, sans-serif;
    color: #1e293b;
  }

  .drag-sort-shell {
    max-width: 760px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid #dbeafe;
    border-radius: 20px;
    box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
    overflow: hidden;
  }

  .drag-sort-header {
    padding: 24px 24px 14px;
    border-bottom: 1px solid #e2e8f0;
  }

  .drag-sort-title {
    margin: 0 0 8px;
    font-size: 28px;
    font-weight: 700;
  }

  .drag-sort-subtitle {
    margin: 0;
    color: #475569;
    line-height: 1.6;
    font-size: 14px;
  }

  .drag-sort-list {
    list-style: none;
    margin: 0;
    padding: 18px;
    position: relative;
  }

  .drag-sort-item,
  .drag-sort-placeholder {
    border-radius: 16px;
    margin-bottom: 12px;
  }

  .drag-sort-item {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    cursor: grab;
    transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
    touch-action: none;
  }

  .drag-sort-item:hover {
    transform: translateY(-1px);
    border-color: #60a5fa;
    box-shadow: 0 10px 18px rgba(59, 130, 246, 0.12);
  }

  .drag-sort-item.dragging-source {
    opacity: 0.35;
    border-style: dashed;
  }

  .drag-handle {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    border: none;
    background: #dbeafe;
    color: #1d4ed8;
    font-size: 20px;
    font-weight: 700;
    cursor: grab;
    flex: 0 0 auto;
  }

  .drag-content {
    flex: 1;
    min-width: 0;
  }

  .drag-item-title {
    margin: 0 0 6px;
    font-size: 17px;
    font-weight: 700;
  }

  .drag-item-detail {
    margin: 0;
    font-size: 14px;
    line-height: 1.5;
    color: #64748b;
  }

  .drag-badge {
    flex: 0 0 auto;
    min-width: 32px;
    height: 32px;
    border-radius: 999px;
    background: #eff6ff;
    color: #1d4ed8;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
  }

  .drag-sort-placeholder {
    border: 2px dashed #3b82f6;
    background: rgba(59, 130, 246, 0.07);
    position: relative;
  }

  .drag-sort-placeholder::before {
    content: "Drop here";
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 13px;
    font-weight: 700;
    color: #2563eb;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .drag-ghost {
    position: fixed;
    z-index: 999;
    pointer-events: none;
    padding: 16px 18px;
    border-radius: 16px;
    border: 1px solid #60a5fa;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 24px 48px rgba(37, 99, 235, 0.2);
    display: flex;
    align-items: center;
    gap: 14px;
    box-sizing: border-box;
  }

  .drag-sort-footer {
    padding: 0 24px 24px;
    color: #475569;
    font-size: 13px;
    line-height: 1.6;
  }

  @media (max-width: 640px) {
    .drag-sort-header {
      padding: 20px 18px 12px;
    }

    .drag-sort-title {
      font-size: 24px;
    }

    .drag-sort-list {
      padding: 14px;
    }

    .drag-sort-item,
    .drag-ghost {
      gap: 12px;
      padding: 14px;
    }
  }
`;

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function getPoint(event: MouseEvent | TouchEvent | React.MouseEvent | React.TouchEvent) {
  if ("touches" in event) {
    const touch = event.touches[0] ?? event.changedTouches[0];
    return { x: touch.clientX, y: touch.clientY };
  }

  return { x: event.clientX, y: event.clientY };
}

function moveItem<T>(list: T[], fromIndex: number, toIndex: number) {
  const next = list.slice();
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const itemRefs = useRef<Record<string, HTMLLIElement | null>>({});

  const draggedItem = useMemo(() => {
    if (!dragState) {
      return null;
    }
    return items[dragState.draggedIndex] ?? null;
  }, [dragState, items]);

  useEffect(() => {
    if (!dragState) {
      return;
    }

    const handleMove = (event: MouseEvent | TouchEvent) => {
      if ("touches" in event) {
        event.preventDefault();
      }

      const point = getPoint(event);
      const draggedId = items[dragState.draggedIndex]?.id;
      const candidateElements = items
        .filter((item) => item.id !== draggedId)
        .map((item) => itemRefs.current[item.id])
        .filter((node): node is HTMLLIElement => Boolean(node));

      let placeholderIndex = candidateElements.length;

      for (let index = 0; index < candidateElements.length; index += 1) {
        const rect = candidateElements[index].getBoundingClientRect();
        if (point.y < rect.top + rect.height / 2) {
          placeholderIndex = index;
          break;
        }
      }

      setDragState((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          ghostX: point.x - prev.pointerOffsetX,
          ghostY: point.y - prev.pointerOffsetY,
          placeholderIndex,
        };
      });
    };

    const handleEnd = () => {
      setItems((currentItems) => {
        if (!dragState) {
          return currentItems;
        }

        const safeTarget = clamp(
          dragState.placeholderIndex > dragState.draggedIndex
            ? dragState.placeholderIndex - 1
            : dragState.placeholderIndex,
          0,
          currentItems.length - 1,
        );

        return moveItem(currentItems, dragState.draggedIndex, safeTarget);
      });

      setDragState(null);
    };

    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleEnd);
    window.addEventListener("touchmove", handleMove, { passive: false });
    window.addEventListener("touchend", handleEnd);
    window.addEventListener("touchcancel", handleEnd);

    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleEnd);
      window.removeEventListener("touchmove", handleMove);
      window.removeEventListener("touchend", handleEnd);
      window.removeEventListener("touchcancel", handleEnd);
    };
  }, [dragState, items]);

  const startDrag = (
    index: number,
    event: React.MouseEvent<HTMLLIElement> | React.TouchEvent<HTMLLIElement>,
  ) => {
    event.preventDefault();

    const point = getPoint(event);
    const element = itemRefs.current[items[index].id];
    if (!element) {
      return;
    }

    const rect = element.getBoundingClientRect();
    setDragState({
      draggedIndex: index,
      placeholderIndex: index,
      ghostX: rect.left,
      ghostY: rect.top,
      pointerOffsetX: point.x - rect.left,
      pointerOffsetY: point.y - rect.top,
      itemWidth: rect.width,
      itemHeight: rect.height,
    });
  };

  const renderedList = useMemo(() => {
    if (!dragState) {
      return items;
    }

    return items.filter((_, index) => index !== dragState.draggedIndex);
  }, [dragState, items]);

  return (
    <div className="drag-sort-page">
      <style>{styles}</style>
      <div className="drag-sort-shell">
        <div className="drag-sort-header">
          <h1 className="drag-sort-title">Draggable Sort List</h1>
          <p className="drag-sort-subtitle">
            Use mouse or touch to reorder the list. The dragged card becomes a ghost, and the dashed
            placeholder shows the drop target in real time.
          </p>
        </div>

        <ul className="drag-sort-list">
          {renderedList.map((item, filteredIndex) => {
            const originalIndex = items.findIndex((candidate) => candidate.id === item.id);
            const showPlaceholder = dragState && dragState.placeholderIndex === filteredIndex;

            return (
              <React.Fragment key={item.id}>
                {showPlaceholder ? (
                  <li
                    className="drag-sort-placeholder"
                    style={{ height: dragState.itemHeight }}
                    aria-hidden="true"
                  />
                ) : null}
                <li
                  ref={(node) => {
                    itemRefs.current[item.id] = node;
                  }}
                  className={`drag-sort-item ${
                    dragState && dragState.draggedIndex === originalIndex ? "dragging-source" : ""
                  }`}
                  onMouseDown={(event) => startDrag(originalIndex, event)}
                  onTouchStart={(event) => startDrag(originalIndex, event)}
                >
                  <button type="button" className="drag-handle" aria-label={`Drag ${item.title}`}>
                    ≡
                  </button>
                  <div className="drag-content">
                    <h2 className="drag-item-title">{item.title}</h2>
                    <p className="drag-item-detail">{item.detail}</p>
                  </div>
                  <span className="drag-badge">{originalIndex + 1}</span>
                </li>
              </React.Fragment>
            );
          })}

          {dragState && dragState.placeholderIndex >= renderedList.length ? (
            <li
              className="drag-sort-placeholder"
              style={{ height: dragState.itemHeight }}
              aria-hidden="true"
            />
          ) : null}
        </ul>

        <div className="drag-sort-footer">
          Current order updates immediately after drop. This implementation uses only mouse and touch
          events, without the HTML5 drag-and-drop API.
        </div>
      </div>

      {dragState && draggedItem ? (
        <div
          className="drag-ghost"
          style={{
            top: dragState.ghostY,
            left: dragState.ghostX,
            width: dragState.itemWidth,
            height: dragState.itemHeight,
          }}
        >
          <button type="button" className="drag-handle" aria-hidden="true">
            ≡
          </button>
          <div className="drag-content">
            <h2 className="drag-item-title">{draggedItem.title}</h2>
            <p className="drag-item-detail">{draggedItem.detail}</p>
          </div>
          <span className="drag-badge">{dragState.draggedIndex + 1}</span>
        </div>
      ) : null}
    </div>
  );
}
