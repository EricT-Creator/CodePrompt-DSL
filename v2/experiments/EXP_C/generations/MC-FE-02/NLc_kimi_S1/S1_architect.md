# MC-FE-02: Virtual Scroll Data Grid - Technical Design Document

## 1. Component Architecture

### Core Components

**VirtualGrid (Root Container)**
- Manages viewport state and scroll position
- Coordinates between header and body
- Calculates visible row range

**GridHeader**
- Fixed header row with sortable column headers
- Handles click events for sorting
- Displays sort direction indicators

**GridBody**
- Virtualized scroll container
- Renders only visible rows
- Handles scroll events for range recalculation

**GridRow**
- Single row representation
- Receives row data and column definitions
- Optimized for minimal re-renders

**GridCell**
- Individual cell component
- Formats cell content based on column type

### Component Relationships
```
VirtualGrid
├── GridHeader (fixed)
│   ├── ColumnHeader (×N, sortable)
│   └── SortIndicator
├── GridBody (scrollable)
│   ├── Spacer (top)
│   ├── GridRow (visible only)
│   │   └── GridCell (×N)
│   └── Spacer (bottom)
└── FilterInput
```

## 2. Virtual Scrolling Algorithm

### Visible Range Calculation

**Key Parameters:**
- `ROW_HEIGHT`: Fixed row height in pixels (e.g., 40px)
- `OVERSCAN`: Number of extra rows to render above/below viewport (e.g., 5)
- `TOTAL_ROWS`: 10,000

**Calculation Logic:**
```typescript
interface VisibleRange {
  startIndex: number;
  endIndex: number;
  offsetY: number;
}

const calculateVisibleRange = (
  scrollTop: number,
  viewportHeight: number,
  rowHeight: number,
  totalRows: number,
  overscan: number
): VisibleRange => {
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const visibleCount = Math.ceil(viewportHeight / rowHeight);
  const endIndex = Math.min(
    totalRows - 1,
    startIndex + visibleCount + overscan * 2
  );
  const offsetY = startIndex * rowHeight;
  
  return { startIndex, endIndex, offsetY };
};
```

### Scroll Event Handling

**Throttled Scroll Handler:**
- Use `requestAnimationFrame` for smooth updates
- Debounce rapid scroll events (16ms threshold)
- Update visible range state only when crossing row boundaries

**Smooth Scrolling Optimization:**
- CSS `will-change: transform` on row container
- Transform-based positioning instead of top margin
- Passive event listeners: `{ passive: true }`

### Spacer Strategy

**Total Height Calculation:**
- Top spacer height: `startIndex * ROW_HEIGHT`
- Bottom spacer height: `(TOTAL_ROWS - endIndex - 1) * ROW_HEIGHT`
- Maintains correct scrollbar position and total scrollable area

## 3. Data Model

```typescript
interface Column {
  key: string;
  title: string;
  width: number;
  sortable: boolean;
  dataType: 'string' | 'number' | 'date';
  formatter?: (value: unknown) => string;
}

interface Row {
  id: string | number;
  [key: string]: unknown;
}

interface GridState {
  data: Row[];
  filteredData: Row[];
  sortedData: Row[];
  visibleRange: VisibleRange;
  sortConfig: {
    key: string | null;
    direction: 'asc' | 'desc' | null;
  };
  filterText: string;
  scrollTop: number;
}

interface GridProps {
  columns: Column[];
  rowHeight: number;
  overscan: number;
  viewportHeight: number;
}

// Mock data structure
interface MockDataRow {
  id: number;
  name: string;
  email: string;
  age: number;
  department: string;
  salary: number;
  joinDate: string;
}
```

## 4. Sort and Filter Approach

### Sorting Implementation

**Sort Algorithm:**
- Use native `Array.prototype.sort()` with comparator
- Memoize sorted results to avoid re-sorting unchanged data
- Support multi-type comparison (string localeCompare, number subtraction)

**Sort State Management:**
```typescript
type SortDirection = 'asc' | 'desc' | null;

interface SortConfig {
  key: string | null;
  direction: SortDirection;
}

// Toggle logic: null -> asc -> desc -> null
const toggleSort = (current: SortConfig, key: string): SortConfig => {
  if (current.key !== key) {
    return { key, direction: 'asc' };
  }
  const next: Record<SortDirection, SortDirection> = {
    asc: 'desc',
    desc: null,
    null: 'asc'
  };
  return { key, direction: next[current.direction] };
};
```

### Filtering Implementation

**Search Strategy:**
- Case-insensitive substring matching
- Search across all string/numeric columns
- Debounce input (300ms) to avoid excessive filtering

**Filter Function:**
```typescript
const filterRows = (rows: Row[], filterText: string): Row[] => {
  if (!filterText.trim()) return rows;
  const searchLower = filterText.toLowerCase();
  return rows.filter(row =>
    Object.values(row).some(value =>
      String(value).toLowerCase().includes(searchLower)
    )
  );
};
```

### Combined Data Pipeline

```
Raw Data (10,000)
    ↓
Filter (search text) → Filtered Data
    ↓
Sort (column + direction) → Sorted Data
    ↓
Virtual Slice (visible range) → Rendered Rows
```

## 5. Constraint Acknowledgment

### TS + React
**Addressed by:** All components use TypeScript interfaces for props and state. React functional components with proper typing throughout.

### Manual virtual scroll, no react-window
**Addressed by:** Custom implementation using scroll position math and spacer elements. No react-window, react-virtualized, or similar libraries. Direct DOM scroll event handling.

### CSS Modules, no Tailwind/inline
**Addressed by:** All styles in `.module.css` files. No Tailwind utility classes. No inline styles except dynamic positioning values (transform/height) which are necessary for virtualization.

### No external deps
**Addressed by:** Only React and TypeScript as dependencies. No additional npm packages for grid functionality.

### Single file, export default
**Addressed by:** All component code in single `.tsx` file with `export default VirtualGrid`. Helper functions and types co-located in same file.

### Inline mock data
**Addressed by:** Mock data array defined as constant in the same file using a generator function. 10,000 rows created programmatically with varied data.
