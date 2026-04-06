# Technical Design Document: Virtual Scroll Data Grid

**Task**: MC-FE-02  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]TS [F]React [!D]NO_VIRT_LIB [SCROLL]MANUAL [Y]CSS_MODULES [!Y]NO_TW_INLINE [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [DT]INLINE_MOCK`

---

## 1. Component Architecture

### Top-Level Component: `DataGrid`
Single Functional Component (SFC) exported as default. Manages scroll state, virtual window calculation, sorting, and filtering.

**Internal Sub-components**:

| Component | Responsibility |
|-----------|---------------|
| `GridHeader` | Renders fixed column headers. Each header cell is clickable for sort toggling (asc → desc → none). |
| `SearchBar` | Text input that updates the filter string. Debounced to avoid excessive re-renders. |
| `VirtualBody` | The scrollable container. Renders only the visible rows plus a small overscan buffer. Manages the sentinel `div` elements for total height. |
| `GridRow` | Renders a single data row with cells aligned to header columns. |

### Rendering Tree

```
DataGrid
├── SearchBar
├── GridHeader (position: sticky)
└── VirtualBody (overflow-y: auto, fixed height)
    ├── div.spacerTop (height = startIndex × rowHeight)
    ├── GridRow × visibleCount
    └── div.spacerBottom (height = remaining × rowHeight)
```

---

## 2. Virtual Scrolling Algorithm

### Core Principle: Fixed Row Height

Each row has a constant height (`ROW_HEIGHT = 36px`). This makes offset calculation O(1).

### Visible Range Calculation

```
scrollTop = container.scrollTop
startIndex = Math.floor(scrollTop / ROW_HEIGHT)
endIndex = Math.min(startIndex + Math.ceil(containerHeight / ROW_HEIGHT) + OVERSCAN, totalRows - 1)
visibleRows = filteredSortedData.slice(startIndex, endIndex + 1)
```

- **OVERSCAN**: Extra rows rendered above and below the viewport (default: 5) to prevent blank flashes during fast scrolling.
- **Total height**: A wrapper div has `height = totalRows × ROW_HEIGHT` to produce a native scrollbar of accurate proportion.
- **Spacer divs**: Top spacer (`startIndex × ROW_HEIGHT`) and bottom spacer (`(totalRows - endIndex - 1) × ROW_HEIGHT`) push visible rows into the correct scroll position.

### Scroll Event Handling

- `onScroll` handler on `VirtualBody` reads `scrollTop` and recalculates `startIndex` / `endIndex`.
- Uses `requestAnimationFrame` gating to throttle recalculations and prevent layout thrashing.
- State update is via `useState` for scroll position (since this is UI-only state, not domain state).

### Flicker Prevention

- Overscan buffer ensures rows are pre-rendered before they enter the viewport.
- `will-change: transform` on the row container hints the browser to composite on GPU.
- Rows are keyed by data `id`, not index, to avoid unnecessary DOM reconciliation.

---

## 3. Data Model (TypeScript Interfaces)

```
interface DataRow {
  id: number;
  name: string;
  email: string;
  department: string;
  salary: number;
  joinDate: string;   // ISO date string
}

interface ColumnDef {
  key: keyof DataRow;
  label: string;
  width: number;       // px
  sortable: boolean;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortState {
  column: keyof DataRow | null;
  direction: SortDirection;
}

interface GridState {
  data: DataRow[];            // full 10,000 rows (inline mock)
  filterText: string;
  sort: SortState;
  scrollTop: number;
}
```

### Inline Mock Data Generation

A factory function generates 10,000 `DataRow` objects at module scope using deterministic patterns (e.g., `name: "User_${i}"`, `salary: 30000 + (i * 7) % 70000`). No external data source or fetch call.

---

## 4. Sort and Filter Approach

### Filtering

- `filterText` is applied as a case-insensitive substring match against the `name` and `email` fields.
- Filtering runs on every keystroke (debounced by 150ms).
- Result: `filteredData = data.filter(row => row.name.includes(text) || row.email.includes(text))`.
- `useMemo` caches `filteredData` with `[data, filterText]` as dependencies.

### Sorting

- Click on a sortable column header cycles: `null → 'asc' → 'desc' → null`.
- Sort comparator is generic: numeric comparison for `salary`/`id`, string `localeCompare` for `name`/`email`/`department`, date string comparison for `joinDate`.
- `sortedData = useMemo(() => [...filteredData].sort(comparator), [filteredData, sort])`.
- Sorting happens after filtering to reduce sort input size.

### Pipeline

```
Raw Data (10,000) → Filter → Sorted Data → Virtual Slice → Rendered Rows
```

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: TypeScript | `[L]TS` | Full TypeScript typing for all interfaces, props, state, and event handlers. |
| Framework: React | `[F]React` | Built with React functional components and hooks (`useState`, `useMemo`, `useCallback`, `useRef`). |
| No virtual scroll library | `[!D]NO_VIRT_LIB` | No react-window, react-virtualized, or tanstack-virtual. Scroll virtualization is hand-implemented. |
| Manual scroll implementation | `[SCROLL]MANUAL` | Visible range calculated from `scrollTop`, `containerHeight`, and `ROW_HEIGHT`. Spacer divs maintain scroll position. |
| Styling: CSS Modules | `[Y]CSS_MODULES` | All grid styles (header, rows, cells, scrollbar area) use `.module.css` with scoped class names. |
| No Tailwind / inline styles | `[!Y]NO_TW_INLINE` | Zero Tailwind utility classes. No inline `style` attributes except dynamic height/transform for spacers (required for virtualization). |
| No external dependencies | `[D]NO_EXTERNAL` | Only React and TypeScript. No lodash, no data libraries. Debounce implemented with `setTimeout`. |
| Single Functional Component | `[O]SFC` | `DataGrid` is the sole exported component. All sub-components are internal. |
| Default export | `[EXP]DEFAULT` | `export default function DataGrid() {...}` |
| Inline mock data | `[DT]INLINE_MOCK` | 10,000 rows generated inline via a factory function. No fetch, no JSON import. |
