import React, { useEffect, useMemo, useRef, useState } from 'react';

const STYLE_ID = 'fe05-draggable-sort-list-styles';
const ITEM_COUNT = 6;

function ensureStyles() {
  if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) {
    return;
  }
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .dsl-drag-list {
      max-width: 560px;
      margin: 32px auto;
      padding: 24px;
      border-radius: 16px;
      background: #ffffff;
      border: 1px solid #d9e2ec;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
      font-family: Arial, Helvetica, sans-serif;
      color: #102a43;
    }
    .dsl-drag-list__title {
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 700;
    }
    .dsl-drag-list__subtitle {
      margin: 0 0 20px;
      font-size: 14px;
      color: #486581;
    }
    .dsl-drag-list__items {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .dsl-drag-list__item {
      display: grid;
      grid-template-columns: 36px 1fr auto;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
      padding: 14px 16px;
      background: #f8fbff;
      border: 1px solid #cbd2d9;
      border-radius: 12px;
      cursor: grab;
      user-select: none;
      transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease, background 160ms ease, opacity 160ms ease;
    }
    .dsl-drag-list__item:last-child {
      margin-bottom: 0;
    }
    .dsl-drag-list__item:hover {
      border-color: #3d5afe;
      box-shadow: 0 10px 24px rgba(61, 90, 254, 0.12);
    }
    .dsl-drag-list__item--dragging {
      opacity: 0.55;
      background: #e9f2ff;
      border-color: #3d5afe;
      box-shadow: 0 16px 28px rgba(61, 90, 254, 0.2);
      cursor: grabbing;
      transform: scale(0.98);
    }
    .dsl-drag-list__item--target {
      border-color: #1f9d55;
      background: #effcf6;
      box-shadow: 0 0 0 2px rgba(31, 157, 85, 0.14);
    }
    .dsl-drag-list__handle {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: #d9e2ec;
      color: #243b53;
      font-size: 18px;
      font-weight: 700;
    }
    .dsl-drag-list__content {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }
    .dsl-drag-list__name {
      font-size: 15px;
      font-weight: 700;
      color: #102a43;
    }
    .dsl-drag-list__meta {
      font-size: 12px;
      color: #627d98;
    }
    .dsl-drag-list__badge {
      padding: 6px 10px;
      border-radius: 999px;
      background: #dbeafe;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 700;
    }
    .dsl-drag-list__status {
      margin-top: 18px;
      padding: 12px 14px;
      border-radius: 10px;
      background: #f0f4f8;
      color: #334e68;
      font-size: 13px;
      line-height: 1.5;
      min-height: 44px;
    }
    .dsl-drag-list__hint {
      margin-top: 14px;
      font-size: 12px;
      color: #829ab1;
    }
  `;
  document.head.appendChild(style);
}

type SortItem = {
  id: string;
  title: string;
  detail: string;
  tag: string;
};

type DragState = {
  activeIndex: number | null;
  overIndex: number | null;
  pointerType: 'mouse' | 'touch' | null;
};

const initialItems: SortItem[] = [
  { id: '1', title: 'Finalize API contract', detail: 'Align frontend and backend response shapes', tag: 'Planning' },
  { id: '2', title: 'Write regression tests', detail: 'Cover pagination and empty-state rendering', tag: 'Quality' },
  { id: '3', title: 'Improve onboarding copy', detail: 'Tighten wording in first-run experience', tag: 'UX' },
  { id: '4', title: 'Profile slow query', detail: 'Inspect the dashboard aggregation path', tag: 'Perf' },
  { id: '5', title: 'Patch auth timeout', detail: 'Retry refresh flow before forced sign-out', tag: 'Bugfix' },
  { id: '6', title: 'Prepare release notes', detail: 'Summarize changes for Friday deployment', tag: 'Release' },
];

function reorderItems(items: SortItem[], fromIndex: number, toIndex: number): SortItem[] {
  if (fromIndex === toIndex) {
    return items;
  }
  const next = [...items];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

export default function DraggableSortList() {
  const [items, setItems] = useState<SortItem[]>(initialItems);
  const [dragState, setDragState] = useState<DragState>({ activeIndex: null, overIndex: null, pointerType: null });
  const itemRefs = useRef<Array<HTMLLIElement | null>>([]);

  useEffect(() => {
    ensureStyles();
  }, []);

  const statusText = useMemo(() => {
    if (dragState.activeIndex === null) {
      return 'Press and drag with mouse or touch to reorder the list. The highlighted row shows the current drop target.';
    }
    const current = items[dragState.activeIndex];
    const target = dragState.overIndex === null ? dragState.activeIndex : dragState.overIndex;
    return `Dragging “${current.title}” with ${dragState.pointerType === 'touch' ? 'touch' : 'mouse'} — drop position ${target + 1} of ${items.length}.`;
  }, [dragState, items]);

  const findClosestIndex = (clientY: number) => {
    for (let index = 0; index < itemRefs.current.length; index += 1) {
      const element = itemRefs.current[index];
      if (!element) {
        continue;
      }
      const rect = element.getBoundingClientRect();
      if (clientY < rect.top + rect.height / 2) {
        return index;
      }
    }
    return items.length - 1;
  };

  const stopDragging = (dropIndex?: number) => {
    setItems((currentItems) => {
      if (dragState.activeIndex === null) {
        return currentItems;
      }
      const finalIndex = dropIndex ?? dragState.overIndex ?? dragState.activeIndex;
      return reorderItems(currentItems, dragState.activeIndex, finalIndex);
    });
    setDragState({ activeIndex: null, overIndex: null, pointerType: null });
  };

  const startDragging = (index: number, pointerType: 'mouse' | 'touch') => {
    setDragState({ activeIndex: index, overIndex: index, pointerType });
  };

  useEffect(() => {
    if (dragState.activeIndex === null) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      event.preventDefault();
      setDragState((current) => {
        if (current.activeIndex === null) {
          return current;
        }
        return { ...current, overIndex: findClosestIndex(event.clientY) };
      });
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (event.touches.length === 0) {
        return;
      }
      event.preventDefault();
      const touch = event.touches[0];
      setDragState((current) => {
        if (current.activeIndex === null) {
          return current;
        }
        return { ...current, overIndex: findClosestIndex(touch.clientY) };
      });
    };

    const handleMouseUp = () => {
      stopDragging();
    };

    const handleTouchEnd = (event: TouchEvent) => {
      const touch = event.changedTouches[0];
      stopDragging(touch ? findClosestIndex(touch.clientY) : undefined);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [dragState.activeIndex, items.length]);

  return (
    <section className="dsl-drag-list" aria-label="Draggable sort list">
      <h2 className="dsl-drag-list__title">Priority Sort Board</h2>
      <p className="dsl-drag-list__subtitle">Reorder the six tasks using only mouse or touch dragging.</p>
      <ul className="dsl-drag-list__items">
        {items.map((item, index) => {
          const isDragging = dragState.activeIndex === index;
          const isTarget = dragState.activeIndex !== null && dragState.overIndex === index && dragState.activeIndex !== index;
          const className = [
            'dsl-drag-list__item',
            isDragging ? 'dsl-drag-list__item--dragging' : '',
            isTarget ? 'dsl-drag-list__item--target' : '',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <li
              key={item.id}
              ref={(node) => {
                itemRefs.current[index] = node;
              }}
              className={className}
              onMouseDown={(event) => {
                event.preventDefault();
                startDragging(index, 'mouse');
              }}
              onTouchStart={(event) => {
                event.preventDefault();
                startDragging(index, 'touch');
              }}
            >
              <span className="dsl-drag-list__handle" aria-hidden="true">≡</span>
              <span className="dsl-drag-list__content">
                <span className="dsl-drag-list__name">{item.title}</span>
                <span className="dsl-drag-list__meta">#{index + 1} · {item.detail}</span>
              </span>
              <span className="dsl-drag-list__badge">{item.tag}</span>
            </li>
          );
        })}
      </ul>
      <div className="dsl-drag-list__status" aria-live="polite">{statusText}</div>
      <div className="dsl-drag-list__hint">Items: {Math.max(items.length, ITEM_COUNT)} · HTML5 drag events are not used.</div>
    </section>
  );
}
