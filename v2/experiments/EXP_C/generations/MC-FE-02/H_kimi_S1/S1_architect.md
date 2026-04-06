# MC-FE-02: Virtual Scroll Data Grid — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Component Architecture

### 1.1 Top-Level Structure
```
DataGrid (Container)
├── GridHeader (title + search input)
├── GridControls (sort buttons)
├── VirtualScrollContainer
│   ├── FixedHeaderRow (column headers)
│   └── ScrollViewport
│       └── VisibleRows (rendered row subset)
└── Scrollbar (custom or native)
```

### 1.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `DataGrid` | State management, data filtering/sorting |
| `GridHeader` | Title display, search input handling |
| `GridControls` | Sort trigger buttons per column |
| `VirtualScrollContainer` | Viewport sizing, scroll event handling |
| `FixedHeaderRow` | Sticky column headers |
| `VisibleRows` | Dynamic row rendering based on scroll position |

---

## 2. Virtual Scrolling Algorithm

### 2.1 Visible Range Calculation

**Constants**:
- `ROW_HEIGHT = 40` (px)
- `OVERSCAN = 5` (buffer rows above/below viewport)
- `CONTAINER_HEIGHT = 400` (px)

**Calculations**:
```
visibleRowCount = Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT)
startIndex = Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN
endIndex = startIndex + visibleRowCount + (OVERSCAN * 2)
visibleRows = allRows.slice(startIndex, endIndex)
```

### 2.2 Total Height Spacer

To maintain scrollbar proportion:
- Render an empty spacer div with `height: totalRows * ROW_HEIGHT`
- Use `position: absolute` for visible rows with `top: index * ROW_HEIGHT`
- This creates the illusion of a full list while only rendering ~20 rows

### 2.3 Scroll Event Handling

- `onScroll` on the viewport container
- Throttle updates to 16ms (60fps)
- Recalculate `startIndex`/`endIndex` on each scroll
- Re-render `VisibleRows` with new slice

---

## 3. Data Model (TypeScript Interfaces)

```typescript
// Row data structure
interface DataRow {
  id: string | number;
  [key: string]: any;  // Dynamic columns
}

// Column definition
interface ColumnDef {
  key: string;
  header: string;
  width?: number;
  sortable: boolean;
}

// Grid state
interface GridState {
  rows: DataRow[];
  columns: ColumnDef[];
  sortColumn: string | null;
  sortDirection: 'asc' | 'desc' | null;
  filterText: string;
  scrollTop: number;
}

// Virtual scroll metrics
interface VirtualMetrics {
  startIndex: number;
  endIndex: number;
  visibleCount: number;
  totalHeight: number;
  offsetY: number;
}
```

---

## 4. Sort and Filter Approach

### 4.1 Sorting

**Trigger**: Click column header

**Algorithm**: JavaScript `Array.prototype.sort()`
```typescript
const sorted = [...rows].sort((a, b) => {
  const valA = a[sortColumn];
  const valB = b[sortColumn];
  const comparison = valA < valB ? -1 : valA > valB ? 1 : 0;
  return sortDirection === 'asc' ? comparison : -comparison;
});
```

### 4.2 Filtering

**Trigger**: Input change in search box

**Algorithm**: Case-insensitive substring match
```typescript
const filtered = rows.filter(row =>
  Object.values(row).some(val =>
    String(val).toLowerCase().includes(filterText.toLowerCase())
  )
);
```

**Performance**: Filter first, then virtual scroll on filtered results

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]TS` | All data structures typed; strict mode |
| `[F]React` | Functional components with hooks |
| `[!D]NO_VIRT_LIB` | Manual virtual scroll implementation |
| `[SCROLL]MANUAL` | Custom scroll handler + visible range math |
| `[Y]CSS_MODULES` | All styling via CSS modules |
| `[!Y]NO_TW_INLINE` | No Tailwind classes; pure CSS |
| `[D]NO_EXTERNAL` | No external dependencies beyond React |
| `[O]SFC` | Single file default export |
| `[EXP]DEFAULT` | `export default DataGrid` |
| `[DT]INLINE_MOCK` | Mock data defined inline in component |

---

## 6. Performance Considerations

### 6.1 Memoization

- `useMemo` for filtered/sorted row arrays
- `useMemo` for virtual metrics calculation
- `React.memo` for row components to prevent unnecessary re-renders

### 6.2 Smooth Scrolling

- CSS `will-change: transform` on row elements
- `transform: translateY()` instead of `top` for GPU acceleration
- Throttled scroll handler (requestAnimationFrame)

---

## 7. File Structure

```
MC-FE-02/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
├── S2_developer/
│   └── DataGrid.tsx
├── DataGrid.module.css
└── types.ts
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
