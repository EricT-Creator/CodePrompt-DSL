# MC-FE-02: Virtual Scroll Data Grid - Technical Design

## Overview

This document outlines the technical design for a high-performance virtual scroll data grid capable of rendering 10,000 rows with smooth scrolling, fixed headers, sortable columns, and search/filter functionality.

## 1. Component Architecture

### Main Component Structure

```
VirtualDataGrid (Main Container)
├── GridHeader (Fixed header row)
│   ├── HeaderCell × N (Sortable column headers)
│   └── Resizer handles (optional)
├── FilterBar
│   └── SearchInput (Filter by text)
├── ScrollContainer (Scrollable viewport)
│   └── Spacer (Total height placeholder)
│       └── VisibleRowsContainer (Absolute positioned)
│           └── Row × visibleCount
│               └── Cell × columnCount
└── StatusBar (Row count, filter status)
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `VirtualDataGrid` | State management, scroll handling, virtual range calculation |
| `GridHeader` | Fixed header rendering, sort indicator display |
| `HeaderCell` | Click handling for sort, sort direction indicator |
| `ScrollContainer` | Scroll event listener, viewport measurement |
| `Row` | Single row rendering with cell data |
| `FilterBar` | Search input, filter state management |

## 2. Virtual Scrolling Algorithm

### Visible Range Calculation

**Constants:**
```typescript
const ROW_HEIGHT = 40; // pixels per row
const OVERSCAN = 5;    // extra rows to render above/below viewport
```

**Calculation Steps:**

1. **Measure viewport**: Get container height via ref
2. **Calculate visible row count**: `Math.ceil(viewportHeight / ROW_HEIGHT)`
3. **Determine scroll position**: Read `scrollTop` from container
4. **Calculate start index**: `Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN`
5. **Calculate end index**: `startIndex + visibleCount + OVERSCAN * 2`
6. **Clamp indices**: Ensure within bounds `[0, totalRows)`

### Spacer Strategy

```typescript
// Total scrollable height
const totalHeight = data.length * ROW_HEIGHT;

// Visible rows offset from top
const offsetY = startIndex * ROW_HEIGHT;

// Render structure
<div style={{ height: totalHeight, position: 'relative' }}>
  <div style={{ transform: `translateY(${offsetY}px)` }}>
    {visibleRows.map(row => <Row data={row} />)}
  </div>
</div>
```

### Scroll Event Handling

**Throttling Strategy:**
- Use `requestAnimationFrame` to batch scroll updates
- Store scroll position in ref (not state) to avoid re-renders
- Update visible range state only when row indices change

```typescript
const handleScroll = () => {
  if (rafId.current) return;
  rafId.current = requestAnimationFrame(() => {
    calculateVisibleRange();
    rafId.current = null;
  });
};
```

## 3. Data Model

### TypeScript Interfaces

```typescript
interface GridColumn {
  key: string;
  title: string;
  width?: number;
  sortable: boolean;
}

interface GridRow {
  id: string | number;
  [key: string]: any;
}

interface GridState {
  data: GridRow[];
  filteredData: GridRow[];
  sortConfig: {
    key: string | null;
    direction: 'asc' | 'desc' | null;
  };
  filterText: string;
  scrollTop: number;
  viewportHeight: number;
}

interface VirtualRange {
  startIndex: number;
  endIndex: number;
  visibleCount: number;
}
```

### Mock Data Generation

```typescript
const generateMockData = (count: number): GridRow[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    name: `User ${i}`,
    email: `user${i}@example.com`,
    role: ['Admin', 'User', 'Editor'][i % 3],
    status: ['Active', 'Inactive'][i % 2],
    createdAt: new Date(2020 + (i % 4), (i % 12), (i % 28) + 1).toISOString(),
  }));
};
```

## 4. Sort and Filter Approach

### Sorting Implementation

**Algorithm:**
```typescript
const sortData = (data: GridRow[], key: string, direction: 'asc' | 'desc'): GridRow[] => {
  return [...data].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];
    
    if (aVal < bVal) return direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return direction === 'asc' ? 1 : -1;
    return 0;
  });
};
```

**Sort Toggle Logic:**
- First click: ascending
- Second click: descending
- Third click: clear sort

### Filtering Implementation

**Search Strategy:**
```typescript
const filterData = (data: GridRow[], filterText: string): GridRow[] => {
  if (!filterText.trim()) return data;
  
  const lowerFilter = filterText.toLowerCase();
  return data.filter(row =>
    Object.values(row).some(val =>
      String(val).toLowerCase().includes(lowerFilter)
    )
  );
};
```

**Debounce:**
- Apply 150ms debounce to filter input
- Prevent excessive re-filtering on every keystroke

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **TypeScript + React** | All types defined via interfaces; generic GridRow allows flexible data shapes |
| **Manual virtual scrolling** | Implement custom visible range calculation using scrollTop and row height; no react-window or react-virtualized |
| **CSS Modules** | Create `VirtualDataGrid.module.css` with all styles scoped; no Tailwind or inline styles |
| **No external npm packages** | Only React and TypeScript as dependencies; all utilities (sort, filter) implemented manually |
| **Single .tsx file** | All components, types, and mock data in one file with `export default VirtualDataGrid` |
| **Inline mock data** | `generateMockData()` function creates 10,000 rows at initialization; no external imports |

## Summary

This design achieves smooth scrolling for 10,000 rows through a custom virtual scrolling implementation. By calculating visible indices based on scroll position and row height, only ~20 rows are rendered at any time regardless of total data size. The manual approach avoids external windowing libraries while maintaining 60fps scrolling performance through requestAnimationFrame throttling and efficient React rendering patterns.
