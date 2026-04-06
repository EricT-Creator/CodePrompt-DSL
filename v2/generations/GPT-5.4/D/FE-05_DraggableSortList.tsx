import React, { useEffect, useMemo, useRef, useState } from "react";

type Item = {
  id: number;
  label: string;
  detail: string;
};

const initialItems: Item[] = [
  { id: 1, label: "需求梳理", detail: "明确范围与验收标准" },
  { id: 2, label: "界面设计", detail: "完成交互原型与视觉层级" },
  { id: 3, label: "接口联调", detail: "串联数据流与错误处理" },
  { id: 4, label: "质量检查", detail: "验证边界条件与兼容性" },
  { id: 5, label: "发布准备", detail: "整理文档并确认上线清单" },
  { id: 6, label: "复盘优化", detail: "记录问题与后续行动" },
];

function reorderList<T>(list: T[], from: number, to: number): T[] {
  const next = [...list];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

export default function DraggableSortList() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [targetIndex, setTargetIndex] = useState<number | null>(null);
  const [pointerY, setPointerY] = useState(0);
  const [grabOffsetY, setGrabOffsetY] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const activeItem = dragIndex === null ? null : items[dragIndex];

  const activeOffset = useMemo(() => {
    if (dragIndex === null || !activeItem) {
      return 0;
    }
    const element = itemRefs.current[activeItem.id];
    if (!element) {
      return 0;
    }
    return pointerY - grabOffsetY - element.offsetTop;
  }, [activeItem, dragIndex, grabOffsetY, pointerY]);

  useEffect(() => {
    if (dragIndex === null) {
      return;
    }

    const updateTarget = (clientY: number) => {
      const metrics = items
        .map((item, index) => ({ index, element: itemRefs.current[item.id] }))
        .filter(
          (entry): entry is { index: number; element: HTMLDivElement } =>
            entry.element instanceof HTMLDivElement,
        );

      if (metrics.length === 0) {
        setTargetIndex(dragIndex);
        return;
      }

      let nextTarget = metrics[metrics.length - 1].index;
      for (const entry of metrics) {
        const rect = entry.element.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        if (clientY < midpoint) {
          nextTarget = entry.index;
          break;
        }
      }
      setTargetIndex(nextTarget);
    };

    const handleMouseMove = (event: MouseEvent) => {
      setPointerY(event.clientY);
      updateTarget(event.clientY);
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (event.touches.length === 0) {
        return;
      }
      event.preventDefault();
      const clientY = event.touches[0].clientY;
      setPointerY(clientY);
      updateTarget(clientY);
    };

    const handleEnd = () => {
      document.body.style.userSelect = "";
      setItems((current) => {
        if (dragIndex === null || targetIndex === null) {
          return current;
        }
        if (dragIndex === targetIndex) {
          return current;
        }
        return reorderList(current, dragIndex, targetIndex);
      });
      setDragIndex(null);
      setTargetIndex(null);
      setGrabOffsetY(0);
      setPointerY(0);
    };

    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleEnd);
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", handleEnd);
    window.addEventListener("touchcancel", handleEnd);

    return () => {
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleEnd);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleEnd);
      window.removeEventListener("touchcancel", handleEnd);
    };
  }, [dragIndex, items, targetIndex]);

  const beginDrag = (
    index: number,
    clientY: number,
    element: HTMLDivElement,
  ) => {
    const rect = element.getBoundingClientRect();
    setDragIndex(index);
    setTargetIndex(index);
    setPointerY(clientY);
    setGrabOffsetY(clientY - rect.top);
  };

  const css = `
    * {
      box-sizing: border-box;
    }

    .dsl-sort-page {
      min-height: 100vh;
      padding: 32px 16px;
      background: linear-gradient(180deg, #f5f7fb 0%, #eef2ff 100%);
      font-family: Arial, Helvetica, sans-serif;
      color: #172033;
    }

    .dsl-sort-shell {
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 24px;
      border: 1px solid #d8e1f2;
      box-shadow: 0 24px 60px rgba(27, 39, 94, 0.12);
      overflow: hidden;
    }

    .dsl-sort-header {
      padding: 24px 24px 12px;
      border-bottom: 1px solid #e7ecf6;
    }

    .dsl-sort-title {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
    }

    .dsl-sort-subtitle {
      margin: 10px 0 0;
      color: #5d6b85;
      line-height: 1.6;
    }

    .dsl-sort-list {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .dsl-sort-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 18px 18px 18px 14px;
      border-radius: 18px;
      border: 1px solid #dbe3f3;
      background: #ffffff;
      transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease, background-color 0.16s ease;
      cursor: grab;
      touch-action: none;
      position: relative;
    }

    .dsl-sort-item:hover {
      border-color: #9ab0f5;
      box-shadow: 0 12px 24px rgba(62, 92, 198, 0.12);
    }

    .dsl-sort-item--dragging {
      z-index: 3;
      box-shadow: 0 22px 42px rgba(62, 92, 198, 0.22);
      border-color: #4966f0;
      background: #f5f8ff;
      cursor: grabbing;
    }

    .dsl-sort-item--target {
      border-color: #4966f0;
      background: #eef3ff;
    }

    .dsl-sort-handle {
      width: 42px;
      height: 42px;
      border-radius: 14px;
      border: 1px solid #cdd7ee;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #4c5f84;
      background: #f7f9fc;
      font-size: 20px;
      flex-shrink: 0;
    }

    .dsl-sort-content {
      flex: 1;
      min-width: 0;
    }

    .dsl-sort-label {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
    }

    .dsl-sort-detail {
      margin: 6px 0 0;
      color: #5b6882;
      line-height: 1.5;
    }

    .dsl-sort-index {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: #edf2ff;
      color: #3450d8;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .dsl-sort-footer {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      border-top: 1px solid #e7ecf6;
      padding: 18px 24px 24px;
      flex-wrap: wrap;
      color: #596985;
    }

    .dsl-sort-order {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .dsl-sort-chip {
      padding: 8px 12px;
      border-radius: 999px;
      background: #f2f5fb;
      border: 1px solid #d8e1f2;
      font-size: 13px;
      color: #33425f;
    }
  `;

  return (
    <div className="dsl-sort-page">
      <style>{css}</style>
      <div className="dsl-sort-shell" ref={containerRef}>
        <div className="dsl-sort-header">
          <h1 className="dsl-sort-title">拖拽排序列表</h1>
          <p className="dsl-sort-subtitle">
            按住任意卡片并拖动，支持鼠标与触摸操作。放开后会立即更新任务顺序，并在拖动过程中高亮目标位置。
          </p>
        </div>

        <div className="dsl-sort-list">
          {items.map((item, index) => {
            const isDragging = dragIndex === index;
            const isTarget = !isDragging && targetIndex === index;

            return (
              <div
                key={item.id}
                ref={(node) => {
                  itemRefs.current[item.id] = node;
                }}
                className={[
                  "dsl-sort-item",
                  isDragging ? "dsl-sort-item--dragging" : "",
                  isTarget ? "dsl-sort-item--target" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onMouseDown={(event) => beginDrag(index, event.clientY, event.currentTarget)}
                onTouchStart={(event) => {
                  if (event.touches.length > 0) {
                    beginDrag(index, event.touches[0].clientY, event.currentTarget);
                  }
                }}
                style={
                  isDragging
                    ? {
                        transform: `translateY(${activeOffset}px) scale(1.02)`,
                      }
                    : undefined
                }
              >
                <div className="dsl-sort-handle" aria-hidden="true">
                  ≡
                </div>
                <div className="dsl-sort-content">
                  <p className="dsl-sort-label">{item.label}</p>
                  <p className="dsl-sort-detail">{item.detail}</p>
                </div>
                <div className="dsl-sort-index">{index + 1}</div>
              </div>
            );
          })}
        </div>

        <div className="dsl-sort-footer">
          <span>当前顺序</span>
          <div className="dsl-sort-order">
            {items.map((item) => (
              <span key={item.id} className="dsl-sort-chip">
                {item.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
